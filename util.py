# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 Brian Savery
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#
# ##### END MIT LICENSE BLOCK #####

import bpy
import mathutils
import re
import os
import platform
import sys
import fnmatch
import subprocess
from subprocess import Popen, PIPE
from extensions_framework import util as efutil
from mathutils import Matrix, Vector
EnableDebugging = False


class BlenderVersionError(Exception):
    pass


def bpy_newer_257():
    if (bpy.app.version[1] < 57 or (bpy.app.version[1] == 57 and
                                    bpy.app.version[2] == 0)):
        raise BlenderVersionError


def clamp(i, low, high):
    if i < low:
        i = low
    if i > high:
        i = high
    return i


def getattr_recursive(ptr, attrstring):
    for attr in attrstring.split("."):
        ptr = getattr(ptr, attr)

    return ptr


def readOSO(filePath):
    line_number = 0
    shader_meta = {}
    prop_names = []
    with open(filePath, encoding='utf-8') as osofile:
        for line in osofile:
            if line.startswith("surface") or line.startswith("shader"):
                line_number += 1
                listLine = line.split()
                # print("SHADER: ", listLine[1])
                shader_meta["shader"] = listLine[1]
            elif line.startswith("param"):
                line_number += 1
                listLine = line.split()
                name = listLine[2]
                type = listLine[1]
                if type == "point" or type == "vector" or type == "normal" or \
                        type == "color":
                    defaultString = []
                    defaultString.append(listLine[3])
                    defaultString.append(listLine[4])
                    defaultString.append(listLine[5])
                    default = []
                    for element in defaultString:
                        default.append(float(element))
                elif type == "matrix":
                    default = []
                    x = 3
                    while x <= 18:
                        default.append(float(listLine[x]))
                        x += 1
                elif type == "closure":
                    debug('error', "Closure types are not supported")
                    type = "void"
                    name = listLine[3]
                else:
                    default = listLine[3]
                prop_names.append(name)
                prop_meta = {"type": type, "default":  default, "IO": "in"}
                shader_meta[name] = prop_meta
            elif line.startswith("oparam"):
                line_number += 1
                listLine = line.split()
                name = listLine[2]
                type = listLine[1]
                if type == "point" or type == "vector" or type == "normal" or \
                        type == "color":
                    default = []
                    default.append(listLine[3])
                    default.append(listLine[4])
                    default.append(listLine[5])
                elif type == "matrix":
                    default = []
                    x = 3
                    while x <= 18:
                        default.append(listLine[x])
                        x += 1
                elif type == "closure":
                    debug('error', "Closure types are not supported")
                    type = "void"
                    name = listLine[3]
                else:
                    default = listLine[3]
                prop_names.append(name)
                prop_meta = {"type": type, "default":  default, "IO": "out"}
                shader_meta[name] = prop_meta
                # print("SHADER: ", shader_meta)
            else:
                line_number += 1
    return prop_names, shader_meta


def debug(warningLevel, *output):

    if warningLevel == 'warning' or warningLevel == 'error' or \
            warningLevel == 'osl':
        if(warningLevel == "warning"):
            print("WARNING: ", output)
        elif(warningLevel == "error"):
            print("ERROR: ", output)
        elif(warningLevel == "osl"):
            for item in output:
                print("OSL INFO: ", item)
    else:
        if EnableDebugging:
            if(warningLevel == "info"):
                print("INFO: ", output)
            else:
                print("DEBUG: ", output)
        else:
            pass

# -------------------- Path Handling -----------------------------

# convert multiple path delimiters from : to ;
# converts both windows style paths (x:C:\blah -> x;C:\blah)
# and unix style (x:/home/blah -> x;/home/blah)


def path_delimit_to_semicolons(winpath):
    return re.sub(r'(:)(?=[A-Za-z]|\/)', r';', winpath)


def args_files_in_path(prefs, idblock, shader_type='', threaded=True):
    init_env(prefs)
    args = {}

    path_list = get_path_list_converted(prefs, 'args')
    for path in path_list:
        for root, dirnames, filenames in os.walk(path):
            for filename in fnmatch.filter(filenames, '*.args'):
                args[filename.split('.')[0]] = os.path.join(root, filename)
    return args


def get_path_list(rm, type):
    paths = []
    if rm.use_default_paths:
        paths.append('@')
        # here for getting args
        if type == 'args':
            paths.append(os.path.join(guess_rmantree(), 'lib', 'RIS',
                                      'pattern'))
            paths.append(os.path.join(guess_rmantree(), 'lib', 'RIS', 'bxdf'))
            paths.append(os.path.join(guess_rmantree(), 'lib', 'rsl',
                                      'shaders'))
            paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'shaders'))
        if type == 'shader':
            paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'shaders'))
        # we need this for bxdf blend for now.
        if type == 'rixplugin':
            paths.append(os.path.join(guess_rmantree(), 'lib', 'RIS', 'r19',
                                      'bxdf'))

    if rm.use_builtin_paths:
        paths.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                  "%ss" % type))

    if hasattr(rm, "%s_paths" % type):
        for p in getattr(rm, "%s_paths" % type):
            paths.append(bpy.path.abspath(p.name))

    return paths


