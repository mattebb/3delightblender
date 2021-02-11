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

from ..rfb_utils import filepath_utils
from ..rfb_utils import object_utils
from ..rfb_utils.shadergraph_utils import is_renderman_nodetree
import os
from distutils.dir_util import copy_tree
import bpy
from bpy.props import StringProperty, EnumProperty, BoolProperty
from . import rmanAssetsBlender as rab
from rman_utils.rman_assets import lib as ral
from rman_utils.filepath import FilePath
import getpass

# if the library isn't present copy it from rmantree to the path in addon prefs
class PRMAN_OT_init_preset_library(bpy.types.Operator):
    bl_idname = "renderman.init_preset_library"
    bl_label = "Init RenderMan Preset Library"
    bl_description = "Choose a preset browser library. If not found, copies the factory library from RMANTREE to the path chosen."

    directory: bpy.props.StringProperty(subtype='FILE_PATH')

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        self.op = getattr(context, 'op_ptr', None) 
        return {'RUNNING_MODAL'}

    def execute(self, context):

        json_file = os.path.join(self.directory, 'library.json')
        hostPrefs = rab.get_host_prefs()

        if os.path.exists(json_file):
            hostPrefs.cfg.addLibraryToLibraryList(self.directory)
            
        
        elif os.access(self.directory, os.W_OK):
            rmantree_lib_path = os.path.join(filepath_utils.guess_rmantree(), 'lib', 'RenderManAssetLibrary')
            copy_tree(rmantree_lib_path, self.directory)
        else:
            raise Exception("No preset library found or directory chosen is not writable.")
            return {'FINISHED'}

        hostPrefs.cfg.setCurrentLibraryByPath(FilePath(self.directory))
        hostPrefs.setSelectedLibrary(self.directory)
        hostPrefs.setSelectedCategory(os.path.join(self.library_paths, 'EnvironmentMaps'))
        hostPrefs.setSelectedPreset('')
        hostPrefs.saveAllPrefs()     
        if self.op:
            self.op.dummy_index = -1
            self.op.preset_categories_index = 0             

        return {'FINISHED'}

class PRMAN_OT_load_asset_to_scene(bpy.types.Operator):
    bl_idname = "renderman.load_asset_to_scene"
    bl_label = "Load Asset to Scene"
    bl_description = "Load the Asset to scene"

    preset_path: StringProperty(default='')
    assign: BoolProperty(default=False)

    def invoke(self, context, event):
        from . import rmanAssetsBlender
        mat = rmanAssetsBlender.importAsset(self.properties.preset_path)
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
    material_version: StringProperty(name='Version', default='1.0')
    include_display_filters: BoolProperty(name='Include DisplayFilters', 
        description="Include display filters with this preset. This is necessary if you want to export any stylized materials.",
        default=False)

    @classmethod
    def poll(cls, context):
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
        col.prop(self, 'material_version')
        col.prop(self, 'include_display_filters')

    def execute(self, context):
        hostPrefs = rab.get_host_prefs()
        if hostPrefs.preExportCheck('material', hdr=None, context=context, include_display_filters=self.include_display_filters):
            infodict = {'label': self.material_label,
                        'author': self.material_author,
                        'version': self.material_version}     
            category = hostPrefs.getSelectedCategory()   
            hostPrefs.exportMaterial(category, infodict, None)


        if self.op:
            self.op.preset_categories_index = 0 
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        mat = self.get_current_material(context)        
        self.material_label = mat.name
        self.material_author = getpass.getuser()
        self.material_version = '1.0'
        self.op = getattr(context, 'op_ptr', None) 
        return wm.invoke_props_dialog(self) 

class PRMAN_OT_save_lightrig_to_lib(bpy.types.Operator):
    bl_idname = "renderman.save_lightrig_to_library"
    bl_label = "Save LightRig to Library"
    bl_description = "Save LightRig to Library"

    category_path: StringProperty(default='')
    label: StringProperty(name='Asset Name', default='')
    author: StringProperty(name='Author', default='')
    version: StringProperty(name='Version', default='1.0')
    category: StringProperty(name='Category', default='')

    @classmethod
    def poll(cls, context):
        selected_light_objects = []
        if context.selected_objects:
            for obj in context.selected_objects:  
                if object_utils._detect_primitive_(obj) == 'LIGHT':
                    selected_light_objects.append(obj)

        if not selected_light_objects:
            return False
            
        return True

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'label')
        col.prop(self, 'author')
        col.prop(self, 'version')

    def execute(self, context):
        hostPrefs = rab.get_host_prefs()
        if hostPrefs.preExportCheck('lightrigs', hdr=None, context=context):
            infodict =  {'label': self.label,
                        'author': self.author,
                        'version': self.version}    
            category = hostPrefs.getSelectedCategory()   
            hostPrefs.exportMaterial(category, infodict, None)        
        if self.op:
            self.op.preset_categories_index = 0 
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        ob = context.active_object    
        if ob:
            self.label = ob.name
        self.author = getpass.getuser()
        self.version = '1.0'
        self.op = getattr(context, 'op_ptr', None) 
        return wm.invoke_props_dialog(self) 

