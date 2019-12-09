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
import math
import mathutils
import os
import sys
import time
import traceback
import platform
from mathutils import Matrix, Vector, Quaternion, Euler

from . import bl_info

from .util import rib, rib_path, rib_ob_bounds
from .util import make_frame_path
from .util import init_env
from .util import get_sequence_path
from .util import user_path
from .util import path_list_convert, get_real_path
from .util import get_properties, check_if_archive_dirty
from .util import locate_openVDB_cache
from .util import debug, get_addon_prefs
from .util import format_seconds_to_hhmmss

from .nodes_sg import is_renderman_nodetree, get_textures, get_textures_for_node, get_tex_file_name
from .nodes_sg import get_mat_name
from .nodes_sg import replace_frame_num

from . import nodes_sg
from . import engine

from. import chatserver
import socketserver
import threading

addon_version = bl_info['version']
port = -1
is_running = False

__RMAN_SG_INITED__ = False
__RMAN_SG_EXPORTER__ = None


try:
    import rman
    __RMAN_SG_INITED__ = True
except Exception as e:
    print('Could not import rman modules: %s' % str(e))


# ------------- Atom's helper functions -------------
GLOBAL_ZERO_PADDING = 5
# Objects that can be exported as a polymesh via Blender to_mesh() method.
# ['MESH','CURVE','FONT']
SUPPORTED_INSTANCE_TYPES = ['MESH', 'CURVE', 'FONT', 'SURFACE']
SUPPORTED_DUPLI_TYPES = ['FACES', 'VERTS', 'COLLECTION']    # Supported dupli types.
# These object types can have materials.
MATERIAL_TYPES = ['MESH', 'CURVE', 'FONT']
# Objects without to_mesh() conversion capabilities.
EXCLUDED_OBJECT_TYPES = ['LIGHT', 'CAMERA', 'ARMATURE']
# Only these light types affect volumes.
VOLUMETRIC_LIGHT_TYPES = ['SPOT', 'AREA', 'POINT']
MATERIAL_PREFIX = "mat_"
TEXTURE_PREFIX = "tex_"
MESH_PREFIX = "me_"
CURVE_PREFIX = "cu_"
GROUP_PREFIX = "group_"
MESHLIGHT_PREFIX = "meshlight_"
PSYS_PREFIX = "psys_"
DUPLI_PREFIX = "dupli_"
DUPLI_SOURCE_PREFIX = "dup_src_"

s_orientTransform = [0, 0, -1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1]

s_orientPxrLight = [-1.0, 0.0, -0.0, 0.0,
                    -0.0, -1.0, -0.0, 0.0,
                    0.0, 0.0, -1.0, 0.0,
                    0.0, 0.0, 0.0, 1.0]

s_orientPxrDomeLight = [0.0, 0.0, -1.0, 0.0,
                       -1.0, -0.0, 0.0, 0.0,
                        0.0, 1.0, 0.0, 0.0,
                        0.0, 0.0, 0.0, 1.0]

s_orientPxrEnvDayLight = [-0.0, 0.0, -1.0, 0.0,
                        1.0, 0.0, -0.0, -0.0,
                        -0.0, 1.0, 0.0, 0.0,
                        0.0, 0.0, 0.0, 1.0]

s_orientPxrEnvDayLightInv = [-0.0, 1.0, -0.0, 0.0,
                            -0.0, 0.0, 1.0, -0.0,
                            -1.0, -0.0, 0.0, -0.0,
                            0.0, -0.0, -0.0, 1.0]

def convert_matrix(m):
    v = [m[0][0], m[1][0], m[2][0], m[3][0],
        m[0][1], m[1][1], m[2][1], m[3][1],
        m[0][2], m[1][2], m[2][2], m[3][2],
        m[0][3], m[1][3], m[2][3], m[3][3]]

    return v

def convert_ob_bounds(ob_bb):
    return (ob_bb[0][0], ob_bb[7][0], ob_bb[0][1],
            ob_bb[7][1], ob_bb[0][2], ob_bb[1][2])    

def transform_points(transform_mtx, P):
    transform_pts = []
    mtx = convert_matrix( transform_mtx )
    m = rman.Types.RtMatrix4x4( mtx[0],mtx[1],mtx[2],mtx[3],
                                mtx[4],mtx[5],mtx[6],mtx[7],
                                mtx[8],mtx[9],mtx[10],mtx[11],
                                mtx[12],mtx[13],mtx[14],mtx[15])
    for i in range(0, len(P), 3):
        pt = m.pTransform( rman.Types.RtFloat3(P[i], P[i+1], P[i+2]) )
        transform_pts.append(pt.x)
        transform_pts.append(pt.y)
        transform_pts.append(pt.z)

    return transform_pts

def __is_prman_running__():
    global is_running
    return is_running            

class ItHandler(chatserver.ItBaseHandler):

    def dspyRender(self):
        if not __is_prman_running__():                          
            bpy.ops.render.render()             

    def dspyIPR(self):
        if __is_prman_running__():
            crop = []
            for c in self.msg.getOpt('crop').split(' '):
                crop.append(float(c))
            if len(crop) == 4:
                rman_sg_exporter().issue_cropwindow_edits(crop)

    def stopRender(self):
        if engine.ipr: 
            engine.shutdown_ipr()    

    def selectObjectById(self):
        obj_id = int(self.msg.getOpt('id', '0'))
        if obj_id < 0 or not (obj_id in rman_sg_exporter().obj_hash):
            return
        name = rman_sg_exporter().obj_hash[obj_id]
        obj = bpy.context.scene.objects[name]
        bpy.context.view_layer.objects.active = obj


    def selectSurfaceById(self):
        self.selectObjectById()
        window = bpy.context.window_manager.windows[0]
        if window.screen:
            for a in window.screen.areas:
                if a.type == "PROPERTIES":
                    for s in a.spaces:
                        if s.type == "PROPERTIES":
                            try:
                                s.context = "MATERIAL"
                            except:
                                pass
                            return

