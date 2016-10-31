# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 Brian Savery
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

from .. import util
import bpy
from .properties import RendermanPresetGroup
from . import icons

# panel for the toolbar of node editor 
class Renderman_Presets_UI_Panel(bpy.types.Panel):
    bl_idname = "renderman_presets_ui_panel"
    bl_label = "Renderman Presets"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "TOOLS"
    bl_category = "Renderman Presets"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    # draw each group and subgroups
    def draw_preset_library(self, lib, lay, indent=0):
        row = lay.row()
        row.alert = lib.is_active()

        for i in range(indent):
            row.label('', icon='BLANK1')

        if len(lib.sub_groups) > 0:
            icon = 'DISCLOSURE_TRI_DOWN' if lib.ui_open \
                            else 'DISCLOSURE_TRI_RIGHT'

            row.prop(lib, 'ui_open', icon=icon, text='',
                                 icon_only=True, emboss=False)

            row.operator('renderman.set_active_preset_library',text=lib.name, emboss=False).lib_path = lib.path
            if lib.ui_open:
                for sub in lib.sub_groups:
                    self.draw_preset_library(sub, lay, indent+1)
        else:
            row.operator('renderman.set_active_preset_library',text=lib.name, emboss=False).lib_path = lib.path

    # draws the panel
    def draw(self, context):
        scene = context.scene
        rm = scene.renderman
        layout = self.layout

        if context.scene.render.engine != "PRMAN_RENDER":
            return

        presets_library = util.get_addon_prefs().presets_library

        if presets_library.name == '':
            layout.operator("renderman.init_preset_library", text="Set up Library",
                     ) 
        else:
            split = layout.split()

            col = split.column()
            self.draw_preset_library(presets_library, col, indent=0)
            row = col.row()
            #row.operator("renderman.init_preset_library", text="Add Folder",
            #         ) 
            #row.operator("renderman.init_preset_library", text="Remove Folder",
            #         ) 
            
            col = split.column()
            active = RendermanPresetGroup.get_active_library()
            if active:
                for preset in active.get_presets():
                    if preset.thumbnail in icons.asset_previews:
                        col.label(preset.name)
                        col.template_icon_view(preset, 'thumbnail')
                        col.operator("renderman.load_asset_to_scene", text="Load to Scene").preset_path = preset.path

                col.operator("renderman.save_asset_to_library", text="Save to Scene").lib_path = active.path



def register():
    try:
        bpy.utils.register_class(Renderman_Presets_UI_Panel)
    except:
        pass #allready registered

def unregister():
    bpy.utils.register_class(Renderman_Presets_UI_Panel)