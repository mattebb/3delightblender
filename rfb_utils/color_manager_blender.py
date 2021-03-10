import os
import bpy
import sys
from ..rfb_utils.env_utils import envconfig
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
        ociopath = envconfig().getenv('OCIO', envconfig().get_blender_ocio_config())
        if ColorManager:
            __clrmgr__ = ColorManager(ociopath)

def get_config_path():
    """return ocio config path. updating with $OCIO
    """
    clrmgr = color_manager()

    ociopath = envconfig().getenv('OCIO', None)
    if ociopath is None:
        ociopath = envconfig().get_blender_ocio_config()

    if ColorManager:
        clrmgr.update(ociopath)
        return clrmgr.config_file_path()

    return ociopath

def get_colorspace_name():
    """return the scene colorspace name. updating with $OCIO
    """
    clrmgr = color_manager()
    
    ociopath = envconfig().getenv('OCIO', None)
    if ociopath is None:
        ociopath = envconfig().get_blender_ocio_config()
    if ColorManager:
        clrmgr.update(ociopath)
        return clrmgr.scene_colorspace_name
        
    return ""