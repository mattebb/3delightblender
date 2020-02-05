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
import os
import subprocess
import blf
import webbrowser
import addon_utils
from .icons.icons import load_icons
from operator import attrgetter, itemgetter
from bl_operators.presets import AddPresetBase

from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty

from bpy_extras.io_utils import ExportHelper

## These should be removed
from .util import get_addon_prefs
from .util import get_real_path
from .util import readOSO, find_it_path, find_local_queue, find_tractor_spool
from .util import get_Files_in_Directory


from . import rman_cycles_convert
from .rfb_logger import rfb_log
from .rman_utils import scene_utils
from .rman_utils.scene_utils import EXCLUDED_OBJECT_TYPES
from .rman_utils import string_utils
from .rman_utils import shadergraph_utils
from .spool import spool_render
from .rman_render import RmanRender


class PRMAN_OT_Renderman_open_stats(bpy.types.Operator):
    bl_idname = 'rman.open_stats'
    bl_label = "Open Frame Stats"
    bl_description = "Open Current Frame stats file"

    def execute(self, context):
        scene = context.scene
        rm = scene.renderman        
        output_dir = string_utils.expand_string(rm.path_rib_output, 
                                                frame=scene.frame_current, 
                                                asFilePath=True)  
        output_dir = os.path.dirname(output_dir)            
        bpy.ops.wm.url_open(
            url="file://" + os.path.join(output_dir, 'stats.%04d.xml' % scene.frame_current))
        return {'FINISHED'}


class PRMAN_OT_Renderman_start_it(bpy.types.Operator):
    bl_idname = 'rman.start_it'
    bl_label = "Start IT"
    bl_description = "Start RenderMan's IT"

    def execute(self, context):
        scene = context.scene
        rm = scene.renderman
        it_path = find_it_path()
        if not it_path:
            self.report({"ERROR"},
                        "Could not find 'it'.")
        else:
            environ = os.environ.copy()
            subprocess.Popen([it_path], env=environ, shell=True)
        return {'FINISHED'}


class PRMAN_OT_Renderman_open_last_RIB(bpy.types.Operator):
    bl_idname = 'rman.open_rib'
    bl_label = "Open Last RIB Scene file."
    bl_description = "Opens the last generated Scene.rib file in the system default text editor"

    def invoke(self, context, event=None):
        """
        rm = context.scene.renderman
        rpass = RPass(context.scene, interactive=False)
        path = rpass.paths['rib_output']
        if not rm.editor_override:
            try:
                webbrowser.open(path)
            except Exception:
                debug('error', "File not available!")
        else:
            command = rm.editor_override + " " + path
            try:
                os.system(command)
            except Exception:
                debug(
                    'error', "File or text editor not available. (Check and make sure text editor is in system path.)")
        """
        return {'FINISHED'}


class RENDERMAN_OT_add_remove_output(bpy.types.Operator):
    bl_idname = "renderman.add_remove_output"
    bl_label = "Add or remove channel from output"
    info_string: StringProperty()

    def execute(self, context):
        self.report({'INFO'}, self.info_string)
        return {'FINISHED'}


class SHADING_OT_convert_all_renderman_nodetree(bpy.types.Operator):

    ''''''
    bl_idname = "shading.convert_cycles_stuff"
    bl_label = "Convert All Cycles to RenderMan"
    bl_description = "Convert all nodetrees to RenderMan"

    def execute(self, context):
        for mat in bpy.data.materials:
            mat.use_nodes = True
            nt = mat.node_tree
            if shadergraph_utils.is_renderman_nodetree(mat):
                continue
            output = nt.nodes.new('RendermanOutputNode')
            try:
                if not rman_cycles_convert.convert_cycles_nodetree(mat, output):
                    default = nt.nodes.new('PxrSurfaceBxdfNode')
                    default.location = output.location
                    default.location[0] -= 300
                    nt.links.new(default.outputs[0], output.inputs[0])
            except Exception as e:
                self.report({'ERROR'}, "Error converting " + mat.name)
                #self.report({'ERROR'}, str(e))
                # uncomment to debug conversion
                import traceback
                traceback.print_exc()

        for light in bpy.data.lights:
            if light.renderman.use_renderman_node:
                continue
            light_type = light.type
            light.renderman.light_primary_visibility = False
            if light_type == 'SUN':
                light.renderman.renderman_type = 'DIST'
            elif light_type == 'HEMI':
                light.renderman.renderman_type = 'ENV'
                light.renderman.light_primary_visibility = True
            else:
                light.renderman.renderman_type = light_type

            if light_type == 'AREA':
                light.shape = 'RECTANGLE'
                light.size = 1.0
                light.size_y = 1.0

            #light.renderman.primary_visibility = not light.use_nodes

            light.renderman.use_renderman_node = True

        # convert cycles vis settings
        for ob in context.scene.objects:
            if not ob.cycles_visibility.camera:
                ob.renderman.visibility_camera = False
            if not ob.cycles_visibility.diffuse or not ob.cycles_visibility.glossy:
                ob.renderman.visibility_trace_indirect = False
            if not ob.cycles_visibility.transmission:
                ob.renderman.visibility_trace_transmission = False
        return {'FINISHED'}