class RmanSgExporter:

    def __init__(self, **kwargs):

        self.rictl = rman.RiCtl.Get()
        self.sgmngr = rman.SGManager.Get()

        self.sg_scene = None
        self.sg_root = None
        self.sg_global_obj = None

        # blender scene and rpass
        self.scene = None
        self.rpass = None
        self.rm = None

        # exporters
        self.shader_exporter = None

        self.sg_nodes_dict = dict() # handles to sg_nodes
        self.mat_networks = dict() # dict material to networks
        self.light_filters_dict = dict() # dict light to light filters
        self.lightfilters_dict = dict() # dict light filters to light
        self.displayfilters_list = list()
        self.samplefilters_list = list()
        self.obj_hash = dict()
        self.obj_id = 1

        self.port = -1
        self.main_camera = None
        self.ipr_mode = False
        self.use_python_dspy = False
        self.cam_matrix = None

    def export_ready(self):
        self.sg_nodes_dict = dict()
        self.mat_networks = dict() 
        self.light_filters_dict = dict()
        self.lightfilters_dict = dict() 
        self.displayfilters_list = list()
        self.samplefilters_list = list()
        self.obj_hash = dict()
        self.obj_id = 1
        self.ipr_mode = False
        self.use_python_dspy = False

        if self.sg_scene:
            self.sgmngr.DeleteScene(self.sg_scene.sceneId)

        self.sg_scene = self.sgmngr.CreateScene()
        self.sg_root = self.sg_scene.Root()
        self.sg_global_obj = None
        self.shader_exporter = nodes_sg.RmanSgShadingExporter(
                                scene=self.scene,
                                sg_scene=self.sg_scene,
                                rman=rman) 
        
    def start_cmd_server(self):

        global port

        if port != -1:
            return port

        # zero port makes the OS pick one
        host, port = "localhost", 0

        # install handler
        chatserver.protocols['it'] = ItHandler

        # Create the server, binding to localhost on some port
        server = socketserver.TCPServer((host, port),
                                        chatserver.CommandHandler)
        ip, port = server.server_address

        thread = threading.Thread(target=server.serve_forever)

        # Exit the server thread when the main thread terminates
        thread.daemon = True
        thread.start()

        return port

    def start_render(self, visible_objects, rpass, scene, progress_cb=None, check_point=-1, for_preview=False):

        global is_running

        if is_running:
            debug('error', "ERROR render already running. Abort")
            return False

        self.rpass = rpass
        self.scene = scene
        self.rm = self.scene.renderman
        self.ipr_mode = False        

        self.export_ready()

        argv = []
        argv.append("prman") 
        argv.append("-progress")
        if not for_preview:
            if self.rpass.display_driver == "it":
                argv.append("-dspyserver")
                argv.append("it")
            argv.append("-t:%d" % self.rm.threads)
            if check_point > 0:
                argv.append("-checkpoint")
                argv.append("%ds" % check_point)

        print("Parsing scene...")
        time_start = time.time()
        if for_preview:
            if self.write_preview_scene() is False:
                # nothing to do?
                return
        else:
            self.write_scene(visible_objects)
                
        if progress_cb:
            ec = rman.EventCallbacks.Get()
            ec.RegisterCallback("Progress", progress_cb, self)

        is_running = True
        self.rictl.PRManBegin(argv)
        if 'RFB_DUMP_RIB' in os.environ:
            print("\tWriting to RIB...")
            rib_time_start = time.time()
            self.sg_scene.Render("rib /var/tmp/blender.rib")     
            print("\tFinished writing RIB. Time: %s" % format_seconds_to_hhmmss(time.time() - rib_time_start))        
        print("Finished parsing scene. Total time: %s" % format_seconds_to_hhmmss(time.time() - time_start))             
        self.sg_scene.Render("prman -blocking")

        self.sgmngr.DeleteScene(self.sg_scene.sceneId)
        self.rictl.PRManEnd()
        print("PRManEnd called.")
        is_running = False

        ec.UnregisterCallback("Progress", progress_cb, self)

        return True

    def write_frame_rib(self, visible_objects, rpass, scene, ribfile):

        global is_running

        self.rpass = rpass
        self.scene = scene
        self.rm = self.scene.renderman
        self.ipr_mode = False        

        self.export_ready()
        self.write_scene(visible_objects)

        rib_options = ""
        if self.rm.rib_compression == "gzip":
            rib_options += " -compression gzip"
        rib_options += " -format %s" % self.rm.rib_format
        if self.rm.rib_format == "ascii":
            rib_options += " -indent"

        is_running = True  
        print("Writing to RIB...")
        rib_time_start = time.time()    
        self.sg_scene.Render("rib %s %s" % (ribfile, rib_options))
        print("Finished parsing scene. Time: %s" % format_seconds_to_hhmmss(time.time() - rib_time_start))       

        self.sgmngr.DeleteScene(self.sg_scene.sceneId)
        is_running = False
        print("Wrote RIB to: %s" % ribfile)     

    def write_archive_rib(self, obj, rpass, scene, ribfile):
        global is_running

        self.rpass = rpass
        self.scene = scene
        self.rm = self.scene.renderman
        self.ipr_mode = False        

        self.export_ready()
        self.write_object_archive(obj)

        rib_options = ""
        if self.rm.rib_compression == "gzip":
            rib_options += " -compression gzip"
        rib_options += " -format %s" % self.rm.rib_format
        if self.rm.rib_format == "ascii":
            rib_options += " -indent"

        is_running = True      
        self.sg_scene.Render("rib %s -archive" % (ribfile))       

        self.sgmngr.DeleteScene(self.sg_scene.sceneId)
        is_running = False
        print("Wrote RIB Archive to: %s" % ribfile)     

    def start_viewport(self, visible_objects, rpass, scene, progress_cb=None):

        global is_running    

        self.rpass = rpass
        self.scene = scene
        self.rm = self.scene.renderman
        self.export_ready()  
        self.ipr_mode = True
        self.use_python_dspy = True

        argv = []
        argv.append("prman") 
        argv.append("-t:%d" % self.rm.threads)

        print("Parsing scene...")
        time_start = time.time()
        self.write_scene(visible_objects)
        #if self.write_preview_scene() is False:
        #    pass

        #ec = rman.EventCallbacks.Get()
        #ec.RegisterCallback("Render", progress_cb, self)            

        is_running = True
        self.rictl.PRManBegin(argv)  
        rman.Dspy.Get() 

        def callback(e, d, ed):
            ed["done"] = (d == 0)
        eventData = { "done": False, "name": 'foobar', "frame": 0 }
        ec = rman.EventCallbacks.Get()
        ec.RegisterCallback("Render", callback, eventData)

        
        if 'RFB_DUMP_RIB' in os.environ:
            print("\tWriting to RIB...")
            rib_time_start = time.time()            
            self.sg_scene.Render("rib /var/tmp/blender.rib")
            print("\tFinished writing RIB. Time: %s" % format_seconds_to_hhmmss(time.time() - rib_time_start))                    
        
        print("Finished parsing scene. Total time: %s" % format_seconds_to_hhmmss(time.time() - time_start))


        print("START RENDER!")
        self.sg_scene.Render("prman -live")  
        #self.EditTestFrame(eventData)


        #self.sgmngr.DeleteScene(self.sg_scene.sceneId)
        #self.rictl.PRManEnd()
        #print("PRManEnd called.")


        #is_running = False

        #ec.UnregisterCallback("Progress", progress_cb, self)   

    def get_python_framebuffer(self):
        if self.use_python_dspy:
            return rman.Dspy.GetFloatFramebuffer()


    def start_ipr(self, visible_objects, rpass, scene, progress_cb=None):

        global is_running    

        self.rpass = rpass
        self.scene = scene
        self.rm = self.scene.renderman        
        self.export_ready()  
        self.ipr_mode = True

        argv = []
        argv.append("prman") 
        argv.append("-progress")
        argv.append("-dspyserver")
        argv.append("it")
        argv.append("-t:%d" % self.rm.threads)

        self.rictl.PRManBegin(argv)
        print("Parsing scene...")
        time_start = time.time()
        self.write_scene(visible_objects)
        is_running = True
        if 'RFB_DUMP_RIB' in os.environ:
            print("\tWriting to RIB...")
            rib_time_start = time.time()            
            self.sg_scene.Render("rib /var/tmp/blender.rib")
            print("\tFinished writing RIB. Time: %s" % format_seconds_to_hhmmss(time.time() - rib_time_start))                    
            
        print("Finished parsing scene. Total time: %s" % format_seconds_to_hhmmss(time.time() - time_start))
        self.sg_scene.Render("prman -live")

    def stop_ipr(self):
        global is_running
        if is_running:
            is_running = False
            self.sgmngr.DeleteScene(self.sg_scene.sceneId)
            self.rictl.PRManEnd()
            print("PRManEnd called.")

    def issue_visibility_edit(self, active, scene):
        self.scene = scene
        db_name = data_name(active, self.scene)
        inst_sg = self.sg_nodes_dict.get(db_name)
        if inst_sg:
            hidden = 0
            if (inst_sg.GetHidden() == -1 and active.hide_render):
                hidden = 1
            elif (inst_sg.GetHidden() == 1 and not(active.hide_render)):
                hidden = -1
            if hidden == 0:
                return
            with rman.SGManager.ScopedEdit(self.sg_scene):
                inst_sg.SetHidden(hidden)

    def mute_lights(self, lights):
        with rman.SGManager.ScopedEdit(self.sg_scene):
            for light in lights:
                sg_node = self.sg_nodes_dict[light.name]
                sg_node.SetHidden(1)        

    def reset_light_illum(self, lights, do_solo=True):
        with rman.SGManager.ScopedEdit(self.sg_scene):
            for light in lights:
                rm = light.data.renderman
                do_light = rm.illuminates_by_default and not rm.mute
                if do_solo and self.rpass.scene.renderman.solo_light:
                    # check if solo
                    do_light = do_light and rm.solo
                sg_node = self.sg_nodes_dict[light.name]
                sg_node.SetHidden(not(do_light))

    def solo_light(self):
        solo_light = None
        with rman.SGManager.ScopedEdit(self.sg_scene):
            for light in self.rpass.scene.objects:
                if light.type == "LIGHT":
                    rm = light.data.renderman
                    sg_node = self.sg_nodes_dict[light.name]                
                    if rm.solo and not solo_light:
                        do_light = rm.illuminates_by_default and not rm.mute
                        solo_light = light
                        sg_node.SetHidden(not(do_light))                    
                    else:
                        sg_node.SetHidden(1)
        
        return solo_light

    def issue_cropwindow_edits(self, crop_window=[]):
        if crop_window:
            with rman.SGManager.ScopedEdit(self.sg_scene): 
                options = self.sg_scene.EditOptionBegin()
                options.SetFloatArray(rman.Tokens.Rix.k_Ri_CropWindow, crop_window, 4)
                self.sg_scene.EditOptionEnd(options)    

    def issue_camera_transform_edit(self, context, depsgraph):
        camera_node_sg = self.sg_nodes_dict['camera']
        cam = context.scene.camera
        v = convert_matrix(cam.matrix_world)
        if v == self.cam_matrix:
            return

        transforms = []
        with rman.SGManager.ScopedEdit(self.sg_scene):        
            self.cam_matrix = v
            transforms.append(v)
            
            camera_node_sg.SetTransform( transforms[0] )                                 

    def issue_transform_edits(self, active, scene):
        self.scene = scene
        #if (active and active.is_updated):
        if (active):
            if active.type == 'CAMERA':
                with rman.SGManager.ScopedEdit(self.sg_scene):
                    camera_node_sg = self.sg_nodes_dict['camera']
                    if camera_node_sg:
                        self.export_camera_transform(camera_node_sg, scene.camera, [])
                    else:
                        print("CANNOT FIND CAMERA!")
            elif active.type == 'EMPTY':
                with rman.SGManager.ScopedEdit(self.sg_scene):
                    self.export_duplis_instances(master=None, prnt=active)           
            elif active.type == 'LIGHT': 
                if active.name not in self.sg_nodes_dict:
                    return
                if active.data.renderman.renderman_type == 'FILTER':

                    sg_lightfilter = self.sg_nodes_dict[active.name]
                    lights = self.lightfilters_dict[active.name]
                    coordsys_name = "%s_coordsys" % active.name
                    coordsys = self.sg_nodes_dict[coordsys_name]

                    with rman.SGManager.ScopedEdit(self.sg_scene): 
                        m = convert_matrix( active.matrix_world )
                        coordsys.SetTransform(m)
                        rix_params = sg_lightfilter.EditParameterBegin()       
                        rix_params.SetString("coordsys", coordsys_name)
                        sg_lightfilter.EditParameterEnd(rix_params)

                        self.sg_nodes_dict[coordsys_name] = coordsys
                        self.sg_nodes_dict[active.name] = sg_lightfilter

                        for l in lights:
                            sg_light = self.sg_nodes_dict[l]
                            lightfilter_sg = self.light_filters_dict[l]
                            sg_light.SetLightFilter(lightfilter_sg)   
                else:
                    sg_light = self.sg_nodes_dict[active.name]
                    with rman.SGManager.ScopedEdit(self.sg_scene):
                        sg_light.SetTransform( convert_matrix(active.matrix_world) )
            else:
                dupli_type = active.instance_type #active.dupli_type                
                if dupli_type != "NONE":
                    data_blocks, instances = cache_motion(self.scene, self.rpass, objects=[active], calc_mb=False)
                    for name, db in data_blocks.items():
                        if db.type != "DUPLI":
                            continue
                        sg_node = self.sg_nodes_dict.get(name)
                        if not sg_node:
                            with rman.SGManager.ScopedEdit(self.sg_scene):
                                self.export_objects(data_blocks, instances)

                        ob = db.data
                        ob.dupli_list_create(self.scene, "RENDER")                            
                        with rman.SGManager.ScopedEdit(self.sg_scene):
                            if ob.dupli_type == 'GROUP' and ob.dupli_group:
                                for dupob in ob.dupli_list:
                                    dupli_name = "%s.DUPLI.%s.%d" % (ob.name, dupob.object.name,
                                                dupob.index)

                                    source_data_name = get_instance(dupob.object, self.scene, False).name
                                    source_sg = self.sg_nodes_dict.get(source_data_name)

                                    if dupli_name in self.sg_nodes_dict:
                                        sg_dupli = self.sg_nodes_dict[dupli_name]
                                        sg_dupli.SetTransform( convert_matrix(dupob.matrix))
                            else:
                                for num, dupob in enumerate(ob.dupli_list):

                                    dupli_name = "%s.DUPLI.%s.%d" % (ob.name, dupob.object.name,
                                                                    dupob.index)

                                    source_data_name = get_instance(dupob.object, self.scene, False).name
                                    source_sg = self.sg_nodes_dict.get(source_data_name)
                                    if source_sg and source_sg.GetHidden() != 1:
                                        source_sg.SetHidden(1)                                                                    

                                    if dupli_name in self.sg_nodes_dict:
                                        sg_dupli = self.sg_nodes_dict[dupli_name]
                                        sg_dupli.SetTransform( convert_matrix(dupob.matrix))
                            
                        ob.dupli_list_clear()     

                else:        
                    instance = get_instance(active, self.scene, False)
                    if instance:
                        inst_mesh_sg = None
                        db_name = data_name(active, self.scene)
                        instance_name = '%s.%s' % (instance.name, db_name)
                        if instance_name in self.sg_nodes_dict.keys():              
                            inst_mesh_sg = self.sg_nodes_dict[instance_name]
                        else:
                            db_name = data_name(active, self.scene)
                            inst_mesh_sg = self.sg_nodes_dict.get(db_name)

                        if inst_mesh_sg:
                            with rman.SGManager.ScopedEdit(self.sg_scene):
                                self.export_transform(instance, inst_mesh_sg)   

                                ## FIXME IS THIS NEEDED?
                                
                                #for psys in active.particle_systems:
                                #    db_name = psys_name(active, psys)
                                #    self.export_particle_system(active, psys, db_name, objectCorrectionMatrix=True, data=None)                                 

                    
                                # check if this object is part of a group/dupli
                                # update accordingly.
                
                                #self.export_duplis_instances(master=active)
                    
        """
        if active and scene.camera.name != active.name and scene.camera.is_updated:
            with rman.SGManager.ScopedEdit(self.sg_scene):
                camera_node_sg = self.sg_nodes_dict['camera']
                if camera_node_sg:
                    self.export_camera_transform(camera_node_sg, scene.camera, [])
                else:
                    print("CANNOT FIND CAMERA!")
        """

    def issue_new_object_edits(self, active, scene):
        self.scene = scene
        if active.type == 'LIGHT':
            # this is a new light
            ob = active
            light = ob.data
            rm = light.renderman
            handle = light.name

            with rman.SGManager.ScopedEdit(self.sg_scene):
                self.export_light(ob, light, handle, rm)  
        else:
            ob = active

            data_blocks, instances = cache_motion(self.scene, self.rpass, objects=[ob], calc_mb=False)
                
            with rman.SGManager.ScopedEdit(self.sg_scene):
                self.export_objects(data_blocks, instances)


    def issue_delete_object_edits(self, obj_name, handle):
        sg_node = self.sg_nodes_dict.get(handle)
        if sg_node:            
            with rman.SGManager.ScopedEdit(self.sg_scene):
                self.sg_scene.DeleteDagNode(sg_node)
                self.sg_nodes_dict.pop(handle, None)
                for k in self.sg_nodes_dict.keys():
                    if k.startswith(handle):
                        if k.endswith('-EMITTER') or k.endswith("-HAIR"):
                            sg_node = self.sg_nodes_dict[k]
                            for c in [ sg_node.GetChild(i) for i in range(0, sg_node.GetNumChildren())]:
                                sg_node.RemoveChild(c)
                            self.sg_root.RemoveChild(sg_node)                        

    def issue_rman_prim_type_edit(self, active):
        if active.type == "MESH":            
            db_name = data_name(active, self.scene)
            mesh_sg = self.sg_nodes_dict.get(db_name)
            if mesh_sg:
                with rman.SGManager.ScopedEdit(self.sg_scene):
                    new_mesh_sg = self.export_geometry_data(active, db_name, data=None)
                    for p in [ mesh_sg.GetParent(i) for i in range(0, mesh_sg.GetNumParents())]:
                        p.RemoveChild(mesh_sg)
                        p.AddChild(new_mesh_sg)     

    def issue_rman_particle_prim_type_edit(self, active, psys):
        if psys is None:
            return
        db_name_emitter = '%s.%s-EMITTER' % (active.name, psys.name)
        sg_node = self.sg_nodes_dict.get(db_name_emitter)
        if sg_node:
            with rman.SGManager.ScopedEdit(self.sg_scene):                
                new_sg_node = self.export_particles(active, psys, db_name_emitter)
                if new_sg_node:
                    for p in [ sg_node.GetParent(i) for i in range(0, sg_node.GetNumParents())]:
                        p.RemoveChild(sg_node)
                        p.AddChild(new_sg_node)                 

    def issue_object_edits(self, active, scene, psys=None):
        self.scene = scene
        if psys:
            db_name_emitter = '%s.%s-EMITTER' % (active.name, psys.name)
            db_name_hair = '%s.%s-HAIR' % (active.name, psys.name)
            rm = psys.settings.renderman
            new_sg_node = None
            with rman.SGManager.ScopedEdit(self.sg_scene): 
                if psys.settings.type == 'EMITTER':    
                    db_name = psys_name(active, psys)
                    new_sg_node = self.export_particle_system(active, psys, db_name, objectCorrectionMatrix=True, data=None) 

                    sg_node = self.sg_nodes_dict.get(db_name_hair)
                    if sg_node:
                        for p in [ sg_node.GetParent(i) for i in range(0, sg_node.GetNumParents())]:
                            p.RemoveChild(sg_node)
                            p.AddChild(new_sg_node)
                else: 
                    db_name = psys_name(active, psys)         
                    new_sg_node = self.export_particle_system(active, psys, db_name, objectCorrectionMatrix=True, data=None)
                    sg_node = self.sg_nodes_dict.get(db_name_emitter)
                    if sg_node:
                        for p in [ sg_node.GetParent(i) for i in range(0, sg_node.GetNumParents())]:
                            p.RemoveChild(sg_node)
                            p.AddChild(new_sg_node)

                if psys.settings.material:
                    psys_mat = active.material_slots[psys.settings.material -
                                     1].material if psys.settings.material and psys.settings.material <= len(active.material_slots) else None
                    if psys_mat:
                        mat_handle = "material.%s" % psys_mat.name
                        sg_material = self.sg_nodes_dict.get(mat_handle)
                        if sg_material:
                            new_sg_node.SetMaterial(sg_material)

                if new_sg_node and new_sg_node.GetNumParents() == 0:
                    # new_sg_node is an orphan
                    # probably because it's a new particle system
                    # add it to the active mesh
                    mesh_db_name = data_name(active, self.scene)
                    mesh_sg = self.sg_nodes_dict.get(mesh_db_name)
                    if mesh_sg:
                        mesh_sg.AddChild(new_sg_node)

        elif active.type == "MESH":
            db_name = data_name(active, self.scene) 
            mesh_sg = self.sg_nodes_dict.get(db_name)
            if mesh_sg:
                prim = active.renderman.primitive if active.renderman.primitive != 'AUTO' \
                    else detect_primitive(active)                
                if active.update_from_editmode():
                    with rman.SGManager.ScopedEdit(self.sg_scene):
                        if prim in ['POLYGON_MESH', 'SUBDIVISION_MESH']:
                            self.export_mesh(active, mesh_sg, active.data, prim)                        
                            self.export_object_primvars(active, mesh_sg)                
            
                #elif active.renderman.id_data.is_updated_data:
                #    with rman.SGManager.ScopedEdit(self.sg_scene):
                #        new_mesh_sg = self.export_geometry_data(active, db_name, data=None)
                #        for p in [ mesh_sg.GetParent(i) for i in range(0, mesh_sg.GetNumParents())]:
                #            p.RemoveChild(mesh_sg)
                #            p.AddChild(new_mesh_sg)                        
                
            
                        for psys in active.particle_systems:
                            if psys:
                                db_name_emitter = '%s.%s-EMITTER' % (active.name, psys.name)
                                db_name_hair = '%s.%s-HAIR' % (active.name, psys.name)
                                rm = psys.settings.renderman
                                new_sg_node = None
                                if psys.settings.type == 'EMITTER':    
                                    db_name = psys_name(active, psys)
                                    new_sg_node = self.export_particle_system(active, psys, db_name, objectCorrectionMatrix=True, data=None) 

                                    sg_node = self.sg_nodes_dict.get(db_name_hair)
                                    if sg_node:
                                        for p in [ sg_node.GetParent(i) for i in range(0, sg_node.GetNumParents())]:
                                            p.RemoveChild(sg_node)
                                            p.AddChild(new_sg_node)
                                else: 
                                    db_name = psys_name(active, psys)         
                                    new_sg_node = self.export_particle_system(active, psys, db_name, objectCorrectionMatrix=True, data=None)
                                    sg_node = self.sg_nodes_dict.get(db_name_emitter)
                                    if sg_node:
                                        for p in [ sg_node.GetParent(i) for i in range(0, sg_node.GetNumParents())]:
                                            p.RemoveChild(sg_node)
                                            p.AddChild(new_sg_node)

                                if psys.settings.material and not rm.use_object_material:
                                    psys_mat = active.material_slots[psys.settings.material -
                                                    1].material if psys.settings.material and psys.settings.material <= len(active.material_slots) else None
                                    if psys_mat:
                                        mat_handle = "material.%s" % psys_mat.name
                                        sg_material = self.sg_nodes_dict.get(mat_handle)
                                        if sg_material:
                                            new_sg_node.SetMaterial(sg_material)

                                if new_sg_node and new_sg_node.GetNumParents() == 0:
                                    # new_sg_node is an orphan
                                    # probably because it's a new particle system
                                    # add it to the active mesh
                                    mesh_db_name = data_name(active, self.scene)
                                    mesh_sg = self.sg_nodes_dict.get(mesh_db_name)
                                    if mesh_sg:
                                        mesh_sg.AddChild(new_sg_node)                         

    def issue_shader_edits(self, nt=None, node=None, ob=None):
        if node is None:
            mat = None        
            if bpy.context.object:
                mat = bpy.context.object.active_material
                if mat not in self.rpass.material_dict:
                    self.rpass.material_dict[mat] = [bpy.context.object]

            light = None
            world = bpy.context.scene.world
            if mat is None and hasattr(bpy.context, 'light') and bpy.context.light:
                light = bpy.context.object
                mat = bpy.context.light
            elif mat is None and nt and nt.name == 'World':
                mat = world
            if mat is None:
                return
            # do an attribute full rebind
            
            # invalidate any textues that were re-made
            tex_files_made = reissue_textures(self.rpass, mat)
            if tex_files_made:
                for f in tex_files_made:
                    self.rictl.InvalidateTexture(f)

            # New material assignment. Loop over all objects:
            if mat in self.rpass.material_dict and is_renderman_nodetree(mat):
                mat_name = get_mat_name(mat.name)

                sg_material = None 
 
                mat_handle = "material.%s" % mat_name
                
                if mat_handle in self.sg_nodes_dict.keys():
                    sg_material = self.sg_nodes_dict[mat_handle]

                with rman.SGManager.ScopedEdit(self.sg_scene): 
                    sg_material, bxdfList = self.shader_exporter.export_shader_nodetree(
                                mat, sg_node=sg_material, mat_sg_handle=mat_handle, handle=None, 
                                iterate_instance=False)
                self.sg_nodes_dict['material.%s' % mat_name] = sg_material

                if ob:
                    instance = get_instance(ob, self.scene, False)
                    if instance:
                        if instance.name in self.sg_nodes_dict:
                            with rman.SGManager.ScopedEdit(self.sg_scene):                            
                                inst_sg = self.sg_nodes_dict[instance.name]
                                inst_sg.SetMaterial(sg_material)

                else:
                    for obj in self.rpass.material_dict[mat]:
                        if not is_multi_material(obj):
                            if obj.material_slots[0].name == mat.name:
                                instance = get_instance(obj, self.scene, False)
                                if instance:
                                    if instance.name in self.sg_nodes_dict:
                                        with rman.SGManager.ScopedEdit(self.sg_scene):
                                            inst_sg = self.sg_nodes_dict[instance.name]
                                            inst_sg.SetMaterial(sg_material)   

                        for psys in obj.particle_systems:
                            if psys.settings.material:
                                psys_mat = obj.material_slots[psys.settings.material -
                                     1].material if psys.settings.material and psys.settings.material <= len(obj.material_slots) else None
                                if psys_mat and psys_mat.name == mat.name:
                                    db_name_emitter = '%s.%s-EMITTER' % (obj.name, psys.name)
                                    db_name_hair = '%s.%s-HAIR' % (obj.name, psys.name)
                                    psys_node = None
                                    if db_name_emitter in self.sg_nodes_dict:
                                        psys_node = self.sg_nodes_dict[db_name_emitter]
                                    elif db_name_hair in self.sg_nodes_dict:
                                        psys_node = self.sg_nodes_dict[db_name_hair]
                                    if psys_node:
                                        with rman.SGManager.ScopedEdit(self.sg_scene):
                                            psys_node.SetMaterial(sg_material)


            elif light:
                light_ob = light
                light = mat
                print('EDITING LIGHT')
                """ri.EditBegin('attribute', {'string scopename': light.name})
                export_light_filters(ri, light, do_coordsys=True)

                export_object_transform(ri, light_ob)
                export_light_shaders(ri, light, get_light_group(ob))
                ri.EditEnd()"""

            elif world:
                pass
                """ri.EditBegin('attribute', {'string scopename': world.name})
                export_world(ri, mat.data, do_geometry=True)
                ri.EditEnd()"""           
        else:
            world = bpy.context.scene.world
            mat = None
            instance_num = 0
            mat_name = None  
            is_light = False

            if bpy.context.object:
                mat = bpy.context.object.active_material
                if mat:
                    instance_num = mat.renderman.instance_num
                    mat_name = get_mat_name(mat.name)
            # if this is a light use that for the mat/name
            if mat is None and node and issubclass(type(node.id_data), bpy.types.Light):
                mat = node.id_data
                is_light = True
            elif mat is None and nt and nt.name == 'World':
                mat = bpy.context.scene.world
            elif mat is None and bpy.context.object and bpy.context.object.type == 'CAMERA':
                self.rpass.edit_num += 1
                #edit_flush(ri, rpass.edit_num, prman)

                #ri.EditBegin('option')
                #export_camera(ri, rpass.scene, [],
                #            camera_to_use=rpass.scene.camera)
                #ri.EditEnd()
                return
            elif mat is None \
                    and hasattr(node, "renderman_node_type") \
                    and node.renderman_node_type \
                    in {'displayfilter', 'displaysamplefilter'}:

                idx = bpy.context.scene.renderman.display_filters_index
                df = bpy.context.scene.renderman.display_filters[idx]
                df_name = df.name
                if df_name == "":
                    df_name = "rman_displayfilter_filter%d" % idx
                with rman.SGManager.ScopedEdit(self.sg_scene): 
                    if len(self.displayfilters_list) == 1:
                        if len(self.displayfilters_list) != len(bpy.context.scene.renderman.display_filters):
                            self.export_displayfilters()
                            return
                    elif len(bpy.context.scene.renderman.display_filters) > 1:
                        if len(self.displayfilters_list)-1 != len(bpy.context.scene.renderman.display_filters):
                            self.export_displayfilters()
                            return

                    if self.displayfilters_list:
                        df_node = self.displayfilters_list[idx]
                        if df_node.GetName().CStr() != df.get_filter_name():
                            self.export_displayfilters()
                        else:
                            params = df_node.EditParameterBegin()
                            property_group_to_rixparams(df.get_filter_node(), df_node)
                            df_node.EditParameterEnd(params)
                            self.sg_scene.SetDisplayFilter(self.displayfilters_list)
                    else:
                        self.export_displayfilters()
                return
            elif mat is None \
                    and hasattr(node, "renderman_node_type") \
                    and node.renderman_node_type \
                    in {'samplefilter', 'displaysamplefilter'}:

                idx = bpy.context.scene.renderman.sample_filters_index
                df = bpy.context.scene.renderman.sample_filters[idx]
                df_name = df.name
                if df_name == "":
                    df_name = "rman_samplefilter_filter%d" % idx
                    if len(self.samplefilters_list) == 1:
                        if len(self.samplefilters_list) != len(bpy.context.scene.renderman.sample_filters):
                            self.export_samplefilters()
                            return
                    elif len(bpy.context.scene.renderman.sample_filters) > 1:
                        if len(self.samplefilters_list)-1 != len(bpy.context.scene.renderman.sample_filters):
                            self.export_samplefilters()
                            return

                    if self.samplefilters_list:
                        df_node = self.samplefilters_list[idx]
                        if df_node.GetName().CStr() != df.get_filter_name():
                            self.export_samplefilters()
                        else:                        
                            params = df_node.EditParameterBegin()
                            property_group_to_rixparams(df.get_filter_node(), df_node)
                            df_node.EditParameterEnd(params)
                            self.sg_scene.SetSampleFilter(self.samplefilters_list)
                    else:
                        self.export_samplefilters()
                return                
            elif mat is None:
                return

            if not mat_name:
                mat_name = mat.name  # for world/light

            # invalidate any textues that were re-made
            tex_files_made = reissue_textures(self.rpass, mat)
            if tex_files_made:
                for f in tex_files_made:
                    self.rictl.InvalidateTexture(f)

            handle = mat_name
            if is_light:
                if node.renderman_node_type == "lightfilter":
                    if mat_name in self.sg_nodes_dict:
                        sg_lightfilter = self.sg_nodes_dict[mat_name]
                        lights = self.lightfilters_dict[mat_name]
                        with rman.SGManager.ScopedEdit(self.sg_scene): 
                            rix_params = sg_lightfilter.EditParameterBegin()       
                            rix_params = nodes_sg.gen_rixparams(node, rix_params, mat_name)
                            coordsys_name = "%s_coordsys" % mat_name
                            rix_params.SetString("coordsys", coordsys_name)
                            sg_lightfilter.EditParameterEnd(rix_params)

                            for l in lights:
                                sg_light = self.sg_nodes_dict[l]
                                lightfilter_sg = self.light_filters_dict[l]
                                sg_light.SetLightFilter(lightfilter_sg)                       
                    pass
                else:
                    sg_light = self.sg_nodes_dict[mat_name]
                    sg_node = self.mat_networks[mat_name]
                    with rman.SGManager.ScopedEdit(self.sg_scene): 
                        rix_params = sg_node.EditParameterBegin()       
                        rix_params = nodes_sg.gen_rixparams(node, rix_params, mat_name)
                        sg_node.EditParameterEnd(rix_params) 
                        sg_light.SetLight(sg_node)                               

            else:
                mat_handle = 'material.%s' % mat_name
                sg_material = self.sg_nodes_dict[mat_handle] 
           
                if sg_material:
                    with rman.SGManager.ScopedEdit(self.sg_scene):
                        sg_material,bxdfList = self.shader_exporter.export_shader_nodetree(
                            mat, sg_node=sg_material, mat_sg_handle=mat_handle, handle=None, 
                            iterate_instance=False)
                    self.sg_nodes_dict[mat_handle] = sg_material

    def update_light_link(self, link, remove=False):
        strs = link.name.split('>')
        ob_names = [strs[3]] if strs[2] == "obj_object" else \
            self.scene.renderman.object_groups[strs[3]].members.keys()

        with rman.SGManager.ScopedEdit(self.sg_scene):
            for ob_name in ob_names:
                sg_node = self.sg_nodes_dict.get(ob_name)
                if not sg_node:
                    continue
                scene_lights = [l.name for l in self.scene.objects if l.type == 'LIGHT']
                light_names = [strs[1]] if strs[0] == "lg_light" else \
                    self.scene.renderman.light_groups[strs[1]].members.keys()
                if strs[0] == 'lg_group' and strs[1] == 'All':
                    light_names = [l.name for l in scene.objects if l.type == 'LIGHT']

                subset = []
                excludesubset = []
                lightfilter_subset = []
                subset.append("World")
                for light_name in light_names:
                    light = self.scene.objects[light_name].data
                    rm = light.renderman
                    if rm.renderman_type == 'FILTER':
                        filter_name = light_name
                        for light_nm in light_names:
                            if filter_name in self.scene.objects[light_nm].data.renderman.light_filters.keys():
                                #lamp_nm = self.scene.objects[light_nm].data.name
                                if link.illuminate == 'ON':
                                    lightfilter_subset.append(filter_name)

                                #if remove or link.illuminate == "DEFAULT":
                                    #ri.EnableLightFilter(lamp_nm, filter_name, 1)
                                #else:
                                    #ri.EnableLightFilter(
                                    #    lamp_nm, filter_name, link.illuminate == 'ON')
                    else:
                        if remove:
                            excludesubset.append(light.name)
                        elif link.illuminate == "DEFAULT":
                            if light.renderman.illuminates_by_default:
                                subset.append(light.name)
                            else:
                                excludesubset.append(light.name)
                        elif link.illuminate == 'ON':
                            subset.append(light.name)
                        else:
                            excludesubset.append(light.name)

                attrs = sg_node.EditAttributeBegin()
                attrs.SetString(rman.Tokens.Rix.k_lighting_subset, ",".join(subset))
                attrs.SetString(rman.Tokens.Rix.k_lighting_excludesubset, ",".join(excludesubset))
                attrs.SetString(rman.Tokens.Rix.k_lighfilter_subset, ",".join(lightfilter_subset))
                sg_node.EditAttributeEnd(attrs)                
 
    def export_searchpaths(self):
        options = self.sg_scene.EditOptionBegin()
        options.SetString("searchpath:shader", "%s" %
                                                ':'.join(path_list_convert(self.rpass.paths['shader'], to_unix=True)))

        rel_tex_paths = [os.path.relpath(path, self.rpass.paths['export_dir'])
                        for path in self.rpass.paths['texture']]
        options.SetString("searchpath:texture", "%s" %
                                                    ':'.join(path_list_convert(rel_tex_paths + ["@"], to_unix=True)))

        # FIXME: 'procedural' key doesn't seem to exist?
        #options.SetString("searchpath:procedural", "%s" % \
        #    ':'.join(path_list_convert(self.rpass.paths['procedural'], to_unix=True)))
        options.SetString("searchpath:procedural", ".:${RMANTREE}/lib/plugins:@")


        options.SetString("searchpath:archive", os.path.relpath(
            self.rpass.paths['archive'], self.rpass.paths['export_dir']))
        self.sg_scene.EditOptionEnd(options)

    def export_object_primvars(self, ob, sg_node):
        rm = ob.renderman
        primvars = sg_node.EditPrimVarBegin()

        if rm.shading_override:
            if rm.shadingrate != 1:
                attrs.SetFloat(rman.Tokens.Rix.k_dice_micropolygonlength, rm.shadingrate)
            if rm.watertight:
                attrs.SetFloat(rman.Tokens.Rix.k_dice_watertight, 1)

        if rm.raytrace_override:                
            if not rm.raytrace_tracedisplacements:
                attrs.SetInteger(rman.Tokens.Rix.k_trace_displacements, 0)
            if not rm.raytrace_autobias:
                attrs.SetFloat(rman.Tokens.Rix.k_trace_autobias, 0)
                if rm.raytrace_bias != 0.01:
                    attrs.SetFloat(rman.Tokens.Rix.k_trace_bias, rm.raytrace_bias)
            if rm.raytrace_samplemotion:
                attrs.SetInteger(rman.Tokens.Rix.k_trace_samplemotion, 1)

        sg_node.EditPrimVarEnd(primvars)

    def export_object_attributes(self, ob, sg_node, visible_objects, name=""):

        # Adds external RIB to object_attributes
        rm = ob.renderman
        attrs = sg_node.EditAttributeBegin()        

        # Add ID
        if name != "":            
            self.obj_hash[self.obj_id] = name
            attrs.SetInteger(rman.Tokens.Rix.k_identifier_id, self.obj_id)
            self.obj_id += 1

        """if rm.pre_object_rib_box != '':
            export_rib_box(ri, rm.pre_object_rib_box)"""

        obj_groups_str = "World"
        obj_groups_str += "," + name
        lpe_groups_str = "*"
        for obj_group in self.scene.renderman.object_groups:
            if ob.name in obj_group.members.keys():
                obj_groups_str += ',' + obj_group.name
                lpe_groups_str += ',' + obj_group.name

        attrs.SetString(rman.Tokens.Rix.k_grouping_membership, obj_groups_str)

        # add to trace sets
        if lpe_groups_str != '*':                       
            attrs.SetString(rman.Tokens.Rix.k_identifier_lpegroup, lpe_groups_str)

        # visibility attributes
        attrs.SetInteger("visibility:transmission", int(ob.renderman.visibility_trace_transmission))
        attrs.SetInteger("visibility:indirect", int(ob.renderman.visibility_trace_indirect))
        if visible_objects and ob.name not in visible_objects:
            attrs.SetInteger("visibility:camera", 0)
        else:
            attrs.SetInteger("visibility:camera", int(ob.renderman.visibility_camera))

        if ob.renderman.matte:
            atttrs.SetInteger(rman.Tokens.Rix.k_Ri_Matte, ob.renderman.matte)

        # ray tracing attributes
        trace_params = {}
        shade_params = {}
        if ob.renderman.raytrace_intersectpriority != 0:
            attrs.SetInteger(rman.Tokens.Rix.k_trace_intersectpriority, ob.renderman.raytrace_intersectpriority)
            attrs.SetFloat(rman.Tokens.Rix.k_shade_indexofrefraction, ob.renderman.raytrace_ior)

        if ob.renderman.holdout:
            attrs.SetInteger(rman.Tokens.Rix.k_trace_holdout, 1)

        if ob.renderman.raytrace_override:
            if ob.renderman.raytrace_maxdiffusedepth != 1:
                attrs.SetInteger(rman.Tokens.Rix.k_trace_maxdiffusedepth, ob.renderman.raytrace_maxdiffusedepth)
            if ob.renderman.raytrace_maxspeculardepth != 2:
                attrs.SetInteger(rman.Tokens.Rix.k_trace_maxspeculardepth, ob.renderman.raytrace_maxspeculardepth)

            #if ob.renderman.raytrace_decimationrate != 1:
            #    trace_params[
            #        "int decimationrate"] = ob.renderman.raycreate_meshtrace_decimationrate
            if ob.renderman.raytrace_intersectpriority != 0:
                attrs.SetInteger(rman.Tokens.Rix.k_trace_intersectpriority, ob.renderman.raytrace_intersectpriority)
            #if ob.renderman.raytrace_pixel_variance != 1.0:
           #     shade_params[
           #         "relativepixelvariance"] = ob.renderman.raytrace_pixel_variance

        
        # light linking
        # get links this is a part of
        ll_str = "obj_object>%s" % ob.name
        lls = [ll for ll in self.scene.renderman.ll if ll_str in ll.name]
        # get links this is a group that is a part of
        for group in self.scene.renderman.object_groups:
            if ob.name in group.members.keys():
                ll_str = "obj_group>%s" % group.name
                lls += [ll for ll in self.scene.renderman.ll if ll_str in ll.name]

        # for each light link do illuminates
        exclude_subset = []
        lightfilter_subset = []
        for link in lls:
            strs = link.name.split('>')

            scene_lights = [l.name for l in self.scene.objects if l.type == 'LIGHT']
            light_names = [strs[1]] if strs[0] == "lg_light" else \
                self.scene.renderman.light_groups[strs[1]].members.keys()
            if strs[0] == 'lg_group' and strs[1] == 'All':
                light_names = scene_lights
            for light_name in light_names:
                if link.illuminate != "DEFAULT" and light_name in self.scene.objects:
                    light_ob = self.scene.objects[light_name]
                    light = light_ob.data
                    if light.renderman.renderman_type == 'FILTER':
                        # for each light this is a part of do enable light filter
                        filter_name = light_name
                        for light_nm in scene_lights:
                            if filter_name in self.scene.objects[light_nm].data.renderman.light_filters.keys():
                                if link.illuminate == 'ON':
                                    lightfilter_subset.append(filter_name)
                    else:
                        if not link.illuminate == 'ON':
                            exclude_subset.append(light_name)

        if exclude_subset:
            attrs.SetString(rman.Tokens.Rix.k_lighting_excludesubset, ' '. join(exclude_subset) )

        if lightfilter_subset:
            attrs.SetString(rman.Tokens.Rix.k_lightfilter_subset, ' ' . join(lightfilter_subset))

        user_attr = {}
        for i in range(8):
            name = 'MatteID%d' % i
            if getattr(rm, name) != [0.0, 0.0, 0.0]:
                attrs.SetColor('user:%s' % name, getattr(rm, name))

        if hasattr(ob, 'color'):
            attrs.SetColor('user:Cs', ob.color[:3])
        
        sg_node.EditAttributeEnd(attrs)       

    def export_mesh(self, ob, sg_node, motion_data=None, prim_type="POLYGON_MESH"):

        if prim_type not in ['POLYGON_MESH', 'SUBDIVISION_MESH']:
            return False

        is_deforming = False
        mesh = None
        time_samples = []
        #if motion_data is not None and isinstance(motion_data, list) and len(motion_data):
        #    time_samples = [sample[0] for sample in motion_data]            
        #    is_deforming = True
        #    mesh = motion_data[0][1]
        #else:
        #    mesh = create_mesh(ob, self.scene)
        mesh = create_mesh(ob, self.scene)

        get_normals = (prim_type == 'POLYGON_MESH')
        (nverts, verts, P, N) = get_mesh(mesh, get_normals=get_normals)
        
        # if this is empty continue:
        if nverts == []:
            debug("error empty mesh %s" % ob.name)
            removeMeshFromMemory(mesh.name)
            return False

        nm_pts = int(len(P)/3)
        sg_node.Define( len(nverts), nm_pts, len(verts) )
        primvar = sg_node.EditPrimVarBegin()
        primvar.Clear()
        if time_samples:        
            primvar.SetTimeSamples( time_samples )

        if is_deforming:
            pts = list( zip(*[iter(P)]*3 ) )
            primvar.SetPointDetail(rman.Tokens.Rix.k_P, pts, "vertex", 0)
            origframe = self.scene.frame_current
            for sample in range(1, len(motion_data)):
                (subframe, m) = motion_data[sample]
                self.scene.frame_set(origframe, subframe=seg)
                m = create_mesh(ob, self.scene)
                P = get_mesh_points(m)
                pts = list( zip(*[iter(P)]*3 ) )
                primvar.SetPointDetail(rman.Tokens.Rix.k_P, pts, "vertex", sample)
            self.scene.frame_set(origframe, subframe=0)
        else:
            pts = list( zip(*[iter(P)]*3 ) )
            primvar.SetPointDetail(rman.Tokens.Rix.k_P, pts, "vertex")
        material_ids = get_primvars(ob, mesh, primvar, "facevarying")   

        primvar.SetIntegerDetail(rman.Tokens.Rix.k_Ri_nvertices, nverts, "uniform")
        primvar.SetIntegerDetail(rman.Tokens.Rix.k_Ri_vertices, verts, "facevarying")            

        if prim_type == "SUBDIVISION_MESH":
            creases = get_subd_creases(mesh)
            tags = ['interpolateboundary', 'facevaryinginterpolateboundary']
            nargs = [1, 0, 0, 1, 0, 0]
            intargs = [ob.data.renderman.interp_boundary,
                    ob.data.renderman.face_boundary]
            floatargs = []
            stringargs = []     

            if len(creases) > 0:
                for c in creases:
                    tags.append('crease')
                    nargs.extend([2, 1, 0])
                    intargs.extend([c[0], c[1]])
                    floatargs.append(c[2])           
                
            primvar.SetStringArray(rman.Tokens.Rix.k_Ri_subdivtags, tags, len(tags))
            primvar.SetIntegerArray(rman.Tokens.Rix.k_Ri_subdivtagnargs, nargs, len(nargs))
            primvar.SetIntegerArray(rman.Tokens.Rix.k_Ri_subdivtagintargs, intargs, len(intargs))
            primvar.SetFloatArray(rman.Tokens.Rix.k_Ri_subdivtagfloatargs, floatargs, len(floatargs))
            primvar.SetStringArray(rman.Tokens.Rix.k_Ri_subdivtagstringtags, stringargs, len(stringargs))

            # TODO make this selectable
            sg_node.SetScheme(rman.Tokens.Rix.k_catmullclark) 

        elif prim_type == "POLYGON_MESH":
            sg_node.SetScheme(None)
            primvar.SetNormalDetail(rman.Tokens.Rix.k_N, N, "facevarying")            

        if is_multi_material(mesh):
            for mat_id, faces in \
                get_mats_faces(nverts, material_ids).items():

                mat = mesh.materials[mat_id]
                mat_handle = "material.%s" % mat.name
                sg_material = None
                if mat_handle in self.sg_nodes_dict:
                    sg_material = self.sg_nodes_dict[mat_handle]

                if mat_id == 0:
                    primvar.SetIntegerArray(rman.Tokens.Rix.k_shade_faceset, faces, len(faces))
                    sg_node.SetMaterial(sg_material)
                else: 
                    sg_sub_mesh =  self.sg_scene.CreateMesh("")
                    pvars = sg_sub_mesh.EditPrimVarBegin()
                    sg_sub_mesh.Define( len(nverts), nm_pts, len(verts) )
                    if time_samples:
                        pvars.SetTimeSamples( time_samples )
                    if prim_type == "SUBDIVISION_MESH":
                        sg_sub_mesh.SetScheme(rman.Tokens.Rix.k_catmullclark)
                    pvars.Inherit(primvar)
                    pvars.SetIntegerArray(rman.Tokens.Rix.k_shade_faceset, faces, len(faces))
                    sg_sub_mesh.EditPrimVarEnd(pvars)
                    sg_sub_mesh.SetMaterial(sg_material)
                    sg_node.AddChild(sg_sub_mesh)                  
                       
        primvar.SetFloat(rman.Tokens.Rix.k_displacementbound_sphere, ob.renderman.displacementbound)
        sg_node.EditPrimVarEnd(primvar)
        if is_deforming:
            for (subframes, m) in motion_data:
                removeMeshFromMemory(m.name)
        else:
            removeMeshFromMemory(mesh.name)
        return True

    def get_curve(self, curve):
        splines = []

        for spline in curve.splines:
            P = []
            width = []
            npt = len(spline.bezier_points) * 3

            for bp in spline.bezier_points:
                P.extend(bp.handle_left)
                P.extend(bp.co)
                P.extend(bp.handle_right)
                width.append(bp.radius * 0.01)

            # basis = ["bezier", 3, "bezier", 3]
            basis = ["BezierBasis", 3, "BezierBasis", 3]
            if spline.use_cyclic_u:
                period = 'periodic'
                # wrap the initial handle around to the end, to begin on the CV
                P = P[3:] + P[:3]
            else:
                period = 'nonperiodic'
                # remove the two unused handles
                npt -= 2
                P = P[3:-3]

            name = spline.id_data.name
            splines.append((P, width, npt, basis, period, name))

        return splines        

    def export_curve(self, sg_node, ob, data):

        if ob.type == 'CURVE':
            curves = data if data is not None else self.get_curve(ob.data)

            for P, width, npt, basis, period, name in curves:
                curves_sg = self.sg_scene.CreateCurves(name)
                curves_sg.Define(rman.Tokens.Rix.k_cubic, period, "bezier", 1, int(len(P)/3))
                
                primvar = curves_sg.EditPrimVarBegin()
                primvar.SetPointDetail(rman.Tokens.Rix.k_P, P, "vertex")   
                primvar.SetIntegerDetail(rman.Tokens.Rix.k_Ri_nvertices, [npt], "uniform")
                if width:
                    primvar.SetFloatDetail(rman.Tokens.Rix.k_width, width, "vertex")
                curves_sg.EditPrimVarEnd(primvar)

                sg_node.AddChild(curves_sg)

                pass
                #ri.Basis(basis[0], basis[1], basis[2], basis[3])
                #ri.Curves("cubic", [npt], period, {"P": rib(P), "width": width})

        else:
            debug("error",
                "export_curve: recieved a non-supported object type of [%s]." %
                ob.type)  

    def export_points(self, sg_node, ob, motion):

        rm = ob.renderman

        mesh = create_mesh(ob, self.scene)
        
        primvar = sg_node.EditPrimVarBegin()

        motion_blur = None
        if motion is not None: 
            motion_blur = ob.name in motion['deformation']

        if motion_blur:
            samples = motion['deformation'][ob.name]
            primvar.SetTimeSamples([sample[0] for sample in ob])
            
        else:
            samples = [get_mesh(mesh)]
        

        nm_pts = -1
        time_sample = 0
        for nverts, verts, P, N in samples:

            if nm_pts == -1:
                nm_pts = int(len(P)/3)
                sg_node.Define(nm_pts)
            
            if motion_blur:
                primvar.SetPointDetail(rman.Tokens.Rix.k_P, P, "vertex", time_sample)
                time_sample += 1
            else:
                primvar.SetPointDetail(rman.Tokens.Rix.k_P, P, "vertex")

            primvar.SetStringDetail("type", rm.primitive_point_type, "uniform")
            primvar.SetFloatDetail(rman.Tokens.Rix.k_constantwidth, rm.primitive_point_width, "constant")
            
        primvar.SetFloat(rman.Tokens.Rix.k_displacementbound_sphere, rm.displacementbound)
        sg_node.EditPrimVarEnd(primvar)
        removeMeshFromMemory(mesh.name)       

    def export_quadrics(self, ob, prim, sg_node):
        rm = ob.renderman
        primvar = sg_node.EditPrimVarBegin()        
        if prim == 'SPHERE':
            sg_node.SetGeometry(rman.Tokens.Rix.k_Ri_Sphere)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_radius, rm.primitive_radius)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_zmin, rm.primitive_zmin)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_zmax, rm.primitive_zmax)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_thetamax, rm.primitive_sweepangle)
    
        elif prim == 'CYLINDER':
            sg_node.SetGeometry(rman.Tokens.Rix.k_Ri_Cylinder)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_radius, rm.primitive_radius)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_zmin, rm.primitive_zmin)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_zmax, rm.primitive_zmax)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_thetamax, rm.primitive_sweepangle)

        elif prim == 'CONE':
            sg_node.SetGeometry(rman.Tokens.Rix.k_Ri_Cone)
            primvar = sg_node.EditPrimVarBegin()
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_radius, rm.primitive_radius)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_height, rm.primitive_height)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_thetamax, rm.primitive_sweepangle)

        elif prim == 'DISK':
            sg_node.SetGeometry(rman.Tokens.Rix.k_Ri_Disk)
            primvar = sg_node.EditPrimVarBegin()
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_radius, rm.primitive_radius)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_height, rm.primitive_height)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_thetamax, rm.primitive_sweepangle)

        elif prim == 'TORUS':
            sg_node.SetGeometry(rman.Tokens.Rix.k_Ri_Torus)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_majorradius, rm.primitive_majorradius)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_minorradius, rm.primitive_minorradius)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_phimin, rm.primitive_phimin)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_phimax, rm.primitive_phimax)            
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_thetamax, rm.primitive_sweepangle)

        primvar.SetFloat(rman.Tokens.Rix.k_displacementbound_sphere, rm.displacementbound)
        sg_node.EditPrimVarEnd(primvar) 


    # many thanks to @rendermouse for this code
    def export_blobby_family(self, sg_node, ob):

        # we are searching the global metaball collection for all mballs
        # linked to the current object context, so we can export them
        # all as one family in RiBlobby

        family = data_name(ob, self.scene)
        master = bpy.data.objects[family]

        fam_blobs = []

        for mball in bpy.data.metaballs:
            fam_blobs.extend([el for el in mball.elements if get_mball_parent(
                el.id_data).name.split('.')[0] == family])

        # transform
        tform = []

        # opcodes
        op = []
        count = len(fam_blobs)
        for i in range(count):
            op.append(1001)  # only blobby ellipsoids for now...
            op.append(i * 16)

        for meta_el in fam_blobs:

            # Because all meta elements are stored in a single collection,
            # these elements have a link to their parent MetaBall, but NOT the actual tree parent object.
            # So I have to go find the parent that owns it.  We need the tree parent in order
            # to get any world transforms that alter position of the metaball.
            parent = get_mball_parent(meta_el.id_data)

            m = {}
            loc = meta_el.co

            # mballs that are only linked to the master by name have their own position,
            # and have to be transformed relative to the master
            ploc, prot, psc = parent.matrix_world.decompose()

            m = Matrix.Translation(loc)

            sc = Matrix(((meta_el.radius, 0, 0, 0),
                        (0, meta_el.radius, 0, 0),
                        (0, 0, meta_el.radius, 0),
                        (0, 0, 0, 1)))

            ro = prot.to_matrix().to_4x4()

            m2 = m @ sc @ ro
            tform = tform + rib(parent.matrix_world @ m2)

        op.append(0)  # blob operation:add
        op.append(count)
        for n in range(count):
            op.append(n)

        primvar = sg_node.EditPrimVarBegin()
        sg_node.Define(count)
        primvar.SetIntegerArray(rman.Tokens.Rix.k_Ri_code, op, len(op))            
        primvar.SetFloatArray(rman.Tokens.Rix.k_Ri_floats, tform, len(tform))      
        primvar.SetFloat(rman.Tokens.Rix.k_displacementbound_sphere, ob.renderman.displacementbound)           
        sg_node.EditPrimVarEnd(primvar)

    def export_openVDB(self, sg_node, ob):
        cacheFile = locate_openVDB_cache(bpy.context.scene.frame_current)
        if not cacheFile:
            debug('error', "Please save and export OpenVDB files before rendering.")
            return

        primvar = sg_node.EditPrimVarBegin() 
        primvar.SetString(rman.Tokens.Rix.k_Ri_type, "blobbydso:impl_openvdb")
        primvar.SetFloatArray(rman.Tokens.Rix.k_Ri_Bound, rib_ob_bounds(ob.bound_box), 6)
        primvar.SetStringArray(rman.Tokens.Rix.k_blobbydso_stringargs, [cacheFile, "density:fogvolume"], 2)

        primvar.SetFloatDetail("density", [], "varying")
        primvar.SetFloatDetail("flame", [], "varying")        
        primvar.SetColorDetail("color", [], "varying")      
        primvar.SetFloat(rman.Tokens.Rix.k_displacementbound_sphere, ob.renderman.displacementbound)                
        sg_node.EditPrimVarEnd(primvar)                              
     
    # make an ri Volume from the smoke modifier
    def export_smoke(self, sg_node, ob):
        smoke_modifier = None
        for mod in ob.modifiers:
            if mod.type == "SMOKE":
                smoke_modifier = mod
                break
        smoke_data = smoke_modifier.domain_settings
        # the original object has the modifier too.
        if not smoke_data:
            return

        sg_node.Define(0,0,0)
        if smoke_data.cache_file_format == 'OPENVDB':
            self.export_openVDB(sg_node, ob)
            return

        smoke_res = rib(smoke_data.domain_resolution)
        if smoke_data.use_high_resolution:
            smoke_res = [(smoke_data.amplify + 1) * i for i in smoke_res]

        primvar = sg_node.EditPrimVarBegin()
        primvar.SetString(rman.Tokens.Rix.k_Ri_type, "box")
        primvar.SetFloatArray(rman.Tokens.Rix.k_Ri_Bound, rib_ob_bounds(ob.bound_box), 6)

        primvar.SetFloatDetail("density", smoke_data.density_grid, "varying")
        primvar.SetFloatDetail("flame", smoke_data.flame_grid, "varying")        
        primvar.SetColorDetail("color", [item for index, item in enumerate(smoke_data.color_grid) if index % 4 != 0], "varying")
        primvar.SetFloatArray(rman.Tokens.Rix.k_Ri_Bound, rib_ob_bounds(ob.bound_box), 6)

        primvar.SetFloat(rman.Tokens.Rix.k_displacementbound_sphere, ob.renderman.displacementbound)
        sg_node.EditPrimVarEnd(primvar)     

    def export_geometry_data(self, ob, db_name, data=None):
        prim = ob.renderman.primitive if ob.renderman.primitive != 'AUTO' \
            else detect_primitive(ob)

        # unsupported type
        if prim == 'NONE':
            debug("WARNING", "Unsupported prim type on %s" % (ob.name))   
            return None    

        sg_node = None
        sg_node = self.sg_nodes_dict.get(db_name)

        if prim in ['POLYGON_MESH', 'SUBDIVISION_MESH']:
            if not sg_node:
                sg_node = self.sg_scene.CreateMesh(db_name)
                self.sg_nodes_dict[db_name] = sg_node
            if self.export_mesh(ob, sg_node, data, prim):
                self.export_object_primvars(ob, sg_node)                
            else:
                self.sg_scene.DeleteDagNode(sg_node)
                self.sg_nodes_dict[db_name] = None

         # mesh only
        elif prim == 'POINTS':
            if not sg_node:
                sg_node = self.sg_scene.CreatePoints(db_name)
            self.export_points(sg_node, ob, data) 
            self.sg_nodes_dict[db_name] = sg_node                       

        # curve only
        elif prim == 'CURVE' or prim == 'FONT':
            # If this curve is extruded or beveled it can produce faces from a
            # to_mesh call.
            l = ob.data.extrude + ob.data.bevel_depth
            if l > 0:
                if not sg_node:
                    sg_node = self.sg_scene.CreateMesh(db_name)
                self.export_mesh(ob, sg_node, data, prim_type="POLYGON_MESH")
                self.export_object_primvars(ob, sg_node)
                self.sg_nodes_dict[db_name] = sg_node                 
            else:
                sg_node = self.sg_scene.CreateGroup(db_name)
                self.export_curve(sg_node, ob, data)
                self.sg_nodes_dict[db_name] = sg_node   

        # RenderMan quadrics
        elif prim in ['SPHERE', 'CYLINDER', 'CONE', 'DISK', 'TORUS']:
            if not sg_node:
                sg_node = self.sg_scene.CreateQuadric(db_name)
            self.export_quadrics(ob, prim, sg_node)
            self.sg_nodes_dict[db_name] = sg_node 

        elif prim == 'RI_VOLUME':
            rm = ob.renderman
            if not sg_node:
                sg_node = self.sg_scene.CreateVolume(db_name)
            sg_node.Define(0,0,0)
            primvar = sg_node.EditPrimVarBegin()
            primvar.SetString(rman.Tokens.Rix.k_Ri_type, "box")
            primvar.SetFloatArray(rman.Tokens.Rix.k_Ri_Bound, rib_ob_bounds(ob.bound_box), 6)
            sg_node.EditPrimVarEnd(primvar)            

            self.sg_nodes_dict[db_name] = sg_node   

        elif prim == 'META':
            if not sg_node:
                sg_node = self.sg_scene.CreateBlobby(db_name)
            self.export_blobby_family(sg_node, ob)  
            self.sg_nodes_dict[db_name] = sg_node            

        elif prim == 'SMOKE':
            if not sg_node:
                sg_node = self.sg_scene.CreateVolume(db_name)
            self.export_smoke(sg_node, ob)                    
            self.sg_nodes_dict[db_name] = sg_node               
                            

        return sg_node  

    def geometry_source_rib(self, ob, db_name):
        rm = ob.renderman
        anim = rm.archive_anim_settings
        blender_frame = self.scene.frame_current

        if rm.geometry_source == 'ARCHIVE':
            archive_path = \
                rib_path(get_sequence_path(rm.path_archive, blender_frame, anim))

            sg_node = self.sg_scene.CreateProcedural(db_name)
            sg_node.Define("DelayedReadArchive", None)
            primvar = sg_moode.EditPrimVarBegin()
            primvar.SetString(rman.Tokens.Rix.k_filename, archive_path)
            bound = (-1, 1, -1, 1, -1, 1)
            primvar.SetFloatArray(rman.Tokens.Rix.k_bound, bound, 6)
            sg_node.EditPrimVarEnd(primvar)
            
            self.sg_nodes_dict[db_name] = sg_node

        else:
            if rm.procedural_bounds == 'MANUAL':
                min = rm.procedural_bounds_min
                max = rm.procedural_bounds_max
                bounds = [min[0], max[0], min[1], max[1], min[2], max[2]]
            else:
                bounds = rib_ob_bounds(ob.bound_box)

            if rm.geometry_source == 'DELAYED_LOAD_ARCHIVE':
                archive_path = rib_path(get_sequence_path(rm.path_archive,
                                                        blender_frame, anim))
                bounds = (-100000, 100000, -100000, 100000, -100000, 100000 )
                sg_node = self.sg_scene.CreateProcedural(db_name)
                sg_node.Define("DelayedReadArchive", None)
                primvar = sg_moode.EditPrimVarBegin()
                primvar.SetString(rman.Tokens.Rix.k_filename, archive_path)
                primvar.SetFloatArray(rman.Tokens.Rix.k_bound, bounds, 6)
                sg_node.EditPrimVarEnd(primvar)
            
                self.sg_nodes_dict[db_name] = sg_node


            elif rm.geometry_source == 'PROCEDURAL_RUN_PROGRAM':
                path_runprogram = rib_path(rm.path_runprogram)
                bounds = (-100000, 100000, -100000, 100000, -100000, 100000 )
                sg_node = self.sg_scene.CreateProcedural(db_name)
                sg_node.Define(rman.Tokens.Rix.k_RunProgram, None)
                primvar = sg_node.EditPrimVarBegin()
                primvar.SetString(rman.Tokens.Rix.k_filename, path_runprogram)
                primvar.SetString(rman.Tokens.Rix.k_data, rm.path_runprogram_args )
                primvar.SetFloatArray(rman.Tokens.Rix.k_bound, bounds, 6)
                sg_node.EditPrimVarEnd(primvar)    

                self.sg_nodes_dict[db_name] = sg_node                              

            elif rm.geometry_source == 'DYNAMIC_LOAD_DSO':
                path_dso = rib_path(rm.path_dso)
                bounds = (-100000, 100000, -100000, 100000, -100000, 100000 )
                sg_node = self.sg_scene.CreateProcedural(db_name)
                sg_node.Define(rman.Tokens.Rix.k_DynamicLoad, None)
                primvar = sg_node.EditPrimVarBegin()
                primvar.SetString(rman.Tokens.Rix.k_dsoname, path_dso)
                primvar.SetString(rman.Tokens.Rix.k_data, rm.path_dso_initial_data )
                primvar.SetFloatArray(rman.Tokens.Rix.k_bound, bounds, 6)
                sg_node.EditPrimVarEnd(primvar)    

                self.sg_nodes_dict[db_name] = sg_node                        

            elif rm.geometry_source == 'OPENVDB':
                openvdb_file = rib_path(replace_frame_num(rm.path_archive))
                sg_node = self.sg_scene.CreateVolume(db_name)
                sg_node.Define(0,0,0)
                primvar = sg_node.EditPrimVarBegin() 
                primvar.SetString(rman.Tokens.Rix.k_Ri_type, "blobbydso:impl_openvdb")
                primvar.SetFloatArray(rman.Tokens.Rix.k_Ri_Bound, rib(bounds), 6)
                primvar.SetStringArray(rman.Tokens.Rix.k_blobbydso_stringargs, [openvdb_file, "density:fogvolume"], 2)
                for channel in rm.openvdb_channels:
                    if channel.type == "float":
                        primvar.SetFloatDetail(channel.name, [], "varying")
                    elif channel.type == "vector":
                        primvar.SetVectorDetail(channel.name, [], "varying")
                    elif channel.type == "color":    
                        primvar.SetColorDetail(channel.name, [], "varying")
                    elif channel.type == "normal":    
                        primvar.SetNormalDetail(channel.name, [], "varying")                    
             
                sg_node.EditPrimVarEnd(primvar)  
                self.sg_nodes_dict[db_name] = sg_node           
                                
    def export_mesh_archive(self, data_block):
        # if we cached a deforming mesh get it.
        motion_data = data_block.motion_data if data_block.deforming else None
        ob = data_block.data
        rm = ob.renderman

        if rm.geometry_source == 'BLENDER_SCENE_DATA':
            self.export_geometry_data(ob, data_block.name, motion_data)
        else:
            self.geometry_source_rib(ob, data_block.name)

        data_block.motion_data = None

    def export_displayfilters(self):
        rm = self.scene.renderman
        display_filter_names = []
        displayfilters_list = []
        
        self.displayfilters_list = list()

        for i, df in enumerate(rm.display_filters):
            df_name = df.name
            if df.name == "":
                df_name = "rman_displayfilter_filter%d" % i

            df_node = self.sg_scene.CreateNode("DisplayFilter", df.get_filter_name(), df_name)
            params = df_node.EditParameterBegin()
            property_group_to_rixparams(df.get_filter_node(), df_node)
            df_node.EditParameterEnd(params)
            display_filter_names.append(df_name)
            self.displayfilters_list.append(df_node)
            self.sg_nodes_dict[df_name] = df_node

        if len(display_filter_names) > 1:
            df_name = "rman_displayfilter_combiner"
            df_node = None
            if df_name in self.sg_nodes_dict:
                df_node = self.sg_nodes_dict[df_name]
            else:
                df_node = self.sg_scene.CreateNode("DisplayFilter", "PxrDisplayFilterCombiner", df_name)
            params = df_node.EditParameterBegin()
            params.ReferenceDisplayFilterArray("filter", display_filter_names, len(display_filter_names))
            df_node.EditParameterEnd(params)
            self.displayfilters_list.append(df_node)
            self.sg_nodes_dict[df_name] = df_node

        self.sg_scene.SetDisplayFilter(self.displayfilters_list)
                 
    def export_samplefilters(self):
        rm = self.scene.renderman
        sample_filter_names = []
        
        self.samplefilters_list = list()

        for i, df in enumerate(rm.sample_filters):
            df_name = df.name
            if df.name == "":
                df_name = "rman_samplefilter_filter%d" % i

            df_node = self.sg_scene.CreateNode("SampleFilter", df.get_filter_name(), df_name)
            params = df_node.EditParameterBegin()
            property_group_to_rixparams(df.get_filter_node(), df_node)
            df_node.EditParameterEnd(params)
            sample_filter_names.append(df_name)
            self.samplefilters_list.append(df_node)
            self.sg_nodes_dict[df_name] = df_node

        if rm.do_holdout_matte != "OFF":
            df_node = self.sg_scene.CreateNode("SampleFilter", "PxrShadowFilter", "rm_PxrShadowFilter_shadows")
            params = df_node.EditParameterBegin()
            params.SetString("occludedAov", "occluded")
            params.SetString("unoccludedAov", "holdoutMatte")
            if rm.do_holdout_matte == "ALPHA":
                params.SetString("shadowAov", "a")
            else:
                params.SetString("shadowAov", "holdoutMatte")

            df_node.EditParameterEnd(params)
            sample_filter_names.append("rm_PxrShadowFilter_shadows")
            self.samplefilters_list.append(df_node)
            self.sg_nodes_dict["rm_PxrShadowFilter_shadow"] = df_node            

        if len(sample_filter_names) > 1:
            df_name = "rman_samplefilter_combiner"
            df_node = None
            if df_name in self.sg_nodes_dict:
                df_node = self.sg_nodes_dict[df_name]
            else:
                df_node = self.sg_scene.CreateNode("SampleFilter", "PxrSampleFilterCombiner", df_name)
            params = df_node.EditParameterBegin()
            params.ReferenceDisplayFilterArray("filter", display_filter_names, len(display_filter_names))
            df_node.EditParameterEnd(params)
            self.samplefilters_list.append(df_node)
            self.sg_nodes_dict[df_name] = df_node

        self.sg_scene.SetSampleFilter(self.samplefilters_list)                    

    def export_integrator(self, preview=False):
        rm = self.scene.renderman
        integrator = rm.integrator
        if preview or self.rpass.is_interactive:
            integrator = "PxrPathTracer"

        integrator_settings = getattr(rm, "%s_settings" % integrator)

        integrator_sg = self.sg_scene.CreateNode("Integrator", integrator, "integrator")
        self.sg_scene.SetIntegrator(integrator_sg)
        property_group_to_rixparams(integrator_settings, integrator_sg)

    def export_transform(self, instance, sg_node):
        ob = instance.ob

        if instance.transforming and len(instance.motion_data) > 0:
            samples = [sample[1] for sample in instance.motion_data]
        else:
            samples = [ob.matrix_local] if ob.parent and ob.parent_type == "object" and ob.type != 'LIGHT'\
                else [ob.matrix_world]

        transforms = []
        for m in samples:
            #if instance.type == 'LIGHT':
            #    m = modify_light_matrix(m.copy(), ob)

            v = convert_matrix(m)
            transforms.append(v)

        if len(instance.motion_data) > 1:
            time_samples = [sample[0] for sample in instance.motion_data]
            sg_node.SetTransform( len(instance.motion_data), transforms, time_samples )
        else:
            sg_node.SetTransform( transforms[0] )

    def export_light(self, ob, light, handle, rm, portal_parent=''):

        group_name=get_light_group(ob)
        light_filters = []

        light_sg = self.sg_scene.CreateAnalyticLight(handle)
        
        for lf in rm.light_filters:
            if lf.filter_name in bpy.data.objects:
                light_filter_sg = None
                light_filter = bpy.data.objects[lf.filter_name]

                if light_filter.data.name in self.sg_nodes_dict:
                    lightf_filter_sg = self.sg_nodes_dict[light_filter.name]
                    self.lightfilters_dict[light_filter.name].append(handle)
                else:

                    filter_plugin = light_filter.data.renderman.get_light_node()  

                    lightfilter_name = light_filter.data.renderman.get_light_node_name()
                    light_filter_sg = self.sg_scene.CreateNode("LightFilter", lightfilter_name, light_filter.name)
                    property_group_to_rixparams(filter_plugin, light_filter_sg)

                    coordsys_name = "%s_coordsys" % light_filter.name
                    rixparams = light_filter_sg.EditParameterBegin()
                    rixparams.SetString("coordsys", coordsys_name)
                    light_filter_sg.EditParameterEnd(rixparams)              

                    self.sg_nodes_dict[light_filter.name] = light_filter_sg
                    
                    coordsys = self.sg_scene.CreateGroup(coordsys_name)
                    m = convert_matrix( light_filter.matrix_world )
                    coordsys.SetTransform(m)
                    self.sg_root.AddChild(coordsys)
                    light_sg.AddCoordinateSystem(coordsys)

                    self.sg_nodes_dict[coordsys_name] = coordsys
                    self.lightfilters_dict[light_filter.name] = [handle]

                if light_filter_sg:
                    light_filters.append(light_filter_sg)

        if len(light_filters) > 0:
            light_sg.SetLightFilter(light_filters)
        
        light_shader = rm.get_light_node()

        node_sg = None            
        light_shader_name = ''
        if light_shader:
            light_shader_name = rm.get_light_node_name()

            node_sg = self.sg_scene.CreateNode("LightFactory", light_shader_name , handle)
            property_group_to_rixparams(light_shader, node_sg)
            
            rixparams = node_sg.EditParameterBegin()
            rixparams.SetString('lightGroup',group_name)
            if hasattr(light_shader, 'iesProfile'):
                rixparams.SetString('iesProfile',  bpy.path.abspath(
                    light_shader.iesProfile) )

            if light.type == 'SPOT':
                rixparams.SetFloat('coneAngle', math.degrees(light.spot_size))
                rixparams.SetFloat('coneSoftness',light.spot_blend)
            if light.type in ['SPOT', 'POINT']:
                rixparams.SetInteger('areaNormalize', 1)

            # portal params
            if rm.renderman_type == 'PORTAL' and portal_parent and portal_parent.type == 'LIGHT' \
                    and portal_parent.data.renderman.renderman_type == 'ENV':
                parent_node = portal_parent.data.renderman.get_light_node()
                parent_params = property_group_to_params(parent_node)
                params = property_group_to_params(light_shader)

                rixparams.SetString('portalName', handle)
                rixparams.SetString('domeColorMap', parent_params['string lightColorMap'])

                if 'vector colorMapGamma' in params and params['vector colorMapGamma'] == (1.0, 1.0, 1.0):
                    rixparams.SetVector('colorMapGamma', parent_params['vector colorMapGamma'] )
                if 'float colorMapSaturation' in params and params['float colorMapSaturation'] == 1.0:
                    rixparams.SetFloat('colorMapSaturation', parent_params[
                        'float colorMapSaturation'] ) 
                rixparams.SetFloat('intensity', parent_params['float intensity'])
                rixparams.SetFloat('exposure', parent_params['float exposure'])
                rixparams.SetColor('lightColor', parent_params['color lightColor'])
                if not params['int enableTemperature']:
                    rixparams.SetInteger('enableTemperature', parent_params['int enableTemperature'])
                    rixparams.SetFloat('temperature', parent_params['float temperature'])                    
                rixparams.SetFloat('specular', params['float specular'] * parent_params['float specular'])
                rixparams.SetFloat('diffuse', params['float diffuse'] * parent_params['float diffuse'])

                orient_mtx = Matrix()
                orient_mtx[0][0] = s_orientPxrLight[0]
                orient_mtx[1][0] = s_orientPxrLight[1]
                orient_mtx[2][0] = s_orientPxrLight[2]
                orient_mtx[3][0] = s_orientPxrLight[3]

                orient_mtx[0][1] = s_orientPxrLight[4]
                orient_mtx[1][1] = s_orientPxrLight[5]
                orient_mtx[2][1] = s_orientPxrLight[6]
                orient_mtx[3][1] = s_orientPxrLight[7]

                orient_mtx[0][2] = s_orientPxrLight[8]
                orient_mtx[1][2] = s_orientPxrLight[9]
                orient_mtx[2][2] = s_orientPxrLight[10]
                orient_mtx[3][2] = s_orientPxrLight[11]

                orient_mtx[0][3] = s_orientPxrLight[12]
                orient_mtx[1][3] = s_orientPxrLight[13]
                orient_mtx[2][3] = s_orientPxrLight[14]
                orient_mtx[3][3] = s_orientPxrLight[15]
                
                portal_mtx = orient_mtx * Matrix(ob.matrix_world)                   
                dome_mtx = Matrix(portal_parent.matrix_world)
                dome_mtx.invert()
                mtx = portal_mtx * dome_mtx  
                 
                rixparams.SetMatrix('portalToDome', convert_matrix(mtx) )

            node_sg.EditParameterEnd(rixparams)
            light_sg.SetLight(node_sg)

            primary_vis = rm.light_primary_visibility
            attrs = light_sg.EditAttributeBegin()
            attrs.SetInteger("visibility:camera", int(primary_vis))
            attrs.SetInteger("visibility:transmission", 0)
            attrs.SetInteger("visibility:indirect", 0)
            obj_groups_str = "World,%s" % handle
            attrs.SetString(rman.Tokens.Rix.k_grouping_membership, obj_groups_str)
            attrs.SetInteger(rman.Tokens.Rix.k_identifier_id, self.obj_id)
            self.obj_hash[self.obj_id] = handle
            self.obj_id += 1
            light_sg.EditAttributeEnd(attrs)

        else:
            names = {'POINT': 'PxrSphereLight', 'SUN': 'PxrEnvDayLight',
                    'SPOT': 'PxrDiskLight', 'HEMI': 'PxrDomeLight', 'AREA': 'PxrRectLight'}
            light_shader_name = names[light.type]
            exposure = light.energy / 200.0
            if light.type == 'SUN':
                exposure = 0
            node_sg = self.sg_scene.CreateNode("LightFactory", light_shader_name , "light")
            rixparams = node_sg.EditParameterBegin()
            rixparams.SetFloat("exposure", exposure)
            rixparams.SetColor("lightColor", rib(light.color))
            if light.type not in ['HEMI', 'SUN']:
                rixparams.SetInteger('areaNormalize', 1)
            node_sg.EditParameterEnd(rixparams)

            light_sg.SetLight(node_sg)

            attrs = light_sg.EditAttributeBegin()
            attrs.SetInteger("visibility:camera", 1)
            attrs.SetInteger("visibility:transmission", 0)
            attrs.SetInteger("visibility:indirect", 0)
            obj_groups_str = "World,%s" % handle
            attrs.SetString(rman.Tokens.Rix.k_grouping_membership, obj_groups_str)
            attrs.SetInteger(rman.Tokens.Rix.k_identifier_id, self.obj_id)
            self.obj_hash[self.obj_id] = handle
            self.obj_id += 1            
            light_sg.EditAttributeEnd(attrs)              

        if  light_shader_name in ("PxrRectLight", 
                                "PxrDiskLight",
                                "PxrPortalLight",
                                "PxrSphereLight",
                                "PxrDistantLight",
                                "PxrPortalLight",
                                "PxrCylinderLight"):

            light_sg.SetOrientTransform(s_orientPxrLight)
            light_sg.SetTransform( convert_matrix(ob.matrix_world) )

        self.sg_root.AddChild(light_sg)
        self.sg_nodes_dict[handle] = light_sg
        self.mat_networks[handle] = node_sg
        self.light_filters_dict[handle] = light_filters
                
    def export_scene_lights(self, instances):
        for instance in [inst for name, inst in instances.items() if inst.type == 'LIGHT']:
            ob = instance.ob
            light = ob.data
            handle = light.name
            rm = light.renderman
            if instance.ob.data.renderman.renderman_type == 'FILTER':
                pass  
            elif instance.ob.data.renderman.renderman_type not in ['FILTER']:
                child_portals = []
                if rm.renderman_type == 'ENV' and ob.children:
                    child_portals = [child for child in ob.children if child.type == 'LIGHT' and
                             child.data.renderman.renderman_type == 'PORTAL']
                if not child_portals:
                    self.export_light(ob, light, handle, rm, ob.parent)

    def export_camera_transform(self, camera_sg, ob, motion):
        r = self.scene.render
        cam = ob.data

        times = []
        if len(motion) > 1:
            times = [sample[0] for sample in motion]

        if motion:
            samples = [sample[1] for sample in motion]
        else:
            samples = [ob.matrix_world]

        transforms = []
        for sample in samples:
            mat = sample
            v = convert_matrix(mat)

            transforms.append(v)

        self.cam_matrix = transforms[0]
        
        if len(motion) > 1:
            camera_sg.SetTransform( len(motion), transforms, times )
        else:
            camera_sg.SetTransform( transforms[0] )
            

    def export_camera(self, instances, camera_to_use=None):
        r = self.scene.render
        motion = []
        if camera_to_use:
            ob = camera_to_use
        else:
            if not self.scene.camera or self.scene.camera.type != 'CAMERA':
                return
            if self.scene.camera.name in instances:
                i = instances[self.scene.camera.name]
                ob = i.ob
                motion = i.motion_data
            else:
                ob = self.scene.camera
        cam = ob.data
        rm = self.scene.renderman

        xaspect, yaspect, aspectratio = render_get_aspect(r, cam)

        options = self.sg_scene.EditOptionBegin()

        if self.scene.renderman.motion_blur:
            shutter_interval = rm.shutter_angle / 360.0
            shutter_open, shutter_close = 0, 1
            if rm.shutter_timing == 'CENTER':
                shutter_open, shutter_close = 0 - .5 * \
                    shutter_interval, 0 + .5 * shutter_interval
            elif rm.shutter_timing == 'PRE':
                shutter_open, shutter_close = 0 - shutter_interval, 0
            elif rm.shutter_timing == 'POST':
                shutter_open, shutter_close = 0, shutter_interval
            options.SetFloatArray(rman.Tokens.Rix.k_Ri_Shutter, (shutter_open, shutter_close), 2)

        if self.scene.render.use_border and not self.scene.render.use_crop_to_border:
            min_x = self.scene.render.border_min_x
            max_x = self.scene.render.border_max_x
            if (min_x >= max_x):
                min_x = 0.0
                max_x = 1.0
            min_y = 1.0 - self.scene.render.border_min_y
            max_y = 1.0 - self.scene.render.border_max_y
            if (min_y >= max_y):
                min_y = 0.0
                max_y = 1.0

            options.SetFloatArray(rman.Tokens.Rix.k_Ri_CropWindow, (min_x, max_x, min_y, max_y), 4)

        proj = None

        if cam.renderman.projection_type != 'none':
            # use pxr Camera
            if cam.renderman.get_projection_name() == 'PxrCamera':
                lens = cam.lens
                sensor = cam.sensor_height \
                    if cam.sensor_fit == 'VERTICAL' else cam.sensor_width
                fov = 360.0 * \
                    math.atan((sensor * 0.5) / lens / aspectratio) / math.pi
            proj = self.sg_scene.CreateNode("ProjectionFactory", "PxrCamera", "proj")
            projparams = proj.EditParameterBegin()
            projparams.SetFloat("fov", fov )
            proj.EditParameterEnd(projparams)                    
            property_group_to_rixparams(cam.renderman.get_projection_node(), proj)
        elif cam.type == 'PERSP':

            lens = cam.lens

            sensor = cam.sensor_height \
                if cam.sensor_fit == 'VERTICAL' else cam.sensor_width

            fov = 360.0 * math.atan((sensor * 0.5) / lens / aspectratio) / math.pi

            #proj = self.sg_scene.CreateNode("ProjectionFactory", "PxrPerspective", "proj")            
            proj = self.sg_scene.CreateNode("ProjectionFactory", "PxrCamera", "proj")

            projparams = proj.EditParameterBegin()
            
            # 3.6 chosen arbitrarily via trial-and-error
            projparams.SetFloat("shiftX", cam.shift_x * 3.6)
            projparams.SetFloat("shiftY", cam.shift_y * 3.6)               

            projparams.SetFloat(rman.Tokens.Rix.k_fov, fov)

            if cam.dof.use_dof:
                if cam.dof.focus_object:
                    dof_distance = (ob.location - cam.dof.focus_object.location).length
                else:
                    dof_distance = cam.dof.focus_distance
                if dof_distance > 0.0:
                    projparams.SetFloat(rman.Tokens.Rix.k_fStop, cam.dof.aperture_fstop)
                    projparams.SetFloat(rman.Tokens.Rix.k_focalLength, (cam.lens * 0.001))
                    #projparams.SetFloat(rman.Tokens.Rix.k_focalLength, (cam.lens))
                    projparams.SetFloat(rman.Tokens.Rix.k_focalDistance, dof_distance)
                
                     
            proj.EditParameterEnd(projparams)
        elif cam.type == 'PANO':
            proj = self.sg_scene.CreateNode("ProjectionFactory", "PxrSphereCamera", "proj")
            projparams = proj.EditParameterBegin()
            projparams.SetFloat("hsweep", 360)
            projparams.SetFloat("vsweep", 180)
            proj.EditParameterEnd(projparams)            
        else:
            lens = cam.ortho_scale
            xaspect = xaspect * lens / (aspectratio * 2.0)
            yaspect = yaspect * lens / (aspectratio * 2.0)
            proj = self.sg_scene.CreateNode("ProjectionFactory", "PxrOrthographic", "proj")

        # convert the crop border to screen window, flip y
        resolution = render_get_resolution(self.scene.render)
        if self.scene.render.use_border and self.scene.render.use_crop_to_border:
            screen_min_x = -xaspect + 2.0 * self.scene.render.border_min_x * xaspect
            screen_max_x = -xaspect + 2.0 * self.scene.render.border_max_x * xaspect
            screen_min_y = -yaspect + 2.0 * (self.scene.render.border_min_y) * yaspect
            screen_max_y = -yaspect + 2.0 * (self.scene.render.border_max_y) * yaspect

            options.SetFloatArray(rman.Tokens.Rix.k_Ri_ScreenWindow, (screen_min_x, screen_max_x, screen_min_y, screen_max_y), 4)

            res_x = resolution[0] * (self.scene.render.border_max_x -
                                    self.scene.render.border_min_x)
            res_y = resolution[1] * (self.scene.render.border_max_y -
                                    self.scene.render.border_min_y)

            options.SetIntegerArray(rman.Tokens.Rix.k_Ri_FormatResolution, (int(res_x), int(res_y)), 2)
            options.SetFloat(rman.Tokens.Rix.k_Ri_FormatPixelAspectRatio, 1.0)        
        else:            
            if cam.type == 'PANO':
                options.SetFloatArray(rman.Tokens.Rix.k_Ri_ScreenWindow, (-1, 1, -1, 1), 4)
            else:
                options.SetFloatArray(rman.Tokens.Rix.k_Ri_ScreenWindow, (-xaspect, xaspect, -yaspect, yaspect), 4)
            if self.rpass.context:
                region = self.rpass.context.region
                print("X: %d Y: %d" % (region.width, region.height))
                options.SetIntegerArray(rman.Tokens.Rix.k_Ri_FormatResolution, (int(region.width), int(region.height)), 2)
            else:
                options.SetIntegerArray(rman.Tokens.Rix.k_Ri_FormatResolution, (resolution[0], resolution[1]), 2)
            options.SetFloat(rman.Tokens.Rix.k_Ri_FormatPixelAspectRatio, 1.0)

        self.sg_scene.EditOptionEnd(options)

        s_rightHanded = rman.Types.RtMatrix4x4(1.0,0.0,0.0,0.0,
                                    0.0,1.0,0.0,0.0,
                                    0.0,0.0,-1.0,0.0,
                                    0.0,0.0,0.0,1.0)

        group = self.sg_scene.CreateGroup("group")
        self.sg_root.AddChild(group)

        camera = self.sg_scene.CreateCamera("camera")
        camera.SetProjection(proj)

        prop = camera.EditPropertyBegin()

        # clipping planes         
        prop.SetFloat(rman.Tokens.Rix.k_nearClip, cam.clip_start)
        prop.SetFloat(rman.Tokens.Rix.k_farClip, cam.clip_end)

        # aperture
        prop.SetInteger(rman.Tokens.Rix.k_apertureNSides, cam.dof.aperture_blades)
        prop.SetFloat(rman.Tokens.Rix.k_apertureAngle, math.degrees(cam.dof.aperture_rotation))
        prop.SetFloat(rman.Tokens.Rix.k_apertureRoundness, cam.renderman.aperture_roundness)
        prop.SetFloat(rman.Tokens.Rix.k_apertureDensity, cam.renderman.aperture_density)

        prop.SetFloat(rman.Tokens.Rix.k_dofaspect, cam.dof.aperture_ratio)

        camera.EditPropertyEnd(prop)

        camtransform = rman.Types.RtMatrix4x4()
        camtransform.Identity()
        camera.SetOrientTransform(s_rightHanded)

        self.export_camera_transform(camera, ob, motion)        

        group.AddChild(camera)
        camera.SetRenderable(True)
        self.sg_nodes_dict['camera'] = camera
        self.main_camera = camera

    def export_material(self, mat, mat_name):
        rm = mat.renderman
        sg_material = None
        bxdfList = []

        mat_sg_handle = 'material.%s' % get_mat_name(mat.name)
        
        if mat.node_tree:
            sg_material, bxdfList = self.shader_exporter.export_shader_nodetree(
                mat, sg_node=None, mat_sg_handle=mat_sg_handle, handle=None,
                iterate_instance=False)
        
        if not sg_material:
            sg_material = self.shader_exporter.export_simple_shader(mat, sg_node=None, mat_handle=mat_sg_handle)

        if sg_material:
            self.sg_nodes_dict[mat_sg_handle] = sg_material
            
        #self.mat_networks['material.%s' % mat_name] = bxdfList

        #for n in bxdfList:
        #    handle = n.GetHandle().CStr()
        #    self.sg_nodes_dict[handle] = n 

        return sg_material     

    # export materials
    def export_materials(self):

        for mat_name, mat in bpy.data.materials.items():

            if mat is None:
                continue
            mat_name = get_mat_name(mat_name)
            self.export_material(mat, mat_name)
       
    def write_instances(self, db_name, data_blocks, data_block, instances, instance, visible_objects=[], parent_sg_node=None):
        if db_name not in self.sg_nodes_dict.keys():
            return

        mesh_sg = self.sg_nodes_dict[db_name]
        if not mesh_sg:
            return

        if not parent_sg_node:
            parent_sg_node = self.sg_global_obj

        psys_group = None
        inst_sg = None
        instance_name = instance.name

        if instance_name in self.sg_nodes_dict:
            inst_sg = self.sg_nodes_dict[instance_name]
        else:
            inst_sg = self.sg_scene.CreateGroup(instance_name)

        if data_block.type == "PSYS":            
            ob, psys = data_block.data

            # add the particle system as a child to the mesh
            parent_db_name = data_name(ob, self.scene)
            parent_sg_node = self.sg_nodes_dict[parent_db_name]
            #psys_group = self.sg_scene.CreateGroup('')
            #psys_group.AddChild(mesh_sg)
            #parent_sg_node.AddChild(psys_group)
            parent_sg_node.AddChild(mesh_sg)
        else:
            if data_block.type == "DUPLI":
                pass
            else:
                inst_mesh_name = '%s.%s' % (instance_name, db_name)
                inst_mesh_sg = self.sg_scene.CreateGroup(inst_mesh_name)
                inst_mesh_sg.AddChild(mesh_sg)
                self.export_transform(instance, inst_mesh_sg)
                inst_sg.AddChild(inst_mesh_sg)   
                self.sg_nodes_dict[inst_mesh_name] = inst_mesh_sg            

        for mat in data_block.material:
            if not hasattr(mat, 'name'):
                continue
            mat_name = get_mat_name(mat.name)
            mat_key = 'material.%s' % mat_name
            if mat_key in self.sg_nodes_dict.keys():
                sg_material = self.sg_nodes_dict[mat_key]
                if data_block.type == "PSYS":
                    rm = psys.settings.renderman
                    if rm.particle_type == "OBJECT" and rm.use_object_material:
                        continue
                    mesh_sg.SetMaterial(sg_material)
                else:
                    inst_sg.SetMaterial(sg_material)             


        self.export_object_attributes(instance.ob, inst_sg, visible_objects, instance_name)      

        if data_block.type == "PSYS":
            return                          
        elif data_block.type == "DUPLI":
            # if this is a dupli, directly add to the global node
            # duplis are already in world space
            self.sg_global_obj.AddChild(mesh_sg)
        else:
            parent_sg_node.AddChild(inst_sg)        
        self.sg_nodes_dict[instance_name] = inst_sg
    
    def export_displays(self):
        rm = self.scene.renderman
        sg_displays = []
        displaychannels = []

        # if IPR mode, always use it
        if self.ipr_mode:
            display_driver = 'it'
        else:
            display_driver = self.rpass.display_driver

        if self.use_python_dspy:
            display_driver = 'python'
            main_display = ""

        else:
            self.rpass.output_files = []
            addon_prefs = get_addon_prefs()
            main_display = user_path(
            addon_prefs.path_display_driver_image, scene=self.scene, display_driver=self.rpass.display_driver)         

        debug("info", "Main_display: " + main_display)

        displaychannel = self.sg_scene.CreateDisplayChannel(rman.Tokens.Rix.k_color, "Ci")
        displaychannels.append(displaychannel)
        displaychannel = self.sg_scene.CreateDisplayChannel(rman.Tokens.Rix.k_float, "a")
        displaychannels.append(displaychannel)
                
        display = self.sg_scene.CreateDisplay(display_driver, main_display)
        display.channels = "Ci,a"
        
        if display_driver == 'it':
            dspy_info = make_dspy_info(self.scene)
            port = self.start_cmd_server()
            dspy_callback = "dspyRender"
            if self.ipr_mode:
                dspy_callback = "dspyIPR"
            display.params.SetString("dspyParams", 
                                    "%s -port %d -crop 1 0 1 0 -notes %s" % (dspy_callback, port, dspy_info))
        elif display_driver == "openexr":
            display.params.SetInteger("asrgba", 1)
            export_metadata(self.scene, display.params)

        sg_displays.append(display)

        self.rpass.output_files.append(main_display) 

        if self.use_python_dspy:
            # early out
            self.main_camera.SetDisplay(sg_displays)
            self.sg_scene.SetDisplayChannel(displaychannels)            
            return

        if self.ipr_mode:
            # add ID display
            display = self.sg_scene.CreateDisplay("it", "_id")
            displaychannel = self.sg_scene.CreateDisplayChannel("integer", "id")
            displaychannels.append(displaychannel)
            display.channels = "id"
            sg_displays.append(display)

        for layer in self.scene.view_layers:
            break
            # custom aovs
            rm_rl = None
            for render_layer_settings in rm.render_layers:
                if layer.name == render_layer_settings.render_layer:
                    rm_rl = render_layer_settings
                    break

            layer_name = layer.name.replace(' ', '')

            # there's no render layer settins
            if not rm_rl:
                # so use built in aovs
                aovs = [
                    # (name, do?, declare type/name, source)
                    ("z", layer.use_pass_z, rman.Tokens.Rix.k_float, None),
                    ("Nn", layer.use_pass_normal, rman.Tokens.Rix.k_normal, None),
                    ("dPdtime", layer.use_pass_vector, rman.Tokens.Rix.k_vector, None),
                    ("u", layer.use_pass_uv, rman.Tokens.Rix.k_float, None),
                    ("v", layer.use_pass_uv, rman.Tokens.Rix.k_float, None),
                    ("id", layer.use_pass_object_index, rman.Tokens.Rix.k_float, None),
                    ("shadows", layer.use_pass_shadow, rman.Tokens.Rix.k_color,
                    "color lpe:shadowcollector"),
                    ("reflection", layer.use_pass_reflection, rman.Tokens.Rix.k_color,
                    "color lpe:reflectioncollector"),
                    ("diffuse", layer.use_pass_diffuse_direct, rman.Tokens.Rix.k_color,
                    "color lpe:diffuse"),
                    ("indirectdiffuse", layer.use_pass_diffuse_indirect,
                    rman.Tokens.Rix.k_color, "color lpe:indirectdiffuse"),
                    ("albedo", layer.use_pass_diffuse_color, rman.Tokens.Rix.k_color,
                    "color lpe:nothruput;noinfinitecheck;noclamp;unoccluded;overwrite;C(U2L)|O"),
                    ("specular", layer.use_pass_glossy_direct, rman.Tokens.Rix.k_color,
                    "color lpe:specular"),
                    ("indirectspecular", layer.use_pass_glossy_indirect,
                    rman.Tokens.Rix.k_color, "color lpe:indirectspecular"),
                    ("subsurface", layer.use_pass_subsurface_indirect,
                    rman.Tokens.Rix.k_color, "color lpe:subsurface"),
                    ("refraction", layer.use_pass_refraction, rman.Tokens.Rix.k_color,
                    "color lpe:refraction"),
                    ("emission", layer.use_pass_emit, rman.Tokens.Rix.k_color,
                    "color lpe:emission"),
                ]

                # declare display channels
                for aov, doit, declare_type, source in aovs:
                    if doit and declare_type:
                        
                        displaychannel = self.sg_scene.CreateDisplayChannel(declare_type, aov)
                        if source:
                            if "lpe" in source:
                                displaychannel.params.SetString(rman.Tokens.Rix.k_source, '%s %s' % (declare_type, source))                                
                            else:
                                displaychannel.params.SetString(rman.Tokens.Rix.k_source, source)
                        displaychannels.append(displaychannel)

                # exports all AOV's
                for aov, doit, declare, source in aovs:
                    if doit:
                        dspy_name = user_path(
                            addon_prefs.path_aov_image, scene=self.scene, display_driver=self.rpass.display_driver,
                            layer_name=layer_name, pass_name=aov)

                        display = self.sg_scene.CreateDisplay(display_driver, dspy_name)
                        display.channels = aov
                        sg_displays.append(display)
                        self.rpass.output_files.append(dspy_name)

            # else we have custom rman render layer settings
            else:
                for aov in rm_rl.custom_aovs:
                    aov_name = aov.name.replace(' ', '')
                    # if theres a blank name we can't make a channel
                    if not aov_name:
                        continue
                    source_type, source = aov.aov_name.split()
                    if source == 'rgba':
                        continue

                    exposure_gain = aov.exposure_gain
                    exposure_gamma = aov.exposure_gamma
                    remap_a = aov.remap_a
                    remap_b = aov.remap_b
                    remap_c = aov.remap_c
                    quantize_zero = aov.quantize_zero
                    quantize_one = aov.quantize_one
                    quantize_min = aov.quantize_min
                    quantize_max = aov.quantize_max
                    pixel_filter = aov.aov_pixelfilter
                    stats = aov.stats_type
                    pixelfilter_x = aov.aov_pixelfilter_x
                    pixelfilter_y = aov.aov_pixelfilter_y
                    channel_name = get_channel_name(aov, layer_name)

                    if channel_name == '':
                        continue

                    displaychannel = self.sg_scene.CreateDisplayChannel(source_type, channel_name)
                    displaychannels.append(displaychannel)

                    if aov.aov_name == "color custom_lpe":
                        source = aov.custom_lpe_string

                    # light groups need to be surrounded with '' in lpes
                    G_string = "'%s'" % rm_rl.object_group if rm_rl.object_group != '' else ""
                    LG_string = "'%s'" % rm_rl.light_group if rm_rl.light_group != '' else ""
                    try:
                        source = source.replace("%G", G_string)
                        source = source.replace("%LG", LG_string)
                    except:
                        pass

                    if "lpe" in source:
                        displaychannel.params.SetString(rman.Tokens.Rix.k_source, '%s %s' % (source_type, source))
                    else:
                        displaychannel.params.SetString(rman.Tokens.Rix.k_source, source)

                    displaychannel.params.SetFloatArray("exposure", [exposure_gain, exposure_gamma], 2)
                    displaychannel.params.SetFloatArray("remap", [remap_a, remap_b, remap_c], 3)
                    displaychannel.params.SetFloatArray("quantize", [quantize_zero, quantize_one, quantize_min, quantize_max], 4)

                    if pixel_filter != 'default':
                        displaychannel.params.SetString("filter", pixel_filter)
                        displaychannel.params.SetFloatArray("filterwidth", [pixelfilter_x, pixelfilter_y], 2 )

                    if stats != 'none':
                        displaychannel.params.SetString("statistics", stats)

                # if this is a multilayer combine em!
                if not self.ipr_mode and rm_rl.export_multilayer and self.rpass.external_render:
                    channels = []
                    for aov in rm_rl.custom_aovs:
                        channel_name = get_channel_name(aov, layer_name)
                        channels.append(channel_name)

                    out_type, ext = ('openexr', 'exr')
                    if rm_rl.use_deep:
                        channels = [x for x in channels if not (
                            "z_back" in x or 'z_depth' in x)]
                        out_type, ext = ('deepexr', 'exr')                        

                    dspy_name = user_path(
                        addon_prefs.path_aov_image, scene=self.scene, display_driver=self.rpass.display_driver,
                        layer_name=layer_name, pass_name='multilayer')

                    display = self.sg_scene.CreateDisplay(out_type, dspy_name)
                    display.channels = ',' . join(channels)
                    if rm.use_metadata:
                        export_metadata(self.scene, display.params)

                    display.params.SetString("storage", rm_rl.exr_storage)
                    if rm_rl.exr_format_options != 'default':
                        display.params.SetString("type", rm_rl.exr_format_options)
                    if rm_rl.exr_compression != 'default':
                        display.params.SetString("compression", rm_rl.exr_compression)
                    if channels[0] == "Ci,a" and not rm.spool_denoise_aov and not rm.enable_checkpoint:
                        display.params.SetInteger("asrgba", 1)

                    sg_displays.append(display)


                else:
                    for aov in rm_rl.custom_aovs:
                        aov_name = aov.name.replace(' ', '')
                        aov_channel_name = get_channel_name(aov, layer_name)
                        if aov_channel_name == '':
                            continue

                        if aov_channel_name == 'Ci,a':
                            continue

                        if layer == self.scene.view_layers[0] and aov == 'rgba':
                            # we already output this skip
                            continue

                        dspy_name = user_path(
                            addon_prefs.path_aov_image, scene=self.scene, display_driver=self.rpass.display_driver,
                            layer_name=layer_name, pass_name=aov_name)
                        self.rpass.output_files.append(dspy_name)

                        display = self.sg_scene.CreateDisplay(display_driver, dspy_name)
                        display.channels = aov_channel_name

                        if rm.use_metadata:
                            export_metadata(self.scene, display.params)
                        if not rm.spool_denoise_aov and not rm.enable_checkpoint:
                            display.params.SetInteger("asrgba", 1)

                        sg_displays.append(display)


        if (rm.do_denoise and not self.rpass.external_render or rm.external_denoise and self.rpass.external_render) and not self.rpass.is_interactive:
            # add display channels for denoising
            
            if display_driver == "openexr":

                denoise_aovs = [
                    # (name, declare type/name, source, statistics, filter)
                    ("Ci", rman.Tokens.Rix.k_color, None, None, None),
                    ("a", rman.Tokens.Rix.k_float, None, None, None),
                    ("mse", rman.Tokens.Rix.k_color, 'color Ci', 'mse', None),
                    ("albedo", rman.Tokens.Rix.k_color,
                    'color lpe:nothruput;noinfinitecheck;noclamp;unoccluded;overwrite;C(U2L)|O',
                    None, None),
                    ("albedo_var", rman.Tokens.Rix.k_color, 'color lpe:nothruput;noinfinitecheck;noclamp;unoccluded;overwrite;C(U2L)|O',
                    "variance", None),
                    ("diffuse", rman.Tokens.Rix.k_color, 'color lpe:C(D[DS]*[LO])|O', None, None),
                    ("diffuse_mse", rman.Tokens.Rix.k_color, 'color lpe:C(D[DS]*[LO])|O', 'mse', None),
                    ("specular", rman.Tokens.Rix.k_color, 'color lpe:CS[DS]*[LO]', None, None),
                    ("specular_mse", rman.Tokens.Rix.k_color, 'color lpe:CS[DS]*[LO]', 'mse', None),
                    ("zfiltered", rman.Tokens.Rix.k_float, 'zfiltered', None, True),
                    ("zfiltered_var", rman.Tokens.Rix.k_float, 'zfiltered', "variance", True),
                    ("normal", rman.Tokens.Rix.k_normal, 'normal Nn', None, None),
                    ("normal_var", rman.Tokens.Rix.k_normal, 'normal Nn', "variance", None),
                    ("forward", rman.Tokens.Rix.k_vector, 'vector motionFore', None, None),
                    ("backward", rman.Tokens.Rix.k_vector, 'vector motionBack', None, None)
                ]

                for aov, declare_type, source, statistics, do_filter in denoise_aovs:
                    displaychannel = self.sg_scene.CreateDisplayChannel(declare_type, aov)
                    displaychannels.append(displaychannel)
                    if source:
                        if "lpe" in source:
                            displaychannel.params.SetString(rman.Tokens.Rix.k_source, '%s %s' % (declare_type, source))                                
                        else:
                            displaychannel.params.SetString(rman.Tokens.Rix.k_source, source)
                    if statistics:
                            displaychannel.params.SetString(rman.Tokens.Rix.k_statistics, statistics)
                    if do_filter:
                            displaychannel.params.SetString(rman.Tokens.Rix.k_filter, rm.pixelfilter)
                        
                    displaychannel.params.SetString("storage", "tiled")


                # output denoise_data.exr
                image_base, ext = main_display.rsplit('.', 1)
                display = self.sg_scene.CreateDisplay("openexr", image_base + '.variance.exr')
                display.channels = ',' . join([aov[0] for aov in denoise_aovs])

                if rm.use_metadata:
                    export_metadata(self.scene, display.params)

                sg_displays.append(display)

        if rm.do_holdout_matte != "OFF":
            # occluded
            occluded = self.sg_scene.CreateDisplayChannel(rman.Tokens.Rix.k_color, "occluded")
            source = "color lpe:holdouts;C[DS]+<L.>"
            occluded.params.SetString(rman.Tokens.Rix.k_source, source)

            display = self.sg_scene.CreateDisplay('null', 'occluded')
            display.channels = 'occluded'
            sg_displays.append(display)
            
            # holdoutMatte
            holdout_matte = self.sg_scene.CreateDisplayChannel(rman.Tokens.Rix.k_color, "holdoutMatte")
            source = "color lpe:holdouts;unoccluded;C[DS]+<L.>"
            holdout_matte.params.SetString(rman.Tokens.Rix.k_source, source)

            # user wants separate AOV for matte
            if rm.do_holdout_matte == "AOV":
                image_base, ext = main_display.rsplit('.', 1)
                drv = 'openexr'
                if self.ipr_mode:
                    drv = 'it'
                display = self.sg_scene.CreateDisplay(drv, image_base + '.holdoutMatte.exr')
                display.channels = 'holdoutMatte'
                sg_displays.append(display)

            displaychannels.append(occluded)
            displaychannels.append(holdout_matte)

        self.main_camera.SetDisplay(sg_displays)
        self.sg_scene.SetDisplayChannel(displaychannels)

    def export_global_obj_settings(self, preview=False):
        self.sg_global_obj = self.sg_scene.CreateGroup("rman_global_obj_settings")
        rm = self.scene.renderman
        r = self.scene.render

        attrs = self.sg_global_obj.EditAttributeBegin()

        max_diffuse_depth = rm.max_diffuse_depth
        max_specular_depth = rm.max_specular_depth

        if preview or self.rpass.is_interactive:
            max_diffuse_depth = rm.preview_max_diffuse_depth
            max_specular_depth = rm.preview_max_specular_depth
                    
        attrs.SetInteger(rman.Tokens.Rix.k_trace_maxdiffusedepth, max_diffuse_depth)
        attrs.SetInteger(rman.Tokens.Rix.k_trace_maxspeculardepth, max_specular_depth)

        attrs.SetFloat(rman.Tokens.Rix.k_dice_micropolygonlength, rm.shadingrate)
        attrs.SetString(rman.Tokens.Rix.k_dice_strategy, rm.dicing_strategy)                     

        if rm.dicing_strategy in ["objectdistance", "worlddistance"]:            
            attrs.SetFloat(rman.Tokens.Rix.k_dice_worlddistancelength, rm.worlddistancelength)
            
        self.sg_global_obj.EditAttributeEnd(attrs)

        self.sg_root.AddChild(self.sg_global_obj)
        

    def export_hider(self, preview=False):
        options = self.sg_scene.EditOptionBegin()
        if self.rpass.bake:
            options.SetString(rman.Tokens.Rix.k_hider, rman.Tokens.Rix.k_bake)
        else:
            rm = self.scene.renderman

            pv = rm.pixel_variance

            options.SetInteger(rman.Tokens.Rix.k_hider_maxsamples, rm.max_samples)
            options.SetInteger(rman.Tokens.Rix.k_hider_minsamples, rm.min_samples)
            options.SetInteger(rman.Tokens.Rix.k_hider_incremental, rm.incremental)

            if preview or self.rpass.is_interactive:
                options.SetInteger(rman.Tokens.Rix.k_hider_maxsamples, rm.preview_max_samples)
                options.SetInteger(rman.Tokens.Rix.k_hider_minsamples, rm.preview_min_samples)
                options.SetInteger(rman.Tokens.Rix.k_hider_incremental, 1)
                pv = rm.preview_pixel_variance

            if (not self.rpass.external_render and rm.render_into == 'blender') or (rm.integrator in ['PxrVCM', 'PxrUPBP']) or rm.enable_checkpoint:
                options.SetInteger(rman.Tokens.Rix.k_hider_incremental, 1)

            if not preview:
                options.SetFloat(rman.Tokens.Rix.k_hider_darkfalloff, rm.dark_falloff)

            if not rm.sample_motion_blur:
                options.SetInteger(rman.Tokens.Rix.k_hider_samplemotion, 0)

            options.SetFloat(rman.Tokens.Rix.k_Ri_PixelVariance, pv)

            if rm.do_denoise and not self.rpass.external_render or rm.external_denoise: # and self.rpass.external_render:
                options.SetString(rman.Tokens.Rix.k_hider_pixelfiltermode, 'importance')

        self.sg_scene.EditOptionEnd(options)            

    def export_global_options(self):
        rm = self.scene.renderman
        options = self.sg_scene.EditOptionBegin()

        # cache sizes
        options.SetInteger(rman.Tokens.Rix.k_limits_geocachememory, rm.geo_cache_size * 100)
        options.SetInteger(rman.Tokens.Rix.k_limits_opacitycachememory, rm.opacity_cache_size * 100)
        options.SetInteger(rman.Tokens.Rix.k_limits_texturememory, rm.texture_cache_size * 100)

        if rm.asfinal:
            options.SetInteger(rman.Tokens.Rix.k_checkpoint_asfinal, 1)

        options.SetInteger("user:osl:lazy_builtins", 1)
        options.SetInteger("user:osl:lazy_inputs", 1)
        
        # Set frame number 
        options.SetInteger(rman.Tokens.Rix.k_Ri_Frame, self.scene.frame_current)

        # Stats
        if rm.use_statistics:
            options.SetInteger(rman.Tokens.Rix.k_statistics_endofframe, 1)
            options.SetString(rman.Tokens.Rix.k_statistics_xmlfilename, 'stats.%04d.xml' % self.scene.frame_current)

        # LPE Tokens for PxrSurface
        options.SetString("lpe:diffuse2", "Diffuse,HairDiffuse")
        options.SetString("lpe:diffuse3", "Subsurface")
        options.SetString("lpe:specular2", "Specular,HairSpecularR")
        options.SetString("lpe:specular3", "RoughSpecular,HairSpecularTRT")
        options.SetString("lpe:specular4", "Clearcoat")
        options.SetString("lpe:specular5", "Iridescence")
        options.SetString("lpe:specular6", "Fuzz,HairSpecularGLINTS")
        options.SetString("lpe:specular7", "SingltScatter,HairSpecularTT")
        options.SetString("lpe:specular8", "Glass")
        options.SetString("lpe:user2", "Albedo,DiffuseAlbedo,SubsurfaceAlbedo,HairAlbedo")

        # Set bucket shape
        bucket_order = rm.bucket_shape.lower()
        bucket_orderorigin = []
        if rm.enable_checkpoint and not self.rpass.is_interactive:
            bucket_order = 'horizontal'
            ri.Option("bucket", {"string order": ['horizontal']})

        elif rm.bucket_shape == 'SPIRAL':
            settings = self.scene.render

            if rm.bucket_sprial_x <= settings.resolution_x and rm.bucket_sprial_y <= settings.resolution_y:
                if rm.bucket_sprial_x == -1:
                    halfX = settings.resolution_x / 2
                    debug("info", halfX)
                    bucket_orderorigin = [int(halfX), rm.bucket_sprial_y]

                elif rm.bucket_sprial_y == -1:
                    halfY = settings.resolution_y / 2
                    bucket_orderorigin = [rm.bucket_sprial_y, int(halfY)]
                else:
                    bucket_orderorigin = [rm.bucket_sprial_x, rm.bucket_sprial_y]

        options.SetString(rman.Tokens.Rix.k_bucket_order, bucket_order)
        if bucket_orderorigin:
            options.SetFloatArray(rman.Tokens.Rix.k_bucket_orderorigin, bucket_orderorigin, 2)

        self.sg_scene.EditOptionEnd(options)

    def preview_model(self, mat):

        sg_node = None
        name = "Preview"

        if mat.preview_render_type == 'SPHERE':
            sg_node = self.sg_scene.CreateQuadric(name)
            sg_node.SetGeometry(rman.Tokens.Rix.k_Ri_Sphere)
            primvar = sg_node.EditPrimVarBegin()
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_radius, 1.0)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_zmin, -1.0)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_zmax, 1.0)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_thetamax, 360)
            sg_node.EditPrimVarEnd(primvar)
        

        elif mat.preview_render_type == 'FLAT':  # FLAT PLANE
            sg_node = self.sg_scene.CreateMesh(name)        
            sg_node.Define( 1, 4, 4)
            primvar = sg_node.EditPrimVarBegin()        
            primvar.SetPointDetail(rman.Tokens.Rix.k_P, [0, -1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1], "vertex")
            primvar.SetIntegerDetail(rman.Tokens.Rix.k_Ri_nvertices, [4], "uniform")
            primvar.SetIntegerDetail(rman.Tokens.Rix.k_Ri_vertices, [0, 1, 2, 3], "facevarying")    
            sg_node.EditPrimVarEnd(primvar)
            transform = rman.Types.RtMatrix4x4()
            transform.Identity()
            transform.Scale(.75, .75, .75) 
            transform.Rotate(90, 0, 0, 1)      
            sg_node.SetTransform(transform)  
              
        elif mat.preview_render_type == 'CUBE':
            sg_node = self.sg_scene.CreateMesh(name)
            self.export_mesh(self.scene.objects[
                                'preview_cube'], sg_node)
            transform = rman.Types.RtMatrix4x4()
            transform.Identity()
            transform.Scale(.75, .75, .75) 
            sg_node.SetTransform(transform)                                               
            
        elif mat.preview_render_type == 'HAIR':
            sg_node = self.export_geometry_data(self.scene.objects[
                                'preview_hair'], name)
            transform = rman.Types.RtMatrix4x4()
            transform.Identity()
            transform.Scale(.75, .75, .75) 
            sg_node.SetTransform(transform)                                 

        elif mat.preview_render_type == 'MONKEY':
            sg_node = self.sg_scene.CreateMesh(name)
            self.export_mesh(self.scene.objects[
                                'preview_monkey'], sg_node)    

            transform = rman.Types.RtMatrix4x4()
            transform.Identity()
            transform.Scale(.75, .75, .75)
            transform.Rotate(-90, 0, 0, 1)
            sg_node.SetTransform(transform)                                                            
        else:
            pass
            """
            sg_node = self.sg_scene.CreateMesh(name)
            self.export_mesh(self.scene.objects[
                                'preview.002'], sg_node)            
            """

        return sg_node

    def write_preview_scene(self):
        org_scene = self.scene
        #self.scene = bpy.data.scenes[0]
        r = self.scene.render

        proj = self.sg_scene.CreateNode("ProjectionFactory", "PxrPerspective", "proj")
        projparams = proj.EditParameterBegin()
        projparams.SetFloat(rman.Tokens.Rix.k_fov, 37.8493)
        proj.EditParameterEnd(projparams)

        group = self.sg_scene.CreateGroup("group")
        self.sg_root.AddChild(group)

        camera = self.sg_scene.CreateCamera("camera")
        camera.SetProjection(proj)

        s_rightHanded = rman.Types.RtMatrix4x4(1.0,0.0,0.0,0.0,
                                    0.0,1.0,0.0,0.0,
                                    0.0,0.0,-1.0,0.0,
                                    0.0,0.0,0.0,1.0)

        #camtransform = rman.Types.RtMatrix4x4()
        #camtransform.Identity()
        #camera.SetOrientTransform(s_rightHanded)
        #camera.SetTransform([0, -0.25, -1, 0, 1, 0, 0, 0, 0,
        #          1, -0.25, 0, 0, -.75, 3.25, 1])

        camtransform = rman.Types.RtMatrix4x4(0, -0.25, -1, 0, 1, 0, 0, 0, 0,
                                                   1, -0.25, 0, 0, -.75, 3.25, 1)

        camtransform.Rotate(60, 0, 1, 0)
        camera.SetTransform(camtransform)

        group.AddChild(camera)
        camera.SetRenderable(True)

        if self.use_python_dspy:
            display = self.sg_scene.CreateDisplay("python", self.rpass.paths['render_output'])
            display.channels = "Ci,a"
        else:
            display = self.sg_scene.CreateDisplay("tiff", self.rpass.paths['render_output'])
            display.channels = "Ci"
        
        camera.SetDisplay(display)

        rm = self.scene.renderman
        xaspect, yaspect, aspectratio = render_get_aspect(r)
        resolution = render_get_resolution(self.scene.render)

        options = self.sg_scene.EditOptionBegin()
        options.SetFloatArray(rman.Tokens.Rix.k_Ri_ScreenWindow, [-xaspect, xaspect, -yaspect, yaspect], 4)
        options.SetIntegerArray(rman.Tokens.Rix.k_Ri_FormatResolution, (resolution[0], resolution[1]), 2)
        options.SetFloat(rman.Tokens.Rix.k_Ri_FormatPixelAspectRatio, 1.0)        
        options.SetInteger(rman.Tokens.Rix.k_hider_minsamples, rm.preview_min_samples)
        options.SetInteger(rman.Tokens.Rix.k_hider_maxsamples, rm.preview_max_samples)
        options.SetInteger(rman.Tokens.Rix.k_hider_incremental, 1)
        self.sg_scene.EditOptionEnd(options)


        integrator = "PxrPathTracer"
        integrator_settings = getattr(rm, "%s_settings" % integrator)

        integrator_sg = self.sg_scene.CreateNode("Integrator", integrator, "integrator")
        self.sg_scene.SetIntegrator(integrator_sg)
        property_group_to_rixparams(integrator_settings, integrator_sg)

        preview_rib_data_path = \
        rib_path(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                              'preview', "preview_scene.rib"))

        # preview scene: walls, lights
        proc = self.sg_scene.CreateProcedural("preview_scene.rib")
        proc.Define("DelayedReadArchive", None)
        primvar = proc.EditPrimVarBegin()
        primvar.SetString("filename", preview_rib_data_path)
        primvar.SetFloatArray("__bound", [-1, 1, -1, 1, -1, 1], 6)
        proc.EditPrimVarEnd(primvar)
        self.sg_root.AddChild(proc)

        mat = find_preview_material(self.scene)
        if mat:
            rm = mat.renderman
            sg_material = None

            if mat.node_tree:
                sg_material, bxdfList = self.shader_exporter.export_shader_nodetree(
                    mat, handle=None,
                    iterate_instance=False)
            else:
                sg_material = self.shader_exporter.export_simple_shader(mat)

            #m = rman.Types.RtMatrix4x4()
            #m.Identity()
            #m.Translate(0, 0, 0.2)
            sg_node = self.preview_model(mat)
            sg_node.SetMaterial(sg_material)
            #sg_node.SetTransform(m)
            self.sg_root.AddChild(sg_node)

        #self.scene = org_scene

        #return (mat != None)
        return True

    def get_primvars_particle(self, primvar, psys, subframes, sample):
        rm = psys.settings.renderman
        cfra = self.scene.frame_current

        for p in rm.prim_vars:
            pvars = []

            if p.data_source in ('VELOCITY', 'ANGULAR_VELOCITY'):
                if p.data_source == 'VELOCITY':
                    for pa in \
                            [p for p in psys.particles if valid_particle(p, subframes)]:
                        pvars.extend(pa.velocity)
                elif p.data_source == 'ANGULAR_VELOCITY':
                    for pa in \
                            [p for p in psys.particles if valid_particle(p, subframes)]:
                        pvars.extend(pa.angular_velocity)

                primvar.SetFloatArrayDetail(p.name, pvars, 3, "uniform", sample)

            elif p.data_source in \
                    ('SIZE', 'AGE', 'BIRTH_TIME', 'DIE_TIME', 'LIFE_TIME', 'ID'):
                if p.data_source == 'SIZE':
                    for pa in \
                            [p for p in psys.particles if valid_particle(p, subframes)]:
                        pvars.append(pa.size)
                elif p.data_source == 'AGE':
                    for pa in \
                            [p for p in psys.particles if valid_particle(p, subframes)]:
                        pvars.append((cfra - pa.birth_time) / pa.lifetime)
                elif p.data_source == 'BIRTH_TIME':
                    for pa in \
                            [p for p in psys.particles if valid_particle(p, subframes)]:
                        pvars.append(pa.birth_time)
                elif p.data_source == 'DIE_TIME':
                    for pa in \
                            [p for p in psys.particles if valid_particle(p, subframes)]:
                        pvars.append(pa.die_time)
                elif p.data_source == 'LIFE_TIME':
                    for pa in \
                            [p for p in psys.particles if valid_particle(p, subframes)]:
                        pvars.append(pa.lifetime)
                elif p.data_source == 'ID':
                    pvars = [id for id, p in psys.particles.items(
                    ) if valid_particle(p, subframes)]
                
                primvar.SetFloatDetail(p.name, pvars, "varying", sample)       

    def export_particle_points(self, sg_node, psys, ob, motion_data, objectCorrectionMatrix=False):
        rm = psys.settings.renderman
        #if(objectCorrectionMatrix):
        #    matrix = ob.matrix_world.inverted_safe()
        #    loc, rot, sca = matrix.decompose()

        primvar = sg_node.EditPrimVarBegin()
        is_deforming = False
        if len(motion_data) > 1:
            time_samples = [sample[0] for sample in motion_data]
            primvar.SetTimeSamples( time_samples )
            is_deforming = True
        else:
            primvar.SetTimeSamples([0])

        nm_pts = -1

        sample = 0
        for (i, (P, rot, width)) in motion_data:
            self.get_primvars_particle(primvar,
                psys, [self.scene.frame_current + i for (i, data) in motion_data], sample)

            m = ob.matrix_world.inverted_safe()
            P = transform_points(m, P)

            if nm_pts == -1:
                nm_pts = int(len(P)/3)
                sg_node.Define(nm_pts)           
            

            if is_deforming:
                primvar.SetPointDetail(rman.Tokens.Rix.k_P, P, "vertex", sample)
                if rm.constant_width:
                    primvar.SetFloatDetail(rman.Tokens.Rix.k_constantwidth, width, "constant", sample)
                else:
                    primvar.SetFloatDetail(rman.Tokens.Rix.k_width, width, "vertex", sample)
                sample += 1 
            else:
                primvar.SetPointDetail(rman.Tokens.Rix.k_P, P, "vertex")                   
                if rm.constant_width:
                    primvar.SetFloatDetail(rman.Tokens.Rix.k_constantwidth, width, "constant")
                else:
                    primvar.SetFloatDetail(rman.Tokens.Rix.k_width, width, "vertex")                     

        primvar.SetFloat(rman.Tokens.Rix.k_displacementbound_sphere, ob.renderman.displacementbound)
        sg_node.EditPrimVarEnd(primvar)

    # only for emitter types for now

    def get_particles(self, ob, psys, valid_frames=None):
        P = []
        rot = []
        width = []

        valid_frames = (self.scene.frame_current,
                        self.scene.frame_current) if valid_frames is None else valid_frames
       #psys.set_resolution(self.scene, ob, 'RENDER')
        for pa in [p for p in psys.particles if valid_particle(p, valid_frames)]:
            P.extend(pa.location)
            rot.extend(pa.rotation)

            if pa.alive_state != 'ALIVE':
                width.append(0.0)
            else:
                width.append(pa.size)
        #psys.set_resolution(self.scene, ob, 'PREVIEW')
        return (P, rot, width)    

    def export_blobby_particles(self, sg_node, psys, ob, motion_data):
        rm = psys.settings.renderman
        subframes = [self.scene.frame_current + i for (i, data) in motion_data]

        primvar = sg_node.EditPrimVarBegin()
        is_deforming = False
        if len(motion_data) > 1:
            time_samples = [sample[0] for sample in motion_data]
            primvar.SetTimeSamples( time_samples )
            is_deforming = True

        num_leafs = -1
        sample = 0
        for (i, (P, rot, widths)) in motion_data:
            m = ob.matrix_world.inverted_safe()
            P = transform_points(m, P)
            op = []
            count = len(widths)
            if num_leafs == -1:
                num_leafs = count
                sg_node.Define(num_leafs)

            for i in range(count):
                op.append(1001)  # only blobby ellipsoids for now...
                op.append(i * 16)
            tform = []
            for i in range(count):
                loc = Vector((P[i * 3 + 0], P[i * 3 + 1], P[i * 3 + 2]))
                rotation = Quaternion((rot[i * 4 + 0], rot[i * 4 + 1],
                                    rot[i * 4 + 2], rot[i * 4 + 3]))
                scale = rm.width if rm.constant_width else widths[i]
                mtx = Matrix.Translation(loc) @ rotation.to_matrix().to_4x4() \
                    @ Matrix.Scale(scale, 4)
                tform.extend(convert_matrix(mtx))

            op.append(0)  # blob operation:add
            op.append(count)
            for n in range(count):
                op.append(n)

            st = ('',)
            self.get_primvars_particle(primvar, psys, subframes, sample)  
            primvar.SetIntegerArray(rman.Tokens.Rix.k_Ri_code, op, len(op))            

            if is_deforming:                
                primvar.SetFloatArray(rman.Tokens.Rix.k_Ri_floats, tform, len(tform), sample)
                sample += 1                 
            else:                
                primvar.SetFloatArray(rman.Tokens.Rix.k_Ri_floats, tform, len(tform)) 
          
        primvar.SetFloat(rman.Tokens.Rix.k_displacementbound_sphere, ob.renderman.displacementbound)
        sg_node.EditPrimVarEnd(primvar)

    def export_particle_instances(self, sg_node, db_name, psys, ob, motion_data, type='OBJECT'):
        rm = psys.settings.renderman

        #params = get_primvars_particle(
        #    self.scene, psys, [self.scene.frame_current + i for (i, data) in motion_data])

        master_sg = None
        if type == 'OBJECT':
            master_ob = bpy.data.objects[rm.particle_instance_object]
            master_db_name = data_name(master_ob, self.scene)
            master_sg = self.sg_nodes_dict.get(master_db_name)

        elif type == 'sphere':
            master_sg = self.sg_scene.CreateQuadric("")
            master_sg.SetGeometry(rman.Tokens.Rix.k_Ri_Sphere)
            primvar = master_sg.EditPrimVarBegin()
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_radius, 1.0)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_zmin, -1.0)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_zmax, 1.0)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_thetamax, 360.0)
            primvar.SetFloat(rman.Tokens.Rix.k_displacementbound_sphere, ob.renderman.displacementbound)
            master_sg.EditPrimVarEnd(primvar)
        else:
            master_sg = self.sg_scene.CreateQuadric("")
            master_sg.SetGeometry(rman.Tokens.Rix.k_Ri_Disk)
            primvar = master_sg.EditPrimVarBegin()
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_radius, 1.0)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_height, 0)
            primvar.SetFloat(rman.Tokens.Rix.k_Ri_thetamax, 360.0)  
            primvar.SetFloat(rman.Tokens.Rix.k_displacementbound_sphere, ob.renderman.displacementbound)          
            primvar = master_sg.EditPrimVarBegin()
    
        
        if type == 'OBJECT' and rm.use_object_material and len(master_ob.data.materials) > 0:
            mat = master_ob.data.materials[0]
            mat_handle = 'material.%s' % mat.name
            sg_material = self.sg_nodes_dict.get(mat_handle)
            if sg_material:
                sg_node.SetMaterial(sg_material)
        
        width = rm.width

        num_points = len(motion_data[0][1][2])
        for i in range(num_points):

            inst_sg = self.sg_scene.CreateGroup('%s_%d' % (db_name, i))
            
            inst_sg.SetTransformNumSamples( len(motion_data))
            samp = 0
            for (seg, (P, rot, point_width)) in motion_data:
                m = ob.matrix_world.inverted_safe()
                P = transform_points(m, P)
                loc = Vector((P[i * 3 + 0], P[i * 3 + 1], P[i * 3 + 2]))
                rotation = Quaternion((rot[i * 4 + 0], rot[i * 4 + 1],
                                    rot[i * 4 + 2], rot[i * 4 + 3]))
                scale = width if rm.constant_width else point_width[i]
                mtx = Matrix.Translation(loc) @ rotation.to_matrix().to_4x4() \
                    @ Matrix.Scale(scale, 4)

                inst_sg.SetTransformSample(samp, convert_matrix(mtx), seg)
                samp +=1

            instance_params = {}
            #for param in params:
            #    instance_params[param] = params[param][i]

            #ri.Attribute("user", instance_params)

            inst_sg.AddChild(master_sg)
            sg_node.AddChild(inst_sg)       

    def export_particles(self, ob, psys, db_name, data=None, objectCorrectionMatrix=False):

        rm = psys.settings.renderman
        sg_node = None

        if not data:
            data = [(0, self.get_particles(ob, psys))]
        # Write object instances or points
        if rm.particle_type == 'particle':
            sg_node = self.sg_nodes_dict.get(db_name)
            if not sg_node:
                sg_node = self.sg_scene.CreatePoints(db_name)
            self.export_particle_points(sg_node, psys, ob, data,
                                objectCorrectionMatrix)
            self.sg_nodes_dict[db_name] = sg_node
        elif rm.particle_type == 'blobby':
            sg_node = self.sg_nodes_dict.get(db_name)
            if not sg_node:
                sg_node = self.sg_scene.CreateBlobby(db_name)
            self.export_blobby_particles(sg_node, psys, ob, data)
            self.sg_nodes_dict[db_name] = sg_node
        else:
            sg_node = self.sg_nodes_dict.get(db_name)
            if not sg_node:
                sg_node = self.sg_scene.CreateGroup(db_name)  
            else:
                for c in [ sg_node.GetChild(i) for i in range(0, sg_node.GetNumChildren())]:
                    sg_node.RemoveChild(c)                          
            self.export_particle_instances(sg_node, db_name, psys, ob, data, type=rm.particle_type)
            self.sg_nodes_dict[db_name] = sg_node
        return sg_node           

    def export_hair(self, sg_node, ob, psys, db_name, data, objectCorrectionMatrix=False):
        
        if data is not None and len(data) > 0:
            # deformation blur case
            num_time_samples = len(data)
            time_samples = [sample[0] for sample in data]
            num_curves = len(data[0][1])

            i = 0

            for i in range(0, num_curves):
                curves_handle = '%s-%d' % (db_name, i)
                curves_sg = self.sg_scene.CreateCurves(curves_handle)                
                primvar = curves_sg.EditPrimVarBegin()
                num_pts = -1

                j = 0
                for subsample, sample in data:
                    vertsArray, points, widthString, widths, scalpS, scalpT = sample[i]
                    if num_pts == -1:
                        num_pts = int(len(points)/3)
                        curves_sg.Define(rman.Tokens.Rix.k_cubic, "nonperiodic", "catmull-rom", len(vertsArray), num_pts)
                        primvar.SetIntegerDetail(rman.Tokens.Rix.k_Ri_nvertices, vertsArray, "uniform")
                        primvar.SetIntegerDetail("index", range(len(vertsArray)), "uniform")
                        if widthString == rman.Tokens.Rix.k_constantwidth:
                            primvar.SetFloatDetail(widthString, widths, "constant")
                        else:
                            primvar.SetFloatDetail(widthString, widths, "vertex")

                        if len(scalpS):
                            primvar.SetFloatDetail("scalpS", scalpS, "uniform")                
                            primvar.SetFloatDetail("scalpT", scalpT, "uniform")
                    pts = list( zip(*[iter(points)]*3 ) )   
                    primvar.SetPointDetail(rman.Tokens.Rix.k_P, pts, "vertex", j)                


                    j += 1
                    
                curves_sg.EditPrimVarEnd(primvar)
                sg_node.AddChild(curves_sg)
                self.sg_nodes_dict[curves_handle] = curves_sg

        else:
            curves = get_strands(self.scene, ob, psys, objectCorrectionMatrix)
            i = 0
            for vertsArray, points, widthString, widths, scalpS, scalpT in curves:
                curves_sg = self.sg_scene.CreateCurves("%s-%d" % (db_name, i))
                i += 1                
                curves_sg.Define(rman.Tokens.Rix.k_cubic, "nonperiodic", "catmull-rom", len(vertsArray), int(len(points)/3))
                primvar = curves_sg.EditPrimVarBegin()

                pts = list( zip(*[iter(points)]*3 ) )
                primvar.SetPointDetail(rman.Tokens.Rix.k_P, pts, "vertex")                
                primvar.SetIntegerDetail(rman.Tokens.Rix.k_Ri_nvertices, vertsArray, "uniform")
                primvar.SetIntegerDetail("index", range(len(vertsArray)), "uniform")

                if widthString == rman.Tokens.Rix.k_constantwidth:
                    primvar.SetFloatDetail(widthString, widths, "constant")
                else:
                    primvar.SetFloatDetail(widthString, widths, "vertex")

                if len(scalpS):
                    primvar.SetFloatDetail("scalpS", scalpS, "uniform")                
                    primvar.SetFloatDetail("scalpT", scalpT, "uniform")
                    
                curves_sg.EditPrimVarEnd(primvar)

                sg_node.AddChild(curves_sg)            

    def export_particle_system(self, ob, psys, db_name, objectCorrectionMatrix=False, data=None):
        sg_node = None
        if psys.settings.type == 'EMITTER':
            # particles are always deformation
            sg_node = self.export_particles(ob, psys, db_name,
                            data, objectCorrectionMatrix)
        else:
            sg_node = self.sg_nodes_dict.get(db_name)
            if not sg_node:
                sg_node = self.sg_scene.CreateGroup(db_name)
            else:
                for c in [ sg_node.GetChild(i) for i in range(0, sg_node.GetNumChildren())]:
                    sg_node.RemoveChild(c)
            self.export_hair(sg_node, ob, psys, db_name, data, objectCorrectionMatrix)
            self.sg_nodes_dict[db_name] = sg_node      

        return sg_node 

    # export the archives for an mesh. If this is a
    # deforming mesh the particle export will handle it
    def export_particle_archive(self, data_block, objectCorrectionMatrix=False):
        ob, psys = data_block.data
        data = data_block.motion_data if data_block.deforming else None
        db_name = data_block.name
        self.export_particle_system(ob, psys, db_name,
                            objectCorrectionMatrix, data=data)
        data_block.motion_data = None        

    def export_dupli_archive(self, sg_dupli, data_block, data_blocks):
        ob = data_block.data

        try:
            ob.dupli_list_create(self.scene, "RENDER")
        except:
            print("Cannot creat dupli list for: %s" % ob.name)
            
        if ob.dupli_type == 'GROUP' and ob.dupli_group:
            for dupob in ob.dupli_list:

                if dupob.object.type == "EMPTY":
                    continue

                dupli_name = "%s.DUPLI.%s.%d" % (ob.name, dupob.object.name,
                                                    dupob.index)

                mat = dupob.object.active_material

                source_data_name = data_name(dupob.object, self.scene)

                if hasattr(dupob.object, 'dupli_type') and dupob.object.dupli_type in SUPPORTED_DUPLI_TYPES:
                    source_data_name = dupob.object.name + '-DUPLI'
                deforming = is_deforming(dupob.object)

                sg_node = self.sg_scene.CreateGroup(dupli_name)
                if source_data_name in self.sg_nodes_dict:   
                    sg_source = self.sg_nodes_dict[source_data_name]                 
                    sg_node.AddChild(sg_source)
                    sg_node.SetTransform( convert_matrix(dupob.matrix))
                    if not is_multi_material(dupob.object):
                        if dupob.object.material_slots:
                            mat = dupob.object.material_slots[0].material
                            if mat:
                                mat_handle = "material.%s" % mat.name
                                if mat_handle in self.sg_nodes_dict:
                                    sg_material = self.sg_nodes_dict[mat_handle]
                                    sg_node.SetMaterial(sg_material)

                sg_dupli.AddChild(sg_node)                
                self.sg_nodes_dict[dupli_name] = sg_node

            ob.dupli_list_clear()
            return

        for num, dupob in enumerate(ob.dupli_list):

            dupli_name = "%s.DUPLI.%s.%d" % (ob.name, dupob.object.name,
                                             dupob.index)

            source_data_name = data_name(dupob.object, self.scene)
            sg_node = self.sg_scene.CreateGroup(dupli_name)
            
            if source_data_name in self.sg_nodes_dict:
                sg_source = self.sg_nodes_dict[source_data_name]
                sg_node.AddChild(sg_source)
                sg_node.SetTransform( convert_matrix(dupob.matrix))
                mat = dupob.object.active_material
                if mat:
                    mat_handle = "material.%s" % mat.name
                    if mat_handle in self.sg_nodes_dict:
                        sg_material = self.sg_nodes_dict[mat_handle]
                        sg_node.SetMaterial(sg_material)
            sg_dupli.AddChild(sg_node)
            self.sg_nodes_dict[dupli_name] = sg_node
        ob.dupli_list_clear()            

    def export_duplis_instances(self, master=None, prnt=None):
        dg = self.rpass.depsgraph #bpy.context.evaluated_depsgraph_get()
        for ob_inst in dg.object_instances:
            if ob_inst.is_instance:
                ob = ob_inst.instance_object.original
                if master and master.name != ob.name:
                    continue
                parent = ob_inst.parent.original
                if prnt and prnt.name != parent.name:
                    continue
                src_name = data_name(ob, self.scene)
                if src_name in self.sg_nodes_dict:
                    dupli_name = "%s.DUPLI.%s.%d" % (parent.name, src_name,
                                ob_inst.random_id)
                    sg_source = self.sg_nodes_dict[src_name]
                    sg_node = self.sg_nodes_dict.get(dupli_name, None)
                    if not sg_node:
                        sg_node = self.sg_scene.CreateGroup(dupli_name)
                        sg_node.AddChild(sg_source)
                        self.sg_global_obj.AddChild(sg_node)       

                    sg_node.SetTransform( convert_matrix( ob_inst.matrix_world.copy() ) )
                    mat = ob.active_material
                    if mat:
                        mat_handle = "material.%s" % mat.name
                        if mat_handle in self.sg_nodes_dict:
                            sg_material = self.sg_nodes_dict[mat_handle]
                            sg_node.SetMaterial(sg_material)

                    self.sg_nodes_dict[dupli_name] = sg_node

    def export_objects(self, data_blocks, instances, visible_objects=None, emptiesToExport=None):

        # loop over objects
        # we do this in sorted order, 
        # first, MESH, then, PSYS, then DUPLI
        print("\t\tExporting datablocks...")
        sorted_data_blocks = sorted(data_blocks.items(), key=lambda x: x[1])
        total = len(sorted_data_blocks)
        i = 1
        print("\t\t    0%")
        sys.stdout.flush()
        for name, db in sorted_data_blocks:
            if db.type == "MESH":
                self.export_mesh_archive(db)
            elif db.type == "PSYS":
                self.export_particle_archive(db, True)  
            #elif db.type == "DUPLI":             
            #    sg_node = self.sg_scene.CreateGroup(name)   
            #    self.export_dupli_archive(sg_node, db, data_blocks)
            #    self.sg_nodes_dict[name] = sg_node                            
            print("\t\t    Processed %d/%d objects (%d%%) " % (i, total, int((i/total) * 100)))
            sys.stdout.flush()
            i += 1  

        # now output the object archives
        print("\t\tExporting instances...")
        sys.stdout.flush()
        for name, instance in instances.items():
            if not instance.parent or instance.ob.parent.type=="EMPTY":
                for db_name in instance.data_block_names:                 
                    self.write_instances(db_name, data_blocks, data_blocks[db_name], instances, instance, visible_objects=visible_objects)

                for child_name in instance.children:
                    if child_name in instances:
                        child_instance = instances[child_name]
                        for db_name in child_instance.data_block_names:
                            inst_sg = self.sg_nodes_dict.get(instance.name)
                            self.write_instances(db_name, data_blocks, data_blocks[db_name], instances, child_instance, visible_objects=visible_objects, parent_sg_node=inst_sg)            
        print("\t\tExporting dupli instances...")
        self.export_duplis_instances()

    def write_scene(self, visible_objects=None, engine=None, do_objects=True):

        # precalculate motion blur data
        print("\tPrecalculate phase...")
        sys.stdout.flush()
        time_start = time.time()        
        do_mb = False
        #if self.use_python_dspy:
        #    do_mb = False
        data_blocks, instances = cache_motion(self.scene, self.rpass, calc_mb=do_mb)
        print("\tFinished precalculation. Time: %s" % format_seconds_to_hhmmss(time.time() - time_start))          

        # get a list of empties to check if they contain a RIB archive.
        # this should be the only time empties are evaluated.
        emptiesToExport = get_valid_empties(self.scene, self.rpass)

        self.export_searchpaths()      
        self.export_hider()

        if not self.rpass.bake:
            self.export_integrator()

        #if not self.use_python_dspy:
        #    self.scene.frame_set(self.scene.frame_current)

        if not self.rpass.bake:
            self.export_global_options()

        if not self.rpass.bake:
            self.export_camera(instances)

        if not self.rpass.bake:
            self.export_displays()
            self.export_displayfilters()
            self.export_samplefilters()
        else:
            pass
            #ri.Display("null", "null", "rgba")

        if not self.rpass.bake:
        #    export_world_rib(ri, scene.world)
        #    export_world(ri, scene.world)

            self.export_scene_lights(instances)
            self.export_global_obj_settings()


        #    export_default_bxdf(ri, "default")
        print("\tExporting materials...")
        sys.stdout.flush()
        time_start = time.time()
        self.export_materials()
        print("\tFinished exporting materials. Time: %s" % format_seconds_to_hhmmss(time.time() - time_start))  
        sys.stdout.flush()

        print("\tExporting objects.")
        sys.stdout.flush()
        time_start = time.time()        
        self.export_objects(data_blocks, instances, visible_objects, emptiesToExport)
        print("\tFinished exporting objects. Time: %s" % format_seconds_to_hhmmss(time.time() - time_start))  
        sys.stdout.flush()

        #for object in emptiesToExport:
        #    export_empties_archives(ri, object)

        instances = None

    def write_object_archive(self, object, engine=None, do_objects=True):

        # precalculate motion blur data
        data_blocks, instances = cache_motion(self.scene, self.rpass, objects=[object, self.scene.camera])

        # get a list of empties to check if they contain a RIB archive.
        # this should be the only time empties are evaluated.
        emptiesToExport = get_valid_empties(self.scene, self.rpass)

        self.export_camera(instances)
        self.export_global_obj_settings()
        self.export_materials()
        self.export_objects(data_blocks, instances, visible_objects=None, emptiesToExport=emptiesToExport)


        #for object in emptiesToExport:
        #    export_empties_archives(ri, object)

        instances = None        

