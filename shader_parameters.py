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

import os
import subprocess
import bpy
import re

from .util import init_env
from .util import path_win_to_unixy
from .util import user_path
from .util import get_sequence_path

shader_ext = 'sdl'

indent = 0


# dictionary of lamp parameters to take from blender
# if a shader requests these parameters, 
# take them from blender's built in equivalents
exclude_lamp_params = { 'intensity':'energy',
                        'lightcolor':'color',
                        'from':'',
                        'to':'',
                        'coneangle':'spot_size',
                        }

reserved_words = ('and', 'assert', 'break', 'class', 'continue',
                   'def', 'del', 'elif', 'else', 'except',
                   'exec', 'finally', 'for', 'from', 'global',
                   'if', 'import', 'in', 'is', 'lambda',
                   'not', 'or', 'pass',	'print', 'raise',
                   'return', 'try', 'while')

# convert multiple path delimiters from : to ;
# converts both windows style paths (x:C:\blah -> x;C:\blah)
# and unix style (x:/home/blah -> x;/home/blah)
def path_delimit_to_semicolons(winpath):
    return re.sub(r'(:)(?=[A-Za-z]|\/)', r';', winpath)

def tex_source_path(tex, blender_frame):
    rm = tex.renderman
    anim = rm.anim_settings
    
    path = get_sequence_path(rm.file_path, blender_frame, anim)
    if path == '':
        return path
    else:
        return os.path.normpath(bpy.path.abspath(path))
    
def tex_optimised_path(tex, frame):
    path = tex_source_path(tex, frame)

    return os.path.splitext(path)[0] + '.tif'

# return the file path of the optimised version of
# the image texture file stored in Texture datablock
def get_texture_optpath(name, frame):
    try:
        tex = bpy.data.textures[name]
        return tex_optimised_path(tex, frame)
    except KeyError:
        return ""

def get_path_list(rm, type):
    paths = []
    if rm.use_default_paths:
        paths.append('@')
        
    if rm.use_builtin_paths:
        paths.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "%ss" % type))
        
    for p in getattr(rm, "%s_paths" % type):
        paths.append(bpy.path.abspath(p.name))

    return paths

# Convert env variables to full paths.
def path_list_convert(path_list, to_unix=False):
    paths = []
    
    for p in path_list:
        
        p = os.path.expanduser(p)
        
        if p == '@' or p.find('$') != -1:
            # path contains environment variables
            p = p.replace('@', os.path.expandvars('$DL_SHADERS_PATH'))
            
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

def slname_to_pyname(name):
    if name[:1] == '_' or name in reserved_words:
        name = 'SL' + name
    return name

def pyname_to_slname(name):
    if name[:2] == 'SL':
        name = name[2:]
    return name

def sp_optionmenu_to_string(sp):
    if sp.data_type == 'float':        
        return [(str(sp.optionmenu.index(opt)), opt, "") for opt in sp.optionmenu]
    elif sp.data_type == 'string':
        return [(opt.lower(), opt, "") for opt in sp.optionmenu]



def shader_supports_shadowmap(scene, rm, stype):    
    if len([sp for sp in rna_to_shaderparameters(scene, rm, stype) if sp.meta == 'use_shadow_map']) > 0:
        return True
    return False

def shader_requires_shadowmap(scene, rm, stype):
    if sum(sp.value for sp in rna_to_shaderparameters(scene, rm, stype) if sp.meta == 'use_shadow_map') > 0:
        return True
    return False






# Return the filename on disk of a particular shader -
# finds it in the available search paths
def shader_filename(shader_path_list, shadername):

    for p in path_list_convert(shader_path_list):
        filename = os.path.join(p, "%s.%s" % (shadername, shader_ext))
       
        if not os.path.exists(filename):
            continue
            
        try:
            output = subprocess.check_output(["shaderinfo", "-t", filename]).decode().split('\n')
        except subprocess.CalledProcessError:
            continue

        output = [o.replace('\r', '') for o in output]
        
        if len(output) > 1:
            return filename

    return None
    

