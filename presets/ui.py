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

from ..rfb_utils.prefs_utils import get_pref, get_addon_prefs
from ..rfb_utils import filepath_utils

# for panel icon
from .. import rfb_icons
from . import icons as rpb_icons

import bpy
from .properties import RendermanPreset, RendermanPresetCategory, refresh_presets_libraries
from bpy.props import *

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
        if get_pref('draw_panel_icon', True):
            rfb_icon = rfb_icons.get_icon("rman_blender")
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

        current_presets_category = get_pref('presets_current_category')
        presets_root_category = get_pref('presets_root_category')

        rman_asset_lib = os.environ.get('RMAN_ASSET_LIBRARY', None)
        if presets_root_category.name == '':
            row = layout.row(align=True)          
            row.operator("renderman.init_preset_library", text="Choose Library")
            if rman_asset_lib:
                row.operator("renderman.load_preset_library_from_env_var", text="Load from RMAN_ASSET_LIBRARY")
        else:          
            layout.operator('renderman.rman_open_presets_editor', text='Preset Browser')

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
        presets_root_category = get_pref('presets_root_category')
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

class VIEW3D_MT_renderman_presets_object_context_menu(bpy.types.Menu):
    bl_label = "Preset Browser"
    bl_idname = "VIEW3D_MT_renderman_presets_object_context_menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        presets_root_category = get_pref('presets_root_category')

        rman_asset_lib = os.environ.get('RMAN_ASSET_LIBRARY', None)
        if presets_root_category.name == '':          
            layout.operator("renderman.init_preset_library", text="Choose Library")
            if rman_asset_lib:
                layout.operator("renderman.load_preset_library_from_env_var", text="Load from RMAN_ASSET_LIBRARY")
            return

        layout.operator('renderman.rman_open_presets_editor', text='Preset Browser')
        layout.separator()
        current = RendermanPresetCategory.get_current_category()
        layout.menu('PRMAN_MT_renderman_presets_categories_menu', text="Select Category")   
        if current:
            refresh_presets_libraries(current.path, current)
            selected_objects = []
            selected_light_objects = []
            if context.selected_objects:
                for obj in context.selected_objects:
                    if obj.type not in ['CAMERA', 'LIGHT', 'SPEAKER']:
                        selected_objects.append(obj)          
                    elif obj.type == 'LIGHT':
                        selected_light_objects.append(obj)

            presets_path = get_pref('presets_root_category').path
            rel_path = os.path.relpath(current.path, presets_path)                      

            asset_type = 'Environment'
            if rel_path.startswith('Materials'):
                asset_type = 'Materials'
            elif rel_path.startswith('LightRigs'):
                asset_type = 'LightRigs'

            layout.separator()  
            if selected_light_objects and asset_type == 'LightRigs':
                layout.operator("renderman.save_lightrig_to_library", text="Save LightRig", icon="LIGHT").category_path = current.path
            elif asset_type == 'Materials':
                layout.operator("renderman.save_asset_to_library", text="Save Material", icon='MATERIAL').category_path = current.path                     

            layout.separator()
            layout.label(text=current.name)
            if asset_type == 'Materials':
                for p in current.get_presets():
                    thumb = icons.get_preset_icon(p)
                    if selected_objects:
                        assign = layout.operator("renderman.load_asset_to_scene", text=p.label, icon_value=thumb.icon_id)
                        assign.preset_path = p.path
                        assign.assign = True   
                    else:             
                        layout.operator("renderman.load_asset_to_scene", text=p.label, icon_value=thumb.icon_id).preset_path = p.path
            else: 
                for p in current.get_presets():
                    thumb = icons.get_preset_icon(p)
                    layout.operator("renderman.load_asset_to_scene", text=p.label, icon_value=thumb.icon_id ).preset_path = p.path 

class PRMAN_MT_renderman_preset_ops_menu(bpy.types.Menu):
    bl_label = "Preset Ops"
    bl_idname = "PRMAN_MT_renderman_preset_ops_menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        current_presets_category = get_pref('presets_current_category')
        preset = RendermanPreset.get_from_path(current_presets_category.selected_preset)    
        if current_presets_category.parent == "Materials":
            assign = layout.operator("renderman.load_asset_to_scene", text="Import and Assign to selected", )
            assign.preset_path = preset.path
            assign.assign = True           
        layout.operator("renderman.load_asset_to_scene", text="Import", )
        layout.separator()
        layout.operator('renderman.move_preset', icon='EXPORT', text="Move to category...").preset_path = preset.path
        layout.separator()
        layout.operator("renderman.view_preset_json", text="Inspect json file")
        layout.separator()        
        layout.operator('renderman.remove_preset', icon='X', text="Delete").preset_path = preset.path                                