def get_real_path(path):
    return os.path.realpath(efutil.filesystem_path(path))


# Convert env variables to full paths.
def path_list_convert(path_list, to_unix=False):
    paths = []

    for p in path_list:
        p = os.path.expanduser(p)

        if p.find('$') != -1:
            # path contains environment variables
            # p = p.replace('@', os.path.expandvars('$DL_SHADERS_PATH'))
            # convert path separators from : to ;
            p = path_delimit_to_semicolons(p)

            if to_unix:
                p = path_win_to_unixy(p)

            envpath = ''.join(p).split(';')
            paths.extend(envpath)
        else:
            if to_unix:
                p = path_win_to_unixy(p)
            paths.append(p)

    return paths


def get_path_list_converted(rm, type, to_unix=False):
    return path_list_convert(get_path_list(rm, type), to_unix)


def path_win_to_unixy(winpath, escape_slashes=False):
    if escape_slashes:
        p = winpath.replace('\\', '\\\\')
    else:
        # convert pattern C:\\blah to //C/blah so 3delight can understand
        p = re.sub(r'([A-Za-z]):\\', r'//\1/', winpath)
        p = p.replace('\\', '/')

    return p


# convert ### to frame number
def make_frame_path(path, frame):
    def repl(matchobj):
        hashes = len(matchobj.group(1))
        return str(frame).zfill(hashes)

    path = re.sub('(#+)', repl, path)

    return path


def get_sequence_path(path, blender_frame, anim):
    if not anim.animated_sequence:
        return path

    frame = blender_frame - anim.blender_start + anim.sequence_in

    # hold
    frame = clamp(frame, anim.sequence_in, anim.sequence_out)
    return make_frame_path(path, frame)


def user_path(path, scene=None, ob=None):
    '''
    # bit more complicated system to allow accessing scene or object attributes.
    # let's stay simple for now...
    def repl(matchobj):
        data, attr = matchobj.group(1).split('.')
        if data == 'scene' and scene != None:
            if hasattr(scene, attr):
                return str(getattr(scene, attr))
        elif data == 'ob' and ob != None:
            if hasattr(ob, attr):
                return str(getattr(ob, attr))
        else:
            return matchobj.group(0)

    path = re.sub(r'\{([0-9a-zA-Z_]+\.[0-9a-zA-Z_]+)\}', repl, path)
    '''

    # first env vars, in case they contain special blender variables
    # recursively expand these (max 10), in case there are vars in vars
    for i in range(10):
        path = os.path.expandvars(path)
        if '$' not in path:
            break

    unsaved = True if bpy.data.filepath == '' else False
    # first builtin special blender variables
    if unsaved:
        path = path.replace('{blend}', 'untitled')
    else:
        blendpath = os.path.splitext(os.path.split(bpy.data.filepath)[1])[0]
        path = path.replace('{blend}', blendpath)
    if scene is not None:
        path = path.replace('{scene}', scene.name)
        path = path.replace('{file_type}', scene.renderman.display_driver[-3:])
    if ob is not None:
        path = path.replace('{object}', ob.name)

    # convert ### to frame number
    if scene is not None:
        path = make_frame_path(path, scene.frame_current)

    # convert blender style // to absolute path
    if unsaved:
        path = bpy.path.abspath(path, start=bpy.app.tempdir)
    else:
        path = bpy.path.abspath(path)

    return path

# ------------- RIB formatting Helpers -------------


def rib(v, type_hint=None):

    # float, int
    if type(v) in (mathutils.Vector, mathutils.Color) or\
            v.__class__.__name__ == 'bpy_prop_array'\
            or v.__class__.__name__ == 'Euler':
        # BBM modified from if to elif
        return list(v)

    # matrix
    elif type(v) == mathutils.Matrix:
        return [v[0][0], v[1][0], v[2][0], v[3][0],
                v[0][1], v[1][1], v[2][1], v[3][1],
                v[0][2], v[1][2], v[2][2], v[3][2],
                v[0][3], v[1][3], v[2][3], v[3][3]]
    elif type(v) == mathutils.Matrix:
        return [v[0][0], v[1][0], v[2][0], v[3][0],
                v[0][1], v[1][1], v[2][1], v[3][1],
                v[0][2], v[1][2], v[2][2], v[3][2],
                v[0][3], v[1][3], v[2][3], v[3][3]]
    elif type_hint == 'int':
        return int(v)
    elif type_hint == 'float':
        return float(v)
    else:
        return v


