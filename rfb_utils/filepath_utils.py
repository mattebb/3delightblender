import bpy
import os
import platform
import sys
import webbrowser
from ..rfb_logger import rfb_log
from .prefs_utils import get_pref
from .env_utils import envconfig

def view_file(file_path):
    
    rman_editor = get_pref('rman_editor', '')

    if rman_editor:
        rman_editor = get_real_path(rman_editor)
        command = rman_editor + " " + file_path
        try:
            os.system(command)
            return
        except Exception:
            rfb_log().error("File or text editor not available. (Check and make sure text editor is in system path.)")        


    if sys.platform == ("win32"):
        try:
            os.startfile(file_path)
            return
        except:
            pass
    else:
        if sys.platform == ("darwin"):
            opener = 'open -t'
        else:
            opener = os.getenv('EDITOR', 'xdg-open')
            opener = os.getenv('VIEW', opener)
        try:
            command = opener + " " + file_path
            os.system(command)
        except Exception as e:
            rfb_log().error("Open file command failed: %s" % command)
            pass
        
    # last resort, try webbrowser
    try:
        webbrowser.open(file_path)
    except Exception as e:
        rfb_log().error("Open file with web browser failed: %s" % str(e))    

def get_cycles_shader_path():
    # figure out the path to Cycles' shader path
    # hopefully, this won't change between versions
    path = ''
    version  = '%d.%d' % (bpy.app.version[0], bpy.app.version[1])
    binary_path = os.path.dirname(bpy.app.binary_path)
    rel_config_path = os.path.join(version, 'scripts', 'addons', 'cycles', 'shader')
    if sys.platform == ("win32"):
        path = os.path.join(binary_path, rel_config_path)
    elif sys.platform == ("darwin"):                
        path = os.path.join(binary_path, '..', 'Resources', rel_config_path )
    else:
        path = os.path.join(binary_path, rel_config_path)        

    return path
 
def filesystem_path(p):
	#Resolve a relative Blender path to a real filesystem path
	if p.startswith('//'):
		pout = bpy.path.abspath(p)
	else:
		pout = os.path.realpath(p)
	
	return pout.replace('\\', '/')

def get_real_path(path):
    if os.path.isabs(path):
        return os.path.realpath(filesystem_path(path))
    return path