def is_ready():
    global __RMAN_SG_INITED__
    return __RMAN_SG_INITED__

def rman_sg_exporter():
    global __RMAN_SG_EXPORTER__
    if __RMAN_SG_EXPORTER__ is None:
        __RMAN_SG_EXPORTER__ = RmanSgExporter()

    return __RMAN_SG_EXPORTER__

def get_matrix_for_object(passedOb):
    if passedOb.parent:
        mtx = Matrix.Identity(4)
    else:
        mtx = passedOb.matrix_world
    return mtx


# check for a singular matrix
def is_singular(mtx):
    return mtx[0][0] == 0.0 and mtx[1][1] == 0.0 and mtx[2][2] == 0.0


# export the instance of an object (dupli)
def export_object_instance(ri, mtx=None, instance_handle=None, num=None):
    if mtx and not is_singular(mtx):
        ri.AttributeBegin()
        ri.Attribute("identifier", {"int id": num})
        ri.Transform(rib(mtx))
        ri.ObjectInstance(instance_handle)
        ri.AttributeEnd()


# ------------- Filtering -------------
def is_visible_layer(scene, ob):
    #
    #FIXME for i in range(len(scene.layers)):
    #    if scene.layers[i] and ob.layers[i]:
    #        return True
    return True


def is_renderable(scene, ob):
    return (is_visible_layer(scene, ob) and not ob.hide_render) or \
        (ob.type in ['ARMATURE', 'LATTICE', 'EMPTY'] and ob.instance_type not in SUPPORTED_DUPLI_TYPES)
    # and not ob.type in ('CAMERA', 'ARMATURE', 'LATTICE'))