class SHADING_OT_add_renderman_nodetree(bpy.types.Operator):

    ''''''
    bl_idname = "shading.add_renderman_nodetree"
    bl_label = "Add RenderMan Nodetree"
    bl_description = "Add a RenderMan shader node tree linked to this material"

    idtype: StringProperty(name="ID Type", default="material")
    bxdf_name: StringProperty(name="Bxdf Name", default="PxrSurface")

    def execute(self, context):
        idtype = self.properties.idtype
        if idtype == 'node_editor':
            idblock = context.space_data.id
            idtype = 'material'
        else:
            context_data = {'material': context.material,
                            'light': context.light, 'world': context.scene.world}
            idblock = context_data[idtype]

        # nt = bpy.data.node_groups.new(idblock.name,
        #                              type='RendermanPatternGraph')
        #nt.use_fake_user = True
        idblock.use_nodes = True
        nt = idblock.node_tree

        if idtype == 'material':
            output = nt.nodes.new('RendermanOutputNode')
            
            if not rman_cycles_convert.convert_cycles_nodetree(idblock, output):
                default = nt.nodes.new('%sBxdfNode' %
                                       self.properties.bxdf_name)
                default.location = output.location
                default.location[0] -= 300
                nt.links.new(default.outputs[0], output.inputs[0])

                if idblock.renderman.copy_color_params:
                    default.diffuseColor = idblock.diffuse_color
                    default.diffuseGain = idblock.diffuse_intensity
                    default.enablePrimarySpecular = True
                    default.specularFaceColor = idblock.specular_color
                      
        elif idtype == 'light':
            light_type = idblock.type
            if light_type == 'SUN':
                context.light.renderman.renderman_type = 'DIST'
            elif light_type == 'HEMI':

                context.light.renderman.renderman_type = 'ENV'
            else:
                context.light.renderman.renderman_type = light_type

            if light_type == 'AREA':
                context.light.shape = 'RECTANGLE'
                context.light.size = 1.0
                context.light.size_y = 1.0

            idblock.renderman.use_renderman_node = True

        else:
            idblock.renderman.renderman_type = "ENV"
            idblock.renderman.use_renderman_node = True
            # light_type = idblock.type
            # light_shader = 'PxrStdAreaLightLightNode'
            # if light_type == 'SUN':
            #     context.light.renderman.type=
            #     light_shader = 'PxrStdEnvDayLightLightNode'
            # elif light_type == 'HEMI':
            #     light_shader = 'PxrStdEnvMapLightLightNode'
            # elif light_type == 'AREA' or light_type == 'POINT':
            #     idblock.type = "AREA"
            #     context.light.size = 1.0
            #     context.light.size_y = 1.0

            # else:
            #     idblock.type = "AREA"

            # output = nt.nodes.new('RendermanOutputNode')
            # default = nt.nodes.new(light_shader)
            # default.location = output.location
            # default.location[0] -= 300
            # nt.links.new(default.outputs[0], output.inputs[1])

        return {'FINISHED'}

######################
# OSL Operators
######################


class PRMAN_OT_refresh_osl_shader(bpy.types.Operator):
    bl_idname = "node.refresh_osl_shader"
    bl_label = "Refresh OSL Node"
    bl_description = "Refreshes the OSL node This takes a second!!"

    def invoke(self, context, event):
        context.node.RefreshNodes(context)
        return {'FINISHED'}
        
class PRMAN_OT_RendermanBake(bpy.types.Operator):
    bl_idname = "renderman.bake"
    bl_label = "Baking"
    bl_description = "Bake pattern nodes to texture"
            
    def execute(self, context):

        scene = context.scene
        rman_render = RmanRender.get_rman_render()
        if not rman_render.rman_interactive_running:
            scene.renderman.hider_type = 'BAKE'
            bpy.ops.render.render()
            scene.renderman.hider_type = 'RAYTRACE'
        else:
            self.report({"ERROR"}, "Viewport rendering is on.")        
        return {'FINISHED'}

class PRMAN_OT_ExternalRender(bpy.types.Operator):

    ''''''
    bl_idname = "renderman.external_render"
    bl_label = "External Render"
    bl_description = "Launch and external render outside Blender"
    rpass = None
    is_running = False

    def execute(self, context):
        scene = context.scene
        rman_render = RmanRender.get_rman_render()
        if not rman_render.rman_interactive_running:        
            scene.renderman.enable_external_rendering = True        
            bpy.ops.render.render()
            scene.renderman.enable_external_rendering = False
        else:
            self.report({"ERROR"}, "Viewport rendering is on.")              
        return {'FINISHED'}        

class PRMAN_OT_StartInteractive(bpy.types.Operator):

    ''''''
    bl_idname = "lighting.start_interactive"
    bl_label = "Start Interactive Rendering"
    bl_description = "Start Interactive Rendering"
    rpass = None
    is_running = False

    def invoke(self, context, event=None):
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            if space.shading.type != 'RENDERED':    
                                space.shading.type = 'RENDERED'

        return {'FINISHED'}

class PRMAN_OT_StoptInteractive(bpy.types.Operator):

    ''''''
    bl_idname = "lighting.stop_interactive"
    bl_label = "Stop Interactive Rendering"
    bl_description = "Stop Interactive Rendering"
    rpass = None
    is_running = False

    def invoke(self, context, event=None):
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            if space.shading.type == 'RENDERED':    
                                space.shading.type = 'SOLID'

        return {'FINISHED'}

######################
# Export RIB Operators
######################


