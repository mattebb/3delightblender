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

from bpy.props import *
from bpy.types import PropertyGroup
import bpy.utils
from .. import util
from . import icons
import os

# This file holds the properties for the preset browser.  
# They will be parsed from the json file

# get the enum items


# an actual preset
class RendermanPreset(PropertyGroup):
    bl_label = "Renderman Preset Group"
    bl_idname = 'RendermanPresetGroup'

    def get_enum_items(self, context):
        return icons.enum_items

    @classmethod
    def get_from_path(cls, lib_path):
        group_path, preset = os.path.split(lib_path)

        group = RendermanPresetGroup.get_from_path(group_path)
        return group.presets[preset] if preset in group.presets.keys() else None
    
    name = StringProperty(default='')
    thumbnail = EnumProperty(items=get_enum_items)
    thumb_path = StringProperty(subtype='FILE_PATH')
    path = StringProperty(subtype='FILE_PATH')
    json_path = StringProperty(subtype='FILE_PATH')


# forward define preset group
class RendermanPresetGroup(PropertyGroup):
    bl_label = "Renderman Preset Group"
    bl_idname = 'RendermanPresetGroup'
    pass

# A property group holds presets and sub groups
class RendermanPresetGroup(PropertyGroup):
    bl_label = "Renderman Preset Group"
    bl_idname = 'RendermanPresetGroup'

    @classmethod
    def get_from_path(cls, lib_path):
        head = util.get_addon_prefs().presets_library
        active = head
        for sub_path in os.path.split(lib_path):
            if sub_path in active.sub_groups.keys():
                active = active.sub_groups[sub_path]
        return active

    # get the active library from the addon pref
    @classmethod
    def get_active_library(cls):
        active_path = util.get_addon_prefs().active_presets_path
        if active_path != '':
            return cls.get_from_path(active_path)
        else:
            return None

    name = StringProperty(default='')
    ui_open = BoolProperty(default=True)

    presets = CollectionProperty(type=RendermanPreset)
    path = StringProperty(
        name="Path for preset files",
        description="Path for preset files, if not present these will be copied from RMANTREE.",
        subtype='FILE_PATH',
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'presets', 'library'))

    

    # gets the presets and all from children
    def get_presets(self):
        all_presets = self.presets[:]
        for group in self.sub_groups:
            all_presets += group.get_presets()
        return all_presets 


def register():
    try:
        bpy.utils.register_class(RendermanPreset)
        bpy.utils.register_class(RendermanPresetGroup)

        # set sub groups type we have to do this after registered
        sub_groups = CollectionProperty(type=RendermanPresetGroup)
        setattr(RendermanPresetGroup, 'sub_groups', sub_groups)
    
    except:
        pass #allready registered

def unregister():
    bpy.utils.unregister_class(RendermanPresetGroup)
    bpy.utils.unregister_class(RendermanPreset)

