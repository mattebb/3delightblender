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

from .. import util
import os
import shutil
import bpy
from bpy.props import StringProperty, EnumProperty, BoolProperty
from .properties import RendermanPresetGroup, RendermanPreset, refresh_presets_libraries
from . import icons
from bpy.types import NodeTree

def get_library_name(jsonfile):
    if not os.path.exists(jsonfile):
        return 'Library'
    data = json.load(open(jsonfile))
    return data["RenderManAssetLibrary"]["name"]

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
        presets_library = util.get_addon_prefs().presets_library
        #presets_path = util.get_addon_prefs().presets_path
        if os.path.exists(json_file):
            presets_library.name = get_library_name(json_file)
            presets_library.path = self.directory
            #util.get_addon_prefs().presets_path = self.directory
        
        elif os.access(self.directory, os.W_OK):
            rmantree_lib_path = os.path.join(util.guess_rmantree(), 'lib', 'RenderManAssetLibrary')
            shutil.copytree(rmantree_lib_path, self.directory)
            presets_library.name = 'Library'
            presets_library.path = self.directory
        else:
            raise Exception("No preset library found or directory chosen is not writable.")
            return {'FINISHED'}
       
        #presets_library.path = presets_path
        #refresh_presets_libraries(presets_path, presets_library)
        refresh_presets_libraries(presets_library.path, presets_library)
        bpy.ops.wm.save_userpref()
        return {'FINISHED'}

# if the library isn't present copy it from rmantree to the path in addon prefs
class PRMAN_OT_refresh_libraries(bpy.types.Operator):
    bl_idname = "renderman.refresh_libraries"
    bl_label = "Refresh Library"
    bl_description = "Refresh preset browser library"

    preset_path: StringProperty(default='')
    assign: BoolProperty(default=False)

    def invoke(self, context, event):
        presets_library = util.get_addon_prefs().presets_library
        refresh_presets_libraries(presets_library.path, presets_library)
        return {'FINISHED'}

# if the library isn't present copy it from rmantree to the path in addon prefs
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
                ob.active_material = mat

        return {'FINISHED'}


# save the current material to the library
class PRMAN_OT_save_asset_to_lib(bpy.types.Operator):
    bl_idname = "renderman.save_asset_to_library"
    bl_label = "Save Asset to Library"
    bl_description = "Save Asset to Library"

    lib_path: StringProperty(default='')

    def invoke(self, context, event):
        presets_path = util.get_addon_prefs().presets_library.path
        path = os.path.relpath(self.properties.lib_path, presets_path)
        library = RendermanPresetGroup.get_from_path(self.properties.lib_path)
        ob = context.active_object
        mat = ob.active_material
        nt = mat.node_tree
        if nt:
            from . import rmanAssetsBlender
            os.environ['RMAN_ASSET_LIBRARY'] = presets_path
            rmanAssetsBlender.exportAsset(nt, 'nodeGraph', 
                                          {'label':mat.name,
                                           'author': '',
                                           'version': ''},
                                           path
                                           )
        refresh_presets_libraries(library.path, library)
        bpy.ops.wm.save_userpref()
        return {'FINISHED'}


# if the library isn't present copy it from rmantree to the path in addon prefs
class PRMAN_OT_set_active_preset_library(bpy.types.Operator):
    bl_idname = "renderman.set_active_preset_library"
    bl_label = "Set active RenderMan Preset Library"
    bl_description = "Sets the clicked library active"

    lib_path: StringProperty(default='')

    def execute(self, context):
        lib_path = self.properties.lib_path
        if lib_path:
            util.get_addon_prefs().active_presets_path = lib_path
            bpy.ops.wm.save_userpref()
        return {'FINISHED'}

# if the library isn't present copy it from rmantree to the path in addon prefs
class PRMAN_OT_add_preset_library(bpy.types.Operator):
    bl_idname = "renderman.add_preset_library"
    bl_label = "Add RenderMan Preset Library"
    bl_description = "Adds a new library"

    new_name: StringProperty(default="")
    
    def execute(self, context):
        active = RendermanPresetGroup.get_active_library()
        lib_path = active.path
        new_folder = self.properties.new_name
        if lib_path and new_folder:
            path = os.path.join(lib_path, new_folder)
            os.mkdir(path)
            sub_group = active.sub_groups.add()
            sub_group.name = new_folder
            sub_group.path = path

            util.get_addon_prefs().active_presets_path = path
        bpy.ops.wm.save_userpref()
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        row = self.layout
        row.prop(self, "new_name", text="New Folder Name:")

class PRMAN_OT_remove_preset_library(bpy.types.Operator):
    bl_idname = "renderman.remove_preset_library"
    bl_label = "Remove RenderMan Preset Library"
    bl_description = "Remove a library"

    def execute(self, context):
        active = RendermanPresetGroup.get_active_library()
        lib_path = active.path
        if lib_path:
            parent_path = os.path.split(active.path)[0]
            parent = RendermanPresetGroup.get_from_path(parent_path)
            util.get_addon_prefs().active_presets_path = parent_path
            
            shutil.rmtree(active.path)

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
            parent = RendermanPresetGroup.get_from_path(parent_path)
            
            shutil.rmtree(active.path)

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
        return get_libs(util.get_addon_prefs().presets_library)

    preset_path: StringProperty(default='')
    new_library: EnumProperty(items=get_libraries, description='New Library', name="New Library")

    def execute(self, context):
        new_parent_path = self.properties.new_library
        active = RendermanPreset.get_from_path(self.properties.preset_path)
        if active:
            old_parent_path = os.path.split(active.path)[0]
            old_parent = RendermanPresetGroup.get_from_path(old_parent_path)
            new_parent = RendermanPresetGroup.get_from_path(new_parent_path)

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

class PRMAN_OT_move_preset_library(bpy.types.Operator):
    bl_idname = "renderman.move_preset_library"
    bl_label = "Move RenderMan Preset Group"
    bl_description = "Move a Preset Group"

    def get_libraries(self, context):
        def get_libs(parent_lib):
            enum = [(parent_lib.path, parent_lib.name, '')]
            for lib in parent_lib.sub_groups:
                enum.extend(get_libs(lib))
            return enum

        return get_libs(util.get_addon_prefs().presets_library)

    lib_path: StringProperty(default='')
    new_library: EnumProperty(items=get_libraries, description='New Library', name="New Library")

    def execute(self, context):
        new_parent_path = self.properties.new_library
        active = RendermanPresetGroup.get_from_path(self.properties.lib_path)
        if active:
            old_parent_path = os.path.split(active.path)[0]
            old_parent = RendermanPresetGroup.get_from_path(old_parent_path)
            new_parent = RendermanPresetGroup.get_from_path(new_parent_path)

            shutil.move(active.path, new_parent_path)
            
            refresh_presets_libraries(old_parent.path, old_parent)
            refresh_presets_libraries(new_parent.path, new_parent)
        bpy.ops.wm.save_userpref()
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        row = self.layout
        row.prop(self, "new_library", text="New Parent")

classes = [
    PRMAN_OT_init_preset_library,
    PRMAN_OT_refresh_libraries,
    PRMAN_OT_set_active_preset_library,
    PRMAN_OT_load_asset_to_scene,
    PRMAN_OT_save_asset_to_lib,
    PRMAN_OT_add_preset_library,
    PRMAN_OT_remove_preset_library,
    PRMAN_OT_move_preset_library,
    PRMAN_OT_move_preset,
    PRMAN_OT_remove_preset
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