class PRMAN_OT_ExportRIBObject(bpy.types.Operator):
    bl_idname = "export.export_rib_archive"
    bl_label = "Export Object as RIB Archive."
    bl_description = "Export single object as a RIB archive for use in other blend files or for other uses"

    export_mat: BoolProperty(
        name="Export Material",
        description="Do you want to export the material?",
        default=True)

    export_all_frames: BoolProperty(
        name="Export All Frames",
        description="Export entire animation time frame",
        default=False)

    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH")

    filename: bpy.props.StringProperty(
        subtype="FILE_NAME",
        default="")

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def execute(self, context):
        ob = context.active_object
        if ob:
            export_path = self.filepath
            export_range = self.export_all_frames
            export_mats = self.export_mat
            rman_render = RmanRender.get_rman_render()
            if not rman_render.rman_interactive_running:
                rman_render.start_export_rib_selected(context, export_path, export_materials=export_mats, export_all_frames=export_range)
            else:
                self.report({"ERROR"}, "Viewport rendering is on.")

        else:
            rfb_log().error("Nothing selected for RIB export.")

        return {'FINISHED'}

    def invoke(self, context, event=None):

        context.window_manager.fileselect_add(self)
        return{'RUNNING_MODAL'}


###########################
# Presets for integrators.
###########################

def quickAddPresets(presetList, pathFromPresetDir, name):
    def as_filename(name):  # could reuse for other presets
        for char in " !@#$%^&*(){}:\";'[]<>,.\\/?":
            name = name.replace(char, '_')
        return name.strip()

    filename = as_filename(name)
    target_path = os.path.join("presets", pathFromPresetDir)
    target_path = bpy.utils.user_resource('SCRIPTS',
                                          target_path,
                                          create=True)
    if not target_path:
        self.report({'WARNING'}, "Failed to create presets path")
        return {'CANCELLED'}
    filepath = os.path.join(target_path, filename) + ".py"
    file_preset = open(filepath, 'w')
    file_preset.write("import bpy\n")

    for item in presetList:
        file_preset.write(str(item) + "\n")
    file_preset.close()


class PRMAN_OT_AddPresetRendermanRender(AddPresetBase, bpy.types.Operator):
    '''Add or remove a RenderMan Sampling Preset'''
    bl_idname = "render.renderman_preset_add"
    bl_label = "Add RenderMan Preset"
    bl_options = {'REGISTER', 'UNDO'}
    preset_menu = "PRMAN_MT_presets"
    preset_defines = ["scene = bpy.context.scene", ]

    preset_values = [
        "scene.renderman.pixel_variance",
        "scene.renderman.min_samples",
        "scene.renderman.max_samples",
        "scene.renderman.max_specular_depth",
        "scene.renderman.max_diffuse_depth",
        "scene.renderman.motion_blur",
        "scene.renderman.do_denoise",
    ]

    preset_subdir = os.path.join("renderman", "render")

# Utility class to contain all default presets
#  this has the added bonus of not using operators for each preset


class RendermanRenderPresets():
    FinalDenoisePreset = [
        "rm = bpy.context.scene.renderman",
        "rm.pixel_variance = 0.01",
        "rm.min_samples = 32",
        "rm.max_samples = 256",
        "rm.max_specular_depth = 6",
        "rm.max_diffuse_depth = 2",
        "rm.motion_blur = True",
        "rm.do_denoise = True",
        "rm.PxrPathTracer_settings.maxPathLength = 10", ]
    FinalHighPreset = [
        "rm = bpy.context.scene.renderman",
        "rm.pixel_variance = 0.0025",
        "rm.min_samples = 64",
        "rm.max_samples = 1024",
        "rm.max_specular_depth = 6",
        "rm.max_diffuse_depth = 3",
        "rm.motion_blur = True",
        "rm.do_denoise = False",
        "rm.PxrPathTracer_settings.maxPathLength = 10", ]
    FinalPreset = [
        "rm = bpy.context.scene.renderman",
        "rm.pixel_variance = 0.005",
        "rm.min_samples = 32",
        "rm.max_samples = 512",
        "rm.max_specular_depth = 6",
        "rm.max_diffuse_depth = 2",
        "rm.motion_blur = True",
        "rm.do_denoise = False",
        "rm.PxrPathTracer_settings.maxPathLength = 10", ]
    MidPreset = [
        "rm = bpy.context.scene.renderman",
        "rm.pixel_variance = 0.05",
        "rm.min_samples = 0",
        "rm.max_samples = 64",
        "rm.max_specular_depth = 6",
        "rm.max_diffuse_depth = 2",
        "rm.motion_blur = True",
        "rm.do_denoise = False",
        "rm.PxrPathTracer_settings.maxPathLength = 10", ]
    PreviewPreset = [
        "rm = bpy.context.scene.renderman",
        "rm.pixel_variance = 0.1",
        "rm.min_samples = 0",
        "rm.max_samples = 16",
        "rm.max_specular_depth = 2",
        "rm.max_diffuse_depth = 1",
        "rm.motion_blur = False",
        "rm.do_denoise = False",
        "rm.PxrPathTracer_settings.maxPathLength = 5", ]
    TractorLocalQueuePreset = [
        "rm = bpy.context.scene.renderman",
        "rm.pixel_variance = 0.01",
        "rm.min_samples = 24",
        "rm.max_samples = 124",
        "rm.max_specular_depth = 6",
        "rm.max_diffuse_depth = 2",
        "rm.motion_blur = True",
        "rm.PxrPathTracer_settings.maxPathLength = 10",
        "rm.enable_external_rendering = True",
        "rm.external_action = \'spool\'", ]


