import bpy
from ..rfb_logger import rfb_log

def rman_print(message, level='INFO'):
    override = bpy.context.copy()
    window = bpy.context.window_manager.windows[0]
    override['window'] = window
    override['screen'] = window.screen
    try:
        bpy.ops.renderman.printer(override, 'INVOKE_DEFAULT', message=message, level=level)    
    except Exception as e:
        rfb_log().debug("Cannot call renderman.printer: %s" % str(e))