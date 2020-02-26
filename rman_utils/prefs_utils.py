from ..rman_constants import RFB_PREFS_NAME
import bpy

def get_addon_prefs():
    addon = bpy.context.preferences.addons[RFB_PREFS_NAME]
    return addon.preferences

def get_bl_temp_dir():
    return bpy.context.preferences.filepaths.temporary_directory