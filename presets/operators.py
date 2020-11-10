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
from ..rfb_utils.shadergraph_utils import is_renderman_nodetree
import os
from distutils.dir_util import copy_tree
import shutil
import bpy
from bpy.props import StringProperty, EnumProperty, BoolProperty
from .properties import RendermanPresetCategory, RendermanPreset, refresh_presets_libraries
from . import icons
import json
from bpy.types import NodeTree
import getpass

def get_library_name(jsonfile):
    if not os.path.exists(jsonfile):
        return 'Library'
    data = json.load(open(jsonfile))
    return data["RenderManAssetLibrary"]["name"]

class PRMAN_OT_reload_preset_library(bpy.types.Operator):
    bl_idname = "renderman.reload_preset_library"
    bl_label = "Reload RenderMan Preset Library"
    bl_description = "Reload Presets Library."

    def execute(self, context):
        presets_root_category = get_pref('presets_root_category')
        presets_current_category = get_pref('presets_current_category')
        rman_asset_lib = os.environ.get('RMAN_ASSET_LIBRARY', None)
        if rman_asset_lib:
            # check if RMAN_ASSET_LIBRARY is diffrent from our current library
            if rman_asset_lib != presets_root_category.path:
                json_file = os.path.join(rman_asset_lib, 'library.json')
                if os.path.exists(json_file):
                    presets_library_name = get_library_name(json_file)
                    presets_root_category.name = presets_library_name
                    presets_root_category.path = rman_asset_lib

        refresh_presets_libraries(presets_root_category.path, presets_root_category)
        presets_current_category = presets_root_category.sub_categories['LightRigs']
        get_addon_prefs().presets_current_category_path = presets_current_category.path     
        bpy.ops.wm.save_userpref()
        return {'FINISHED'}


# if the library isn't present copy it from rmantree to the path in addon prefs
class PRMAN_OT_init_preset_library(bpy.types.Operator):
    bl_idname = "renderman.init_preset_library"
    bl_label = "Init RenderMan Preset Library"
    bl_description = "Choose a preset browser library. If not found, copies the factory library from RMANTREE to the path chosen."

    directory: bpy.props.StringProperty(subtype='FILE_PATH')

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):

        json_file = os.path.join(self.directory, 'library.json')
        presets_root_category = get_pref('presets_root_category')
        if os.path.exists(json_file):
            presets_library_name = get_library_name(json_file)
            presets_root_category.name = presets_library_name
            presets_root_category.path = self.directory
        
        elif os.access(self.directory, os.W_OK):
            rmantree_lib_path = os.path.join(filepath_utils.guess_rmantree(), 'lib', 'RenderManAssetLibrary')
            copy_tree(rmantree_lib_path, self.directory)
            presets_root_category.name = 'Library'
            presets_root_category.path = self.directory
        else:
            raise Exception("No preset library found or directory chosen is not writable.")
            return {'FINISHED'}

        bpy.ops.renderman.reload_preset_library()        

        return {'FINISHED'}

class PRMAN_OT_load_preset_library_from_env_var(bpy.types.Operator):
    bl_idname = "renderman.load_preset_library_from_env_var"
    bl_label = "Load RenderMan Preset Library from RMAN_ASSET_LIBRARY"
    bl_description = "Load a RenderMan Preset Library from RMAN_ASSET_LIBRARY "

    def execute(self, context):
        rman_asset_lib = os.environ.get('RMAN_ASSET_LIBRARY', None)
        if not rman_asset_lib:
            raise Exception("RMAN_ASSET_LIBRARY not set.")
            return {'FINISHED'}

        json_file = os.path.join(rman_asset_lib, 'library.json')
        presets_root_category = get_pref('presets_root_category')
        if os.path.exists(json_file):
            presets_library_name = get_library_name(json_file)
            presets_root_category.name = presets_library_name
            presets_root_category.path = rman_asset_lib

        else:
            raise Exception("Could not find a library.json file in RMAN_ASSET_LIBRARY.")
            return {'FINISHED'}
       
        bpy.ops.renderman.reload_preset_library()                  

        return {'FINISHED'}        

class PRMAN_OT_refresh_preset_category(bpy.types.Operator):
    bl_idname = "renderman.refresh_preset_category"
    bl_label = "Refresh Category"
    bl_description = "Refresh current preset category"

    def invoke(self, context, event):
        current_category = RendermanPresetCategory.get_current_category()
        refresh_presets_libraries(current_category.path, current_category)
        return {'FINISHED'}

