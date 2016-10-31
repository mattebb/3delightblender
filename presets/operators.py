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
import os
import shutil
import bpy
from bpy.props import StringProperty
from .properties import RendermanPresetGroup, RendermanPreset
from . import icons

# update the tree structure from disk file
def refresh_presets_libraries(disk_lib, preset_library):
    dirs = os.listdir(disk_lib)
    for dir in dirs:
        cdir = os.path.join(disk_lib, dir)
        # skip if not a dir
        if not os.path.isdir(cdir):
            continue
        
        is_asset = '.rma' in dir
        path = os.path.join(disk_lib, dir)

        if is_asset:
            preset = preset_library.presets.add()
            preset.name = dir
            preset.path = path
            preset.json_path = os.path.join(path, 'asset.json')

        else:
            sub_group = preset_library.sub_groups.get(dir, None)
            if not sub_group:
                sub_group = preset_library.sub_groups.add()
                sub_group.name = dir
                sub_group.path = path

            refresh_presets_libraries(cdir, sub_group)

    for name,sub_group in preset_library.sub_groups.items():
        if name not in dirs:
            preset_library.sub_groups.remove(sub_group)


# if the library isn't present copy it from rmantree to the path in addon prefs
class init_preset_library(bpy.types.Operator):
    bl_idname = "renderman.init_preset_library"
    bl_label = "Init RenderMan Preset Library"
    bl_description = "Copies the Preset Library from RMANTREE to the library path if not present"

    def invoke(self, context, event):
        presets_path = util.get_addon_prefs().presets_library.path
        presets_library = util.get_addon_prefs().presets_library

        if not os.path.exists(presets_path):
            rmantree_lib_path = os.path.join(util.guess_rmantree(), 'lib', 'RenderManAssetLibrary')
            shutil.copytree(rmantree_lib_path, presets_path)
            
        presets_library.name = 'Library'
        refresh_presets_libraries(presets_path, presets_library)

        return {'FINISHED'}

# if the library isn't present copy it from rmantree to the path in addon prefs
class load_asset_to_scene(bpy.types.Operator):
    bl_idname = "renderman.load_asset_to_scene"
    bl_label = "Load Asset to Scene"
    bl_description = "Load the Asset to scene"

    preset_path = StringProperty(default='')

    def invoke(self, context, event):
        presets_path = util.get_addon_prefs().presets_library.path
        path = os.path.relpath(self.properties.preset_path, presets_path)
        preset = RendermanPreset.get_from_path(path)
        from . import rmanAssetsBlender
        rmanAssetsBlender.importAsset(preset.json_path)

        return {'FINISHED'}


# save the current material to the library
class save_asset_to_lib(bpy.types.Operator):
    bl_idname = "renderman.save_asset_to_library"
    bl_label = "Save Asset to Library"
    bl_description = "Save Asset to Library"

    lib_path = StringProperty(default='')

    def invoke(self, context, event):
        presets_path = util.get_addon_prefs().presets_library.path
        path = os.path.relpath(self.properties.lib_path, presets_path)
        library = RendermanPresetGroup.get_from_path(path)

        return {'FINISHED'}


# if the library isn't present copy it from rmantree to the path in addon prefs
class set_active_preset_library(bpy.types.Operator):
    bl_idname = "renderman.set_active_preset_library"
    bl_label = "Set active RenderMan Preset Library"
    bl_description = "Sets the clicked library active"

    lib_path = StringProperty(default='')

    def invoke(self, context, event):
        lib_path = self.properties.lib_path
        if lib_path:
            presets_path = util.get_addon_prefs().presets_library.path
            path = os.path.relpath(lib_path, presets_path)
            active = RendermanPresetGroup.get_from_path(path)
            util.get_addon_prefs().active_presets_path = path
            if active:
                icons.load_previews(active)
            else:
                print('error ' + lib_path, presets_path, path)
        return {'FINISHED'}

def register():
    try:
        bpy.utils.register_class(init_preset_library)
        bpy.utils.register_class(set_active_preset_library)
    except:
        pass #allready registered

def unregister():
    bpy.utils.register_class(init_preset_library)
    bpy.utils.unregister_class(set_active_preset_library)