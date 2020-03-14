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
from .icons.icons import load_icons

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

class RendermanPreferences(AddonPreferences):
    bl_idname = __package__

    # find the renderman options installed
    def find_installed_rendermans(self, context):
        options = [('NEWEST', 'Newest Version Installed',
                    'Automatically updates when new version installed. NB: If an RMANTREE environment variable is set, this will always take precedence.')]
        for vers, path in filepath_utils.get_installed_rendermans():
            options.append((path, vers, path))
        return options

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

    draw_ipr_text: BoolProperty(
        name="Draw IPR Text",
        description="Draw notice on View3D when IPR is active",
        default=True)

    draw_panel_icon: BoolProperty(
        name="Draw Panel Icon",
        description="Draw an icon on RenderMan Panels",
        default=True)

    path_display_driver_image: StringProperty(
        name="Beauty Image Path",
        description="Path for the beauty image",
        subtype='FILE_PATH',
        default=os.path.join('{OUT}', 'images', '{scene}.{layer}.{F4}.{ext}'))

    path_aov_image: StringProperty(
        name="AOV Image Path",
        description="Path for the rendered AOV images",
        subtype='FILE_PATH',
        default=os.path.join('{OUT}', 'images', '{scene}.{layer}.{aov}.{F4}.{ext}'))

    path_bake_illum_ptc: StringProperty(
        name="Bake 3D Illumination Path",
        description="Path for bake illumation point cloud files",
        subtype='FILE_PATH',
        default=os.path.join('{OUT}', 'bake', '{scene}.{layer}.{aov}.{F4}.{ext}'))

    path_bake_illum_img: StringProperty(
        name="Bake 2D Illumination Path",
        description="Path for bake illumation point cloud files",
        subtype='FILE_PATH',
        default=os.path.join('{OUT}', 'bake', '{scene}.{layer}.{aov}.{F4}.{ext}'))        

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
        description='''Log level verbosity. Advanced: Setting the RFB_LOG_LEVEL environment variable will override this preference. Requires a restart.
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

    rman_logging_file: StringProperty(
        name='Logging File',
        description='''A file to write logging to. This will always write at DEBUG level. Setting the RFB_LOG_FILE environment variable will override this preference. Requires a restart.''',
        default = '',
        subtype='FILE_PATH'
    )

    rman_do_preview_renders: BoolProperty(
        name="Render Previews",
        description="Enable rendering of material previews. This is considered a WIP.",
        default=False)

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
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False        
        layout = self.layout

        icons = load_icons()
        rman_r_icon = icons.get("rfb_panel")

        row = layout.row()
        row.use_property_split = False
        col = row.column()
        col.prop(self, 'rmantree_method')
        if self.rmantree_method == 'DETECT':
            col.prop(self, 'rmantree_choice')
            if self.rmantree_choice == 'NEWEST':
                col.label(text="RMANTREE: %s " % filepath_utils.guess_rmantree())
        elif self.rmantree_method == 'ENV':
            col.label(text="RMANTREE: %s" % filepath_utils.rmantree_from_env())
        else:
            col.prop(self, "path_rmantree")
        if filepath_utils.guess_rmantree() is None:
            row = layout.row()
            row.alert = True
            row.label(text='Error in RMANTREE. Reload addon to reset.', icon='ERROR')

        # Workspace
        env = self.env_vars
        row = layout.row()
        row.label(text='Workspace', icon_value=rman_r_icon.icon_id)
        row = layout.row()
        col = row.column()
        col.prop(env, "out")
        col.prop(self, 'path_display_driver_image')
        col.prop(self, 'path_aov_image')
        col.prop(self, 'path_bake_illum_ptc')
        col.prop(self, 'path_bake_illum_img')
        col.prop(self, 'path_fallback_textures_path')

        # UI Prefs
        row = layout.row()
        row.label(text='UI', icon_value=rman_r_icon.icon_id)
        row = layout.row()
        col = row.column()
        layout.prop(self, 'rman_do_preview_renders')     
        layout.prop(self, 'draw_ipr_text')
        layout.prop(self, 'draw_panel_icon')

        # Preset Browser
        row = layout.row()
        row.label(text='Preset Browser', icon_value=rman_r_icon.icon_id)
        row = layout.row()
        col = row.column()
        layout.prop(self.presets_library, 'path')

        # Logging
        row = layout.row()
        row.label(text='Logging', icon_value=rman_r_icon.icon_id)
        row = layout.row()
        col = row.column()
        col.prop(self, 'rman_logging_level')
        col.prop(self, 'rman_logging_file')



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