class PRMAN_MT_PresetsMenu(bpy.types.Menu):
    bl_label = "RenderMan Presets"
    bl_idname = "PRMAN_MT_presets"
    preset_subdir = os.path.join("renderman", "render")
    preset_operator = "script.execute_preset"
    draw = bpy.types.Menu.draw_preset

#################
# Sample scenes menu.
#################
# Watch out for global list!!
# Its name should be too long to be accedenty called but you never know.

blenderAddonPaths = addon_utils.paths()
rendermanExampleFilesList = []
names = []
for path in blenderAddonPaths:
    basePath = os.path.join(path, "RenderManForBlender", "examples")
    exists = os.path.exists(basePath)
    if exists:
        names = get_Files_in_Directory(basePath)
for name in names:
    class PRMAN_OT_examplesRenderman(bpy.types.Operator):
        bl_idname = ("rendermanexamples." + name.lower())
        bl_label = name
        bl_description = name

        def invoke(self, context, event):
            sucess = self.loadFile(self, self.bl_label)
            if not sucess:
                self.report({'ERROR'}, "Example Does Not Exist!")
            return {'FINISHED'}

        def loadFile(self, context, exampleName):
            blenderAddonPaths = addon_utils.paths()
            for path in blenderAddonPaths:
                basePath = os.path.join(path, "RenderManForBlender", "examples")
                exists = os.path.exists(basePath)
                if exists:
                    examplePath = os.path.join(
                        basePath, exampleName, exampleName + ".blend")
                    if(os.path.exists(examplePath)):
                        bpy.ops.wm.open_mainfile(filepath=examplePath)
                        return True
                    else:
                        return False
    rendermanExampleFilesList.append(PRMAN_OT_examplesRenderman)


class PRMAN_MT_LoadSceneMenu(bpy.types.Menu):
    bl_label = "RenderMan Examples"
    bl_idname = "PRMAN_MT_examples"

    def get_operator_failsafe(self, idname):
        op = bpy.ops
        for attr in idname.split("."):
            if attr not in dir(op):
                return lambda: None
            op = getattr(op, attr)
        return op

    def draw(self, context):
        for operator in rendermanExampleFilesList:
            self.layout.operator(operator.bl_idname)


def menu_draw(self, context):
    if context.scene.render.engine != "PRMAN_RENDER":
        return
    icons = load_icons()
    examples_menu = icons.get("help")
    self.layout.menu("PRMAN_MT_examples", icon_value=examples_menu.icon_id)

# Yuck, this should be built in to blender... Yes it should


class COLLECTION_OT_add_remove(bpy.types.Operator):
    bl_label = "Add or Remove Paths"
    bl_idname = "collection.add_remove"

    action: EnumProperty(
        name="Action",
        description="Either add or remove properties",
        items=[('ADD', 'Add', ''),
               ('REMOVE', 'Remove', '')],
        default='ADD')
    context: StringProperty(
        name="Context",
        description="Name of context member to find renderman pointer in",
        default="")
    collection: StringProperty(
        name="Collection",
        description="The collection to manipulate",
        default="")
    collection_index: StringProperty(
        name="Index Property",
        description="The property used as a collection index",
        default="")
    defaultname: StringProperty(
        name="Default Name",
        description="Default name to give this collection item",
        default="")
    # BBM addition begin
    is_shader_param: BoolProperty(name='Is shader parameter', default=False)
    shader_type: StringProperty(
        name="shader type",
        default='surface')
    # BBM addition end

    def invoke(self, context, event):
        scene = context.scene
        # BBM modification
        if not self.properties.is_shader_param:
            id = string_utils.getattr_recursive(context, self.properties.context)
            rm = id.renderman if hasattr(id, 'renderman') else id
        else:
            if context.active_object.name in bpy.data.lights.keys():
                rm = bpy.data.lights[context.active_object.name].renderman
            else:
                rm = context.active_object.active_material.renderman
            id = getattr(rm, '%s_shaders' % self.properties.shader_type)
            rm = getattr(id, self.properties.context)

        prop_coll = self.properties.collection
        coll_idx = self.properties.collection_index

        collection = getattr(rm, prop_coll)
        index = getattr(rm, coll_idx)

        # otherwise just add an empty one
        if self.properties.action == 'ADD':
            collection.add()

            index += 1
            setattr(rm, coll_idx, index)
            collection[-1].name = self.properties.defaultname
            # BBM addition begin
            # if coshader array, add the selected coshader
            if self.is_shader_param:
                coshader_name = getattr(rm, 'bl_hidden_%s_menu' % prop_coll)
                collection[-1].name = coshader_name
            # BBM addition end
        elif self.properties.action == 'REMOVE':
            if prop_coll == 'light_groups' and collection[index].name == 'All':
                return {'FINISHED'}
            elif prop_coll == 'object_groups' and collection[index].name == 'collector':
                return {'FINISHED'}
            elif prop_coll == 'aov_channels' and not collection[index].custom:
                return {'FINISHED'}
            else:
                collection.remove(index)
                setattr(rm, coll_idx, index - 1)

        return {'FINISHED'}


