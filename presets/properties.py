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

from bpy.props import *
from bpy.types import PropertyGroup
import bpy.utils
from ..rman_utils import prefs_utils
from . import icons
import json
import os

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
            preset = preset_library.presets.get(dir, None)
            if not preset:
                preset = preset_library.presets.add()         

            preset.name = dir
            json_path = os.path.join(path, 'asset.json')
            data = json.load(open(json_path))
            preset.label = data['RenderManAsset']['label']
            preset.path = path
            preset.json_path = os.path.join(path, 'asset.json')
            try:
                meta_data = data['RenderManAsset']['asset'].get('envMap', None)
                if not meta_data:
                    meta_data = data['RenderManAsset']['asset'].get('nodeGraph', None)
                if meta_data:
                    preset.author = meta_data['metadata'].get('author', '')
                    preset.version = str(meta_data['metadata'].get('version', ''))
                    preset.created = str(meta_data['metadata'].get('created', ''))
                    preset.resolution = str(meta_data['metadata'].get('Resolution', ''))
            except:
                pass

        else:
            sub_group = preset_library.sub_categories.get(dir, None)
            if not sub_group:
                sub_group = preset_library.sub_categories.add()
            sub_group.name = dir
            sub_group.path = path

            refresh_presets_libraries(cdir, sub_group)

    for i,sub_group in enumerate(preset_library.sub_categories):
        if sub_group.name not in dirs:
            preset_library.sub_categories.remove(i)
    for i,preset in enumerate(preset_library.presets):
        if preset.name not in dirs:
            preset_library.presets.remove(i)

class RendermanPreset(PropertyGroup):
    '''This class represents a single RendderMan preset on disk

    Attributes:
        name (bpy.props.StringProperty) - name of the preset
        label (bpy.props.StringProperty) - the preset's label
        thumb_path (bpy.props.StringProperty) - the path to the thumbnail for this preset
        path (bpy.props.StringProperty) - the path to the preset on disk
        json_path (bpy.props.StringProperty) - the path to the preset's JSON file on disk
        author (bpy.props.StringProperty) - the preset's author
        version (bpy.props.StringProperty) - the preset's version
        created (bpy.props.StringProperty) - the preset's creation timestamp
    '''


    bl_label = "RenderMan Preset"
    bl_idname = 'RendermanPreset'

    @classmethod
    def get_from_path(cls, preset_path):
        if not preset_path:
            return
        if preset_path == 'none':
            return
        group_path,preset = os.path.split(preset_path)

        group = RendermanPresetCategory.get_from_path(group_path)
        return group.presets[preset] if preset in group.presets.keys() else None
    
    name: StringProperty(default='', name="Name")
    label: StringProperty(default='', name="Label")
    author: StringProperty(default='', name="Author")
    version: StringProperty(default='', name="Version")
    created: StringProperty(default='', name="Created")
    resolution: StringProperty(default='', name="Resolution")
    thumb_path: StringProperty(subtype='FILE_PATH')
    path: StringProperty(subtype='FILE_PATH')
    json_path: StringProperty(subtype='FILE_PATH')


# forward define preset category
class RendermanPresetCategory(PropertyGroup):
    bl_label = "RenderMan Preset Category"
    bl_idname = 'RendermanPresetCategory'
    pass

# A property group holds presets and sub groups
class RendermanPresetCategory(PropertyGroup):
    '''This class represents a single preset category
    and presets that belong to said category

    Attributes
        name (bpy.props.StringProperty) - category name
        path (bpy.props.StringProperty) - full path on disk to this category in the presets library
        presets (bpy.props.CollectionProperty) - a collection of RenderManPreset(s)
        selected_preset (bpy.props.EnumProperty) - the currently selected preset in this category. 
                                                    The enum created in presets.icons module
        sub_categories (bpy.props.CollectionProperty) - a collection of RendermanPresetCategory that are subdirectories
                                                    of this category on disk
    '''

    bl_label = "RenderMan Preset Category"
    bl_idname = 'RendermanPresetCategory'

    @classmethod
    def get_from_path(cls, preset_path):
        ''' get from abs preset_path '''
        preset_library_path = presets_root_category = prefs_utils.get_addon_prefs().presets_root_category.path
        head = prefs_utils.get_addon_prefs().presets_root_category
        preset_path = os.path.relpath(preset_path, preset_library_path)
        active = head
        for sub_path in preset_path.split(os.sep):
            if sub_path in active.sub_categories.keys():
                active = active.sub_categories[sub_path]       
        #refresh_presets_libraries(active.path, active)
        return active

    # get the current category from the addon pref 
    @classmethod
    def get_current_category(cls):
        current_path = prefs_utils.get_addon_prefs().presets_current_category_path
        if current_path != '':
            return cls.get_from_path(current_path)
        else:
            return None

    name: StringProperty(default='')
    ui_open: BoolProperty(default=True)

    def generate_previews(self, context):
        return icons.load_previews(self)
    
    path: StringProperty(default='', name='Category Path', subtype="FILE_PATH")
    presets: CollectionProperty(type=RendermanPreset)
    selected_preset: EnumProperty(items=generate_previews, name='Selected Preset')

    # gets the presets and all from children
    def get_presets(self):
        all_presets = self.presets[:]
        for group in self.sub_categories:
            all_presets += group.get_presets()
        return all_presets 

    def is_current_category(self):
        return self.path == prefs_utils.get_addon_prefs().presets_current_category_path

classes = [
    RendermanPreset,
    RendermanPresetCategory
]

def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    # set sub groups after registering the class
    RendermanPresetCategory.__annotations__['sub_categories'] = CollectionProperty(type=RendermanPresetCategory)
   

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