class PRMAN_OT_save_envmap_to_lib(bpy.types.Operator):
    bl_idname = "renderman.save_envmap_to_library"
    bl_label = "Save EnvMap to Library"
    bl_description = "Save EnvMap to Library"

    category_path: StringProperty(default='')
    label: StringProperty(name='Asset Name', default='')
    author: StringProperty(name='Author', default=getpass.getuser())
    version: StringProperty(name='Version', default='1.0')
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH")

    filename: bpy.props.StringProperty(
        subtype="FILE_NAME",
        default="")

    filter_glob: bpy.props.StringProperty(
        default="*.hdr;*.tex",
        options={'HIDDEN'},
        )        

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'label')
        col.prop(self, 'author')
        col.prop(self, 'version')

    def execute(self, context):
        if self.properties.filename == '':
            return {'FINISHED'}            

        hostPrefs = rab.get_host_prefs()
        hdr = FilePath(self.properties.filepath)
        if self.label == '':
            self.label = os.path.splitext(os.path.basename(self.properties.filepath))[0]
        if hostPrefs.preExportCheck('envmap', hdr=hdr):
            infodict = {'label': self.label,
                        'author': self.author,
                        'version': self.version}     
            category = hostPrefs.getSelectedCategory()   
            hostPrefs.exportEnvMap(category, infodict)

        if self.op:
            self.op.preset_categories_index = 0 
        return {'FINISHED'}

    def invoke(self, context, event=None):
        context.window_manager.fileselect_add(self)
        self.op = getattr(context, 'op_ptr', None)         
        return{'RUNNING_MODAL'}                

class PRMAN_OT_set_current_preset_category(bpy.types.Operator):
    bl_idname = "renderman.set_current_preset_category"
    bl_label = "Set current RenderMan Preset category"
    bl_description = "Sets the clicked category to be the current category"

    preset_current_path: StringProperty(default='')

    def execute(self, context):
        hostPrefs = rab.get_host_prefs()
        hostPrefs.setSelectedCategory(self.properties.preset_current_path)
        hostPrefs.saveAllPrefs()

        return {'FINISHED'}  

class PRMAN_OT_add_new_preset_category(bpy.types.Operator):
    bl_idname = "renderman.add_new_preset_category"
    bl_label = "Add New RenderMan Preset Category"
    bl_description = "Adds a new preset category"

    new_name: StringProperty(default="")
    current_path: StringProperty(default="")
    
    def execute(self, context):
        if self.properties.new_name == '':
            return {'FINISHED'}

        hostPrefs = rab.get_host_prefs()
        rel_path = os.path.relpath(self.properties.current_path, hostPrefs.getSelectedLibrary())          
        rel_path = os.path.join(rel_path, self.properties.new_name)
        ral.createCategory(hostPrefs.cfg, rel_path)
        if self.op:
            self.op.dummy_index = -1
            self.op.preset_categories_index = 0         
        return {'FINISHED'}

    def invoke(self, context, event):
        self.op = getattr(context, 'op_ptr', None)               
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        row = self.layout
        row.prop(self, "new_name", text="New Name:")      


class PRMAN_OT_remove_preset_category(bpy.types.Operator):
    bl_idname = "renderman.remove_preset_category"
    bl_label = "Remove Current Preset Category"
    bl_description = "Remove preset category"

    @classmethod
    def poll(cls, context):
        hostPrefs = rab.get_host_prefs()
        current_category_path = hostPrefs.getSelectedCategory()
        if current_category_path == '':
            return False
        rel_path = os.path.relpath(current_category_path, hostPrefs.getSelectedLibrary())  
        if rel_path in ['EnvironmentMaps', 'Materials', 'LightRigs']:
            return False
        return True    

    def execute(self, context):
        hostPrefs = rab.get_host_prefs()
        current_category_path = hostPrefs.getSelectedCategory()
        rel_path = os.path.relpath(current_category_path, hostPrefs.getSelectedLibrary())  
        ral.deleteCategory(hostPrefs.cfg, rel_path)
        self.op = getattr(context, 'op_ptr', None)
        if self.op:
            self.op.dummy_index = -1
            self.op.preset_categories_index = 0    

        return {'FINISHED'}

class PRMAN_OT_remove_preset(bpy.types.Operator):
    bl_idname = "renderman.remove_preset"
    bl_label = "Remove RenderMan Preset"
    bl_description = "Remove a Preset"

    preset_path: StringProperty()

    def execute(self, context):
        preset_path = self.properties.preset_path
        hostPrefs = rab.get_host_prefs()
        ral.deleteAsset(preset_path)
        hostPrefs.setSelectedPreset('')
        hostPrefs.saveAllPrefs()
        if self.op:
            self.op.preset_categories_index = self.op.preset_categories_index        
        return {'FINISHED'}

    def invoke(self, context, event):
        self.op = getattr(context, 'op_ptr', None)          
        return context.window_manager.invoke_confirm(self, event)

