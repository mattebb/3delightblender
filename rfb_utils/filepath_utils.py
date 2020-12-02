import bpy
import os
import subprocess
import platform
import sys
import webbrowser
import xml.etree.ElementTree as ET
from ..rfb_logger import rfb_log
from .. import rman_constants
from .prefs_utils import get_pref

__RMANTREE__ = None
__IS_NCR_LICENSE__ = None

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

def is_ncr_license():
    global __IS_NCR_LICENSE__
    if __IS_NCR_LICENSE__:
        return __IS_NCR_LICENSE__

    pixar_license = os.path.join(guess_rmantree(), '..', 'pixar.license')
    pixar_license = os.environ.get('PIXAR_LICENSE_FILE', pixar_license)

    tree = ET.parse(pixar_license)
    root = tree.getroot()
    license_info = None
    for child in root:
        if child.tag == 'LicenseInfo':
            license_info = child
            break
    if not license_info:
        __IS_NCR_LICENSE__ = False
        return __IS_NCR_LICENSE__

    serial_num = None
    for child in license_info:
        if child.tag == 'SerialNumber':
            serial_num = child
            break

    __IS_NCR_LICENSE__ = (serial_num.text == 'Non-commercial')

    return __IS_NCR_LICENSE__

def rmantree_from_env():
    RMANTREE = ''

    if 'RMANTREE' in os.environ.keys():
        RMANTREE = os.environ['RMANTREE']
    return RMANTREE


def set_pythonpath(path):
    sys.path.append(path)


def set_rmantree(rmantree):
    global __RMANTREE__
    os.environ['RMANTREE'] = rmantree
    __RMANTREE__ = rmantree


def set_path(paths):
    for path in paths:
        if path is not None:
            os.environ['PATH'] = path + os.pathsep + os.environ['PATH']


def check_valid_rmantree(rmantree):
    prman = 'prman.exe' if platform.system() == 'Windows' else 'prman'

    if os.path.exists(rmantree) and \
       os.path.exists(os.path.join(rmantree, 'bin')) and \
       os.path.exists(os.path.join(rmantree, 'bin', prman)):
        return True
    return False

# return the major, minor rman version


def get_rman_version(rmantree):
    try:        
        prman = 'prman.exe' if platform.system() == 'Windows' else 'prman'
        exe = os.path.join(rmantree, 'bin', prman)
        desc = subprocess.check_output(
            [exe, "-version"], stderr=subprocess.STDOUT)
        vstr = str(desc, 'ascii').split('\n')[0].split()[-1]
        major_vers, minor_vers = vstr.split('.')
        vers_modifier = ''
        for v in ['b', 'rc']:
            if v in minor_vers:
                i = minor_vers.find(v)
                vers_modifier = minor_vers[i:]
                minor_vers = minor_vers[:i]
                break
        return int(major_vers), int(minor_vers), vers_modifier
    except:
        return 0, 0, ''


def guess_rmantree():

    global __RMANTREE__

    if __RMANTREE__:
        return __RMANTREE__

    rmantree_method = get_pref('rmantree_method', 'ENV')
    choice = get_pref('rmantree_choice')

    rmantree = ''

    if rmantree_method == 'MANUAL':
        rmantree = get_pref('path_rmantree')

    if rmantree_method == 'DETECT' and choice != 'NEWEST':
        rmantree = choice

    if rmantree == '' or rmantree_method == 'ENV':
        # Fallback to RMANTREE env var
        if rmantree == '':
            rfb_log().info('Fallback to using RMANTREE.')
        rmantree = rmantree_from_env()

    if rmantree == '':
        if rmantree_method == 'ENV':
            rfb_log().info('Fallback to autodetecting newest.')
                 
        if choice == 'NEWEST':
            # get from detected installs (at default installation path)
            try:
                base = {'Windows': r'C:\Program Files\Pixar',
                        'Darwin': '/Applications/Pixar',
                        'Linux': '/opt/pixar'}[platform.system()]
                latest = (0, 0, '')
                for d in os.listdir(base):
                    if "RenderManProServer" in d:
                        d_rmantree = os.path.join(base, d)
                        d_version = get_rman_version(d_rmantree)
                        if d_version > latest:
                            rmantree = d_rmantree
                            latest = d_version
            except:
                pass

    version = get_rman_version(rmantree)  # major, minor, mod

    # check rmantree valid
    if version[0] == 0:
        rfb_log().error(
            "Error loading addon.  RMANTREE %s is not valid.  Correct RMANTREE setting in addon preferences." % rmantree)
        return None

    # check if this version of RenderMan is supported
    if version[0] < rman_constants.RMAN_SUPPORTED_VERSION_MAJOR:
        rfb_log().error("Error loading addon using RMANTREE=%s.  RMANTREE must be version %s or greater.  Correct RMANTREE setting in addon preferences." % (rmantree, rman_constants.RMAN_SUPPORTED_VERSION_STRING))
        return None

    __RMANTREE__ = rmantree
    return rmantree