class PRMAN_OT_add_renderman_aovs(bpy.types.Operator):
    bl_idname = 'renderman.add_renderman_aovs'
    bl_label = "Switch to RenderMan Passes"

    def execute(self, context):
        scene = context.scene
        scene.renderman.render_layers.add()
        active_layer = context.view_layer
        # this sucks.  but can't find any other way to refer to render layer
        scene.renderman.render_layers[-1].render_layer = active_layer.name

        # add the already existing passes
        scene = context.scene
        rm = scene.renderman
        rm_rl = scene.renderman.render_layers[-1]
        active_layer = context.view_layer

        rl = active_layer

        aovs = [
            # (name, do?, declare type/name, source)
            ("color rgba", active_layer.use_pass_combined, "rgba"),
            ("float z", active_layer.use_pass_z, "z"),
            ("normal Nn", active_layer.use_pass_normal, "Normal"),
            ("vector dPdtime", active_layer.use_pass_vector, "Vectors"),
            ("float u", active_layer.use_pass_uv, "u"),
            ("float v", active_layer.use_pass_uv, "v"),
            ("float id", active_layer.use_pass_object_index, "id"),
            ("color lpe:shadows;C[<.D><.S>]<L.>",
             active_layer.use_pass_shadow, "Shadows"),
            ("color lpe:C<.D><L.>",
             active_layer.use_pass_diffuse_direct, "Diffuse"),
            ("color lpe:(C<RD>[DS]+<L.>)|(C<RD>[DS]*O)",
             active_layer.use_pass_diffuse_indirect, "IndirectDiffuse"),
            ("color lpe:nothruput;noinfinitecheck;noclamp;unoccluded;overwrite;C(U2L)|O",
             active_layer.use_pass_diffuse_color, "Albedo"),
            ("color lpe:C<.S><L.>",
             active_layer.use_pass_glossy_direct, "Specular"),
            ("color lpe:(C<RS>[DS]+<L.>)|(C<RS>[DS]*O)",
             active_layer.use_pass_glossy_indirect, "IndirectSpecular"),
            ("color lpe:(C<TD>[DS]+<L.>)|(C<TD>[DS]*O)",
             active_layer.use_pass_subsurface_indirect, "Subsurface"),
            ("color lpe:emission", active_layer.use_pass_emit, "Emission"),
        ]

        for aov_type, attr, name in aovs:
            if attr:
                if name == "rgba":
                    aov_setting = rm_rl.custom_aovs.add()
                    aov_setting.name = 'beauty'
                    channel = aov_setting.dspy_channels.add()
                    channel.name = 'Ci'
                    channel.aov_name = 'color Ci'
                    channel = aov_setting.dspy_channels.add()
                    channel.name = 'a'
                    channel.aov_name = 'float a'    

                else:
                    aov_setting = rm_rl.custom_aovs.add()
                    aov_setting.name = name

                    channel = aov_setting.dspy_channels.add()
                    channel.name = name
                    channel.aov_name = aov_type
                    channel.channel_name = name                    

                    #aov_setting.aov_name = aov_type
                    #aov_setting.name = name
                    #aov_setting.channel_name = name

        return {'FINISHED'}


class PRMAN_OT_add_multilayer_list(bpy.types.Operator):
    bl_idname = 'renderman.add_multilayer_list'
    bl_label = 'Add multilayer list'

    def execute(self, context):
        scene = context.scene
        scene.renderman.multilayer_lists.add()
        active_layer = context.view_layer
        scene.renderman.multilayer_lists[-1].render_layer = active_layer.name
        return {'FINISHED'}


class PRMAN_OT_add_to_group(bpy.types.Operator):
    bl_idname = 'renderman.add_to_group'
    bl_label = 'Add Selected to Object Group'

    group_index: IntProperty(default=0)
    item_type: StringProperty(default='object')

    def execute(self, context):
        scene = context.scene
        group_index = self.properties.group_index
        item_type = self.properties.item_type

        object_group = scene.renderman.object_groups if item_type == 'object' \
            else scene.renderman.light_groups
        object_group = object_group[group_index].members
        if hasattr(context, 'selected_objects'):

            members = object_group.keys()

            for ob in context.selected_objects:
                if ob.name not in members:
                    if item_type != 'light' or ob.type == 'LIGHT':
                        do_add = True
                        if item_type == 'light' and ob.type == 'LIGHT':
                            # check if light is already in another group
                            # can only be in one
                            for lg in scene.renderman.light_groups:
                                if ob.name in lg.members.keys():
                                    do_add = False
                                    self.report({'WARNING'}, "Light %s cannot be added to light group %s, already a member of %s" % (
                                        ob.name, scene.renderman.light_groups[group_index].name, lg.name))

                        if do_add:
                            ob_in_group = object_group.add()
                            ob_in_group.name = ob.name

        return {'FINISHED'}


class PRMAN_OT_remove_from_group(bpy.types.Operator):
    bl_idname = 'renderman.remove_from_group'
    bl_label = 'Remove Selected from Object Group'

    group_index: IntProperty(default=0)
    item_type: StringProperty(default='object')

    def execute(self, context):
        scene = context.scene
        group_index = self.properties.group_index
        item_type = self.properties.item_type

        object_group = scene.renderman.object_groups if item_type == 'object' \
            else scene.renderman.light_groups
        object_group = object_group[group_index].members
        if hasattr(context, 'selected_objects'):
            for ob in context.selected_objects:
                if ob.name in object_group.keys():
                    index = object_group.keys().index(ob.name)
                    object_group.remove(index)

        return {'FINISHED'}


