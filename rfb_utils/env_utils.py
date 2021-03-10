from .prefs_utils import get_pref
from ..rfb_logger import rfb_log
from .. import rman_constants
from ..rman_constants import RFB_ADDON_PATH
import os
import xml.etree.ElementTree as ET
import subprocess
import platform
import sys

__RMAN_ENV_CONFIG__ = None

class RmanEnvConfig(object):

    def __init__(self):
        self.rmantree = ''
        self.rman_version = ''
        self.rman_version_major = 0
        self.rman_version_minor = 0
        self.rman_version_modifier = ''
        self.rman_it_path = ''
        self.rman_lq_path = ''
        self.rman_tractor_path = ''
        self.is_ncr_license = False

    def config_environment(self):

        self.setenv('RMANTREE', self.rmantree)
        self._set_path(os.path.join(self.rmantree, 'bin'))
        self._set_it_path()
        self._set_localqueue_path()
        self._config_pythonpath()
        self._set_ocio()
        self._parse_license()

    def getenv(self, k, default):
        return os.environ.get(k, default)

    def setenv(self, k, val):
        os.environ[k] = val

    def get_shader_registration_paths(self):
        paths = []
        rmantree = self.rmantree
        paths.append(os.path.join(rmantree, 'lib', 'shaders'))    
        paths.append(os.path.join(rmantree, 'lib', 'plugins', 'Args'))
        paths.append(os.path.join(RFB_ADDON_PATH, 'Args'))

        RMAN_SHADERPATH = os.environ.get('RMAN_SHADERPATH', '')
        for p in RMAN_SHADERPATH.split(os.path.pathsep):
            paths.append(p)

        RMAN_RIXPLUGINPATH = os.environ.get('RMAN_RIXPLUGINPATH', '')
        for p in RMAN_RIXPLUGINPATH.split(os.path.pathsep):
            paths.append(os.path.join(p, 'Args'))

        return paths        

    def _config_pythonpath(self):

        if platform.system() == 'Windows':
            rman_packages = os.path.join(self.rmantree, 'lib', 'python3.7', 'Lib', 'site-packages')
        else:
            rman_packages = os.path.join(self.rmantree, 'lib', 'python3.7', 'site-packages')
        sys.path.append(rman_packages)        
        sys.path.append(os.path.join(self.rmantree, 'bin'))
        pythonbindings = os.path.join(self.rmantree, 'bin', 'pythonbindings')
        sys.path.append(pythonbindings)          

    def _set_path(self, path):        
        if path is not None:
            os.environ['PATH'] = path + os.pathsep + os.environ['PATH']        

    def _set_it_path(self):

        if platform.system() == 'Windows':
            self.rman_it_path = os.path.join(self.rmantree, 'bin', 'it.exe')
        elif platform.system() == 'Darwin':
            self.rman_it_path = os.path.join(
                self.rmantree, 'bin', 'it.app', 'Contents', 'MacOS', 'it')
        else:
            self.rman_it_path = os.path.join(self.rmantree, 'bin', 'it')

    def _set_localqueue_path(self):
        if platform.system() == 'Windows':
            self.rman_lq_path = os.path.join(self.rmantree, 'bin', 'LocalQueue.exe')
        elif platform.system() == 'Darwin':
            self.rman_lq_path = os.path.join(
                self.rmantree, 'bin', 'LocalQueue.app', 'Contents', 'MacOS', 'LocalQueue')
        else:
            self.rman_lq_path= os.path.join(self.rmantree, 'bin', 'LocalQueue')

    def _set_tractor_path(self):
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

        if tractor_dir:
            self.rman_tractor_path = os.path.join(tractor_dir, 'bin', 'tractor-spool')

    def get_blender_ocio_config(self):
        # return rman's version filmic-blender OCIO config
        ocioconfig = os.path.join(self.rmantree, 'lib', 'ocio', 'filmic-blender', 'config.ocio')

        return ocioconfig            

    def _set_ocio(self):
        # make sure we set OCIO env var
        # so that "it" will also get the correct configuration
        path = self.getenv('OCIO', '')
        if path == '':
            self.setenv('OCIO', self.get_blender_ocio_config())

    def _parse_license(self):
        pixar_license = os.path.join(self.rmantree, '..', 'pixar.license')
        pixar_license = os.environ.get('PIXAR_LICENSE_FILE', pixar_license)

        if not os.path.isfile(pixar_license):
            self.is_ncr_license = False
            return

        tree = ET.parse(pixar_license)
        root = tree.getroot()
        license_info = None
        for child in root:
            if child.tag == 'LicenseInfo':
                license_info = child
                break
        if not license_info:
            self.is_ncr_license = False
            return

        serial_num = None
        for child in license_info:
            if child.tag == 'SerialNumber':
                serial_num = child
                break

        self.is_ncr_license = (serial_num.text == 'Non-commercial')          