def is_renderable_or_parent(scene, ob):
    if ob.type == 'CAMERA':
        return True
    if is_renderable(scene, ob):
        return True
    elif hasattr(ob, 'children') and ob.children:
        for child in ob.children:
            if is_renderable_or_parent(scene, child):
                return True
    return False


def is_data_renderable(scene, ob):
    return (is_visible_layer(scene, ob) and not ob.hide_render and ob.type not in ('EMPTY', 'ARMATURE', 'LATTICE'))


def renderable_objects(scene):
    return [ob for ob in scene.objects if (is_renderable(scene, ob) or is_data_renderable(scene, ob))]


# ------------- Archive Helpers -------------
# Generate an automatic path to write an archive when
# 'Export as Archive' is enabled
def auto_archive_path(paths, objects, create_folder=False):
    filename = objects[0].name + ".rib"

    if os.getenv("ARCHIVE") is not None:
        archive_dir = os.getenv("ARCHIVE")
    else:
        archive_dir = os.path.join(paths['export_dir'], "archives")

    if create_folder and not os.path.exists(archive_dir):
        os.mkdir(archive_dir)

    return os.path.join(archive_dir, filename)


def archive_objects(scene):
    archive_obs = []

    for ob in renderable_objects(scene):
        # explicitly set
        if ob.renderman.export_archive:
            archive_obs.append(ob)

        # particle instances
        for psys in ob.particle_systems:
            rm = psys.settings.renderman
            if rm.particle_type == 'OBJECT':
                try:
                    ob = bpy.data.objects[rm.particle_instance_object]
                    archive_obs.append(ob)
                except:
                    pass

        # dupli objects (TODO)

    return archive_obs