class PRMAN_OT_remove_add_rem_light_link(bpy.types.Operator):
    bl_idname = 'renderman.add_rem_light_link'
    bl_label = 'Add/Remove Selected from Object Group'

    add_remove: StringProperty(default='add')
    ll_name: StringProperty(default='')

    def execute(self, context):
        scene = context.scene

        add_remove = self.properties.add_remove
        ll_name = self.properties.ll_name

        if add_remove == 'add':
            ll = scene.renderman.ll.add()
            ll.name = ll_name
        else:
            ll_index = scene.renderman.ll.keys().index(ll_name)
            if engine.is_ipr_running():
                engine.ipr.remove_light_link(
                    context, scene.renderman.ll[ll_index])
            scene.renderman.ll.remove(ll_index)

        return {'FINISHED'}


#################
#       Tab     #
#################

class PRMAN_OT_Add_Subdiv_Sheme(bpy.types.Operator):
    bl_idname = "object.add_subdiv_sheme"
    bl_label = "Add Subdiv Sheme"
    bl_description = ""
    bl_options = {"REGISTER"}

    def execute(self, context):
        bpy.context.object.renderman.primitive = 'SUBDIVISION_MESH'

        return {"FINISHED"}


class PRMAN_OT_RM_Add_Area(bpy.types.Operator):
    bl_idname = "object.mr_add_area"
    bl_label = "Add RenderMan Area"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        bpy.ops.object.light_add(type='AREA')
        bpy.ops.shading.add_renderman_nodetree(
            {'material': None, 'light': bpy.context.active_object.data}, idtype='light')
        return {"FINISHED"}


class PRMAN_OT_RM_Add_LightFilter(bpy.types.Operator):
    bl_idname = "object.mr_add_light_filter"
    bl_label = "Add RenderMan Light Filter"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        bpy.ops.object.light_add(type='POINT')
        light = bpy.context.active_object.data
        bpy.ops.shading.add_renderman_nodetree(
            {'material': None, 'light': light}, idtype='light')
        light.renderman.renderman_type = 'FILTER'
        return {"FINISHED"}


class PRMAN_OT_RM_Add_Hemi(bpy.types.Operator):
    bl_idname = "object.mr_add_hemi"
    bl_label = "Add RenderMan Hemi"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        bpy.ops.object.light_add(type='SUN')
        bpy.ops.shading.add_renderman_nodetree(
            {'material': None, 'light': bpy.context.active_object.data}, idtype='light')
        bpy.context.object.data.renderman.renderman_type = 'ENV'
        return {"FINISHED"}


class PRMAN_OT_RM_Add_Sky(bpy.types.Operator):
    bl_idname = "object.mr_add_sky"
    bl_label = "Add RenderMan Sky"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.ops.object.light_add(type='SUN')
        bpy.ops.shading.add_renderman_nodetree(
            {'material': None, 'light': bpy.context.active_object.data}, idtype='light')
        bpy.context.object.data.renderman.renderman_type = 'SKY'

        return {"FINISHED"}


class PRMAN_OT_Add_bxdf(bpy.types.Operator):
    bl_idname = "object.add_bxdf"
    bl_label = "Add BXDF"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def get_type_items(self, context):
        items = [
            ("PxrSurface", "PxrSurface",
             'PxrSurface Uber shader. For most hard surfaces'),
            ("PxrLayerSurface", "PxrLayerSurface",
             "PxrLayerSurface, creates a surface with two Layers"),
            ("PxrMarschnerHair", "PxrMarschnerHair", "Hair Shader"),
            ("PxrDisney", "PxrDisney",
             "Disney Bxdf, a simple uber shader with no layering"),
            ("PxrVolume", "PxrVolume", "Volume Shader")
        ]
        # for nodetype in RendermanPatternGraph.nodetypes.values():
        #    if nodetype.renderman_node_type == 'bxdf':
        #        items.append((nodetype.bl_label, nodetype.bl_label,
        #                      nodetype.bl_label))
        return items
    bxdf_name: EnumProperty(items=get_type_items, name="Bxdf Name")

    def execute(self, context):
        selection = bpy.context.selected_objects if hasattr(
            bpy.context, 'selected_objects') else []
        #selection = bpy.context.selected_objects
        bxdf_name = self.properties.bxdf_name
        mat = bpy.data.materials.new(bxdf_name)

        mat.use_nodes = True
        nt = mat.node_tree

        output = nt.nodes.new('RendermanOutputNode')
        default = nt.nodes.new('%sBxdfNode' % bxdf_name)
        default.location = output.location
        default.location[0] -= 300
        nt.links.new(default.outputs[0], output.inputs[0])

        if bxdf_name == 'PxrLayerSurface':
            mixer = nt.nodes.new("PxrLayerMixerPatternNode")
            layer1 = nt.nodes.new("PxrLayerPatternNode")
            layer2 = nt.nodes.new("PxrLayerPatternNode")

            mixer.location = default.location
            mixer.location[0] -= 300

            layer1.location = mixer.location
            layer1.location[0] -= 300
            layer1.location[1] += 300

            layer2.location = mixer.location
            layer2.location[0] -= 300
            layer2.location[1] -= 300

            nt.links.new(mixer.outputs[0], default.inputs[0])
            nt.links.new(layer1.outputs[0], mixer.inputs['baselayer'])
            nt.links.new(layer2.outputs[0], mixer.inputs['layer1'])

        for obj in selection:
            if(obj.type not in EXCLUDED_OBJECT_TYPES):
                bpy.ops.object.material_slot_add()

                obj.material_slots[-1].material = mat

        return {"FINISHED"}


