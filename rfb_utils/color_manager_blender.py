import os
import bpy
import sys
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
    """initialize ColorManager with houdini's $OCIO
    which can be different from system's $OCIO if 
    set in Edit > Color Settings
    """
    global __clrmgr__

    if __clrmgr__ is None:
        ociopath = os.getenv('OCIO', None)
        if ColorManager:
            __clrmgr__ = ColorManager(ociopath)

def get_blender_ocio_config():
    # figure out the path to Blender's default ocio config file
    # hopefully, this won't change between versions
    ocioconfig = ''
    version  = '%d.%d' % (bpy.app.version[0], bpy.app.version[1])
    binary_path = os.path.dirname(bpy.app.binary_path)
    rel_config_path = os.path.join(version, 'datafiles', 'colormanagement', 'config.ocio')
    if sys.platform == ("win32"):
        ocioconfig = os.path.join(binary_path, rel_config_path)
    elif sys.platform == ("darwin"):                
        ocioconfig = os.path.join(binary_path, '..', 'Resources', rel_config_path )
    else:
        ocioconfig = os.path.join(binary_path, rel_config_path)    

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