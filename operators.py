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
from .util import get_Files_in_Directory

from .rfb_logger import rfb_log
from .rman_utils import scene_utils
from .rman_utils.scene_utils import EXCLUDED_OBJECT_TYPES
from .rman_utils import string_utils

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

def menu_draw(self, context):
    if context.scene.render.engine != "PRMAN_RENDER":
        return
    icons = load_icons()
    examples_menu = icons.get("rman_help.png")
    self.layout.menu("PRMAN_MT_examples", icon_value=examples_menu.icon_id)

# Yuck, this should be built in to blender... Yes it should


class PRMAN_OT_add_multilayer_list(bpy.types.Operator):
    bl_idname = 'renderman.add_multilayer_list'
    bl_label = 'Add multilayer list'

    def execute(self, context):
        scene = context.scene
        scene.renderman.multilayer_lists.add()
        active_layer = context.view_layer
        scene.renderman.multilayer_lists[-1].render_layer = active_layer.name
        return {'FINISHED'}


#################
#       Tab     #
#################

# Menus
compile_shader_menu_func = (lambda self, context: self.layout.operator(
    TEXT_OT_compile_shader.bl_idname))

classes = [
    PRMAN_OT_AddPresetRendermanRender,
    PRMAN_MT_PresetsMenu,
    PRMAN_OT_add_multilayer_list
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
