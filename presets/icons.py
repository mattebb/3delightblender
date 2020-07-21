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

import os
import bpy
import bpy.utils.previews
from ..rman_utils.prefs_utils import get_pref
from ..rman_utils import filepath_utils

asset_previews = bpy.utils.previews.new()
__RMAN_MAT_FLAT_PATH__ = 'lib/rmanAssetResources/icons'
__RMAN_MAT_FLAT_FILENAME__ = 'rman_Mat_default_big_100.png'

def get_presets_for_category(preset_category):
    items = list(preset_category.presets)
    
    if get_pref('presets_show_subcategories', False):
        for sub_category in preset_category.sub_categories:
            items.extend(get_presets_for_category(sub_category))

    return items

def get_icon(path):
    global asset_previews
    thumb = asset_previews.get(path, None)
    if not thumb:
        flat_icon_path = os.path.join( filepath_utils.guess_rmantree(), __RMAN_MAT_FLAT_PATH__)
        flat_icon_thumb = asset_previews.get(flat_icon_path, None)
        if not flat_icon_thumb:
            flat_icon_thumb_path = os.path.join(flat_icon_path, __RMAN_MAT_FLAT_FILENAME__)
            flat_icon_thumb = asset_previews.load(flat_icon_path, flat_icon_thumb_path, 'IMAGE', force_reload=True)     

        return flat_icon_thumb
    return thumb   

def load_previews(preset_category):
    '''Load icons for this preset category

        Returns:
            (list) - a list of tuples containing preset path, preset label, and icon ID
    '''
    global asset_previews
    flat_icon_path = os.path.join( filepath_utils.guess_rmantree(), __RMAN_MAT_FLAT_PATH__)
    flat_icon_thumb = asset_previews.get(flat_icon_path, None)
    if not flat_icon_thumb:
        flat_icon_thumb_path = os.path.join(flat_icon_path, __RMAN_MAT_FLAT_FILENAME__)
        flat_icon_thumb = asset_previews.load(flat_icon_path, flat_icon_thumb_path, 'IMAGE', force_reload=True)

    enum_items = []

    category_dir = get_pref('presets_current_category').path

    items = get_presets_for_category(preset_category)
    items = sorted(items, key=lambda item: item.label)

    for i, asset in enumerate(items):
        path = asset.path
        
        if path not in asset_previews:
            thumb_path = os.path.join(asset.path, 'asset_100.png')
            if os.path.exists(thumb_path):
                thumb = asset_previews.load(path, thumb_path, 'IMAGE', force_reload=True)
            else:
                thumb = flat_icon_thumb
        else:
            thumb = asset_previews[path]
        enum_items.append((asset.path, asset.label, '', thumb.icon_id, i))

    # FIXME: Not sure why this is needed
    # Without it, icons don't seem to show up?
    for img in asset_previews.values():
        x = img.icon_size[0]
        y = img.icon_size[1]

    if not enum_items:
        return [('none', 'none', '', '', 0)]

    return enum_items