import bpy

def get_addon_prefs():
    addon = bpy.context.preferences.addons[__name__.split('.')[0]]
    return addon.preferences

def get_bl_temp_dir():
    return bpy.context.preferences.filepaths.temporary_directory