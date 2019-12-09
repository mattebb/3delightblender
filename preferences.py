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
import sys
import os
from bpy.types import AddonPreferences
from bpy.props import CollectionProperty, BoolProperty, StringProperty
from bpy.props import IntProperty, PointerProperty, EnumProperty

from .rman_utils import filepath_utils
from . import rfb_logger

from .presets.properties import RendermanPresetGroup

class RendermanPreferencePath(bpy.types.PropertyGroup):
    name: StringProperty(name="", subtype='DIR_PATH')


class RendermanEnvVarSettings(bpy.types.PropertyGroup):
    if sys.platform == ("win32"):
        outpath = os.path.join(
            "C:", "Users", os.getlogin(), "Documents", "PRMan")
        out: StringProperty(
            name="OUT (Output Root)",
            description="Default RIB export path root",
            subtype='DIR_PATH',
            default='C:/tmp/renderman_for_blender/{blend}')

    else:
        outpath = os.path.join(os.environ.get('HOME'), "Documents", "PRMan")
        out: StringProperty(
            name="OUT (Output Root)",
            description="Default RIB export path root",
            subtype='DIR_PATH',
            default='/tmp/renderman_for_blender/{blend}')

    shd: StringProperty(
        name="SHD (Shadow Maps)",
        description="SHD environment variable",
        subtype='DIR_PATH',
        default=os.path.join('$OUT', 'shadowmaps'))

    ptc: StringProperty(
        name="PTC (Point Clouds)",
        description="PTC environment variable",
        subtype='DIR_PATH',
        default=os.path.join('$OUT', 'pointclouds'))

    arc: StringProperty(
        name="ARC (Archives)",
        description="ARC environment variable",
        subtype='DIR_PATH',
        default=os.path.join('$OUT', 'archives'))