def rib_ob_bounds(ob_bb):
    return (ob_bb[0][0], ob_bb[7][0], ob_bb[0][1],
            ob_bb[7][1], ob_bb[0][2], ob_bb[1][2])


def rib_path(path, escape_slashes=False):
    return path_win_to_unixy(bpy.path.abspath(path),
                             escape_slashes=escape_slashes)


# return a list of properties set on this group
def get_properties(prop_group):
    props = []
    for (key, prop) in prop_group.bl_rna.properties.items():
        # This is somewhat ugly, but works best!!
        if key not in ['rna_type', 'name']:
            props.append(prop)
    return props


def get_global_worldspace(vec, ob):
    wmatx = ob.matrix_world.to_4x4().inverted()
    vec = vec * wmatx
    return vec


def get_local_worldspace(vec, ob):
    lmatx = ob.matrix_local.to_4x4().inverted()
    vec = vec * lmatx
    return vec
# ------------- Environment Variables -------------


def rmantree_from_env():
    RMANTREE = ''

    if 'RMANTREE' in os.environ.keys():
        RMANTREE = os.environ['RMANTREE']
    return RMANTREE


def set_pythonpath(path):
    sys.path.append(path)


def set_rmantree(rmantree):
    os.environ['RMANTREE'] = rmantree


def set_path(paths):
    for path in paths:
        if path is not None:
            os.environ['PATH'] = os.environ['PATH'] + os.pathsep + path


def guess_rmantree():
    guess = rmantree_from_env()
    if guess != '':
        vstr = guess.split('-')[1]
        vf = float(vstr[:4])

        # if this is < 20.0 they have misconfigured their RMANTREE
        # so lets find one
        if vf >= 20.0:
            return guess

    base = ""
    if platform.system() == 'Windows':
        # default installation path
        # or base = 'C:/Program Files/Pixar'
        base = r'C:\Program Files\Pixar'

    elif platform.system() == 'Darwin':
        base = '/Applications/Pixar'

    elif platform.system() == 'Linux':
        base = '/opt/pixar'

    latestver = 0.0
    for d in os.listdir(base):
        if "RenderManProServer" in d:
            vstr = d.split('-')[1]
            vf = float(vstr[:4])
            if vf >= latestver:
                latestver = vf
                guess = os.path.join(base, d)

    if not guess:
        print('ERROR!!!  No RMANTREE found.  Did you install \
            RenderMan Pro Server?  Or set your RMANTREE environment variable?')
    elif latestver < 20.0:
        print('ERROR!!!  You need RenderMan version 20.0 or above.')

    return guess


# return true if an archive is older than the timestamp
def check_if_archive_dirty(update_time, archive_filename):
    if update_time > 0 and os.path.exists(archive_filename) \
            and os.path.getmtime(archive_filename) >= update_time:
        return False
    else:
        return True


def find_it_path():
    rmstree = os.environ['RMSTREE'] if 'RMSTREE' in os.environ.keys() else ''

    if rmstree == '':
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
            if "RenderManStudio" in d:
                vstr = d.split('-')[1]
                vf = float(vstr[:4])
                if vf >= latestver:
                    latestver = vf
                    guess = os.path.join(base, d)
        rmstree = guess

    if rmstree == '':
        return None
    else:
        rmstree = os.path.join(rmstree, 'bin')
        if platform.system() == 'Windows':
            it_path = os.path.join(rmstree, 'it.exe')
        elif platform.system() == 'Darwin':
            it_path = os.path.join(
                rmstree, 'it.app', 'Contents', 'MacOS', 'it')
        elif platform.system() == 'Linux':
            it_path = os.path.join(rmstree, 'it')
        if os.path.exists(it_path):
            return it_path
        else:
            return None


# Default exporter specific env vars
def init_exporter_env(prefs):
    if 'OUT' not in os.environ.keys():
        os.environ['OUT'] = prefs.env_vars.out

    # if 'SHD' not in os.environ.keys():
    #     os.environ['SHD'] = rm.env_vars.shd
    # if 'PTC' not in os.environ.keys():
    #     os.environ['PTC'] = rm.env_vars.ptc
    if 'ARC' not in os.environ.keys():
        os.environ['ARC'] = prefs.env_vars.arc


def init_env(rm):
    # init_exporter_env(scene.renderman)
    # try user set (or guessed) path
    RMANTREE = guess_rmantree()
    RMANTREE_BIN = os.path.join(RMANTREE, 'bin')
    if RMANTREE_BIN not in sys.path:
        sys.path.append(RMANTREE_BIN)
    pathsep = os.pathsep
    if 'PATH' in os.environ.keys():
        os.environ['PATH'] += pathsep + os.path.join(RMANTREE, "bin")
    else:
        os.environ['PATH'] = os.path.join(RMANTREE, "bin")
