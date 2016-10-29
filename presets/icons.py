import os
import bpy
import bpy.utils.previews
from .. import util

asset_previews = bpy.utils.previews.new()
enum_items = [('0', '0', '0')]

def load_previews(lib):
    global asset_previews
    lib_dir = presets_library = util.get_addon_prefs().presets_library.path

    for asset_name,asset in lib.presets.items():
        path = asset.path
        
        if path not in asset_previews:
            thumb_path = os.path.join(asset.path, 'asset_100.png')
            
            thumb = asset_previews.load(path, thumb_path, 'IMAGE', force_reload=True)
            enum_items.append((path, path, "", thumb.icon_id, len(enum_items) + 1))
            asset.thumbnail = path


    for sub_group in lib.sub_groups:
        load_previews(sub_group)