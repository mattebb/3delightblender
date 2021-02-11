# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 - 2021 Pixar
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
from .properties import RendermanPreset, RendermanPresetCategory
from bpy.props import *

# for previews of assets
from . import icons
from . import rmanAssetsBlender as rab
from rman_utils.rman_assets import core as ra

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

        layout.operator('renderman.rman_open_presets_editor', text='Preset Browser')

class PRMAN_MT_Renderman_Presets_Categories_Menu(bpy.types.Menu):
    bl_idname = "PRMAN_MT_renderman_presets_categories_menu"
    bl_label = "RenderMan Presets Categories Menu"

    path: StringProperty(default="")

    def draw(self, context):
        hostPrefs = rab.get_host_prefs()
        for cat in hostPrefs.getAllCategories(asDict=False):
            tokens = cat.split('/')
            category_path = os.path.join(hostPrefs.getSelectedLibrary(), cat)
            level = len(tokens)
            category_name = ''
            for i in range(0, level-1):
                category_name += '    '
            category_name = '%s%s' % (category_name, tokens[-1])           
            self.layout.operator('renderman.set_current_preset_category',text=category_name).preset_current_path = category_path
                        
class VIEW3D_MT_renderman_presets_object_context_menu(bpy.types.Menu):
    bl_label = "Preset Browser"
    bl_idname = "VIEW3D_MT_renderman_presets_object_context_menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout

        layout.operator('renderman.rman_open_presets_editor', text='Preset Browser')
        layout.separator()
        layout.menu('PRMAN_MT_renderman_presets_categories_menu', text="Select Category")   

        hostPrefs = rab.get_host_prefs()
        libInfo = hostPrefs.cfg.getCurrentLibraryInfos()        
        selected_objects = []
        selected_light_objects = []
        if context.selected_objects:
            for obj in context.selected_objects:
                if obj.type not in ['CAMERA', 'LIGHT', 'SPEAKER']:
                    selected_objects.append(obj)          
                elif obj.type == 'LIGHT':
                    selected_light_objects.append(obj)

        current_category_path = hostPrefs.getSelectedCategory()
        if current_category_path == '':
            return 
        rel_path = os.path.relpath(current_category_path, hostPrefs.getSelectedLibrary())                      

        asset_type = 'Environment'
        if rel_path.startswith('Materials'):
            asset_type = 'Materials'
        elif rel_path.startswith('LightRigs'):
            asset_type = 'LightRigs'

        layout.separator()  
        if libInfo.isEditable():        
            if selected_light_objects and asset_type == 'LightRigs':
                layout.operator("renderman.save_lightrig_to_library", text="Save LightRig", icon="LIGHT").category_path = current_category_path
            elif asset_type == 'Materials':
                layout.operator("renderman.save_asset_to_library", text="Save Material", icon='MATERIAL').category_path = current_category_path                   

        layout.separator()
        category_name = current_category_path.split('/')[-1]
        layout.label(text=category_name)
        if asset_type == 'Materials':
            for asset in hostPrefs.getAssetList(current_category_path):
                ass = ra.RmanAsset()
                path = os.path.join(hostPrefs.getSelectedLibrary(), asset)
                json_path = os.path.join(path, 'asset.json')
                ass.load(json_path)
                label = ass.label()       
                thumb = icons.get_preset_icon(path)
                if selected_objects:
                    assign = layout.operator("renderman.load_asset_to_scene", text=label, icon_value=thumb.icon_id)
                    assign.preset_path = json_path
                    assign.assign = True   
                else:             
                    layout.operator("renderman.load_asset_to_scene", text=label, icon_value=thumb.icon_id).preset_path = json_path                      
        else: 
            for asset in hostPrefs.getAssetList(current_category_path):
                ass = ra.RmanAsset()
                path = os.path.join(hostPrefs.getSelectedLibrary(), asset)
                json_path = os.path.join(path, 'asset.json')
                ass.load(json_path)
                label = ass.label()       
                thumb = icons.get_preset_icon(path)       
                layout.operator("renderman.load_asset_to_scene", text=label, icon_value=thumb.icon_id).preset_path = json_path  