class PRMAN_OT_load_asset_to_scene(bpy.types.Operator):
    bl_idname = "renderman.load_asset_to_scene"
    bl_label = "Load Asset to Scene"
    bl_description = "Load the Asset to scene"

    preset_path: StringProperty(default='')
    assign: BoolProperty(default=False)

    def invoke(self, context, event):
        preset = RendermanPreset.get_from_path(self.properties.preset_path)
        from . import rmanAssetsBlender
        mat = rmanAssetsBlender.importAsset(preset.json_path)
        if self.properties.assign and mat and type(mat) == bpy.types.Material:
            for ob in context.selected_objects:
                if ob.type == 'EMPTY':
                    ob.renderman.rman_material_override = mat
                    ob.update_tag(refresh={'OBJECT'})
                else:
                    ob.active_material = mat

        return {'FINISHED'}

# save the current material to the library
class PRMAN_OT_save_asset_to_lib(bpy.types.Operator):
    bl_idname = "renderman.save_asset_to_library"
    bl_label = "Save Asset to Library"
    bl_description = "Save Asset to Library"

    category_path: StringProperty(default='')
    material_label: StringProperty(name='Asset Name', default='')
    material_author: StringProperty(name='Author', default='')
    material_category: StringProperty(name='Category', default='')
    material_version: StringProperty(name='Version', default='1.0')

    @classmethod
    def poll(cls, context):
        category_path = get_pref('presets_current_category_path')
        root_presets_path = get_pref('presets_root_category').path
        path = os.path.relpath(category_path, root_presets_path)
        if not path.startswith('Materials'):
            return False

        ob = context.active_object
        if ob is None:
            return False
        if not hasattr(ob, 'active_material'):
            return False
        mat = ob.active_material
        return is_renderman_nodetree(mat)

    def get_current_material(self, context):
        ob = context.active_object
        return ob.active_material

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'material_label')
        col.prop(self, 'material_author')
        col.prop(self, 'material_category')
        col.prop(self, 'material_version')

    def execute(self, context):
        presets_path = get_pref('presets_root_category').path
        path = os.path.relpath(self.properties.category_path, presets_path)
        category = RendermanPresetCategory.get_from_path(self.properties.category_path)
        ob = context.active_object
        mat = ob.active_material
        nt = mat.node_tree
        if nt:
            if not path.endswith(self.material_category):
                path = os.path.join(path, self.material_category)
            assetPath = os.path.join(presets_path, path)
            from . import rmanAssetsBlender
            rmanAssetsBlender.exportAsset(nt, 'nodeGraph', 
                                          {'label': self.material_label,
                                           'author': self.material_author,
                                           'version': self.material_version},
                                           path,
                                           assetPath
                                           )
        refresh_presets_libraries(category.path, category)
        bpy.ops.wm.save_userpref()
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        mat = self.get_current_material(context)        
        self.material_label = mat.name
        self.material_author = getpass.getuser()
        self.material_version = '1.0'
        presets_path = get_pref('presets_root_category').path
        current_category_path = get_pref('presets_current_category_path')
        path = os.path.relpath(current_category_path, presets_path)        
        self.material_category = path.split('/')[-1]     

        return wm.invoke_props_dialog(self) 


class PRMAN_OT_set_current_preset_category(bpy.types.Operator):
    bl_idname = "renderman.set_current_preset_category"
    bl_label = "Set current RenderMan Preset category"
    bl_description = "Sets the clicked category to be the current category"

    preset_current_path: StringProperty(default='')

    def execute(self, context):
        preset_current_path = self.properties.preset_current_path  
        if preset_current_path:
            get_addon_prefs().presets_current_category_path = preset_current_path
            bpy.ops.wm.save_userpref()
        return {'FINISHED'}  

class PRMAN_OT_add_new_preset_category(bpy.types.Operator):
    bl_idname = "renderman.add_new_preset_category"
    bl_label = "Add New RenderMan Preset Category"
    bl_description = "Adds a new preset category"

    new_name: StringProperty(default="")
    
    def execute(self, context):
        current = RendermanPresetCategory.get_current_category()
        current_path = current.path
        new_folder = self.properties.new_name
        if current_path and new_folder:
            path = os.path.join(current_path, new_folder)
            os.mkdir(path)
            sub_category = current.sub_categories.add()
            sub_category.name = new_folder
            sub_category.path = path

            get_addon_prefs().presets_current_category_path = path
        bpy.ops.wm.save_userpref()
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        row = self.layout
        row.prop(self, "new_name", text="New Folder Name:")      


class PRMAN_OT_remove_preset_category(bpy.types.Operator):
    bl_idname = "renderman.remove_preset_category"
    bl_label = "Remove Current Preset Category"
    bl_description = "Remove preset category"

    @classmethod
    def poll(cls, context):
        current = RendermanPresetCategory.get_current_category()
        if current.name in ['EnvironmentMaps', 'Materials', 'LightRigs']:
            return False
        return True    

    def execute(self, context):
        current = RendermanPresetCategory.get_current_category()
        current_path = current.path
        if current_path:
            parent_path = os.path.split(current.path)[0]
            parent = RendermanPresetCategory.get_from_path(parent_path)
            get_addon_prefs().presets_current_category_path = parent_path
            
            shutil.rmtree(current.path)

            refresh_presets_libraries(parent.path, parent)
        bpy.ops.wm.save_userpref()  
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