def get_installed_rendermans():
    base = ""
    if platform.system() == 'Windows':
        # default installation path
        # or base = 'C:/Program Files/Pixar'
        base = r'C:\Program Files\Pixar'

    elif platform.system() == 'Darwin':
        base = '/Applications/Pixar'

    elif platform.system() == 'Linux':
        base = '/opt/pixar'

    rendermans = []
    rmantree = rmantree_from_env
    #if rmantree != '':
    #    rendermans.append(('From RMANTREE', rmantree))

    try:
        for d in os.listdir(base):
            if "RenderManProServer" in d:
                try:
                    vstr = d.split('-')[1]
                    rendermans.append((vstr, os.path.join(base, d)))
                except:
                    pass
    except:
        pass

    return rendermans

def find_it_path():
    rmantree = guess_rmantree()

    if not rmantree:
        return None
    else:
        rmantree = os.path.join(rmantree, 'bin')
        if platform.system() == 'Windows':
            it_path = os.path.join(rmantree, 'it.exe')
        elif platform.system() == 'Darwin':
            it_path = os.path.join(
                rmantree, 'it.app', 'Contents', 'MacOS', 'it')
        elif platform.system() == 'Linux':
            it_path = os.path.join(rmantree, 'it')
        if os.path.exists(it_path):
            return it_path
        else:
            return None

def find_local_queue():
    rmantree = guess_rmantree()

    if not rmantree:
        return None
    else:
        rmantree = os.path.join(rmantree, 'bin')
        if platform.system() == 'Windows':
            lq = os.path.join(rmantree, 'LocalQueue.exe')
        elif platform.system() == 'Darwin':
            lq = os.path.join(
                rmantree, 'LocalQueue.app', 'Contents', 'MacOS', 'LocalQueue')
        elif platform.system() == 'Linux':
            lq = os.path.join(rmantree, 'LocalQueue')
        if os.path.exists(lq):
            return lq
        else:
            return None

def find_tractor_spool():
    base = ""
    if platform.system() == 'Windows':
        # default installation path
        base = r'C:\Program Files\Pixar'

    elif platform.system() == 'Darwin':
        base = '/Applications/Pixar'

    elif platform.system() == 'Linux':
        base = '/opt/pixar'

    latestver = 0.0
    guess = ''
    for d in os.listdir(base):
        if "Tractor" in d:
            vstr = d.split('-')[1]
            vf = float(vstr)
            if vf >= latestver:
                latestver = vf
                guess = os.path.join(base, d)
    tractor_dir = guess

    if not tractor_dir:
        return None
    else:
        spool_name = os.path.join(tractor_dir, 'bin', 'tractor-spool')
        if os.path.exists(spool_name):
            return spool_name
        else:
            return None            

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

def init_env(rm):
    RMANTREE = guess_rmantree()
    os.environ['RMANTREE'] = RMANTREE
    RMANTREE_BIN = os.path.join(RMANTREE, 'bin')
    if RMANTREE_BIN not in sys.path:
        sys.path.append(RMANTREE_BIN)
    pathsep = os.pathsep
    if 'PATH' in os.environ.keys():
        os.environ['PATH'] += pathsep + os.path.join(RMANTREE, "bin")
    else:
        os.environ['PATH'] = os.path.join(RMANTREE, "bin")    