class RENDERMAN_UL_Presets_Categories_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=item.name)

class RENDERMAN_UL_Presets_Preset_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=item.name, icon_value=item.icon_id)        
                                
class PRMAN_OT_Renderman_Presets_Editor(bpy.types.Operator):

    bl_idname = "renderman.rman_open_presets_editor"
    bl_label = "RenderMan Preset Browser"

    def load_presets(self, context):
        self.presets.clear()
        self.presets_index = -1
        category = self.preset_categories[self.preset_categories_index]
        bpy.ops.renderman.set_current_preset_category('EXEC_DEFAULT', preset_current_path = category.path)  

        current_presets_category = RendermanPresetCategory.get_current_category()
        refresh_presets_libraries(current_presets_category.path, current_presets_category)
        for p in current_presets_category.get_presets():
            preset = self.presets.add()
            preset.label = p.label
            preset.name = p.label
            preset.path = p.path
            preset.author = p.author
            preset.version = p.version
            preset.created = p.created
            preset.resolution = p.resolution
            thumb = icons.get_preset_icon(p)
            preset.icon_id = thumb.icon_id                

    def update_selected_preset(self, context):
        if self.presets_index > -1 and self.presets_index < len(self.presets):
            preset = self.presets[self.presets_index]
            self.icon_id = preset.icon_id        
            current_presets_category = get_pref('presets_current_category')
            current_presets_category.selected_preset = preset.path

    preset_categories: CollectionProperty(type=RendermanPresetCategory,
                                      name='Categories')
    preset_categories_index: IntProperty(min=-1, default=-1, update=load_presets) 

    presets: CollectionProperty(type=RendermanPreset,
                                      name='Presets')
    presets_index: IntProperty(min=-1, default=-1, update=update_selected_preset)    

    read_only: BoolProperty(default=False)
    icon_id: IntProperty(default=-1) 

    def execute(self, context):
        self.save_prefs(context)
        return{'FINISHED'}  

    def cancel(self, context):
        self.save_prefs(context)

    def save_prefs(self, context):
        cat = self.preset_categories[self.preset_categories_index]
        current_presets_category = get_pref('presets_current_category')
        if cat.path != current_presets_category.path:
            bpy.ops.renderman.set_current_preset_category('EXEC_DEFAULT', preset_current_path = cat.path)

    def load_subcategories(self, context, sub_categories, parent='', cur_path='', level=1):
        for cat in sub_categories:
            category = self.preset_categories.add()
            category_name = ''
            for i in range(0, level):
                category_name += '    '
            category.name = '%s%s' % (category_name, cat.name)
            category.path = cat.path  
            if cur_path == category.path:
                self.preset_categories_index = len(self.preset_categories)-1             
            category.parent = parent     
            self.load_subcategories(context, cat.sub_categories, parent=parent, cur_path=cur_path, level=level+1)            


    def load_categories(self, context, cur_path=''):
        presets_root_category = get_pref('presets_root_category')
        for p in ['EnvironmentMaps', 'LightRigs', 'Materials']:
            cat = presets_root_category.sub_categories[p]
            category = self.preset_categories.add()
            category.name = cat.name
            category.path = cat.path 
            category.parent = p  
            if cur_path == category.path:
                self.preset_categories_index = len(self.preset_categories)-1
            self.load_subcategories(context, cat.sub_categories, parent=p, cur_path=cur_path)
        if cur_path == '':
            self.properties.preset_categories_index = 0            

               
    def draw(self, context):

        layout = self.layout  
        scene = context.scene 
        rm = scene.renderman   

        presets_root_category = get_pref('presets_root_category')
        rman_asset_lib = os.environ.get('RMAN_ASSET_LIBRARY', None)
        if presets_root_category.name == '':
            row = layout.row(align=True)          
            row.operator("renderman.init_preset_library", text="Choose Library")
            if rman_asset_lib:
                row.operator("renderman.load_preset_library_from_env_var", text="Load from RMAN_ASSET_LIBRARY")
            return
        else:   
            presets_root_category = get_pref('presets_root_category')
            layout.label(text=presets_root_category.name)
            row = layout.row(align=True)           
            col = row.column()  
            col.operator("renderman.init_preset_library", text="Select Another Library")
            col = row.column()
            col.operator("renderman.reload_preset_library", text="Reload Presets Library")
            col = row.column()
            col.operator("renderman.forget_preset_library", text="Forget Library")


        row = layout.row()
        col = row.column()
        cat = self.preset_categories[self.preset_categories_index]
        preset = None
        box = col.box()
        box.template_icon(self.icon_id, scale=8.0)         
        if self.presets_index > -1 and self.presets_index < len(self.presets):
            preset = self.presets[self.presets_index]

        row2 = box.row()
        col = row2.column()
        col.enabled = (cat.parent == 'LightRigs')
        #col.enabled = False
        col.operator("renderman.save_lightrig_to_library", text="", icon="LIGHT").category_path = cat.path
        col = row2.column()
        col.enabled = (cat.parent == 'Materials')
        col.operator("renderman.save_asset_to_library", text="", icon='MATERIAL').category_path = cat.path        
        col = row2.column()
        col.enabled = (cat.parent == 'EnvironmentMaps')
        op = col.operator('renderman.save_envmap_to_library', text='', icon='FILE_IMAGE')            

        col = row.column()
        box = col.box()
        if preset:
            box.label(text='Name: %s' % preset.label)
            box.label(text='Author: %s' % preset.author)
            box.label(text='Version: %s' % preset.version)
            box.label(text='Created: %s' % preset.created)
            if preset.resolution != '':
                box.label(text='Resolution: %s' % preset.resolution)
        else:
            box.label(text='')
      
        row = layout.row()
        col = row.column()    
        col.label(text='Categories')
        col.template_list("RENDERMAN_UL_Presets_Categories_List", "Preset Categories",
                            self.properties, "preset_categories", self.properties, 'preset_categories_index', rows=10)   
        row2 = col.row()
        op = row2.operator('renderman.add_new_preset_category', text='', icon='ADD')
        op.current_path = cat.path
        row2.operator('renderman.remove_preset_category', text='', icon='REMOVE')
        row2.operator("renderman.refresh_preset_category", text="", icon="FILE_REFRESH")


        col = row.column()
        col.label(text='')
        box = col.box()
        box.template_list("RENDERMAN_UL_Presets_Preset_List", "Presets",
                            self.properties, "presets", self.properties, 'presets_index', columns=4, type='GRID')   
        if preset:
            row = col.row(align=True)
            col2 = row.column()
            col2.menu('PRMAN_MT_renderman_preset_ops_menu', text="")   
            col2 = row.column()
            col2.label(text="")
      

    def invoke(self, context, event):
        presets_root_category = get_pref('presets_root_category')
        
        if presets_root_category.name != '':        
            current_path = get_pref('presets_current_category_path')
            self.load_categories(context, cur_path=current_path)
            self.load_presets(context)

        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=600)   