# return the major, minor rman version
def _get_rman_version(rmantree):

    def parse_version(s):
        major_vers, minor_vers = vstr.split('.')
        vers_modifier = ''
        for v in ['b', 'rc']:
            if v in minor_vers:
                i = minor_vers.find(v)
                vers_modifier = minor_vers[i:]
                minor_vers = minor_vers[:i]
                break
        return int(major_vers), int(minor_vers), vers_modifier 

    try:        
        prman = 'prman.exe' if platform.system() == 'Windows' else 'prman'
        exe = os.path.join(rmantree, 'bin', prman)
        desc = subprocess.check_output(
            [exe, "-version"], stderr=subprocess.STDOUT)
        vstr = str(desc, 'ascii').split('\n')[0].split()[-1]
        major_vers, minor_vers, vers_modifier = parse_version(vstr)
        return major_vers, minor_vers, vers_modifier
    except:
        return 0, 0, ''

def _get_default_install_dir():
    path = {'Windows': r'C:\Program Files\Pixar',
            'Darwin': '/Applications/Pixar',
            'Linux': '/opt/pixar'}[platform.system()]    
    return path

def _guess_rmantree():
    '''
    Try to figure out what RMANTREE should be set to based on what's set in the preferences.
    
    ENV = Get From RMANTREE Environment Variable
    DETECT = Choose a version based on what's installed on the local machine (looks in the default install path)
    MANUAL =  Use the path that is manually set in the preferences.

    '''

    global __RMAN_ENV_CONFIG__

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
        rmantree = os.environ.get('RMANTREE', '') 

    if rmantree == '':
        if rmantree_method == 'ENV':
            rfb_log().info('Fallback to autodetecting newest.')
                 
        if choice == 'NEWEST':
            # get from detected installs (at default installation path)
            try:
                base = _get_default_install_dir()
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

    version = _get_rman_version(rmantree)  # major, minor, mod

    # check rmantree valid
    if version[0] == 0:
        rfb_log().error(
            "Error loading addon.  RMANTREE %s is not valid.  Correct RMANTREE setting in addon preferences." % rmantree)
        return None

    # check if this version of RenderMan is supported
    if version[0] < rman_constants.RMAN_SUPPORTED_VERSION_MAJOR:
        rfb_log().error("Error loading addon using RMANTREE=%s.  RMANTREE must be version %s or greater.  Correct RMANTREE setting in addon preferences." % (rmantree, rman_constants.RMAN_SUPPORTED_VERSION_STRING))
        return None

    # Create an RmanEnvConfig object
    __RMAN_ENV_CONFIG__ = RmanEnvConfig()
    __RMAN_ENV_CONFIG__.rmantree = rmantree
    __RMAN_ENV_CONFIG__.rman_version = '%d.%d%s' % (version[0], version[1], version[2])
    __RMAN_ENV_CONFIG__.rman_version_major = version[0]
    __RMAN_ENV_CONFIG__.rman_version_minor = version[1]
    __RMAN_ENV_CONFIG__.rman_version_modifier = version[2]
    __RMAN_ENV_CONFIG__.config_environment()

    return __RMAN_ENV_CONFIG__

def get_installed_rendermans():
    base = _get_default_install_dir()
    rendermans = []

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

def reload_envconfig():
    global __RMAN_ENV_CONFIG__
    if not _guess_rmantree():
        return None
    return __RMAN_ENV_CONFIG__    

def envconfig():

    global __RMAN_ENV_CONFIG__
    if not __RMAN_ENV_CONFIG__:
        if not _guess_rmantree():
            return None
    return __RMAN_ENV_CONFIG__

    