# ------------- Data Access Helpers -------------
def get_subframes(segs, scene):
    if segs == 0:
        return []
    min = -1.0
    rm = scene.renderman
    shutter_interval = rm.shutter_angle / 360.0
    if rm.shutter_timing == 'CENTER':
        min = 0 - .5 * shutter_interval
    elif rm.shutter_timing == 'PRE':
        min = 0 - shutter_interval
    elif rm.shutter_timing == 'POST':
        min = 0

    return [min + i * shutter_interval / (segs - 1) for i in range(segs)]


def is_subd_last(ob):
    return ob.modifiers and \
        ob.modifiers[len(ob.modifiers) - 1].type == 'SUBSURF'


def is_subd_displace_last(ob):
    if len(ob.modifiers) < 2:
        return False

    return (ob.modifiers[len(ob.modifiers) - 2].type == 'SUBSURF' and
            ob.modifiers[len(ob.modifiers) - 1].type == 'DISPLACE')


def is_subdmesh(ob):
    return (is_subd_last(ob) or is_subd_displace_last(ob))


# XXX do this better, perhaps by hooking into modifier type data in RNA?
# Currently assumes too much is deforming when it isn't
def is_deforming(ob):
    deforming_modifiers = ['ARMATURE', 'MESH_SEQUENCE_CACHE', 'CAST', 'CLOTH', 'CURVE', 'DISPLACE',
                           'HOOK', 'LATTICE', 'MESH_DEFORM', 'SHRINKWRAP', 'EXPLODE',
                           'SIMPLE_DEFORM', 'SMOOTH', 'WAVE', 'SOFT_BODY',
                           'SURFACE', 'MESH_CACHE', 'FLUID_SIMULATION',
                           'DYNAMIC_PAINT']
    if ob.modifiers:
        # special cases for auto subd/displace detection
        if len(ob.modifiers) == 1 and is_subd_last(ob):
            return False
        if len(ob.modifiers) == 2 and is_subd_displace_last(ob):
            return False

        for mod in ob.modifiers:
            if mod.type in deforming_modifiers:
                return True
    if ob.data and hasattr(ob.data, 'shape_keys') and ob.data.shape_keys:
        return True

    return is_deforming_fluid(ob)