def rman_presets_object_menu(self, context):

    rd = context.scene.render
    if rd.engine != 'PRMAN_RENDER':
        return

    layout = self.layout 
    rman_icon = rfb_icons.get_icon("rman_blender")    
    layout.menu('VIEW3D_MT_renderman_presets_object_context_menu', text="Presets", icon_value=rman_icon.icon_id)     

classes = [
    PRMAN_MT_Renderman_Presets_Categories_Menu,
    PRMAN_MT_Renderman_Presets_Categories_SubMenu,
    PRMAN_PT_Renderman_Presets_UI_Panel,
    VIEW3D_MT_renderman_presets_object_context_menu,
    PRMAN_MT_renderman_preset_ops_menu,
    RENDERMAN_UL_Presets_Categories_List,
    RENDERMAN_UL_Presets_Preset_List,
    PRMAN_OT_Renderman_Presets_Editor
]


def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.VIEW3D_MT_add.prepend(rman_presets_object_menu) 
    bpy.types.VIEW3D_MT_object_context_menu.prepend(rman_presets_object_menu)        

def unregister():

    bpy.types.VIEW3D_MT_add.remove(rman_presets_object_menu)
    bpy.types.VIEW3D_MT_object_context_menu.remove(rman_presets_object_menu)

    for cls in classes:
        bpy.utils.unregister_class(cls)
