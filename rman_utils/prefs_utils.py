from ..rman_constants import RFB_PREFS_NAME
import bpy

def get_addon_prefs():
    addon = bpy.context.preferences.addons[RFB_PREFS_NAME]
    return addon.preferences

def get_pref_val(pref_name=''):
    """ Return the value of a preference

    Args:
        pref_name (str) - name of the preference to look up

    Returns:
        (AnyType) - preference value. Returns None if pref_name does not exist
    """

    prefs = get_addon_prefs()
    return getattr(prefs, pref_name, None)

def get_bl_temp_dir():
    return bpy.context.preferences.filepaths.temporary_directory