# handle special case of fluid sim a bit differently
def is_deforming_fluid(ob):
    if ob.modifiers:
        mod = ob.modifiers[len(ob.modifiers) - 1]
        return mod.type == 'SMOKE' and mod.smoke_type == 'DOMAIN'


def psys_name(ob, psys):
    return "%s.%s-%s" % (ob.name, psys.name, psys.settings.type)


# if we don't replace slashes could end up with them in file names
def fix_name(name):
    return name.replace('/', '')

# get a name for the data block.  if it's modified by the obj we need it
# specified


def data_name(ob, scene):
    if not ob:
        return ''

    if not ob.data:
        return fix_name(ob.name)

    # if this is a blob return the family name
    if ob.type == 'META':
        return fix_name(ob.name.split('.')[0])

    if is_smoke(ob) or ob.renderman.primitive == 'RI_VOLUME':
        return "%s-VOLUME" % fix_name(ob.name)

    if ob.data.users > 1 and (ob.is_modified(scene, "RENDER") or
                              ob.is_deform_modified(scene, "RENDER") or
                              ob.renderman.primitive != 'AUTO' or
                              (ob.renderman.motion_segments_override and
                               is_deforming(ob))):
        return "%s.%s-MESH" % (fix_name(ob.name), fix_name(ob.data.name))

    else:
        return "%s-MESH" % fix_name(ob.data.name)


