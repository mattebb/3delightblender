# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2011 Matt Ebb
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


class BlenderVersionError(Exception):
    pass

def bpy_newer_257():
    if (bpy.app.version[1] < 57 or (bpy.app.version[1] == 57 and bpy.app.version[2] == 0)):
        raise BlenderVersionError

def clamp(i, low, high):
    if i < low: i = low
    if i > high: i = high
    return i

def getattr_recursive(ptr, attrstring):
    for attr in attrstring.split("."):
        ptr = getattr(ptr, attr)

    return ptr
# -------------------- Path Handling -----------------------------

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
        if not '$' in path: break
    
    unsaved = True if bpy.data.filepath == '' else False
    
    # first builtin special blender variables
    if unsaved:
        path = path.replace('{blend}', 'untitled')
    else:
        blendpath = os.path.splitext( os.path.split(bpy.data.filepath)[1] )[0]
        path = path.replace('{blend}', blendpath)
        
    if scene != None:
        path = path.replace('{scene}', scene.name)
    if ob != None:
        path = path.replace('{object}', ob.name)

    # convert ### to frame number
    if scene != None:
        path =  make_frame_path(path, scene.frame_current)

    # convert blender style // to absolute path
    if unsaved:
        path = bpy.path.abspath( path, start=bpy.app.tempdir )
    else:
        path = bpy.path.abspath( path )
    
    return path
    

# ------------- RIB formatting Helpers -------------

def rib(v):
    
    # float, int
    if type(v) in (float, int, mathutils.Vector, mathutils.Color):
        vlen = 1
        
        if hasattr(v, '__len__'):
            vlen = len(v)
        if vlen > 1:
            return '[ ' + ' '.join([str(i) for i in v]) + ' ]'

        else:
            return str(v)
    
    # string
    elif type(v) == str:
        return '"%s"' % v
        
    # list, tuple
    elif type(v) in (list, tuple):
        return "[ " + " ".join(str(i) for i in v) + " ]"
    
    # matrix
    elif type(v) == mathutils.Matrix:
        return '[ %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f ]' % \
            (v[0][0], v[1][0], v[2][0], v[3][0], \
             v[0][1], v[1][1], v[2][1], v[3][1], \
             v[0][2], v[1][2], v[2][2], v[3][2], \
             v[0][3], v[1][3], v[2][3], v[3][3])

    

def rib_ob_bounds(ob_bb):
    return ( ob_bb[0][0], ob_bb[7][0], bb[0][1], ob_bb[7][1], bb[0][2], ob_bb[7][2] )

def rib_path(path, escape_slashes=False):
    return path_win_to_unixy(bpy.path.abspath(path), escape_slashes=escape_slashes)
    
    
     
# ------------- Environment Variables -------------   

def path_from_3dl_env_txt():
    DELIGHT = ''
    
    # check 3delight environment file
    envfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), "3delight_env.txt")
    if os.path.exists(envfile):
        f = open(envfile)
        for line in f:
            s = line.split("=")
            if s[0] == 'DELIGHT' and s[1].strip() != '':
                DELIGHT = s[1]
                break
        f.close()

    return DELIGHT

def guess_3dl_path():
    guess = path_from_3dl_env_txt()
    if guess != '': return guess
    
    if platform.system() == 'Windows':
        # default installation path
        if os.path.exists('C:\Program Files\3Delight'):
            guess = 'C:\Program Files\3Delight'

    elif platform.system() == 'Darwin':        
        # scan /Applications/Graphics looking for most recent installed 3delight version
        lastver = 0.0
        for f in os.listdir('/Applications/Graphics'):
            if f[:9] != '3Delight-': continue
            
            vstr = f.rsplit('3Delight-')[1]
            vf = float(vstr.rsplit('.', 1)[0] + vstr.rsplit('.', 1)[1])
            
            if vf > lastver:
                lastver = vf
                guess = os.path.join('/Applications/Graphics', f)            
                
    return guess    

# Default exporter specific env vars
def init_exporter_env(scene):
    rm = scene.renderman
    
    if 'OUT' not in os.environ.keys():
        os.environ['OUT'] = rm.env_vars.out

    if 'SHD' not in os.environ.keys():
        os.environ['SHD'] = rm.env_vars.shd
       
    if 'PTC' not in os.environ.keys():
        os.environ['PTC'] = rm.env_vars.ptc
    
    if 'ARC' not in os.environ.keys():
        os.environ['ARC'] = rm.env_vars.arc
        
    
        
def init_env(scene):

    init_exporter_env(scene)


    if 'DELIGHT' in os.environ.keys():
        return

    # try user set (or guessed) path
    DELIGHT = scene.renderman.path_3delight
    
    # try 3Delight environment file
    env_txt = path_from_3dl_env_txt()
    if env_txt != '': DELIGHT = env_txt

    # 3Delight-specific env vars
    if DELIGHT != '':
        # only add these as envvars if they're not already set
        if 'DELIGHT' not in os.environ.keys():
            os.environ['DELIGHT'] = DELIGHT
        if 'DL_DISPLAYS_PATH' not in os.environ.keys():
            os.environ['DL_DISPLAYS_PATH'] = os.path.join(DELIGHT, "displays")
        if 'DL_SHADERS_PATH' not in os.environ.keys():
            os.environ['DL_SHADERS_PATH'] = os.path.join(DELIGHT, "shaders")
            
        if platform.system() == 'Darwin':
            if 'DYLD_LIBRARY_PATH' not in os.environ.keys():
                os.environ['DYLD_LIBRARY_PATH'] = os.path.join(DELIGHT, "lib")
        
        if platform.system() == 'Linux':
            if 'LD_LIBRARY_PATH' not in os.environ.keys():
                os.environ['LD_LIBRARY_PATH'] = os.path.join(DELIGHT, "lib")
        
        pathsep = ';' if platform.system() == 'Windows' else ':'
        
        if 'PATH' in os.environ.keys():
            os.environ['PATH'] += pathsep + os.path.join(DELIGHT, "bin")
        else:
            os.environ['PATH'] = os.path.join(DELIGHT, "bin")
    