def shader_recompile(scene, shader_name):
    compiler_path = scene.renderman.path_shader_compiler
    shader_path_list = get_path_list(scene.renderman, 'shader')
    filename = shader_filename(shader_path_list, shader_name)

    if os.path.splitext(filename)[1] != '.sdl':
        return

    cmd = [compiler_path, '--recompile-sdl', filename, '-d', os.path.dirname(filename)]
    subprocess.Popen(cmd)

def shader_recompile_all(scene):
    shader_path_list = get_path_list(scene.renderman, 'shader')
    for p in path_list_convert(shader_path_list):
        for filename in os.listdir(p):
            if os.path.splitext(filename)[1] != '.sdl':
                continue
            cmd = [compiler_path, '--recompile-sdl', filename, '-d', os.path.dirname(filename)]
            subprocess.Popen(cmd)


# Return list-formatted shader parameters etc from 3Delight shaderinfo
def get_3dl_shaderinfo(shader_path_list, shader_name):

    filename = shader_filename(shader_path_list, shader_name)
    
    if filename == None:
        return None
        
    try:
        output = subprocess.check_output(["shaderinfo", "-t", filename]).decode().split('\n')
    except subprocess.CalledProcessError:
        return None
        
    output = [o.replace('\r', '') for o in output]
    
    return output

# Return list-formatted shader annotations etc from 3Delight shaderinfo
def get_3dl_annotations(shader_path_list, shader_name):

    filename = shader_filename(shader_path_list, shader_name)
    if filename == None:
        return None

    try:
        output = subprocess.check_output(["shaderinfo", "-a", filename], stderr=subprocess.STDOUT).decode().split('\n')
    except subprocess.CalledProcessError:
        return None

    output = [o.replace('\r', '') for o in output]
    
    return output


def update_shader_parameter(self, context):
    # XXX Hack to update material preview by setting blender-native property
    if type(self.id_data) == bpy.types.Material:
        self.id_data.diffuse_color = self.id_data.diffuse_color

def update_noop(self, context):
    pass

def update_parameter(propname, vis_name):

    valid_vis_names = ('distant_scale','distant_shadow_type')

    if not vis_name in valid_vis_names:
        return update_noop

    def update_parameter_distantlight(self):
        self.id_data.type = 'AREA'
        self.id_data.distance = 10
        
    def modified_update_parameter(self, context):

        if vis_name == 'distant_scale':
            update_parameter_distantlight(self)
            self.id_data.size = getattr(self, propname)
        elif vis_name == 'distant_shadow_type':
            update_parameter_distantlight(self)
            if getattr(self, propname) == 0:
                self.id_data.size = 0

    return modified_update_parameter
    

# Helpers for dealing with shader parameters
class ShaderParameter():
    
    def __init__(self, name="", data_type="", value=None, shader_type="", length=1):
        self.shader_type = shader_type
        self.data_type = data_type
        self.value = value
        self.name = name
        self.label = name
        self.pyname = slname_to_pyname(self.name)
        self.length = 1
        if data_type in ('color', 'point', 'vector'):
            self.length = 3
        elif data_type == 'float':
            self.length = length
        self.min = 0.0
        self.max = 1.0
        self.hint = ''
        self.hide = False
        self.gadgettype = ''
        self.optionmenu = []
        self.update = update_parameter
        self.meta = {}

    def __repr__(self):
        return "shader %s type: %s data_type: %s, value: %s, length: %s" %  \
            (self.name, self.shader_type, self.data_type, self.value, self.length)


