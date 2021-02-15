import os
import bpy
import sys
from ..rfb_utils.filepath_utils import guess_rmantree
try:
    from rman_utils.color_manager import ColorManager
except:
    ColorManager = None

__clrmgr__ = None

def color_manager():
    """return the color manager singleton
    """
    if __clrmgr__ is None:
        init()
    return __clrmgr__


def init():
    """initialize ColorManager
    """
    global __clrmgr__

    if __clrmgr__ is None:
        ociopath = os.getenv('OCIO', get_blender_ocio_config())
        if ColorManager:
            __clrmgr__ = ColorManager(ociopath)

def get_blender_ocio_config():
    # return rman's version filmic-blender OCIO config
    ocioconfig = os.path.join(guess_rmantree(), 'lib', 'ocio', 'filmic-blender', 'config.ocio')

    return ocioconfig

def get_config_path():
    """return ocio config path. updating with $OCIO
    """
    clrmgr = color_manager()

    ociopath = os.getenv('OCIO', None)
    if ociopath is None:
        ociopath = get_blender_ocio_config()

    if ColorManager:
        clrmgr.update(ociopath)
        return clrmgr.config_file_path()

    return ociopath

def get_colorspace_name():
    """return the scene colorspace name. updating with $OCIO
    """
    clrmgr = color_manager()
    
    ociopath = os.getenv('OCIO', None)
    if ociopath is None:
        ociopath = get_blender_ocio_config()
    if ColorManager:
        clrmgr.update(ociopath)
        return clrmgr.scene_colorspace_name
        
    return ""