class PRMAN_MT_renderman_preset_ops_menu(bpy.types.Menu):
    bl_label = "Preset Ops"
    bl_idname = "PRMAN_MT_renderman_preset_ops_menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        hostPrefs = rab.get_host_prefs()
        current_preset = hostPrefs.getSelectedPreset()
        ass = ra.RmanAsset()
        json_path = os.path.join(current_preset, 'asset.json')
        ass.load(json_path)  
        rel_path = os.path.relpath(hostPrefs.getSelectedCategory(), hostPrefs.getSelectedLibrary())  

        op = getattr(context, 'op_ptr')
        if rel_path.startswith("Materials"):
            assign = layout.operator("renderman.load_asset_to_scene", text="Import and Assign to selected", )
            assign.preset_path = current_preset
            assign.assign = True           
        layout.context_pointer_set("op_ptr", op)
        layout.operator("renderman.load_asset_to_scene", text="Import", )
        layout.separator()
        layout.operator('renderman.move_preset', icon='EXPORT', text="Move to category...").preset_path = current_preset
        layout.separator()
        layout.operator("renderman.view_preset_json", text="Inspect json file").preset_path = current_preset
        layout.separator()        
        layout.operator('renderman.remove_preset', icon='X', text="Delete").preset_path = current_preset                

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
        hostPrefs = rab.get_host_prefs()

        self.presets.clear()
        self.presets_index = -1
        category = self.preset_categories[self.preset_categories_index]
        libInfo = hostPrefs.cfg.getCurrentLibraryInfos()
        self.library_name = libInfo.getData('name')
        self.is_editable = libInfo.isEditable()

        hostPrefs.setSelectedCategory(category.path)
        hostPrefs.saveAllPrefs()
        for asset in hostPrefs.getAssetList(category.path):
            ass = ra.RmanAsset()
            ass.load(os.path.join(hostPrefs.getSelectedLibrary(), asset, 'asset.json'))

            preset = self.presets.add()
            preset.label = ass.label()
            preset.name = ass.label()  
            preset.path =  os.path.join(hostPrefs.getSelectedLibrary(), asset)     
            preset.author = ass.getMetadata('author')
            preset.version = str(ass.getMetadata('version'))
            preset.created = ass.getMetadata('created')
            thumb = icons.get_preset_icon(preset.path)
            preset.icon_id = thumb.icon_id                       

    def update_selected_preset(self, context):
        if self.presets_index > -1 and self.presets_index < len(self.presets):
            preset = self.presets[self.presets_index]
            self.icon_id = preset.icon_id        
            hostPrefs = rab.get_host_prefs()
            hostPrefs.setSelectedPreset(preset.path)
            hostPrefs.saveAllPrefs()

    preset_categories: CollectionProperty(type=RendermanPresetCategory,
                                      name='Categories')
    preset_categories_index: IntProperty(min=-1, default=-1, update=load_presets) 

    presets: CollectionProperty(type=RendermanPreset,
                                      name='Presets')
    presets_index: IntProperty(min=-1, default=-1, update=update_selected_preset)    

    icon_id: IntProperty(default=-1) 
    library_name: StringProperty(default="")
    is_editable: BoolProperty(default=False)

    def execute(self, context):
        self.save_prefs(context)
        return{'FINISHED'}  

    def cancel(self, context):
        self.save_prefs(context)

    def save_prefs(self, context):
        rab.get_host_prefs().saveAllPrefs()

    def load_categories(self, context):
        hostPrefs = rab.get_host_prefs()
        current_category_path = hostPrefs.getSelectedCategory()
        self.preset_categories.clear()
        for cat in hostPrefs.getAllCategories(asDict=False):
            category = self.preset_categories.add()
            tokens = cat.split('/')
            level = len(tokens)
            category_name = ''
            for i in range(0, level-1):
                category_name += '    '            
            category.name = '%s%s' % (category_name, tokens[-1])
            category.path = os.path.join(hostPrefs.getSelectedLibrary(), cat)
            cat.rel_path = cat
            if current_category_path == category.path:
                self.preset_categories_index = len(self.preset_categories)-1

    dummy_index: IntProperty(min=-1, default=-1, update=load_categories)              
               
    def draw(self, context):

        layout = self.layout  
        scene = context.scene 
        rm = scene.renderman   

        hostPrefs = rab.get_host_prefs()
        lock = 'LOCKED'
        if self.is_editable:
            lock = 'UNLOCKED'
        layout.label(text=self.library_name, icon=lock)
        row = layout.row(align=True)           
        col = row.column()  
        col.context_pointer_set('op_ptr', self) 
        col.operator("renderman.init_preset_library", text="Add Another Library")
        col = row.column()
        col.context_pointer_set('op_ptr', self) 
        col.operator("renderman.select_preset_library", text="Select Library")
        col = row.column()
        col.context_pointer_set('op_ptr', self) 
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
        rel_path = os.path.relpath(cat.path, hostPrefs.getSelectedLibrary())        
        col.enabled = (rel_path.startswith('LightRigs')) and self.is_editable
        col.operator("renderman.save_lightrig_to_library", text="", icon="LIGHT").category_path = cat.path
        col = row2.column()
        col.enabled = (rel_path.startswith('Materials')) and self.is_editable
        col.operator("renderman.save_asset_to_library", text="", icon='MATERIAL').category_path = cat.path        
        col = row2.column()
        col.enabled = (rel_path.startswith('EnvironmentMaps')) and self.is_editable
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
        row2.context_pointer_set('op_ptr', self) 
        row2.enabled = self.is_editable
        op = row2.operator('renderman.add_new_preset_category', text='', icon='ADD')
        op.current_path = cat.path
        row2.operator_context = 'EXEC_DEFAULT'
        row2.operator('renderman.remove_preset_category', text='', icon='REMOVE')

        col = row.column()
        col.label(text='')
        box = col.box()
        box.template_list("RENDERMAN_UL_Presets_Preset_List", "Presets",
                            self.properties, "presets", self.properties, 'presets_index', columns=4, type='GRID')   
        if preset:
            row = col.row(align=True)
            col2 = row.column()
            col2.context_pointer_set('op_ptr', self) 
            col2.menu('PRMAN_MT_renderman_preset_ops_menu', text="")   
            col2 = row.column()
            col2.label(text="")
     

    def invoke(self, context, event):
        self.load_categories(context)
             
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
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass   
