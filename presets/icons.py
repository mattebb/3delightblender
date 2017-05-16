import os
import bpy
import bpy.utils.previews
from .. import util

asset_previews = bpy.utils.previews.new()

def get_presets_for_lib(lib):
    items = list(lib.presets)
    for sub_group in lib.sub_groups:
        items.extend(get_presets_for_lib(sub_group))
    return items

def load_previews(lib):
    global asset_previews
    enum_items = []

    lib_dir = presets_library = util.get_addon_prefs().presets_library.path

    items = get_presets_for_lib(lib)
    items = sorted(items, key=lambda item: item.label)

    for i, asset in enumerate(items):
        path = asset.path
        
        if path not in asset_previews:
            thumb_path = os.path.join(asset.path, 'asset_100.png')
            
            thumb = asset_previews.load(path, thumb_path, 'IMAGE', force_reload=True)
        else:
            thumb = asset_previews[path]
        enum_items.append((asset.path, asset.label, '', thumb.icon_id, i))

    return enum_items if enum_items else [('', '', '')]