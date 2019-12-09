# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 - 2017 Pixar
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#
# ##### END MIT LICENSE BLOCK #####
import bpy
import bpy_types
import math
import os
import time
import subprocess
from subprocess import Popen, PIPE
import mathutils
from mathutils import Matrix, Vector, Quaternion
import re
import traceback
import glob

from . import bl_info

from .util import bpy_newer_257
from .util import BlenderVersionError
from .util import rib, rib_path, rib_ob_bounds
from .util import make_frame_path
from .util import init_exporter_env
from .util import get_sequence_path
from .util import user_path
from .util import get_path_list_converted, set_path
from .util import path_list_convert, guess_rmantree, set_pythonpath,\
    set_rmantree
from .util import get_real_path, find_it_path
from .util import debug
from .util import get_Selected_Objects
from .util import get_addon_prefs
from .util import format_seconds_to_hhmmss
from random import randint
import sys
from bpy.app.handlers import persistent

#from .nodes import get_tex_file_name

addon_version = bl_info['version']

rman__sg__inited = False

ipr_handle = None

def init_prman():
    # set pythonpath before importing prman
    set_rmantree(guess_rmantree())
    set_pythonpath(os.path.join(guess_rmantree(), 'bin'))
    it_dir = os.path.dirname(find_it_path()) if find_it_path() else None
    set_path([os.path.join(guess_rmantree(), 'bin'), it_dir])
    pythonbindings = os.path.join(guess_rmantree(), 'bin', 'pythonbindings')
    set_pythonpath(pythonbindings)

    # import RixSceneGraph modules
    try:
        global rman__sg__inited
        global export_sg
        global rman_sg_exporter
        global __is_prman_running__
        global get_texture_list
        global get_texture_list_preview
        from . import export_sg
        from .export_sg import rman_sg_exporter
        from .export_sg import __is_prman_running__
        from .export_sg import get_texture_list, get_texture_list_preview
        rman__sg__inited = export_sg.is_ready()
    except Exception as e:
        print("Could not load scenegraph modules: %s" % str(e)) 

ipr = None


def init():
    pass


def is_ipr_running():
    if ipr is not None and ipr.is_interactive and ipr.is_interactive_ready:
        if ipr.is_prman_running():
            return True
        else:
            # shutdown IPR
            ipr.is_interactive_ready = False
            bpy.ops.lighting.start_interactive('INVOKE_DEFAULT')
            return False
    else:
        return False

def shutdown_ipr():
    global rman__sg__inited
    if ipr is not None and rman__sg__inited:
        if ipr.is_prman_running():
            # shutdown IPR
            ipr.is_interactive_ready = False

            # For some reason bpy.context.window is None
            # So we have to make a copy and pass that on to bpy.ops
            # We're assuming the window we're interested in is the first
            # one in the window_manager
            override = bpy.context.copy()
            window = bpy.context.window_manager.windows[0]
            override['window'] = window
            override['screen'] = window.screen
            #override['selected_bases'] = list(bpy.context.scene.object_bases)
            bpy.ops.lighting.start_interactive(override, 'INVOKE_DEFAULT')

def create(engine, data, depsgraph, region=0, space_data=0, region_data=0):
    # TODO add support for regions (rerendering)
    engine.render_pass = RPass(depsgraph.scene, preview_render=engine.is_preview)


def free(engine):
    if hasattr(engine, 'render_pass'):
        if engine.render_pass.is_interactive and engine.render_pass.is_prman_running():
            engine.render_pass.end_interactive()
        if engine.render_pass:
            del engine.render_pass


def render(engine, depsgraph):
    global rman__sg__inited
    if hasattr(engine, 'render_pass') and engine.render_pass.do_render:
        if engine.is_preview:
            if rman__sg__inited:
                engine.render_pass.render_sg(engine, for_preview=True)            
        else:
            if rman__sg__inited:
                engine.render_pass.render_sg(engine)