class PRMAN_OT_remove_preset(bpy.types.Operator):
    bl_idname = "renderman.remove_preset"
    bl_label = "Remove RenderMan Preset"
    bl_description = "Remove a Preset"

    preset_path: StringProperty()

    def execute(self, context):
        preset_path = self.properties.preset_path
        active = RendermanPreset.get_from_path(preset_path)
        if active:
            parent_path = os.path.split(preset_path)[0]
            parent = RendermanPresetCategory.get_from_path(parent_path)
            
            try:
                shutil.rmtree(active.path)
            except:
                pass

            refresh_presets_libraries(parent.path, parent)
        bpy.ops.wm.save_userpref()   
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

class PRMAN_OT_move_preset(bpy.types.Operator):
    bl_idname = "renderman.move_preset"
    bl_label = "Move RenderMan Preset"
    bl_description = "Move a Preset"

    def get_libraries(self, context):
        def get_libs(parent_lib):
            enum = [(parent_lib.path, parent_lib.name, '')]
            for lib in parent_lib.sub_groups:
                enum.extend(get_libs(lib))
            return enum
        return get_libs(get_pref('presets_library'))

    preset_path: StringProperty(default='')
    new_library: EnumProperty(items=get_libraries, description='New Library', name="New Library")

    def execute(self, context):
        new_parent_path = self.properties.new_library
        active = RendermanPreset.get_from_path(self.properties.preset_path)
        if active:
            old_parent_path = os.path.split(active.path)[0]
            old_parent = RendermanPresetCategory.get_from_path(old_parent_path)
            new_parent = RendermanPresetCategory.get_from_path(new_parent_path)

            shutil.move(active.path, new_parent_path)
            
            refresh_presets_libraries(old_parent.path, old_parent)
            refresh_presets_libraries(new_parent.path, new_parent)
        bpy.ops.wm.save_userpref()
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        row = self.layout
        row.prop(self, "new_library", text="New Library")

class PRMAN_OT_move_preset_category(bpy.types.Operator):
    bl_idname = "renderman.move_preset_category"
    bl_label = "Move RenderMan Preset Category"
    bl_description = "Move a Preset category"

    @classmethod
    def poll(cls, context):
        current = RendermanPresetCategory.get_current_category()
        if current.name in ['EnvironmentMaps', 'Materials', 'LightRigs']:
            return False
        return True    

    def get_all_categories(self, context):
        current_category = RendermanPresetCategory.get_current_category()
        root_category = get_pref('presets_root_category')
        relpath = os.path.relpath(current_category.path, root_category.path)
        asset_type = relpath.split(os.sep)[0]

        def get_sub_categories(parent_catgegory):
            enum = []
            # don't include self
            if (current_category.name != parent_catgegory.name) and (current_category.path != os.path.join(parent_catgegory.path, current_category.name)):
                enum = [(parent_catgegory.path, parent_catgegory.name, '')]
            for category in parent_catgegory.sub_categories:
                enum.extend(get_sub_categories(category))
            return enum

        return get_sub_categories(root_category.sub_categories[asset_type])

    category_path: StringProperty(default='')
    new_category: EnumProperty(items=get_all_categories, description='New Category', name="New Category")

    def execute(self, context):
        new_parent_path = self.properties.new_category
        active = RendermanPresetCategory.get_from_path(self.properties.category_path)
        if active:
            old_parent_path = os.path.split(active.path)[0]
            old_parent = RendermanPresetCategory.get_from_path(old_parent_path)
            new_parent = RendermanPresetCategory.get_from_path(new_parent_path)

            shutil.move(active.path, new_parent_path)
            
            refresh_presets_libraries(old_parent.path, old_parent)
            refresh_presets_libraries(new_parent.path, new_parent)
        bpy.ops.wm.save_userpref()
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        row = self.layout
        row.prop(self, "new_category", text="New Parent")        

classes = [
    PRMAN_OT_reload_preset_library,
    PRMAN_OT_init_preset_library,
    PRMAN_OT_load_preset_library_from_env_var,
    PRMAN_OT_refresh_preset_category,
    PRMAN_OT_set_current_preset_category,
    PRMAN_OT_load_asset_to_scene,
    PRMAN_OT_save_asset_to_lib,
    PRMAN_OT_add_new_preset_category,
    PRMAN_OT_remove_preset_category,
    PRMAN_OT_move_preset_category,
    PRMAN_OT_move_preset,
    PRMAN_OT_remove_preset
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