class PRMAN_OT_New_bxdf(bpy.types.Operator):
    bl_idname = "nodes.new_bxdf"
    bl_label = "New RenderMan Material"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ob = context.object
        bxdf_name = 'PxrSurface'
        mat = bpy.data.materials.new(bxdf_name)
        ob.active_material = mat
        mat.use_nodes = True
        nt = mat.node_tree

        output = nt.nodes.new('RendermanOutputNode')
        default = nt.nodes.new('PxrSurfaceBxdfNode')
        default.location = output.location
        default.location[0] -= 300
        nt.links.new(default.outputs[0], output.inputs[0])

        return {"FINISHED"}


class PRMAN_OT_add_GeoLight(bpy.types.Operator):
    bl_idname = "object.addgeoarealight"
    bl_label = "Add GeoAreaLight"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        selection = bpy.context.selected_objects
        mat = bpy.data.materials.new("PxrMeshLight")

        mat.use_nodes = True
        nt = mat.node_tree

        output = nt.nodes.new('RendermanOutputNode')
        geoLight = nt.nodes.new('PxrMeshLightLightNode')
        geoLight.location[0] -= 300
        geoLight.location[1] -= 420
        if(output is not None):
            nt.links.new(geoLight.outputs[0], output.inputs[1])

        # add PxrBlack Bxdf
        default = nt.nodes.new('PxrBlackBxdfNode')
        default.location = output.location
        default.location[0] -= 300
        if (default is not None):
            nt.links.new(default.outputs[0], output.inputs[0])

        for obj in selection:
            if(obj.type not in EXCLUDED_OBJECT_TYPES):
                bpy.ops.object.material_slot_add()
                obj.material_slots[-1].material = mat
        return {"FINISHED"}


class PRMAN_OT_Select_Lights(bpy.types.Operator):
    bl_idname = "object.selectlights"
    bl_label = "Select Lights"

    Light_Name: bpy.props.StringProperty(default="")

    def execute(self, context):

        bpy.ops.object.select_all(action='DESELECT')
        bpy.data.objects[self.Light_Name].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects[self.Light_Name]

        return {'FINISHED'}


class PRMAN_MT_Hemi_List_Menu(bpy.types.Menu):
    #bl_idname = "object.hemi_list_menu"
    bl_label = "EnvLight list"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        lights = [obj for obj in bpy.context.scene.objects if obj.type == "LIGHT"]

        if len(lights):
            for light in lights:
                if light.data.type == 'HEMI':
                    name = light.name
                    op = layout.operator(
                        "object.selectlights", text=name, icon='LIGHT_HEMI')
                    op.Light_Name = name

        else:
            layout.label(text="No EnvLight in the Scene")


class PRMAN_MT_Area_List_Menu(bpy.types.Menu):
    #bl_idname = "object.area_list_menu"
    bl_label = "AreaLight list"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        lights = [obj for obj in bpy.context.scene.objects if obj.type == "LIGHT"]

        if len(lights):
            for light in lights:
                if light.data.type == 'AREA':
                    name = light.name
                    op = layout.operator(
                        "object.selectlights", text=name, icon='LIGHT_AREA')
                    op.Light_Name = name

        else:
            layout.label(text="No AreaLight in the Scene")


class PRMAN_MT_DayLight_List_Menu(bpy.types.Menu):
    #bl_idname = "object.daylight_list_menu"
    bl_label = "DayLight list"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        lights = [obj for obj in bpy.context.scene.objects if obj.type == "LIGHT"]

        if len(lights):
            for light in lights:
                if light.data.type == 'SUN':
                    name = light.name
                    op = layout.operator(
                        "object.selectlights", text=name, icon='LIGHT_SUN')
                    op.Light_Name = name

        else:
            layout.label(text="No Daylight in the Scene")


class PRMAN_OT_Select_Cameras(bpy.types.Operator):
    bl_idname = "object.select_cameras"
    bl_label = "Select Cameras"

    Camera_Name: bpy.props.StringProperty(default="")

    def execute(self, context):

        bpy.ops.object.select_all(action='DESELECT')
        bpy.data.objects[self.Camera_Name].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects[self.Camera_Name]

        return {'FINISHED'}


class PRMAN_MT_Camera_List_Menu(bpy.types.Menu):
    #bl_idname = "object.camera_list_menu"
    bl_label = "Camera list"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        cameras = [
            obj for obj in bpy.context.scene.objects if obj.type == "CAMERA"]

        if len(cameras):
            for cam in cameras:
                name = cam.name
                op = layout.operator(
                    "object.select_cameras", text=name, icon='CAMERA_DATA')
                op.Camera_Name = name

        else:
            layout.label(text="No Camera in the Scene")


class PRMAN_OT_DeleteLights(bpy.types.Operator):
    bl_idname = "object.delete_lights"
    bl_label = "Delete Lights"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        type_light = bpy.context.object.data.type
        bpy.ops.object.delete()

        lights = [obj for obj in bpy.context.scene.objects if obj.type ==
                 "LIGHT" and obj.data.type == type_light]

        if len(lights):
            lights[0].select = True
            bpy.context.view_layer.objects.active = lights[0]
            return {"FINISHED"}

        else:
            return {"FINISHED"}


