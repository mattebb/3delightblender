from ..rman_constants import RFB_PREFS_NAME
import bpy

def get_addon_prefs():
    try:
        addon = bpy.context.preferences.addons[RFB_PREFS_NAME]
        return addon.preferences
    except:
        return None

def get_pref(pref_name='', default=None):
    """ Return the value of a preference

    Args:
        pref_name (str) - name of the preference to look up
        default (AnyType) - default to return, if pref_name doesn't exist

    Returns:
        (AnyType) - preference value.
    """

    prefs = get_addon_prefs()
    if not prefs:
        return default
    return getattr(prefs, pref_name, default)

def get_bl_temp_dir():
    return bpy.context.preferences.filepaths.temporary_directory