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
import time
import subprocess
import blf
import webbrowser
import math
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
from .rman_utils import prefs_utils
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
            '''
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
            '''
            light.renderman.renderman_light_role = 'RMAN_LIGHT'
            if light_type == 'SUN':
                light.renderman.renderman_light_shader = 'PxrDistantLight'  
            elif light_type == 'HEMI':
                light.renderman.renderman_light_shader = 'PxrDomeLight'
            elif light_type == 'AREA':
                if light.shape == 'DISK':
                    light.renderman.renderman_light_shader = 'PxrDiskLight'
                elif light.shape == 'ELLIPSE':
                    light.renderman.renderman_light_shader = 'PxrSphereLight'
                else:
                    context.light.renderman.renderman_light_shader = 'PxrRectLight'
            elif light_type == 'SPOT':
                light.renderman.renderman_light_shader = 'PxrDiskLight'
                node = context.light.renderman.get_light_node()
                node.coneAngle(math.degrees(light.spot_size))
                node.coneSoftness(light.spot_blend)
            elif light_type == 'POINT':
                context.light.renderman.renderman_light_shader = 'PxrSphereLight'

            light.type = 'AREA'
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
            if context.material.grease_pencil:
                shadergraph_utils.convert_grease_pencil_mat(context.material, nt, output)

            elif not rman_cycles_convert.convert_cycles_nodetree(idblock, output):
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
            light = idblock
            '''
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
            '''

            light.renderman.renderman_light_role = 'RMAN_LIGHT'
            if light_type == 'SUN':
                light.renderman.renderman_light_shader = 'PxrDistantLight'  
            elif light_type == 'HEMI':
                light.renderman.renderman_light_shader = 'PxrDomeLight'
            elif light_type == 'AREA':
                if light.shape == 'DISK':
                    light.renderman.renderman_light_shader = 'PxrDiskLight'
                elif light.shape == 'ELLIPSE':
                    light.renderman.renderman_light_shader = 'PxrSphereLight'
                else:
                    context.light.renderman.renderman_light_shader = 'PxrRectLight'
            elif light_type == 'SPOT':
                light.renderman.renderman_light_shader = 'PxrDiskLight'
                node = context.light.renderman.get_light_node()
                node.coneAngle = math.degrees(light.spot_size)
                node.coneSoftness = light.spot_blend
            elif light_type == 'POINT':
                context.light.renderman.renderman_light_shader = 'PxrSphereLight'            

            light.type = 'AREA'
            light.renderman.use_renderman_node = True

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
    examples_menu = icons.get("rman_help.png")
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
            ("float z", active_layer.use_pass_z, "z_depth"),
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
                    channel.channel_name = 'Ci'
                    channel.channel_def = 'color Ci'
                    channel = aov_setting.dspy_channels.add()
                    channel.name = 'a'
                    channel.channel_name = 'a'
                    channel.channel_def = 'float a'    

                else:
                    aov_setting = rm_rl.custom_aovs.add()
                    aov_setting.name = name

                    channel = aov_setting.dspy_channels.add()
                    channel.name = name
                    channel.channel_def = aov_type
                    channel.channel_name = name                    

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
    RENDERMAN_OT_add_remove_output,
    SHADING_OT_convert_all_renderman_nodetree,
    SHADING_OT_add_renderman_nodetree,
    PRMAN_OT_refresh_osl_shader,
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
    PRMAN_OT_New_bxdf,
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
