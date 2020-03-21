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

from ..rman_utils import prefs_utils

# for panel icon
from .. icons import icons as ui_icons

import bpy
from .properties import RendermanPreset, RendermanPresetCategory, refresh_presets_libraries

# for previews of assets
from . import icons

from bpy.props import StringProperty, IntProperty
import os


# panel for the toolbar of node editor
class PRMAN_PT_Renderman_Presets_UI_Panel(bpy.types.Panel):
    bl_idname = "PRMAN_PT_renderman_presets_ui_panel"
    bl_label = "RenderMan Presets"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Renderman"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw_header(self, context):
        if prefs_utils.get_addon_prefs().draw_panel_icon:
            rfb_icons = ui_icons.load_icons()
            rfb_icon = rfb_icons.get("rman_blender.png")
            self.layout.label(text="", icon_value=rfb_icon.icon_id)
        else:
            pass

    # draws the panel
    def draw(self, context):
        scene = context.scene
        rm = scene.renderman
        layout = self.layout

        if context.scene.render.engine != "PRMAN_RENDER":
            return

        current_presets_category = prefs_utils.get_addon_prefs().presets_current_category
        presets_root_category = prefs_utils.get_addon_prefs().presets_root_category

        rman_asset_lib = os.environ.get('RMAN_ASSET_LIBRARY', None)
        if presets_root_category.name == '':
            row = layout.row(align=True)          
            row.operator("renderman.init_preset_library", text="Choose Library")
            if rman_asset_lib:
                row.operator("renderman.load_preset_library_from_env_var", text="Load from RMAN_ASSET_LIBRARY")
        else:                
            layout = self.layout

            row = layout.row(align=True)
            row.operator("renderman.init_preset_library", text="Select Another Library")
            row.operator("renderman.reload_preset_library", text="Reload Presets Library")
            row = layout.row(align=True)
            row.menu('PRMAN_MT_renderman_presets_categories_menu', text="Select Category")
            row.operator("renderman.refresh_preset_category", text="", icon="FILE_REFRESH")
            current = RendermanPresetCategory.get_current_category()

            if current:
                row = layout.row(align=True)
                row.prop(current, 'name', text='Category')
                row.operator('renderman.add_new_preset_category', text='', icon='ADD')
                row.operator('renderman.move_preset_category', text='', icon='EXPORT').category_path = current.path
                row.operator('renderman.remove_preset_category', text='', icon='X')
                selected_preset = RendermanPreset.get_from_path(current.selected_preset)      

                if selected_preset:
                    row = layout.row()
                    row.label(text="Selected Preset:")
                    row.prop(current, 'selected_preset', text='')

                    # This doesn't seem to always work?
                    if prefs_utils.get_addon_prefs().presets_show_large_icons:
                        layout.template_icon_view(current, "selected_preset", show_labels=True)

                    # row of controls for preset
                    row = layout.row(align=True)
                    row.prop(selected_preset, 'label', text="")
                    row.operator('renderman.move_preset', icon='EXPORT', text="").preset_path = selected_preset.path
                    row.operator('renderman.remove_preset', icon='X', text="").preset_path = selected_preset.path

                    row = layout.row()
                    box = row.box()
                    box.label(text='Name: %s' % selected_preset.label)
                    box.label(text='Author: %s' % selected_preset.author)
                    box.label(text='Version: %s' % selected_preset.version)
                    box.label(text='Created: %s' % selected_preset.created)
                    if selected_preset.resolution != '':
                        box.label(text='Resolution: %s' % selected_preset.resolution)

                    # add to scene
                    row = layout.row(align=True)
                    row.operator("renderman.load_asset_to_scene", text="Load to Scene", ).preset_path = selected_preset.path
                    assign = row.operator("renderman.load_asset_to_scene", text="Assign to selected", )
                    assign.preset_path = selected_preset.path
                    assign.assign = True
                else:
                    row = layout.row()
                    row.label(text="NO PRESETS", icon='ERROR')                

                # get from scene
                layout.separator()
                layout.operator("renderman.save_asset_to_library", text="Save Material to Library", icon='MATERIAL').category_path = current.path


class PRMAN_MT_Renderman_Presets_Categories_SubMenu(bpy.types.Menu):
    bl_idname = "PRMAN_MT_renderman_presets_categories_submenu"
    bl_label = "RenderMan Presets Categories SubMenu"

    path: StringProperty(default="")

    def draw(self, context):

        category = context.presets_current_category
        prefix = "*" if category.is_current_category() else ''
        self.layout.operator('renderman.set_current_preset_category',text=prefix + category.name).preset_current_path = category.path
        if len(category.sub_categories) > 0:
            for key in sorted(category.sub_categories.keys(), key=lambda k: k.lower()):
                sub = category.sub_categories[key]
                self.layout.context_pointer_set('presets_current_category', sub)
                prefix = "* " if sub.is_current_category() else ''
                if len(sub.sub_categories):
                    self.layout.menu('PRMAN_MT_renderman_presets_categories_submenu', text=prefix + sub.name)
                else:
                    prefix = "* " if sub.is_current_category() else ''
                    self.layout.operator('renderman.set_current_preset_category',text=prefix + sub.name).preset_current_path = sub.path

class PRMAN_MT_Renderman_Presets_Categories_Menu(bpy.types.Menu):
    bl_idname = "PRMAN_MT_renderman_presets_categories_menu"
    bl_label = "RenderMan Presets Categories Menu"

    path: StringProperty(default="")

    def draw(self, context):
        presets_root_category = prefs_utils.get_addon_prefs().presets_root_category
        presets_envmaps_category = presets_root_category.sub_categories['EnvironmentMaps']
        presets_lightrigs_category = presets_root_category.sub_categories['LightRigs']
        presets_materials_category = presets_root_category.sub_categories['Materials']
        self.layout.label(text=presets_root_category.name)

        prefix = "*" if presets_envmaps_category.is_current_category() else ''
        if len(presets_envmaps_category.sub_categories) > 0:
            self.layout.context_pointer_set('presets_current_category', presets_envmaps_category)
            self.layout.menu('PRMAN_MT_renderman_presets_categories_submenu', text=prefix + presets_envmaps_category.name)
        else:
            self.layout.operator('renderman.set_current_preset_category',text=prefix + presets_envmaps_category.name).preset_current_path = presets_envmaps_category.path

        prefix = "*" if presets_lightrigs_category.is_current_category() else ''
        if len(presets_lightrigs_category.sub_categories) > 0:
            self.layout.context_pointer_set('presets_current_category', presets_lightrigs_category)
            self.layout.menu('PRMAN_MT_renderman_presets_categories_submenu', text=prefix + presets_lightrigs_category.name)
        else:
            self.layout.operator('renderman.set_current_preset_category',text=prefix + presets_lightrigs_category.name).preset_current_path = presets_lightrigs_category.path

        prefix = "*" if presets_materials_category.is_current_category() else ''
        if len(presets_materials_category.sub_categories) > 0:
            self.layout.context_pointer_set('presets_current_category', presets_materials_category)
            self.layout.menu('PRMAN_MT_renderman_presets_categories_submenu', text=prefix + presets_materials_category.name)
        else:
            self.layout.operator('renderman.set_current_preset_category',text=prefix + presets_materials_category.name).preset_current_path = presets_materials_category.path

classes = [
    PRMAN_MT_Renderman_Presets_Categories_Menu,
    PRMAN_MT_Renderman_Presets_Categories_SubMenu,
    PRMAN_PT_Renderman_Presets_UI_Panel
]


def register():

    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)