def reset(engine, data, depsgraph):
    del engine.render_pass.ri

    engine.render_pass.set_scene(depsgraph.scene)
    engine.render_pass.update_frame_num(depsgraph.scene.frame_current)

def update(engine, data, depsgraph):
    engine.render_pass.update_time = int(time.time())

# assumes you have already set the scene
def start_interactive(engine):
    global rman__sg__inited
    if rman__sg__inited:
        engine.render_pass.start_interactive_sg()

def update_interactive(engine, context):
    engine.render_pass.issue_edits(context)


# update the timestamp on an object
# note that this only logs the active object.  So it might not work say
# if a script updates objects.  We would need to iterate through all objects
@persistent
def update_timestamp(scene):
    active = bpy.context.view_layer.objects.active
    #TODO: fixme
    #if active and (active.is_updated_data or (active.data and active.data.is_updated)):
    #    # mark object for update
    #    now = int(time.time())
    #    active.renderman.update_timestamp = now


class RPass:

    def __init__(self, scene, interactive=False, external_render=False, preview_render=False, bake=False):
        self.rib_done = False
        self.scene = scene
        self.output_files = []
        # set the display driver
        if external_render:
            self.display_driver = scene.renderman.display_driver
        elif preview_render:
            self.display_driver = 'openexr'
        else:
            self.display_driver = 'it' if scene.renderman.render_into == 'it' else 'openexr'

        # pass addon prefs to init_envs
        addon = bpy.context.preferences.addons[__name__.split('.')[0]]
        init_exporter_env(addon.preferences)
        self.initialize_paths(scene)
        self.rm = scene.renderman
        self.external_render = external_render
        self.bake=bake
        self.do_render = (scene.renderman.output_action == 'EXPORT_RENDER')
        self.is_interactive = interactive
        self.is_interactive_ready = False
        self.options = []
        self.depsgraph = None
        self.context = None

        # check if prman is imported
        if not rman__sg__inited:
            init_prman()

        self.edit_num = 0
        self.update_time = None
        self.last_edit_mat = None

    def __del__(self):

        global rman__sg__inited

        if rman__sg__inited:
            if __is_prman_running__():
                rman_sg_exporter().stop_ipr()

    def initialize_paths(self, scene):
        rm = scene.renderman
        self.paths = {}
        self.paths['rman_binary'] = rm.path_renderer
        self.paths['path_texture_optimiser'] = rm.path_texture_optimiser
        self.paths['rmantree'] = rm.path_rmantree

        self.paths['rib_output'] = user_path(rm.path_rib_output, scene=scene)
        self.paths['texture_output'] = user_path(rm.path_texture_output,
                                                 scene=scene)
        rib_dir = os.path.dirname(self.paths['rib_output'])
        self.paths['export_dir'] = user_path(rib_dir, scene=scene)

        if not os.path.exists(self.paths['export_dir']):
            os.makedirs(self.paths['export_dir'])

        addon_prefs = get_addon_prefs()
        self.paths['render_output'] = user_path(addon_prefs.path_display_driver_image,
                                                scene=scene, display_driver=self.display_driver)
        self.paths['aov_output'] = user_path(
            addon_prefs.path_aov_image, scene=scene, display_driver=self.display_driver)
        debug("info", self.paths)
        self.paths['shader'] = [user_path(rm.out_dir, scene=scene)] +\
            get_path_list_converted(rm, 'shader')
        self.paths['rixplugin'] = get_path_list_converted(rm, 'rixplugin')
        self.paths['texture'] = [self.paths['texture_output']]

        temp_archive_name = rm.path_object_archive_static
        static_archive_dir = os.path.dirname(user_path(temp_archive_name,
                                                       scene=scene))
        temp_archive_name = rm.path_object_archive_animated
        frame_archive_dir = os.path.dirname(user_path(temp_archive_name,
                                                      scene=scene))
        self.paths['static_archives'] = static_archive_dir
        self.paths['frame_archives'] = frame_archive_dir

        if not os.path.exists(self.paths['static_archives']):
            os.makedirs(self.paths['static_archives'])
        if not os.path.exists(self.paths['frame_archives']):
            os.makedirs(self.paths['frame_archives'])
        self.paths['archive'] = os.path.dirname(static_archive_dir)

    def update_frame_num(self, num):
        self.scene.frame_set(num)
        self.paths['rib_output'] = user_path(self.scene.renderman.path_rib_output,
                                             scene=self.scene)
        addon_prefs = get_addon_prefs()
        self.paths['render_output'] = user_path(addon_prefs.path_display_driver_image,
                                                scene=self.scene, display_driver=self.display_driver)
        self.paths['aov_output'] = user_path(
            addon_prefs.path_aov_image, scene=self.scene, display_driver=self.display_driver)
        temp_archive_name = self.scene.renderman.path_object_archive_animated
        frame_archive_dir = os.path.dirname(user_path(temp_archive_name,
                                                      scene=self.scene))
        self.paths['frame_archives'] = frame_archive_dir
        if not os.path.exists(self.paths['frame_archives']):
            os.makedirs(self.paths['frame_archives'])

    def preview_render(self, engine):
        render_output = self.paths['render_output']
        images_dir = os.path.split(render_output)[0]
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
        if os.path.exists(render_output):
            try:
                os.remove(render_output)  # so as not to load the old file
            except:
                debug("error", "Unable to remove previous render",
                      render_output)

        def update_image():
            render = self.scene.render
            image_scale = 100.0 / render.resolution_percentage
            result = engine.begin_result(0, 0,
                                         render.resolution_x * image_scale,
                                         render.resolution_y * image_scale)
            lay = result.layers[0]
            # possible the image wont load early on.
            try:
                lay.load_from_file(render_output)
            except:
                pass
            engine.end_result(result)

        # create command and start process
        options = self.options
        prman_executable = os.path.join(self.paths['rmantree'], 'bin',
                                        self.paths['rman_binary'])
        cmd = [prman_executable] + options + ["-t:%d" % self.rm.threads] + \
            [self.paths['rib_output']]
        cdir = os.path.dirname(self.paths['rib_output'])
        environ = os.environ.copy()
        environ['RMANTREE'] = self.paths['rmantree']

        # Launch the command to begin rendering.
        try:
            process = subprocess.Popen(cmd, cwd=cdir, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, env=environ)
            process.communicate()
            update_image()
        except:
            engine.report({"ERROR"},
                          "Problem launching RenderMan from %s." % prman_executable)
            isProblem = True

    def get_denoise_names(self):
        base, ext = self.paths['render_output'].rsplit('.', 1)
        # denoise data has the name .denoise.exr
        return (base + '.variance.' + 'exr', base + '.filtered.' + 'exr')

    def render_sg(self, engine, for_preview=False):
        DELAY = 1
        render_output = self.paths['render_output']
        if for_preview:
            previewdir = os.path.join(self.paths['export_dir'], "preview")
            self.paths['render_output'] = os.path.join(previewdir, "preview.tif") 
            render_output = self.paths['render_output']
                   
        aov_output = self.paths['aov_output']
        cdir = os.path.dirname(self.paths['rib_output'])
        update_frequency = 10 if not self.rm.do_denoise else 60
        rm = self.scene.renderman

        images_dir = os.path.split(render_output)[0]
        aov_dir = os.path.split(aov_output)[0]
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
        if not os.path.exists(aov_dir):
            os.makedirs(aov_dir)
        if os.path.exists(render_output):
            try:
                os.remove(render_output)  # so as not to load the old file
            except:
                debug("error", "Unable to remove previous render",
                      render_output)

        # convert textures
        if for_preview:
            self.convert_textures(get_texture_list_preview(self.scene))
        else:
            self.convert_textures(get_texture_list(self.scene))            

        if self.display_driver == 'it':
            update_frequency = -1
            it_path = find_it_path()
            if not it_path:
                engine.report({"ERROR"},
                              "Could not find 'it'. Install RenderMan Studio \
                              or use a different display driver.")
            else:
                environ = os.environ.copy()
                subprocess.Popen([it_path], env=environ, shell=True)

        # Check if rendering select objects only.
        if rm.render_selected_objects_only:
            visible_objects = get_Selected_Objects(self.scene)
        else:
            visible_objects = None

        def progress_cb(e, d, db):
            engine.update_progress(float(d) / 100.0)

        progress_cb_ptr = progress_cb

        if for_preview:
        #    progress_cb_ptr = None
            # TODO: fix material preview renders
            return

        if not rman_sg_exporter().start_render(visible_objects, self, self.scene, progress_cb_ptr, update_frequency, for_preview):
            return

        if self.display_driver not in ['it']:
            if os.path.exists(render_output):

                render = self.scene.render
                image_scale = 100.0 / render.resolution_percentage
                result = engine.begin_result(0, 0,
                                            render.resolution_x * image_scale,
                                            render.resolution_y * image_scale)
                lay = result.layers[0]
                # possible the image wont load early on.
                try:
                    lay.load_from_file(render_output)
                except:
                    pass
                engine.end_result(result)


    def set_scene(self, scene):
        self.scene = scene

    def is_prman_running(self):
        if rman__sg__inited:
            return __is_prman_running__()

    def reset_filter_names(self):
        self.light_filter_map = {}
        for obj in self.scene.objects:
            if obj.type == 'LIGHT':
                # add the filters to the filter ma
                for lf in obj.data.renderman.light_filters:
                    if lf.filter_name not in self.light_filter_map:
                        self.light_filter_map[lf.filter_name] = []
                    self.light_filter_map[lf.filter_name].append(
                        (obj.data.name, obj.name))

    def get_python_framebuffer(self):       
        if __is_prman_running__():        
            return rman_sg_exporter().get_python_framebuffer()                 
        return None

    # start the interactive session, using RixSceneGraph
    def start_interactive_sg(self, viewport=False):
        print("Starting interactive")
        rm = self.scene.renderman
        if find_it_path() is None:
            debug('error', "ERROR no 'it' installed.  \
                    Cannot start interactive rendering.")
            return

        if self.scene.camera is None:
            debug('error', "ERROR no Camera.  \
                    Cannot start interactive rendering.")
            self.end_interactive()
            return     

        self.material_dict = {}
        self.instance_dict = {}
        self.lights = {}
        self.scene_objects = {}
        self.light_filter_map = {}
        self.current_solo_light = None
        self.muted_lights = []
        self.crop_window = [self.scene.render.border_min_x, self.scene.render.border_max_x,
                      1.0 - self.scene.render.border_min_y, 1.0 - self.scene.render.border_max_y]
        for obj in self.scene.objects:
            if obj.type == 'LIGHT' and obj.name not in self.lights:
                # add the filters to the filter ma
                for lf in obj.data.renderman.light_filters:
                    if lf.filter_name not in self.light_filter_map:
                        self.light_filter_map[lf.filter_name] = []
                    self.light_filter_map[lf.filter_name].append(
                        (obj.data.name, obj.name))
                self.lights[obj.name] = obj.data.name
                if obj.data.renderman.solo:
                    self.current_solo_light = obj
                if obj.data.renderman.mute:
                    self.muted_lights.append(obj)
            elif obj.name not in self.scene_objects:
                self.scene_objects[obj.name] = obj.data.name if obj.data else obj
            for mat_slot in obj.material_slots:
                if mat_slot.material not in self.material_dict:
                    self.material_dict[mat_slot.material] = []
                self.material_dict[mat_slot.material].append(obj)

        self.convert_textures(get_texture_list(self.scene))

        # Check if rendering select objects only.
        if(self.scene.renderman.render_selected_objects_only):
            visible_objects = get_Selected_Objects(self.scene)
        else:
            visible_objects = None
       
        if viewport:
            rman_sg_exporter().start_viewport(visible_objects, self, self.scene)
        else:    
            rman_sg_exporter().start_ipr(visible_objects, self, self.scene)    

        self.is_interactive_ready = True        
        return           

    def blender_scene_updated_pre_cb(self, scene):
        return    

    def update_scene(self, context, depsgraph):
        for obj in depsgraph.updates:
            ob = obj.id
            if isinstance(obj.id, bpy.types.Camera):
                cam = obj.object
                print("CAMERA UPDATED")            
            elif isinstance(obj.id, bpy.types.Material):
                print("MATERIAL UPDATED")
            elif isinstance(obj.id, bpy.types.Object):
                obj_key = obj.id.name_full
                if obj.id.type == 'MESH':
                    print("MESH UPDATED")
                elif obj.id.type == 'LIGHT':
                    print("LIGHT UPDATED!")



    def update_view(self, context, depsgraph):
        rman_sg_exporter().issue_camera_transform_edit(context, depsgraph)


    def blender_scene_updated_cb(self, scene):
        if __is_prman_running__():
            self.scene = scene
            #active = bpy.context.view_layer.objects.active

            cw = [scene.render.border_min_x, scene.render.border_max_x,
                        1.0 - scene.render.border_min_y, 1.0 - scene.render.border_max_y]

            if cw != self.crop_window:
                self.crop_window = cw
                rman_sg_exporter().issue_cropwindow_edits(cw)
                return    

            dgraph = bpy.context.view_layer.depsgraph
            depupdates = dgraph.updates

            for dupd in dgraph.updates:
                active = None
                if isinstance(dupd.id, bpy.types.Object):
                    if dupd.id.type == "MESH":
                        active = bpy.types.Mesh(dupd.id)
                    else:
                        active = bpy.types.Object(dupd.id)
                obj_type = None

                if hasattr(active, "type"):
                    obj_type = active.type
                elif bpy.context.view_layer.objects.active:
                    obj_type = bpy.context.view_layer.objects.active.type
                    active = bpy.context.view_layer.objects.active

                if obj_type and obj_type not in ['MESH', 
                                    'CURVE', 
                                    'SURFACE', 
                                    'META', 
                                    'FONT', 
                                    'LATTICE', 
                                    'LIGHT', 
                                    'CAMERA',
                                    'EMPTY']:
                    continue

                if obj_type:                    
                    
                    """
                    if obj_type == 'LIGHT':
                        if active.name not in self.lights:
                            rman_sg_exporter().issue_new_object_edits(active, scene)
                            self.lights[active.name] = active.data.name 
                            continue

                    elif active.name not in self.scene_objects:
                        if obj_type == "MESH":
                            rman_sg_exporter().issue_new_object_edits(active, scene)
                            self.scene_objects[active.name] = active.data.name if active.data else active                               
                        continue        
                    """

                    if dupd.is_updated_transform:
                        rman_sg_exporter().issue_transform_edits(active, scene)
                        continue                         

                    elif dupd.is_updated_geometry:
                        rman_sg_exporter().issue_object_edits(active, scene)
                        continue

                """
                else:
                    # check if an object got deleted
                    if len(self.lights) > len([o for o in scene.objects if o.type == 'LIGHT']):
                        lights_deleted = []
                        for light_name, data_name in self.lights.items():
                            if light_name not in scene.objects:
                                rman_sg_exporter().issue_delete_object_edits(light_name, data_name)
                                lights_deleted.append(light_name)

                        for light_name in lights_deleted:
                            self.lights.pop(light_name, None)             

                    elif len(self.scene_objects) > len([o for o in scene.objects if o.type != 'LIGHT']):
                        objects_deleted = []
                        for obj_name, data_name in self.scene_objects.items():
                            if obj_name not in scene.objects:
                                rman_sg_exporter().issue_delete_object_edits(obj_name, data_name)
                                objects_deleted.append(obj_name)

                        for obj_name in objects_deleted:
                            self.scene_objects.pop(obj_name, None)    
                """                                     
        
            """
            if (active and active.particle_systems.active and active.particle_systems.active.id_data.is_updated_data):
                # particles updated
                psys_active = active.particle_systems.active
                rman_sg_exporter().issue_object_edits(active, scene, psys=psys_active) 

            if active and active.type != 'LIGHT':
                rman_sg_exporter().issue_visibility_edit(active, scene)           

            if (active and active.is_updated):
                if active.type == 'LIGHT':
                    light = active.data
                    if active.name not in self.lights:
                        rman_sg_exporter().issue_new_object_edits(active, scene)
                        self.lights[active.name] = active.data.name 
                    else:
                        rman_sg_exporter().issue_transform_edits(active, scene)

                elif active.name not in self.scene_objects:
                    rman_sg_exporter().issue_new_object_edits(active, scene)
                    self.scene_objects[active.name] = active.data.name if active.data else active                      
                else:
                    rman_sg_exporter().issue_transform_edits(active, scene)
            elif (active and active.is_updated_data):
                rman_sg_exporter().issue_object_edits(active, scene)

            if active and active.renderman.id_data.is_updated_data:
                rman_sg_exporter().issue_object_edits(active, scene)

            if active and scene.camera.name != active.name and scene.camera.is_updated:
                rman_sg_exporter().issue_transform_edits(active, scene)

            # check if light is deleted
            if not active and len(self.lights) > len([o for o in scene.objects if o.type == 'LIGHT']):
                lights_deleted = []
                for light_name, data_name in self.lights.items():
                    if light_name not in scene.objects:
                        rman_sg_exporter().issue_delete_object_edits(light_name, data_name)
                        lights_deleted.append(light_name)

                for light_name in lights_deleted:
                    self.lights.pop(light_name, None)                

            # check if object has been deleted
            if not active and len(self.scene_objects) > len([o for o in scene.objects if o.type != 'LIGHT']):
                objects_deleted = []
                for obj_name, data_name in self.scene_objects.items():
                    if obj_name not in scene.objects:
                        rman_sg_exporter().issue_delete_object_edits(obj_name, data_name)
                        objects_deleted.append(obj_name)

                for obj_name in objects_deleted:
                    self.scene_objects.pop(obj_name, None) 

            if active and active.type in ['MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'LATTICE']:
                for mat_slot in active.material_slots:
                    if mat_slot.material not in self.material_dict:
                        self.material_dict[mat_slot.material] = []
                    if active not in self.material_dict[mat_slot.material]:
                        self.material_dict[mat_slot.material].append(active)
                        if mat_slot.material and mat_slot.material.node_tree:
                            rman_sg_exporter().issue_shader_edits(nt=mat_slot.material.node_tree, ob=active)
            """

    def issue_shader_edits(self, nt=None, node=None):
        if rman__sg__inited:
            rman_sg_exporter().issue_shader_edits(nt=nt, node=node)

    def issue_rman_prim_type_edit(self, active):
        if rman__sg__inited:
            rman_sg_exporter().issue_rman_prim_type_edit(active) 

    def issue_rman_particle_prim_type_edit(self, active, psys):
        if rman__sg__inited:
            rman_sg_exporter().issue_rman_particle_prim_type_edit(active, psys)                  

    def update_light_link(self, context, ll):
        if rman__sg__inited:
            rman_sg_exporter().update_light_link(ll)

    def remove_light_link(self, context, ll):
        if rman__sg__inited:
            rman_sg_exporter().update_light_link(ll, remove=True)        

    # ri.end
    def end_interactive(self):
        global rman__sg__inited
        self.is_interactive = False
        if rman__sg__inited:
            rman_sg_exporter().stop_ipr()

        self.material_dict = {}
        self.lights = {}
        self.light_filter_map = {}
        self.instance_dict = {}
        self.scene_objects = {}


    def gen_rib(self, do_objects=True, engine=None, convert_textures=True):
        global rman__sg__inited

        rm = self.scene.renderman
        if self.scene.camera is None:
            debug('error', "ERROR no Camera.  \
                    Cannot generate rib.")
            return
        time_start = time.time()
        if convert_textures:
            self.convert_textures(get_texture_list(self.scene))

        if engine:
            engine.report({"INFO"}, "Texture generation took %s" %
                          format_seconds_to_hhmmss(time.time() - time_start))

        self.scene.frame_set(self.scene.frame_current)
        time_start = time.time()

        # Check if rendering select objects only.
        if rm.render_selected_objects_only:
            visible_objects = get_Selected_Objects(self.scene)
        else:
            visible_objects = None  

        if rman__sg__inited:      
            rman_sg_exporter().write_frame_rib(visible_objects, self, self.scene, self.paths['rib_output'])

        if engine:
            engine.report({"INFO"}, "RIB generation took %s" %
                          format_seconds_to_hhmmss(time.time() - time_start))

    def gen_rib_archive(self, object, ribfile, export_mats, export_range, convert_textures=True, engine=None):
        global rman__sg__inited

        rm = self.scene.renderman
        if self.scene.camera is None:
            debug('error', "ERROR no Camera.  \
                    Cannot generate rib.")
            return
        time_start = time.time()
        if convert_textures:
            self.convert_textures(get_texture_list(self.scene))

        if engine:
            engine.report({"INFO"}, "Texture generation took %s" %
                          format_seconds_to_hhmmss(time.time() - time_start))


        time_start = time.time()
        if export_range:
            rangeStart = self.scene.frame_start
            rangeEnd = self.scene.frame_end
            rangeLength = rangeEnd - rangeStart
            # Assume user is smart and wont pass us a negative range.
            if rman__sg__inited:
                dir_path = os.path.dirname(ribfile)
                ext = '.rib'
                basename = os.path.splitext(os.path.basename(ribfile))[0]
                for i in range(rangeStart, rangeEnd + 1):      
                    self.scene.frame_set(i)
                    rib = os.path.join(dir_path, '%s_%04d%s' % (basename, i, ext))       
                    rman_sg_exporter().write_archive_rib(object, self, self.scene, rib)
        else:
            self.scene.frame_set(self.scene.frame_current)

            if rman__sg__inited:      
                rman_sg_exporter().write_archive_rib(object, self, self.scene, ribfile)

        if engine:
            engine.report({"INFO"}, "RIB generation took %s" %
                          format_seconds_to_hhmmss(time.time() - time_start))        

    def convert_textures(self, temp_texture_list):
        pass
        """
        if not os.path.exists(self.paths['texture_output']):
            os.mkdir(self.paths['texture_output'])

        files_converted = []
        texture_list = []

        if not temp_texture_list:
            return

        # for UDIM textures
        for in_file, out_file, options in temp_texture_list:
            if '_MAPID_' in in_file:
                in_file = get_real_path(in_file)
                for udim_file in glob.glob(in_file.replace('_MAPID_', '*')):
                    texture_list.append(
                        (udim_file, get_tex_file_name(udim_file), options))
            else:
                texture_list.append((in_file, out_file, options))

        for in_file, out_file, options in texture_list:
            in_file = get_real_path(in_file)
            out_file_path = os.path.join(
                self.paths['texture_output'], out_file)

            if os.path.isfile(out_file_path) and os.path.exists(in_file) and\
                    self.rm.always_generate_textures is False and \
                    os.path.getmtime(in_file) <= \
                    os.path.getmtime(out_file_path):
                debug("info", "TEXTURE %s EXISTS (or is not dirty)!" %
                      out_file)
            else:
                cmd = [os.path.join(self.paths['rmantree'], 'bin',
                                    self.paths['path_texture_optimiser'])] + \
                    options + [in_file, out_file_path]
                debug("info", "TXMAKE STARTED!", cmd)

                Blendcdir = bpy.path.abspath("//")
                if not Blendcdir:
                    Blendcdir = None

                environ = os.environ.copy()
                environ['RMANTREE'] = self.paths['rmantree']
                process = subprocess.Popen(cmd, cwd=Blendcdir,
                                           stdout=subprocess.PIPE, env=environ)
                process.communicate()
                files_converted.append(out_file_path)

        return files_converted
        """