def get_name(ob):
    return psys_name(ob) if type(ob) == bpy.types.ParticleSystem \
        else fix_name(ob.data.name)


# ------------- Geometry Access -------------
def get_strands(scene, ob, psys, objectCorrectionMatrix=True):

    psys_modifier = None
    for mod in ob.modifiers:
        if hasattr(mod, 'particle_system') and mod.particle_system == psys:
            psys_modifier = mod
            break

    # !!!!!!!!!!!!!!!!!!!!!
    # Check if the modifier has show_viewport set to True
    # If set to False, Blender will crash when psys.co_hair is called
    # !!!!!!!!!!!!!!!!!!!!!
    #if not psys_modifier.show_viewport:
    #    return []

    tip_width = psys.settings.tip_radius * psys.settings.radius_scale
    base_width = psys.settings.root_radius * psys.settings.radius_scale

    conwidth = (tip_width == base_width)
    steps = 2 ** psys.settings.render_step
    if conwidth:
        widthString = rman.Tokens.Rix.k_constantwidth
        hair_width = base_width
        debug("info", widthString, hair_width)
    else:
        widthString = rman.Tokens.Rix.k_width
        hair_width = []

    #psys.set_resolution(scene=scene, object=ob, resolution='RENDER')

    num_parents = len(psys.particles)
    num_children = len(psys.child_particles)
    total_hair_count = num_parents + num_children
    export_st = psys.settings.renderman.export_scalp_st and psys_modifier and len(
        ob.data.uv_layers) > 0

    curve_sets = []

    points = []

    vertsArray = []
    scalpS = []
    scalpT = []
    nverts = 0
    no = 0
    
    for pindex in range(total_hair_count):
        if psys.settings.child_type != 'NONE' and pindex < num_parents:
            continue

        strand_points = []
        # walk through each strand
        for step in range(0, steps + 1):           
            pt = psys.co_hair(ob, particle_no=pindex, step=step)

            if pt.length_squared == 0:
                # this strand ends prematurely                    
                break
            
            if(objectCorrectionMatrix):
                # put points in object space
                m = ob.matrix_world.inverted_safe()
                pt = Vector(transform_points( m, pt))

            strand_points.extend(pt)

        if len(strand_points) > 1:
            # double the first and last
            strand_points = strand_points[:3] + \
                strand_points + strand_points[-3:]
            vertsInStrand = len(strand_points) // 3

            # catmull-rom requires at least 4 vertices
            if vertsInStrand < 4:
                continue

            # for varying width make the width array
            if not conwidth:
                decr = (base_width - tip_width) / (vertsInStrand - 2)
                hair_width.extend([base_width] + [(base_width - decr * i)
                                                for i in range(vertsInStrand - 2)] +
                                [tip_width])

            # add the last point again
            points.extend(strand_points)
            vertsArray.append(vertsInStrand)
            nverts += vertsInStrand

            # get the scalp S
            if export_st:
                if pindex >= num_parents:
                    particle = psys.particles[
                        (pindex - num_parents) % num_parents]
                else:
                    particle = psys.particles[pindex]
                st = psys.uv_on_emitter(psys_modifier, particle, pindex)
                scalpS.append(st[0])
                scalpT.append(st[1])

        # if we get more than 100000 vertices, export ri.Curve and reset.  This
        # is to avoid a maxint on the array length
        if nverts > 100000:
            curve_sets.append(
                (vertsArray, points, widthString, hair_width, scalpS, scalpT))

            nverts = 0
            points = []
            vertsArray = []
            if not conwidth:
                hair_width = []
            scalpS = []
            scalpT = []

    if nverts > 0:
        curve_sets.append((vertsArray, points, widthString,
                        hair_width, scalpS, scalpT))

    #psys.set_resolution(scene=scene, object=ob, resolution='PREVIEW')

    return curve_sets           

# only export particles that are alive,
# or have been born since the last frame


def valid_particle(pa, valid_frames):
    return pa.die_time >= valid_frames[-1] and pa.birth_time <= valid_frames[0]


def get_particles(scene, ob, psys, valid_frames=None):
    P = []
    rot = []
    width = []

    valid_frames = (scene.frame_current,
                    scene.frame_current) if valid_frames is None else valid_frames
    #psys.set_resolution(scene, ob, 'RENDER')
    for pa in [p for p in psys.particles if valid_particle(p, valid_frames)]:
        P.extend(pa.location)
        rot.extend(pa.rotation)

        if pa.alive_state != 'ALIVE':
            width.append(0.0)
        else:
            width.append(pa.size)
    #psys.set_resolution(scene, ob, 'PREVIEW')
    return (P, rot, width)

def get_mesh_points(mesh):
    # return just the points on the mesh
    P = []
    verts = []

    for v in mesh.vertices:
        P.extend(v.co)

    for p in mesh.polygons:
        verts.extend(p.vertices)

    if len(verts) > 0:
        P = P[:int(max(verts) + 1) * 3]

    return P

def get_mesh(mesh, get_normals=False):
    nverts = []
    verts = []
    P = []
    N = []

    for v in mesh.vertices:
        P.extend(v.co)

    for p in mesh.polygons:
        nverts.append(p.loop_total)
        verts.extend(p.vertices)
        if get_normals:
            if p.use_smooth:
                for vi in p.vertices:
                    N.extend(mesh.vertices[vi].normal)
            else:
                N.extend(list(p.normal) * p.loop_total)

    if len(verts) > 0:
        P = P[:int(max(verts) + 1) * 3]
    # return the P's minus any unconnected
    return (nverts, verts, P, N)


# requires facevertex interpolation
def get_mesh_uv(mesh, name="", flipvmode='NONE'):
    uvs = []
    if not name:
        uv_loop_layer = mesh.uv_layers.active
    else:
        # assuming uv loop layers and uv textures share identical indices
        idx = mesh.uv_textures.keys().index(name)
        uv_loop_layer = mesh.uv_layers[idx]

    if uv_loop_layer is None:
        return None

    for uvloop in uv_loop_layer.data:
        uvs.append(uvloop.uv.x)
        # renderman expects UVs flipped vertically from blender
        # best to do this in pattern, provided here as additional option
        if flipvmode == 'UV':
            uvs.append(1.0-uvloop.uv.y)
        elif flipvmode == 'TILE':
            uvs.append(math.ceil(uvloop.uv.y) - uvloop.uv.y + math.floor(uvloop.uv.y))
        elif flipvmode == 'NONE':
            uvs.append(uvloop.uv.y)

    return uvs


# requires facevertex interpolation
def get_mesh_vcol(mesh, name=""):
    vcol_layer = mesh.vertex_colors[name] if name != "" \
        else mesh.vertex_colors.active
    cols = []

    if vcol_layer is None:
        return None

    for vcloop in vcol_layer.data:
        cols.extend(vcloop.color)

    return cols

# requires per-vertex interpolation


def get_mesh_vgroup(ob, mesh, name=""):
    vgroup = ob.vertex_groups[name] if name != "" else ob.vertex_groups.active
    weights = []

    if vgroup is None:
        return None

    for v in mesh.vertices:
        if len(v.groups) == 0:
            weights.append(0.0)
        else:
            weights.extend([g.weight for g in v.groups
                            if g.group == vgroup.index])

    return weights

# if a mesh has more than one material


def is_multi_material(mesh):
    if type(mesh) != bpy.types.Mesh or len(mesh.materials) < 2 \
            or len(mesh.polygons) == 0:
        return False
    first_mat = mesh.polygons[0].material_index
    for p in mesh.polygons:
        if p.material_index != first_mat:
            return True
    return False


def get_primvars(ob, geo, rixparams, interpolation=""):
    material_ids = {}
    if ob.type != 'MESH':
        return None
    rm = ob.data.renderman

    interpolation = 'facevarying' if not interpolation else interpolation

    # get material id if this is a multi-material mesh
    if is_multi_material(geo):
        material_id = rib([p.material_index for p in geo.polygons])
        material_ids["uniform float material_id"] = material_id
        #rixparams.SetFloatDetail("material_id", material_id, "uniform")

    if rm.export_default_uv:
        uvs = get_mesh_uv(geo, flipvmode=rm.export_flipv)
        if uvs and len(uvs) > 0:
            #primvars["%s float[2] st" % interpolation] = uvs
            rixparams.SetFloatArrayDetail("st", uvs, 2, interpolation)

    if rm.export_default_vcol:
        vcols = get_mesh_vcol(geo)
        if vcols and len(vcols) > 0:
            #primvars["%s color Cs" % interpolation] = rib(vcols)
            rixparams.SetColorDetail("Cs", rib(vcols, type_hint="color"), interpolation)

    # custom prim vars
    for p in rm.prim_vars:
        if p.data_source == 'VERTEX_COLOR':
            vcols = get_mesh_vcol(geo, p.data_name)
            if vcols and len(vcols) > 0:
                #primvars["%s color %s" % (interpolation, p.name)] = rib(vcols)
                rixparams.SetColorDetail(p.name, rib(vcols, type_hint="color"), interpolation)

        elif p.data_source == 'UV_TEXTURE':
            uvs = get_mesh_uv(geo, p.data_name, flipvmode=rm.export_flipv)
            if uvs and len(uvs) > 0:
                #primvars["%s float[2] %s" % (interpolation, p.name)] = uvs
                rixparams.SetFloatArrayDetail(p.name, uvs, 2, interpolation)

        elif p.data_source == 'VERTEX_GROUP':
            weights = get_mesh_vgroup(ob, geo, p.data_name)
            if weights and len(weights) > 0:
                #primvars["vertex float %s" % p.name] = weights
                rixparams.SetFloatDetail(p.name, weights, "vertex")

    return material_ids

def get_fluid_mesh(scene, ob):

    subframe = scene.frame_subframe

    fluidmod = [m for m in ob.modifiers if m.type == 'FLUID_SIMULATION'][0]
    fluidmeshverts = fluidmod.settings.fluid_mesh_vertices

    mesh = create_mesh(ob, scene)
    (nverts, verts, P, N) = get_mesh(mesh)
    removeMeshFromMemory(mesh.name)

    # use fluid vertex velocity vectors to reconstruct moving points
    P = [P[i] + fluidmeshverts[int(i / 3)].velocity[i % 3] * subframe * 0.5 for
         i in range(len(P))]

    return (nverts, verts, P, N)


def get_subd_creases(mesh):
    creases = []

    # only do creases 1 edge at a time for now,
    # detecting chains might be tricky..
    for e in mesh.edges:
        if e.crease > 0.0:
            creases.append((e.vertices[0], e.vertices[1],
                            e.crease * e.crease * 10))
            # squared, to match blender appareance better
            #: range 0 - 10 (infinitely sharp)
    return creases


def create_mesh(ob, scene):
    # 2 special cases to ignore:
    # subsurf last or subsurf 2nd last +displace last
    reset_subd_mod = False
    if is_subd_last(ob) and ob.modifiers[len(ob.modifiers) - 1].show_render:
        reset_subd_mod = True
        #ob.modifiers[len(ob.modifiers) - 1].show_render = False

    # elif is_subd_displace_last(ob):
    #    ob.modifiers[len(ob.modifiers)-2].show_render = False
    #    ob.modifiers[len(ob.modifiers)-1].show_render = False
    #FIXME mesh = ob.to_mesh(scene, True, 'RENDER', calc_tessface=False,
    #                  calc_undeformed=True)
    mesh = ob.to_mesh()
    #if reset_subd_mod:
    #    ob.modifiers[len(ob.modifiers) - 1].show_render = True
    return mesh

def get_light_group(light_ob):
    scene_rm = bpy.context.scene.renderman
    for lg in scene_rm.light_groups:
        if lg.name != 'All' and light_ob.name in lg.members:
            return lg.name
    return ''

def recursive_texture_set(ob):
    mat_set = []
    SUPPORTED_MATERIAL_TYPES = ['MESH', 'CURVE', 'FONT', 'SURFACE']
    if ob.type in SUPPORTED_MATERIAL_TYPES:
        for mat in ob.data.materials:
            if mat:
                mat_set.append(mat)

    for child in ob.children:
        mat_set += recursive_texture_set(child)

    if ob.instance_collection:
        for child in ob.instance_collection.objects:
            mat_set += recursive_texture_set(child)

    return mat_set


def get_texture_list(scene):
    # if not rpass.light_shaders: return

    textures = []
    mats_to_scan = []
    for o in renderable_objects(scene):
        if o.type == 'CAMERA' or o.type == 'EMPTY':
            continue
        elif o.type == 'LIGHT':
            if o.data.renderman.get_light_node():
                textures = textures + \
                    get_textures_for_node(o.data.renderman.get_light_node())
        else:
            mats_to_scan += recursive_texture_set(o)
    if scene.world and scene.world.renderman.renderman_type != 'NONE':
        textures = textures + \
            get_textures_for_node(scene.world.renderman.get_light_node())

    # cull duplicates by only doing mats once
    for mat in set(mats_to_scan):
        new_textures = get_textures(mat)
        if new_textures:
            textures.extend(new_textures)
    return textures


def get_select_texture_list(object):
    textures = []
    for mat in set(recursive_texture_set(object)):
        new_textures = get_textures(mat)
        if(new_textures):
            textures.extend(new_textures)
    return textures


def get_texture_list_preview(scene):
    # if not rpass.light_shaders: return
    textures = []
    return get_textures(find_preview_material(scene))

def export_default_bxdf(ri, name):
    # default bxdf a nice grey plastic
    ri.Bxdf("PxrDisney", "default", {
            'color baseColor': [0.18, 0.18, 0.18], 'string __instanceid': name})


def export_shader(ri, mat):
    rm = mat.renderman
    # if rm.surface_shaders.active == '' or not rpass.surface_shaders: return
    name = get_mat_name(mat.name)
    params = {"color baseColor": rib(mat.diffuse_color),
              "float specular": mat.specular_intensity,
              'string __instanceid': get_mat_name(mat.name)}

    if mat.emit:
        params["color emitColor"] = rib(mat.diffuse_color)
    if mat.subsurface_scattering.use:
        params["float subsurface"] = mat.subsurface_scattering.scale
        params["color subsurfaceColor"] = \
            rib(mat.subsurface_scattering.color)
    if mat.raytrace_mirror.use:
        params["float metallic"] = mat.raytrace_mirror.reflect_factor
    ri.Bxdf("PxrDisney", get_mat_name(mat.name), params)


def is_smoke(ob):
    for mod in ob.modifiers:
        if mod.type == "SMOKE" and mod.domain_settings:
            return True
    return False


def detect_primitive(ob):
    if type(ob) == bpy.types.ParticleSystem:
        return ob.settings.type

    rm = ob.renderman

    if rm.primitive == 'AUTO':
        if ob.type == 'MESH':
            if is_subdmesh(ob):
                return 'SUBDIVISION_MESH'
            elif is_smoke(ob):
                return 'SMOKE'
            else:
                return 'POLYGON_MESH'
        elif ob.type == 'CURVE':
            return 'CURVE'
        elif ob.type in ('SURFACE', 'FONT'):
            return 'POLYGON_MESH'
        elif ob.type == "META":
            return "META"
        else:
            return 'NONE'
    else:
        return rm.primitive


def get_mats_faces(nverts, primvars):
    if "uniform float material_id" not in primvars:
        return {}

    else:
        mats = {}

        for face_id, num_verts in enumerate(nverts):
            mat_id = primvars["uniform float material_id"][face_id]
            if mat_id not in mats:
                mats[mat_id] = []
            mats[mat_id].append(face_id)
        return mats

def removeMeshFromMemory(passedName):
    # Extra test because this can crash Blender if not done correctly.
    result = False
    mesh = bpy.data.meshes.get(passedName)
    if mesh is not None:
        if mesh.users == 0:
            try:
                mesh.user_clear()
                can_continue = True
            except:
                can_continue = False

            if can_continue:
                try:
                    bpy.data.meshes.remove(mesh)
                    result = True
                except:
                    result = False
            else:
                # Unable to clear users, something is holding a reference to it.
                # Can't risk removing. Favor leaving it in memory instead of
                # risking a crash.
                result = False
    else:
        # We could not fetch it, it does not exist in memory, essentially
        # removed.
        result = True
    return result


def get_mball_parent(mball):
    for ob in bpy.data.objects:
        if ob.data == mball:
            return ob


def is_transforming(ob, do_mb, recurse=False):
    transforming = (do_mb and ob.animation_data is not None)
    if not transforming and ob.parent:
        transforming = is_transforming(ob.parent, do_mb, recurse=True)
        if not transforming and ob.parent.type == 'CURVE' and ob.parent.data:
            transforming = ob.parent.data.use_path
    return transforming


# Instance holds all the data needed for making an instance of data_block
class Instance:
    name = ''
    type = ''
    transforming = False
    motion_data = []
    archive_filename = ''
    ob = None
    material = None

    def __init__(self, name, type, ob=None,
                 transforming=False):
        self.name = name
        self.type = type
        self.transforming = transforming
        self.ob = ob
        self.motion_data = []
        self.children = []
        self.data_block_names = []
        self.parent = None
        if hasattr(ob, 'parent') and ob.parent:
            self.parent = ob.parent.name
        if hasattr(ob, 'children') and ob.children:
            for child in ob.children:
                self.children.append(child.name)


# Data block holds the info for exporting the archive of a data_block
class DataBlock:
    motion_data = []
    archive_filename = ''
    deforming = False
    type = ''
    data = None
    name = ''
    material = []
    do_export = False
    dupli_data = False

    def __init__(self, name, type, archive_filename, data, deforming=False, material=[], do_export=True, dupli_data=False):
        self.name = name
        self.type = type
        self.archive_filename = archive_filename
        self.deforming = deforming
        self.data = data
        self.motion_data = []
        self.material = material
        self.do_export = do_export
        self.dupli_data = dupli_data
        self.types_dict = {'MESH': 0, 'PSYS': 1, 'DUPLI': 2} # sort order

    def __eq__(self, other):
        return (self.types_dict[self.type] == self.types_dict[other.type])

    def __ne__(self, other):
        return (self.types_dict[self.type] != self.types_dict[other.type])

    def __lt__(self, other):
        return (self.types_dict[self.type] < self.types_dict[other.type])

    def __le__(self, other):
        return (self.types_dict[self.type] <= self.types_dict[other.type])        

    def __gt__(self, other):
        return (self.types_dict[self.type] > self.types_dict[other.type])

    def __ge__(self, other):
        return (self.types_dict[self.type] >= self.types_dict[other.type])            

def has_emissive_material(db):
    for mat in db.material:
        if mat and mat.node_tree:
            nt = mat.node_tree

            out = next((n for n in nt.nodes if hasattr(n, 'renderman_node_type') and n.renderman_node_type == 'output'),
                       None)
            if out and out.inputs['Light'].is_linked:
                return True
    return False


def export_for_bake(db):
    for mat in db.material:
        if mat and mat.node_tree:
            for n in mat.node_tree.nodes:
                if n.bl_idname in ("PxrBakeTexturePatternNode", "PxrBakePointCloudPatternNode"):
                    return True
        return False

# return if a psys should be animated
# NB:  we ALWAYS need the animating psys if the emitter is transforming,
# not just if MB is on


def is_psys_animating(ob, psys, do_mb):
    return (psys.settings.frame_start != psys.settings.frame_end) or is_transforming(ob, True, recurse=True)

# constructs a list of instances and data blocks based on objects in a scene
# only the needed for rendering data blocks and instances are cached
# also save a data structure of the set of motion segments with
# instances/datablocks that have the number of motion segments


def get_instances_and_blocks(obs, rpass):
    bake = rpass.bake
    instances = {}
    data_blocks = {}
    motion_segs = {}
    scene = rpass.scene
    mb_on = scene.renderman.motion_blur if not bake else False
    mb_segs = scene.renderman.motion_segments

    for ob in obs:
        inst = get_instance(ob, rpass.scene, mb_on)
        if inst:
            ob_mb_segs = ob.renderman.motion_segments if ob.renderman.motion_segments_override else mb_segs

            # add the instance to the motion segs list if transforming
            if inst.transforming:
                if ob_mb_segs not in motion_segs:
                    motion_segs[ob_mb_segs] = ([], [])
                motion_segs[ob_mb_segs][0].append(inst.name)

            # now get the data_blocks for the instance
            inst_data_blocks = get_data_blocks_needed(ob, rpass, mb_on)
            for db in inst_data_blocks:
                do_db = False if (bake and not export_for_bake(db)) else True

                if do_db and not db.dupli_data:
                    inst.data_block_names.append(db.name)

                # if this data_block is already in the list to export...
                if db.name in data_blocks:
                    continue

                # add data_block to mb list
                if do_db and db.deforming and mb_on:
                    if ob_mb_segs not in motion_segs:
                        motion_segs[ob_mb_segs] = ([], [])
                    motion_segs[ob_mb_segs][1].append(db.name)

                if do_db:
                    data_blocks[db.name] = db

            instances[inst.name] = inst

    return instances, data_blocks, motion_segs

# get the used materials for an object


def get_used_materials(ob):
    if ob.type == 'MESH' and len(ob.data.materials) > 0:
        if len(ob.data.materials) == 1:
            return [ob.data.materials[0]]
        mat_ids = []
        mesh = ob.data
        num_materials = len(ob.data.materials)
        for p in mesh.polygons:
            if p.material_index not in mat_ids:
                mat_ids.append(p.material_index)
            if num_materials == len(mat_ids):
                break
        return [mesh.materials[i] for i in mat_ids]
    else:
        return [ob.active_material]

# get the instance type for this object.
# If no instance needs exporting, return None


def get_instance(ob, scene, do_mb):
    if is_renderable_or_parent(scene, ob):
        return Instance(ob.name, ob.type, ob, is_transforming(ob, do_mb))
    else:
        return None