class PRMAN_OT_Deletecameras(bpy.types.Operator):
    bl_idname = "object.delete_cameras"
    bl_label = "Delete Cameras"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        type_camera = bpy.context.object.data.type
        bpy.ops.object.delete()

        camera = [obj for obj in bpy.context.scene.objects if obj.type ==
                  "CAMERA" and obj.data.type == type_camera]

        if len(camera):
            camera[0].select = True
            bpy.context.view_layer.objects.active = camera[0]
            return {"FINISHED"}

        else:
            return {"FINISHED"}


class PRMAN_OT_AddCamera(bpy.types.Operator):
    bl_idname = "object.add_prm_camera"
    bl_label = "Add Camera"
    bl_description = "Add a Camera in the Scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        bpy.context.space_data.lock_camera = False

        bpy.ops.object.camera_add()

        bpy.ops.view3d.object_as_camera()

        bpy.ops.view3d.view_camera()

        bpy.ops.view3d.camera_to_view()

        bpy.context.object.data.clip_end = 10000
        bpy.context.object.data.lens = 85

        return {"FINISHED"}

# This operator should not be exposed to the UI as
#   this can cause the loss of data since Blender does not
#   preserve any information during script restart.


class PRMAN_OT_restart_addon(bpy.types.Operator):
    bl_idname = "renderman.restartaddon"
    bl_label = "Restart Addon"
    bl_description = "Restarts the RenderMan for Blender addon"

    def execute(self, context):
        bpy.ops.script.reload()
        return {"FINISHED"}


# Menus
compile_shader_menu_func = (lambda self, context: self.layout.operator(
    TEXT_OT_compile_shader.bl_idname))

classes = [
    PRMAN_OT_Renderman_open_stats,
    PRMAN_OT_Renderman_start_it,
    PRMAN_OT_Renderman_open_last_RIB,
    RENDERMAN_OT_add_remove_output,
    SHADING_OT_convert_all_renderman_nodetree,
    SHADING_OT_add_renderman_nodetree,
    PRMAN_OT_refresh_osl_shader,
    PRMAN_OT_RendermanBake,
    PRMAN_OT_ExternalRender,
    PRMAN_OT_StartInteractive,
    PRMAN_OT_StoptInteractive,
    PRMAN_OT_ExportRIBObject,
    PRMAN_OT_AddPresetRendermanRender,
    PRMAN_MT_PresetsMenu,
    PRMAN_OT_examplesRenderman,
    PRMAN_MT_LoadSceneMenu,
    COLLECTION_OT_add_remove,
    PRMAN_OT_add_renderman_aovs,
    PRMAN_OT_add_multilayer_list,
    PRMAN_OT_add_to_group,
    PRMAN_OT_remove_from_group,
    PRMAN_OT_remove_add_rem_light_link,
    PRMAN_OT_Add_Subdiv_Sheme,
    PRMAN_OT_RM_Add_Area,
    PRMAN_OT_RM_Add_LightFilter,
    PRMAN_OT_RM_Add_Hemi,
    PRMAN_OT_RM_Add_Sky,
    PRMAN_OT_Add_bxdf,
    PRMAN_OT_New_bxdf,
    PRMAN_OT_add_GeoLight,
    PRMAN_OT_Select_Lights,
    PRMAN_MT_Hemi_List_Menu,
    PRMAN_MT_Area_List_Menu,
    PRMAN_MT_DayLight_List_Menu,
    PRMAN_OT_Select_Cameras,
    PRMAN_MT_Camera_List_Menu,
    PRMAN_OT_DeleteLights,
    PRMAN_OT_Deletecameras,
    PRMAN_OT_AddCamera,
    PRMAN_OT_restart_addon,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.TEXT_MT_text.append(compile_shader_menu_func)
    #bpy.types.TEXT_MT_toolbox.append(compile_shader_menu_func)
    bpy.types.TOPBAR_MT_help.append(menu_draw)

    # Register any default presets here. This includes render based and
    # Material based
    quickAddPresets(RendermanRenderPresets.FinalDenoisePreset,
                    os.path.join("renderman", "render"), "FinalDenoisePreset")
    quickAddPresets(RendermanRenderPresets.FinalHighPreset,
                    os.path.join("renderman", "render"), "FinalHigh_Preset")
    quickAddPresets(RendermanRenderPresets.FinalPreset,
                    os.path.join("renderman", "render"), "FinalPreset")
    quickAddPresets(RendermanRenderPresets.MidPreset,
                    os.path.join("renderman", "render"), "MidPreset")
    quickAddPresets(RendermanRenderPresets.PreviewPreset,
                    os.path.join("renderman", "render"), "PreviewPreset")
    quickAddPresets(RendermanRenderPresets.TractorLocalQueuePreset, os.path.join(
        "renderman", "render"), "TractorLocalQueuePreset")


def unregister():
    bpy.types.TEXT_MT_text.remove(compile_shader_menu_func)
    #bpy.types.TEXT_MT_toolbox.remove(compile_shader_menu_func)
    bpy.types.TOPBAR_MT_help.remove(menu_draw)
    
    # It should be fine to leave presets registered as they are not in memory.
    
    for cls in classes:
        bpy.utils.unregister_class(cls)
