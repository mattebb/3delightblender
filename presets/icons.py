import os
import bpy
import bpy.utils.previews
from .. import util

asset_previews = bpy.utils.previews.new()

def load_previews(lib, start=0):
    global asset_previews
    enum_items = []

    lib_dir = presets_library = util.get_addon_prefs().presets_library.path

    for i,asset in enumerate(lib.presets):
        path = asset.path
        
        if path not in asset_previews:
            thumb_path = os.path.join(asset.path, 'asset_100.png')
            
            thumb = asset_previews.load(path, thumb_path, 'IMAGE', force_reload=True)
        else:
            thumb = asset_previews[path]
        enum_items.append((asset.path, asset.label, '', thumb.icon_id, start + i))
        
    start += len(enum_items)
    for sub_group in lib.sub_groups:
        enum_items.extend(load_previews(sub_group, start))

    return enum_items if enum_items else [('', '', '')]