# get the data_block needed for a dupli
def get_dupli_block(ob, rpass, do_mb):
    if not ob:
        return []

    if ob.instance_type != "NONE" and ob.instance_type in SUPPORTED_DUPLI_TYPES:
        name = ob.name + '-DUPLI'
        # duplis aren't animated
        dbs = []
        deforming = False
        if ob.instance_type == "COLLECTION" and ob.instance_collection:
            for dupli_ob in ob.instance_collection.objects:
                sub_dbs = get_dupli_block(dupli_ob, rpass, do_mb)
                if not deforming:
                    for db in sub_dbs:
                        if db.deforming:
                            deforming = True
                            break
                dbs.extend(sub_dbs)
        archive_filename = get_archive_filename(name, rpass, deforming)
        dbs.append(DataBlock(name, "DUPLI", archive_filename, ob, deforming=deforming,
                             dupli_data=True,
                             do_export=file_is_dirty(rpass.scene, ob, archive_filename)))
        return dbs

    else:
        name = data_name(ob, rpass.scene)
        deforming = is_deforming(ob)
        archive_filename = get_archive_filename(data_name(ob, rpass.scene),
                                                rpass, deforming)

        return [DataBlock(name, "MESH", archive_filename, ob,
                          deforming, material=get_used_materials(ob),
                          do_export=file_is_dirty(
                              rpass.scene, ob, archive_filename),
                          dupli_data=True)]


# get the data blocks needed for an object
def get_data_blocks_needed(ob, rpass, do_mb):
    if not is_renderable(rpass.scene, ob):
        return []
    data_blocks = []
    emit_ob = True
    dupli_emitted = False
    # get any particle systems, or if a particle sys is duplis
    if len(ob.particle_systems):
        #emit_ob = False
        for psys in ob.particle_systems:

            # if this is an objct emitter use dupli
            #if psys.settings.use_render_emitter:
            #    emit_ob = True


            if psys.settings.render_type not in ['OBJECT', 'COLLECTION']:
                name = psys_name(ob, psys)
                type = 'PSYS'
                data = (ob, psys)
                archive_filename = get_archive_filename(name, rpass,
                                                        is_psys_animating(ob, psys, do_mb))
            else:
                name = ob.name + '-DUPLI'
                type = 'DUPLI'
                archive_filename = get_archive_filename(name, rpass,
                                                        is_psys_animating(ob, psys, do_mb))
                dupli_emitted = True
                data = ob
                if psys.settings.render_type == 'OBJECT':
                    data_blocks.extend(get_dupli_block(
                        psys.settings.instance_object, rpass, do_mb))
                elif psys.settings.instance_collection:
                    for dupli_ob in psys.settings.instance_collection.objects:
                        data_blocks.extend(
                            get_dupli_block(dupli_ob, rpass, do_mb))     

            mat = [ob.material_slots[psys.settings.material -
                                     1].material] if psys.settings.material and psys.settings.material <= len(ob.material_slots) else []
            data_blocks.append(DataBlock(name, type, archive_filename, data,
                                         is_psys_animating(ob, psys, do_mb), material=mat,
                                         do_export=file_is_dirty(rpass.scene, ob, archive_filename)))

    if ob.instance_type != "NONE" and ob.instance_type in SUPPORTED_DUPLI_TYPES:
        name = ob.name + '-DUPLI'
        # duplis aren't animated
        dupli_deforming = False
        if ob.instance_type == "COLLECTION" and ob.instance_collection:
            for dupli_ob in ob.instance_collection.objects:
                sub_dbs = get_dupli_block(dupli_ob, rpass, do_mb)
                if not dupli_deforming:
                    dupli_deforming = any(db.deforming for db in sub_dbs)
                data_blocks.extend(sub_dbs)
        archive_filename = get_archive_filename(name, rpass, dupli_deforming)
        data_blocks.append(DataBlock(name, "DUPLI", archive_filename, ob, dupli_deforming,
                                     do_export=file_is_dirty(rpass.scene, ob, archive_filename)))

    # now the objects data
    if is_data_renderable(rpass.scene, ob) and emit_ob:
        # Check if the object is referring to an archive to use rather then its
        # geometry.
        if ob.renderman.geometry_source != 'BLENDER_SCENE_DATA':
            name = data_name(ob, rpass.scene)
            deforming = is_deforming(ob)
            archive_filename = bpy.path.abspath(ob.renderman.path_archive)
            data_blocks.append(DataBlock(name, "MESH", archive_filename, ob,
                                         deforming, material=get_used_materials(
                                             ob),
                                         do_export=False))
        else:
            name = data_name(ob, rpass.scene)
            deforming = is_deforming(ob)
            archive_filename = get_archive_filename(data_name(ob, rpass.scene),
                                                    rpass, deforming)
            data_blocks.append(DataBlock(name, "MESH", archive_filename, ob,
                                         deforming, material=get_used_materials(
                                             ob),
                                         do_export=file_is_dirty(rpass.scene, ob, archive_filename)))

    return data_blocks


def relpath_archive(archive_filename, rpass):
    if not archive_filename:
        return ''
    else:
        return os.path.relpath(archive_filename, rpass.paths['archive'])


def file_is_dirty(scene, ob, archive_filename):
    if scene.renderman.lazy_rib_gen:
        return check_if_archive_dirty(ob.renderman.update_timestamp,
                                      archive_filename)
    else:
        return True


def get_transform(instance, subframe):
    if not instance.transforming:
        return
    else:
        ob = instance.ob
        if ob.parent and ob.parent_type == "object":
            mat = ob.matrix_local
        else:
            mat = ob.matrix_world
        instance.motion_data.append((subframe, mat.copy()))


def get_deformation(data_block, subframe, scene, subframes):
    if not data_block.deforming or not data_block.do_export:
        return
    else:
        if data_block.type == "MESH":
            mesh = None #create_mesh(data_block.data, scene)
            data_block.motion_data.append((subframe, mesh))
        elif data_block.type == "PSYS":
            ob, psys = data_block.data
            if psys.settings.type == "EMITTER":
                begin_frame = scene.frame_current - 1 if subframe == 1 else scene.frame_current
                end_frame = scene.frame_current + 1 if subframe != 1 else scene.frame_current
                points = get_particles(
                    scene, ob, psys, subframes)
                data_block.motion_data.append((subframe, points))
            else:
                # this is hair
                hairs = get_strands(scene, ob, psys)
                data_block.motion_data.append((subframe, hairs))

# Create two lists, one of data blocks to export and one of instances to export
# Collect and store motion blur transformation data in a pre-process.
# More efficient, and avoids too many frame updates in blender.


def cache_motion(scene, rpass, objects=None, calc_mb=True):
    if objects is None:
        objects = rpass.depsgraph.objects #scene.objects
        #objects = scene.objects
    origframe = scene.frame_current
    instances, data_blocks, motion_segs = \
        get_instances_and_blocks(objects, rpass)
        
    if not calc_mb:
        return data_blocks, instances

    # the aim here is to do only a minimal number of scene updates,
    # so we process objects in batches of equal numbers of segments
    # and update the scene only once for each of those unique fractional
    # frames per segment set
   
    for num_segs, (instance_names, data_names) in motion_segs.items():
        # prepare list of frames/sub-frames in advance,
        # ordered from future to present,
        # to prevent too many scene updates
        # (since loop ends on current frame/subframe)
        subframes = get_subframes(num_segs, scene)
        actual_subframes = [origframe + subframe for subframe in subframes]
        for seg in subframes:
            if seg < 0.0:
                scene.frame_set(origframe - 1, subframe=1.0 + seg)
            else:
                scene.frame_set(origframe, subframe=seg)

            for name in instance_names:
                get_transform(instances[name], seg)

            for name in data_names:
                get_deformation(data_blocks[name],
                                seg, scene, actual_subframes)

    scene.frame_set(origframe, subframe=0)

    return data_blocks, instances


def get_valid_empties(scene, rpass):
    empties = []
    for object in scene.objects:
        if(object.type == 'EMPTY'):
            if(object.renderman.geometry_source == 'ARCHIVE'):
                empties.append(object)
    return empties


# return the filename for a readarchive that this object will be written into
# objects with attached psys's, probably always need to be animated


def get_archive_filename(name, rpass, animated, relative=False):
    path = rpass.paths['frame_archives'] if animated \
        else rpass.paths['static_archives']
    path = os.path.join(path, name + ".rib")
    if relative:
        path = os.path.relpath(path, rpass.paths['archive'])
    return path


def export_rib_box(ri, text_name):
    if text_name not in bpy.data.texts:
        return
    text_block = bpy.data.texts.get(text_name)
    for line in text_block.lines:
        ri.ArchiveRecord(ri.VERBATIM, line.body + "\n")


def get_bounding_box(ob):
    bounds = rib_ob_bounds(ob.bound_box)
    return bounds


def update_timestamp(rpass, obj):
    if obj and rpass.update_time:
        obj.renderman.update_timestamp = rpass.update_time

def property_group_to_rixparams(node, sg_node, light=None):

    params = sg_node.EditParameterBegin()
    for prop_name, meta in node.prop_meta.items():
        prop = getattr(node, prop_name)
        # if property group recurse
        if meta['renderman_type'] == 'page' or prop_name == 'notes' or meta['renderman_type'] == 'enum':
            continue
        # if input socket is linked reference that
        else:
            type = meta['renderman_type']
            name = meta['renderman_name']
            # if struct is not linked continue
            if 'arraySize' in meta:
                if type == 'float':
                    params.SetFloatArray(name, rib(prop), len(prop))
                elif type == 'int':
                    params.SetIntegerArray(name, rib(prop), len(prop))
                elif type == 'color':
                    params.SetColorArray(name, rib(prop), len(prop)/3)
                elif type == 'string':
                    params.SetStringArray(name, rib(prop), len(prop))

            elif ('widget' in meta and meta['widget'] == 'assetIdInput' and prop_name != 'iesProfile'):
                params.SetString(name, get_tex_file_name(prop))

            else:
                
                if type == 'float':
                    params.SetFloat(name, float(prop))
                elif type == 'int':
                    params.SetInteger(name, int(prop))
                elif type == 'color':
                    params.SetColor(name, list(prop)[:3])
                elif type == 'string':
                    params.SetString(name, str(prop))

    if light and node.plugin_name in ['PxrBlockerLightFilter', 'PxrRampLightFilter',
                                     'PxrRodLightFilter']:
        rm = light.renderman
        nt = light.node_tree
        if nt and rm.float_ramp_node in nt.nodes.keys():
            knot_param = 'ramp_Knots' if node.plugin_name == 'PxrRampLightFilter' else 'falloff_Knots'
            float_param = 'ramp_Floats' if node.plugin_name == 'PxrRampLightFilter' else 'falloff_Floats'
            params.Remove('%s' % knot_param)
            params.Remove('%s' % float_param)
            float_node = nt.nodes[rm.float_ramp_node]
            curve = float_node.mapping.curves[0]
            knots = []
            vals = []
            # double the start and end points
            knots.append(curve.points[0].location[0])
            vals.append(curve.points[0].location[1])
            for p in curve.points:
                knots.append(p.location[0])
                vals.append(p.location[1])
            knots.append(curve.points[-1].location[0])
            vals.append(curve.points[-1].location[1])

            params.SetFloatArray(knot_param, knots, len(knots))
            params.SetFloatArray(fkiat_param, vals, len(vals))

        if nt and rm.color_ramp_node in nt.nodes.keys():
            params.Remove('colorRamp_Knots')
            color_node = nt.nodes[rm.color_ramp_node]
            color_ramp = color_node.color_ramp
            colors = []
            positions = []
            # double the start and end points
            positions.append(float(color_ramp.elements[0].position))
            colors.extend(color_ramp.elements[0].color[:3])
            for e in color_ramp.elements:
                positions.append(float(e.position))
                colors.extend(e.color[:3])
            positions.append(
                float(color_ramp.elements[-1].position))
            colors.extend(color_ramp.elements[-1].color[:3])

            params.SetFloatArray('colorRamp_Knots', positions, len(positions))
            params.SetColorArray('colorRamp_Colors', colors, len(positions))            

    sg_node.EditParameterEnd(params)

# takes a list of bpy.types.properties and converts to params for rib
def property_group_to_params(node, light=None):
    params = {}
    for prop_name, meta in node.prop_meta.items():
        prop = getattr(node, prop_name)
        # if property group recurse
        if meta['renderman_type'] == 'page' or prop_name == 'notes' or meta['renderman_type'] == 'enum':
            continue
        # if input socket is linked reference that
        else:
            # if struct is not linked continue
            if 'arraySize' in meta:
                params['%s[%d] %s' % (meta['renderman_type'], len(prop),
                                      meta['renderman_name'])] = rib(prop)
            elif ('widget' in meta and meta['widget'] == 'assetIdInput' and prop_name != 'iesProfile'):
                params['%s %s' % (meta['renderman_type'],
                                  meta['renderman_name'])] = \
                    rib(get_tex_file_name(prop),
                        type_hint=meta['renderman_type'])

            else:
                params['%s %s' % (meta['renderman_type'],
                                  meta['renderman_name'])] = \
                    rib(prop, type_hint=meta['renderman_type'])

    if light and node.plugin_name in ['PxrBlockerLightFilter', 'PxrRampLightFilter',
                                     'PxrRodLightFilter']:
        rm = light.renderman
        nt = light.node_tree
        if nt and rm.float_ramp_node in nt.nodes.keys():
            knot_param = 'ramp_Knots' if node.plugin_name == 'PxrRampLightFilter' else 'falloff_Knots'
            float_param = 'ramp_Floats' if node.plugin_name == 'PxrRampLightFilter' else 'falloff_Floats'
            del params['float[16] %s' % knot_param]
            del params['float[16] %s' % float_param]
            float_node = nt.nodes[rm.float_ramp_node]
            curve = float_node.mapping.curves[0]
            knots = []
            vals = []
            # double the start and end points
            knots.append(curve.points[0].location[0])
            vals.append(curve.points[0].location[1])
            for p in curve.points:
                knots.append(p.location[0])
                vals.append(p.location[1])
            knots.append(curve.points[-1].location[0])
            vals.append(curve.points[-1].location[1])
            params['float[%d] %s' % (len(knots), knot_param)] = knots
            params['float[%d] %s' % (len(vals), float_param)] = vals

        if nt and rm.color_ramp_node in nt.nodes.keys():
            del params['float[16] colorRamp_Knots']
            color_node = nt.nodes[rm.color_ramp_node]
            color_ramp = color_node.color_ramp
            colors = []
            positions = []
            # double the start and end points
            positions.append(float(color_ramp.elements[0].position))
            colors.extend(color_ramp.elements[0].color[:3])
            for e in color_ramp.elements:
                positions.append(float(e.position))
                colors.extend(e.color[:3])
            positions.append(
                float(color_ramp.elements[-1].position))
            colors.extend(color_ramp.elements[-1].color[:3])
            params['float[%d] colorRamp_Knots' % len(positions)] = positions
            params['color[%d] colorRamp_Colors' % len(positions)] = colors

    return params


def render_get_resolution(r):
    xres = int(r.resolution_x * r.resolution_percentage * 0.01)
    yres = int(r.resolution_y * r.resolution_percentage * 0.01)
    return xres, yres


def render_get_aspect(r, camera=None):
    xres, yres = render_get_resolution(r)

    xratio = xres * r.pixel_aspect_x / 200.0
    yratio = yres * r.pixel_aspect_y / 200.0

    if camera is None or camera.type != 'PERSP':
        fit = 'AUTO'
    else:
        fit = camera.sensor_fit

    if fit == 'HORIZONTAL' or fit == 'AUTO' and xratio > yratio:
        aspectratio = xratio / yratio
        xaspect = aspectratio
        yaspect = 1.0
    elif fit == 'VERTICAL' or fit == 'AUTO' and yratio > xratio:
        aspectratio = yratio / xratio
        xaspect = 1.0
        yaspect = aspectratio
    else:
        aspectratio = xaspect = yaspect = 1.0

    return xaspect, yaspect, aspectratio

def export_metadata(scene, params):
    rm = scene.renderman
    if "Camera" not in bpy.data.cameras:
        return
    if "Camera" not in bpy.data.objects:
        return
    cam = bpy.data.cameras["Camera"]
    obj = bpy.data.objects["Camera"]
    if cam.dof.focus_object:
        dof_distance = (obj.location - cam.dof.focus_object.location).length
    else:
        dof_distance = cam.dof.focus_distance
    output_dir = os.path.dirname(user_path(rm.path_rib_output, scene=scene))
    statspath=os.path.join(output_dir, 'stats.%04d.xml' % scene.frame_current)
    
    params.SetString('exrheader_dcc', 'Blender %s\nRenderman for Blender %s' % (bpy.app.version, bl_info['version']))
    params.SetFloat('exrheader_fstop', cam.dof.aperture_fstop )
    params.SetFloat('exrheader_focaldistance', dof_distance )
    params.SetFloat('exrheader_focal', cam.lens )
    params.SetFloat('exrheader_haperture', cam.sensor_width )
    params.SetFloat('exrheader_vaperture', cam.sensor_height )

    params.SetString('exrheader_renderscene', bpy.data.filepath)
    params.SetString('exrheader_user', os.getenv('USERNAME'))
    params.SetString('exrheader_statistics', statspath)
    params.SetString('exrheader_integrator', rm.integrator)
    params.SetFloatArray('exrheader_samples', [rm.min_samples, rm.max_samples], 2)
    params.SetFloat('exrheader_pixelvariance', rm.pixel_variance)
    params.SetString('exrheader_comment', rm.custom_metadata)
    
# --------------- Hopefully temporary --------------- #


def get_instance_materials(ob):
    obmats = []
    # Grab materials attached to object instances ...
    if hasattr(ob, 'material_slots'):
        for ms in ob.material_slots:
            obmats.append(ms.material)
    # ... and to the object's mesh data
    if hasattr(ob.data, 'materials'):
        for m in ob.data.materials:
            obmats.append(m)
    return obmats


def find_preview_material(scene):
    # taken from mitsuba exporter
    objects_materials = {}

    for object in renderable_objects(scene):
        for mat in get_instance_materials(object):
            if mat is not None:
                if object.name not in objects_materials.keys():
                    objects_materials[object] = []
                objects_materials[object].append(mat)

    # find objects that are likely to be the preview objects
    preview_objects = [o for o in objects_materials.keys()
                       if o.name.startswith('preview')]
    if len(preview_objects) < 1:
        return

    # find the materials attached to the likely preview object
    likely_materials = objects_materials[preview_objects[0]]
    if len(likely_materials) < 1:
        return

    return likely_materials[0]

# --------------- End Hopefully temporary --------------- #

channel_name_map = {
    "directDiffuseLobe": "diffuse",
    "subsurfaceLobe": "diffuse",
    "Subsurface": "diffuse",
    "transmissiveSingleScatterLobe": "diffuse",
    "Caustics": "diffuse",
    "Albedo": "diffuse",
    "Diffuse": "diffuse",
    "IndirectDiffuse": "indirectdiffuse",
    "indirectDiffuseLobe": "indirectdiffuse",
    "directSpecularPrimaryLobe": "specular",
    "directSpecularRoughLobe": "specular",
    "directSpecularClearcoatLobe": "specular",
    "directSpecularIridescenceLobe": "specular",
    "directSpecularFuzzLobe": "specular",
    "directSpecularGlassLobe": "specular",
    "transmissiveGlassLobe": "specular",
    "Reflection": "specular",
    "Refraction": "specular",
    "Specular": "specular",
    "indirectSpecularPrimaryLobe": "indirectspecular",
    "indirectSpecularRoughLobe": "indirectspecular",
    "IndirectSpecular": "indirectspecular",
    "indirectSpecularClearcoatLobe": "indirectspecular",
    "indirectSpecularIridescenceLobe": "indirectspecular",
    "indirectSpecularFuzzLobe": "indirectspecular",
    "indirectSpecularGlassLobe": "indirectspecular",
    "Shadows": "emission",
    "All Lighting": "emission",
    "Emission": "emission"
}


def get_channel_name(aov, layer_name):
    aov_name = aov.name.replace(' ', '')
    aov_channel_name = aov.channel_name
    if not aov.aov_name or not aov.channel_name:
        return ''
    elif aov.aov_name == "color rgba":
        aov_channel_name = "Ci,a"
    # Remaps any color lpe channel names to a denoise friendly one
    elif aov_name in channel_name_map.keys():
        aov_channel_name = '%s_%s_%s' % (
            channel_name_map[aov_name], aov_name, layer_name)

    elif aov.aov_name == "color custom_lpe":
        aov_channel_name = aov.name

    else:
        aov_channel_name = '%s_%s' % (
            aov_name, layer_name)

    return aov_channel_name

def anim_archive_path(filepath, frame):
    if filepath.find("#") != -1:
        ribpath = make_frame_path(filepath, fr)
    else:
        ribpath = os.path.splitext(filepath)[0] + "." + str(frame).zfill(4) + \
            os.path.splitext(filepath)[1]
    return ribpath

def make_dspy_info(scene):
    """
    Create some render parameter from scene and pass it to image tool.

    If current scene renders to "it", collect some useful infos from scene
    and send them alongside the render job to RenderMan's image tool. Applies to
    renderpass result only, does not affect postprocessing like denoise.
    """
    params = {}
    rm = scene.renderman
    from time import localtime, strftime
    ts = strftime("%a %x, %X", localtime())
    ts = bytes(ts, 'ascii', 'ignore').decode('utf-8', 'ignore')

    dspy_notes = "Render start:\t%s\r\r" % ts
    dspy_notes += "Integrator:\t%s\r\r" % rm.integrator
    dspy_notes += "Samples:\t%d - %d\r" % (rm.min_samples, rm.max_samples)
    dspy_notes += "Pixel Variance:\t%f\r\r" % rm.pixel_variance

    # moved this in front of integrator check. Was called redundant in
    # both cases
    integrator = getattr(rm, "%s_settings" % rm.integrator)

    if rm.integrator == 'PxrPathTracer':
        dspy_notes += "Mode:\t%s\r" % integrator.sampleMode
        dspy_notes += "Light:\t%d\r" % integrator.numLightSamples
        dspy_notes += "Bxdf:\t%d\r" % integrator.numBxdfSamples

        if integrator.sampleMode == 'bxdf':
            dspy_notes += "Indirect:\t%d\r\r" % integrator.numIndirectSamples
        else:
            dspy_notes += "Diffuse:\t%d\r" % integrator.numDiffuseSamples
            dspy_notes += "Specular:\t%d\r" % integrator.numSpecularSamples
            dspy_notes += "Subsurface:\t%d\r" % integrator.numSubsurfaceSamples
            dspy_notes += "Refraction:\t%d\r" % integrator.numRefractionSamples

    elif rm.integrator == "PxrVCM":
        dspy_notes += "Light:\t%d\r" % integrator.numLightSamples
        dspy_notes += "Bxdf:\t%d\r\r" % integrator.numBxdfSamples

    return dspy_notes

# flush the current edit


# search this material/lamp for textures to re txmake and do them


def reissue_textures(rpass, mat):
    made_tex = False
    files = []
    if mat is not None:
        textures = get_textures(mat) if type(mat) == bpy.types.Material else \
            get_textures_for_node(mat.renderman.get_light_node())

        files = rpass.convert_textures(textures)

    return files

# return true if an object has an emissive connection


def is_emissive(object):
    if hasattr(object.data, 'materials'):
        # update the light position and shaders if updated
        for mat in object.data.materials:
            if mat is not None and mat.node_tree:
                nt = mat.node_tree
                if 'Output' in nt.nodes and \
                        nt.nodes['Output'].inputs['Light'].is_linked:
                    return True
    return False

def update_light_link(rpass, ri, prman, link, remove=False):
    rpass.edit_num += 1
    scene = rpass.scene
    edit_flush(ri, rpass.edit_num, prman)
    strs = link.name.split('>')
    ob_names = [strs[3]] if strs[2] == "obj_object" else \
        scene.renderman.object_groups[strs[3]].members.keys()

    for ob_name in ob_names:
        print("OB_NAME: %s" % ob_name)
        # ri.EditBegin('attribute', {'string scopename': ob_name})
        # scene_lights = [l.name for l in scene.objects if l.type == 'LIGHT']
        # light_names = [strs[1]] if strs[0] == "lg_light" else \
        #     scene.renderman.light_groups[strs[1]].members.keys()
        # if strs[0] == 'lg_group' and strs[1] == 'All':
        #     light_names = [l.name for l in scene.objects if l.type == 'LIGHT']
        # for light_name in light_names:
        #     light = scene.objects[light_name].data
        #     rm = light.renderman
        #     if rm.renderman_type == 'FILTER':
        #         filter_name = light_name
        #         for light_nm in light_names:
        #             if filter_name in scene.objects[light_nm].data.renderman.light_filters.keys():
        #                 lamp_nm = scene.objects[light_nm].data.name
        #                 if remove or link.illuminate == "DEFAULT":
        #                     ri.EnableLightFilter(lamp_nm, filter_name, 1)
        #                 else:
        #                     ri.EnableLightFilter(
        #                         lamp_nm, filter_name, link.illuminate == 'ON')
        #     else:
        #         if remove or link.illuminate == "DEFAULT":
        #             ri.Illuminate(
        #                 light.name, light.renderman.illuminates_by_default)
        #         else:
        #             ri.Illuminate(light.name, link.illuminate == 'ON')
        # ri.EditEnd()

# test the active object type for edits to do then do them