# Get a list of ShaderParameters from a shader file on disk
def get_parameters_shaderinfo(shader_path_list, shader_name, data_type):
    parameters = []
    name = ''
    
    shaderinfo_list = get_3dl_shaderinfo(shader_path_list, shader_name)
    if shaderinfo_list == None:
        print("shader %s not found in path. \n" % shader_name)
        return name, parameters
    
    # current shader name, to cache in material
    name = shaderinfo_list[0]
    type = shaderinfo_list[1]
    
    # return empty if shader is not the requested type
    if type == 'volume':
        if data_type not in ('atmosphere', 'interior', 'exterior'):
            return name, parameters
    elif type != data_type:
        return name, parameters

    
    # add parameters for this shader
    for param in shaderinfo_list[3:]:
        param_items = param.split(',')
        
        if len(param_items) <= 1:
            continue
        
        param_name = param_items[0]
        
        if param_items[3] == 'float':
            default = [float(c) for c in param_items[6].split(' ')]
            length = len(default)
            if length == 1:
                default = default[0]
            sp = ShaderParameter(param_name, 'float', default, type, length)
            
        elif param_items[3] == 'color':
            default = [float(c) for c in param_items[6].split(' ')]
            sp = ShaderParameter(param_name, 'color', default, type)
            
        elif param_items[3] == 'point':
            default = [float(c) for c in param_items[6].split(' ')]
            sp = ShaderParameter(param_name, 'point', default, type)

        elif param_items[3] == 'vector':
            default = [float(c) for c in param_items[6].split(' ')]
            sp = ShaderParameter(param_name, 'vector', default, type)

        elif param_items[3] == 'string':
            default = str(param_items[6])          
            sp = ShaderParameter(param_name, 'string', default, type)

        else:   # XXX support other parameter types
            continue
       
        parameters.append(sp)


    # match annotations with parameters, add additional meta info
    annotations_list = get_3dl_annotations(shader_path_list, shader_name)
    
    if len(annotations_list) > 2:
        for an in annotations_list:
            an_items = an.split('"')
            
            if len(an_items) < 2:
                continue
            
            # parse annotation name and values
            an_name = an_items[1]
            an_values = an_items[3].split(";")

            # find a corresponding shaderParameter and add extra metadata
            for sp in [sp for sp in parameters if an_name == sp.name ]:
            
                # parse through annotation metadata
                for v in an_values:
                    v_items = v.split("=")
                    
                    if len(v_items) < 2:
                        continue
                    
                    if v_items[0] in ('hint', 'label'):
                        setattr(sp, v_items[0], str(v_items[1]))
                    elif v_items[0] in ('min', 'max'):
                        setattr(sp, v_items[0], float(v_items[1]))
                    elif v_items[0] == 'hide':
                        if v_items[1].lower() == 'false':
                            setattr(sp, v_items[0], False)
                        elif v_items[1].lower() == 'true':
                            setattr(sp, v_items[0], True)
                    elif v_items[0] == 'gadgettype':
                        gadget_items = v_items[1].split(":")
                        
                        sp.gadgettype = gadget_items[0]
                        
                        if gadget_items[0] == 'optionmenu':
                            sp.optionmenu = gadget_items[1:]
                    elif v_items[0] == 'meta':
                        sp.meta = v_items[1]
                        sp.update = update_parameter(an_name, v_items[1])



    return name, parameters


def get_shader_pointerproperty(ptr, shader_type):

    stored_shaders = getattr(ptr, "%s_shaders" % shader_type)
    if stored_shaders.active == '':
        return None
    
    try:
        shaderpointer = getattr(stored_shaders, stored_shaders.active)
        return shaderpointer
    except AttributeError:
        return None

def rna_to_propnames(ptr):
    return [n for n in ptr.bl_rna.properties.keys() if n not in ('rna_type', 'name') ]        