class RendermanPreferences(AddonPreferences):
    bl_idname = __package__

    # find the renderman options installed
    def find_installed_rendermans(self, context):
        options = [('NEWEST', 'Newest Version Installed',
                    'Automatically updates when new version installed. NB: If an RMANTREE environment variable is set, this will always take precedence.')]
        for vers, path in filepath_utils.get_installed_rendermans():
            options.append((path, vers, path))
        return options

    shader_paths: CollectionProperty(type=RendermanPreferencePath,
                                      name="Shader Paths")
    shader_paths_index: IntProperty(min=-1, default=-1)

    texture_paths: CollectionProperty(type=RendermanPreferencePath,
                                       name="Texture Paths")
    texture_paths_index: IntProperty(min=-1, default=-1)

    procedural_paths: CollectionProperty(type=RendermanPreferencePath,
                                          name="Procedural Paths")
    procedural_paths_index: IntProperty(min=-1, default=-1)

    archive_paths: CollectionProperty(type=RendermanPreferencePath,
                                       name="Archive Paths")
    archive_paths_index: IntProperty(min=-1, default=-1)

    use_default_paths: BoolProperty(
        name="Use RenderMan default paths",
        description="Includes paths for default shaders etc. from RenderMan Pro\
            Server install",
        default=True)
    use_builtin_paths: BoolProperty(
        name="Use built in paths",
        description="Includes paths for default shaders etc. from RenderMan\
            exporter",
        default=False)

    rmantree_choice: EnumProperty(
        name='RenderMan Version to use',
        description='Leaving as "Newest" will automatically update when you install a new RenderMan version',
        # default='NEWEST',
        items=find_installed_rendermans
    )

    rmantree_method: EnumProperty(
        name='RenderMan Location',
        description='''How RenderMan should be detected.  Most users should leave to "Detect". 
                    Users should restart Blender after making a change.
                    ''',
        items=[('ENV', 'Get From RMANTREE Environment Variable',
                'This will use the RMANTREE set in the enviornment variables'),
                ('DETECT', 'Choose From Installed', 
                '''This will scan for installed RenderMan locations to choose from.'''),
                ('MANUAL', 'Set Manually', 'Manually set the RenderMan installation (for expert users)')],
        default='ENV')

    path_rmantree: StringProperty(
        name="RMANTREE Path",
        description="Path to RenderMan Pro Server installation folder",
        subtype='DIR_PATH',
        default='')
    path_renderer: StringProperty(
        name="Renderer Path",
        description="Path to renderer executable",
        subtype='FILE_PATH',
        default="prman")
    path_shader_compiler: StringProperty(
        name="Shader Compiler Path",
        description="Path to shader compiler executable",
        subtype='FILE_PATH',
        default="shader")
    path_shader_info: StringProperty(
        name="Shader Info Path",
        description="Path to shaderinfo executable",
        subtype='FILE_PATH',
        default="sloinfo")
    path_texture_optimiser: StringProperty(
        name="Texture Optimiser Path",
        description="Path to tdlmake executable",
        subtype='FILE_PATH',
        default="txmake")

    draw_ipr_text: BoolProperty(
        name="Draw IPR Text",
        description="Draw notice on View3D when IPR is active",
        default=True)

    draw_panel_icon: BoolProperty(
        name="Draw Panel Icon",
        description="Draw an icon on RenderMan Panels",
        default=True)

    path_display_driver_image: StringProperty(
        name="Main Image path",
        description="Path for the rendered main image",
        subtype='FILE_PATH',
        default=os.path.join('{OUT}', 'images', '{scene}.{layer}.{F4}.{ext}'))

    path_aov_image: StringProperty(
        name="AOV Image path",
        description="Path for the rendered aov images",
        subtype='FILE_PATH',
        default=os.path.join('{OUT}', 'images', '{scene}.{layer}.{aov}.{F4}.{ext}'))

    path_fallback_textures_path: StringProperty(
        name="Fallback Texture Path",
        description="Fallback path for textures, when the current directory is not writable",
        subtype='FILE_PATH',
        default=os.path.join('{OUT}', 'textures'))        

    env_vars: PointerProperty(
        type=RendermanEnvVarSettings,
        name="Environment Variable Settings")

    auto_check_update: bpy.props.BoolProperty(
        name = "Auto-check for Update",
        description = "If enabled, auto-check for updates using an interval",
        default = True,
        )

    def update_rman_logging_level(self, context):
        level = rfb_logger.__LOG_LEVELS__[self.rman_logging_level]
        rfb_logger.set_logger_level(level)

    rman_logging_level: EnumProperty(
        name='Logging Level',
        description='''Log level verbosity. Advanced: Setting the RFB_LOG_LEVEL environment variable will override this preference.
                    ''',
        items=[('CRITICAL', 'Critical', ''),
                ('ERROR', 'Error', ''),
                ('WARNING', 'Warning', ''),
                ('INFO', 'Info', ''),
                ('VERBOSE', 'Verbose', ''),
                ('DEBUG', 'Debug', ''),
        ],
        default='WARNING',
        update=update_rman_logging_level)

    presets_library: PointerProperty(
        type=RendermanPresetGroup,
    )

    # both these paths are absolute
    active_presets_path: StringProperty(default = '')
    presets_path:StringProperty(
        name="Path for preset Library",
        description="Path for preset files, if not present these will be copied from RMANTREE.\n  Set this if you want to pull in an external library.",
        subtype='FILE_PATH',
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'presets', 'RenderManAssetLibrary'))


    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'rmantree_method')
        if self.rmantree_method == 'DETECT':
            layout.prop(self, 'rmantree_choice')
            if self.rmantree_choice == 'NEWEST':
                layout.label(text="RMANTREE: %s " % filepath_utils.guess_rmantree())
        elif self.rmantree_method == 'ENV':
            layout.label(text="RMANTREE: %s " % filepath_utils.rmantree_from_env())
        else:
            layout.prop(self, "path_rmantree")
        if filepath_utils.guess_rmantree() is None:
            row = layout.row()
            row.alert = True
            row.label(text='Error in RMANTREE. Reload addon to reset.', icon='ERROR')

        layout.prop(self, 'rman_logging_level')
        env = self.env_vars
        layout.prop(env, "out")
        layout.prop(self, 'path_display_driver_image')
        layout.prop(self, 'path_aov_image')
        layout.prop(self, 'path_fallback_textures_path')        
        layout.prop(self, 'draw_ipr_text')
        layout.prop(self, 'draw_panel_icon')
        #layout.prop(self, 'active_presets_path')
        layout.prop(self.presets_library, 'path')

        #layout.prop(env, "shd")
        #layout.prop(env, "ptc")
        #layout.prop(env, "arc")


def register():
    #from .presets import properties
    #properties.register()
    bpy.utils.register_class(RendermanPreferencePath)
    bpy.utils.register_class(RendermanEnvVarSettings)
    bpy.utils.register_class(RendermanPreferences)


def unregister():
    bpy.utils.unregister_class(RendermanPreferences)
    bpy.utils.unregister_class(RendermanEnvVarSettings)
    bpy.utils.unregister_class(RendermanPreferencePath)