class PRMAN_OT_move_preset(bpy.types.Operator):
    bl_idname = "renderman.move_preset"
    bl_label = "Move RenderMan Preset"
    bl_description = "Move a Preset"

    def get_categories(self, context):
        hostPrefs = rab.get_host_prefs()
        items = []
        for cat in hostPrefs.getAllCategories(asDict=False):
            tokens = cat.split('/')
            level = len(tokens)
            category_name = ''
            for i in range(0, level-1):
                category_name += '    '            
            category_name = '%s%s' % (category_name, tokens[-1])            
            items.append((str(cat), str(cat), ''))
        return items

    preset_path: StringProperty(default='')
    new_category: EnumProperty(items=get_categories, description='New Category', name="New Category")

    def execute(self, context):
        preset_path = self.properties.preset_path
        hostPrefs = rab.get_host_prefs()
        ral.moveAsset(hostPrefs.cfg, preset_path, self.properties.new_category)
        dst = os.path.join(hostPrefs.getSelectedLibrary(), self.properties.new_category)
        hostPrefs.setSelectedPreset(dst)
        hostPrefs.saveAllPrefs()      
        if self.op:
            self.op.preset_categories_index = self.op.preset_categories_index
        return {'FINISHED'}

    def invoke(self, context, event):
        self.op = getattr(context, 'op_ptr', None)     
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        row = self.layout
        row.prop(self, "new_category")
 
class PRMAN_OT_view_preset_json(bpy.types.Operator):
    bl_idname = "renderman.view_preset_json"
    bl_label = "View Preset JSON"
    bl_description = "View Preset JSON"

    preset_path: StringProperty(default='')
    
    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def execute(self, context):
        json_path = os.path.join(self.properties.preset_path, 'asset.json')
        filepath_utils.view_file(json_path)
        return {'FINISHED'}

class PRMAN_OT_forget_preset_library(bpy.types.Operator):
    bl_idname = "renderman.forget_preset_library"
    bl_label = "Forgot Library"
    bl_description = "Forget Library"

    library_path: StringProperty(default='')
    
    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def execute(self, context):
        json_file = os.path.join(self.library_path, 'library.json')
        if not os.path.exists(json_file):
            return {'FINISHED'}

        hostPrefs = rab.get_host_prefs()
        hostPrefs.cfg.removeLibraryFromLibraryList(self.library_path)
        hostPrefs.cfg.setCurrentLibraryByName(None)
        hostPrefs.setSelectedLibrary(
            hostPrefs.cfg.getCurrentLibraryPath())       

        hostPrefs.setSelectedPreset('')
        hostPrefs.setSelectedCategory('')
        hostPrefs.saveAllPrefs()    

        
        return {'FINISHED'}

class PRMAN_OT_select_preset_library(bpy.types.Operator):
    bl_idname = "renderman.select_preset_library"
    bl_label = "Select Library"
    bl_description = "Select Library"

    def get_libraries(self, context):
        items = []
        hostPrefs = rab.get_host_prefs()
        for p,libinfo in hostPrefs.cfg.libs.items():
            items.append((p, libinfo.getData('name'), p))    

        return items

    library_paths: EnumProperty(items=get_libraries, name="Select Library")
    
    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def execute(self, context):
        json_file = os.path.join(self.library_paths, 'library.json')
        if not os.path.exists(json_file):
            return {'FINISHED'}

        hostPrefs = rab.get_host_prefs()
        hostPrefs.cfg.setCurrentLibraryByPath(FilePath(self.library_paths))
        hostPrefs.setSelectedLibrary(self.library_paths)
      
        hostPrefs.setSelectedPreset('')
        hostPrefs.setSelectedCategory(os.path.join(self.library_paths, 'EnvironmentMaps'))
        hostPrefs.saveAllPrefs()    

        if self.op:
            self.op.dummy_index = -1
            self.op.preset_categories_index = 0         
        
        return {'FINISHED'}        
        
    def invoke(self, context, event):
        self.op = getattr(context, 'op_ptr', None)     
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        row = self.layout
        row.prop(self, "library_paths")        

classes = [
    PRMAN_OT_init_preset_library,
    PRMAN_OT_set_current_preset_category,
    PRMAN_OT_load_asset_to_scene,
    PRMAN_OT_save_asset_to_lib,
    PRMAN_OT_save_lightrig_to_lib,
    PRMAN_OT_save_envmap_to_lib,
    PRMAN_OT_add_new_preset_category,
    PRMAN_OT_remove_preset_category,
    PRMAN_OT_move_preset,
    PRMAN_OT_remove_preset,
    PRMAN_OT_view_preset_json,
    PRMAN_OT_forget_preset_library,
    PRMAN_OT_select_preset_library
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass   