# Get a list of ShaderParameters from properties stored in an idblock
def rna_to_shaderparameters(scene, rmptr, shader_type):
    parameters = []
    
    sptr = get_shader_pointerproperty(rmptr, shader_type)

    if sptr == None:
        return parameters
    
    for p in rna_to_propnames(sptr):
        prop = getattr(sptr, p)
        
        typename = type(prop).__name__
        rnatypename = sptr.rna_type.properties[p].type
        subtypename = sptr.rna_type.properties[p].subtype

        if sptr.rna_type.properties[p].is_hidden:
            continue
        
        sp = ShaderParameter()
        sp.pyname = p
        sp.name = pyname_to_slname(p)
        sp.value = prop
        sp.meta = sptr.meta[sp.pyname] if sp.pyname in sptr.meta.keys() else ''

        # inspect python/RNA types and convert to renderman types
        if rnatypename == 'FLOAT':
            if typename.lower() == 'color':
                sp.data_type = 'color'
            elif typename.lower() == 'vector':
                if subtypename == 'TRANSLATION':
                    sp.data_type = 'point'
                elif subtypename == 'XYZ':
                    sp.data_type = 'vector'
                elif subtypename == 'EULER':
                    sp.data_type = 'normal'
            else:
                sp.data_type = 'float'
        elif rnatypename == 'BOOLEAN':
            sp.data_type = 'float'
            sp.value = float(prop)
        elif rnatypename == 'ENUM':
            
            if sp.value.isnumeric():
                # enum values must be stored as string, convert to float
                sp.data_type = 'float'
                sp.value = float(sp.value)
                sp.gadgettype = 'optionmenu'
            else:
                sp.data_type = 'string'
                sp.gadgettype = 'optionmenu'                
                
        elif rnatypename == 'STRING':
            sp.data_type = 'string'

            # check to see if this is the name of a blender texture block
            # if not, it will be left empty.
            texpath = get_texture_optpath(sp.value, scene.frame_current)

            if texpath != '':
                sp.value = path_win_to_unixy(user_path(texpath, scene=scene))
            else:
                sp.value = path_win_to_unixy(user_path(sp.value, scene=scene))

        parameters.append(sp)

    return parameters    

def rna_type_initialise(scene, rmptr, shader_type, replace_existing):

    init_env(scene)
    
    # check to see if this blender data type holds this shader type
    try: stored_shaders = getattr(rmptr, "%s_shaders" % shader_type)
    except AttributeError: return

    # if the type exists and we are overwriting existing, delete all existing rna properties so we can start fresh
    if replace_existing:
        sptr = get_shader_pointerproperty(rmptr, shader_type)
        if sptr is not None:
            for p in rna_to_propnames(sptr):
                exec('del bpy.types.%s.%s' % (sptr.rna_type.name, p))
        
            # delete the pointerproperty that's the instance of the idproperty group
            # for this shader, from the shaders collection
            # assuming it's the active shader, similar logic to get_shader_pointerproperty
            exec('del bpy.types.%s.%s' % (stored_shaders.rna_type.name, stored_shaders.active))

    shader_paths = get_path_list(scene.renderman, 'shader')
    name, parameters = get_parameters_shaderinfo(shader_paths, stored_shaders.active, shader_type)

    if name == '':
        return



    # Generate an RNA Property group for this shader, limiting name length for rna specs
    new_class = type('%sShdSettings' % name[:21], (bpy.types.PropertyGroup,), {})
    bpy.utils.register_class(new_class)

    # Create the RNA pointer property
    setattr(type(stored_shaders), name, bpy.props.PointerProperty(type=new_class, name="%s shader settings" % name) )

    new_class.meta = {}

    # Generate RNA properties for each shader parameter  
    for sp in parameters:
        options = {'ANIMATABLE'}
        
        new_class.meta[sp.pyname] = sp.meta

        if sp.hide:
            options.add('HIDDEN')
       
        if sp.data_type == 'float':
            if sp.gadgettype == 'checkbox':
                setattr(new_class, sp.pyname, bpy.props.BoolProperty(name=sp.label, default=bool(sp.value),
                                        options=options, description=sp.hint, update=sp.update))
                                                
            elif sp.gadgettype == 'optionmenu':
                setattr(new_class, sp.pyname, bpy.props.EnumProperty(name=sp.label, items=sp_optionmenu_to_string(sp),
                                        default=str(int(sp.value)),
                                        options=options, description=sp.hint, update=sp.update))

            elif sp.gadgettype == 'floatslider':
                setattr(new_class, sp.pyname, bpy.props.FloatProperty(name=sp.label, default=sp.value, precision=3,
                                        min=sp.min, max=sp.max, subtype="FACTOR",
                                        options=options, description=sp.hint, update=sp.update))
            elif sp.length == 3:
                setattr(new_class, sp.pyname, bpy.props.FloatVectorProperty(name=sp.label, default=sp.value, size=3,
                                        min=sp.min, max=sp.max,
                                        options=options, description=sp.hint, update=sp.update))
            else:
                setattr(new_class, sp.pyname, bpy.props.FloatProperty(name=sp.label, default=sp.value, precision=3,
                                        options=options, description=sp.hint, update=sp.update))

        elif sp.data_type == 'color':
            setattr(new_class, sp.pyname, bpy.props.FloatVectorProperty(name=sp.label, default=sp.value, size=3,
                                        min=sp.min, soft_min=0.0, max=sp.max, soft_max=1.0, subtype="COLOR",
                                        options=options, description=sp.hint, update=sp.update))
        elif sp.data_type == 'string':
            if sp.gadgettype == 'inputfile':
                setattr(new_class, sp.pyname, bpy.props.StringProperty(name=sp.label, default=sp.value, subtype="FILE_PATH",
                                        options=options, description=sp.hint, update=sp.update))
            else:
                setattr(new_class, sp.pyname, bpy.props.StringProperty(name=sp.label, default=sp.value,
                                        options=options, description=sp.hint, update=sp.update))
                                        
        elif sp.data_type == 'point':
            setattr(new_class, sp.pyname, bpy.props.FloatVectorProperty(name=sp.label, default=sp.value, size=3, subtype="TRANSLATION",
                                        options=options, description=sp.hint, update=sp.update))
        
        elif sp.data_type == 'vector':
            setattr(new_class, sp.pyname, bpy.props.FloatVectorProperty(name=sp.label, default=sp.value, size=3, subtype="XYZ",
                                        options=options, description=sp.hint, update=sp.update))

        elif sp.data_type == 'normal':
            setattr(new_class, sp.pyname, bpy.props.FloatVectorProperty(name=sp.label, default=sp.value, size=3, subtype="EULER",
                                        options=options, description=sp.hint, update=sp.update))

        


def shader_type_initialised(ptr, shader_type):
    if not hasattr(ptr, "%s_shaders" % shader_type):
        return False

    stored_shaders = getattr(ptr, "%s_shaders" % shader_type)
    
    
    sptr = get_shader_pointerproperty(ptr, shader_type)

    if sptr != None:
        return True
    elif sptr == None and stored_shaders.active in ("", "null"):
        return True

    return False


def rna_types_initialise(scene):
    
    #idblocks = list(bpy.data.materials) + list(bpy.data.lamps) + list(bpy.data.worlds)
    ptrs = [ getattr(id, "renderman") for id in list(bpy.data.materials) + list(bpy.data.lamps) + list(bpy.data.worlds) ]
    
    for id in bpy.data.worlds:
        rm = getattr(id, "renderman")
        ptrs.append(getattr(rm, "integrator"))
        #ptrs.extend((getattr(rm, "gi_primary"), getattr(rm, "gi_secondary")))
    
    # material surface coshaders
    for mat in bpy.data.materials:
        ptrs.extend( (coshader for coshader in mat.renderman.coshaders) )
    
    shader_types = ('surface', 'displacement', 'interior', 'atmosphere', 'light')
    
    # iterate over all data that can have shaders
    for rmptr in ptrs:
    
        for shader_type in shader_types:
            # only initialise types that haven't already been initialised - safest by default and at render time
            if not shader_type_initialised(rmptr, shader_type):
                rna_type_initialise(scene, rmptr, shader_type, False)
    
    