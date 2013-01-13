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
from .util import get_path_list
from .util import path_list_convert
from .util import path_win_to_unixy
from .util import user_path
from .util import get_sequence_path

from .shader_scan import shaders_in_path

#import properties_shader
from .properties_shader import RendermanCoshader
'''
# BBM addition begin
# temporarily a straight copy of properties.py
from bpy.props import PointerProperty, StringProperty, BoolProperty, EnumProperty, \
IntProperty, FloatProperty, FloatVectorProperty, CollectionProperty

class coshaderShaders(bpy.types.PropertyGroup):

    def coshader_shader_active_update(self, context):
		# BBM addition begin
        if self.id_data.name == 'World': # world coshaders
            location = 'world'
            mat_rm = context.scene.world.renderman
        elif bpy.context.active_object.name in bpy.data.lamps.keys(): # lamp coshaders
            location = 'lamp'
            lamp = bpy.data.lamps.get(bpy.context.active_object.name)
            mat_rm = lamp.renderman
        else: # material coshaders
            location = 'material'
            mat_rm = context.active_object.active_material.renderman
        shader_active_update(self, context, 'shader', location) # BBM modified (from 'surface' to 'shader')
        cosh_index = mat_rm.coshaders_index
        active_cosh = mat_rm.coshaders[cosh_index]
        active_cosh_name = active_cosh.shader_shaders.active
        if active_cosh_name == 'null':
            coshader_name = active_cosh_name
        else:
            all_cosh = [ (cosh.name) for cosh in mat_rm.coshaders ]
            same_name = 1
            for cosh in all_cosh:
                if cosh.startswith( active_cosh_name ):
                    same_name += 1
            coshader_name = ('%s_%d' % (active_cosh_name, same_name))
        active_cosh.name = coshader_name
        # BBM addition end
    
    active = StringProperty(
                name="Active Co-Shader",
                description="Shader name to use for coshader",
                update=coshader_shader_active_update,
                default="null"
                )

    def coshader_shader_list_items(self, context):
        return shader_list_items(self, context, 'shader')

    def coshader_shader_list_update(self, context):
        shader_list_update(self, context, 'shader')

    shader_list = EnumProperty(
                name="Active Co-Shader",
                description="Shader name to use for coshader",
                update=coshader_shader_list_update,
                items=coshader_shader_list_items
                )

class RendermanCoshader(bpy.types.PropertyGroup):
    name = StringProperty(
                name="Name (Handle)",
                description="Handle to refer to this co-shader from another shader")
    
	#BBM replace begin
    #surface_shaders = PointerProperty( 
    #            type=surfaceShaders,
    #            name="Surface Shader Settings")
    #by
    shader_shaders = PointerProperty(
                type=coshaderShaders,
                name="Coshader Shader Settings")

bpy.utils.register_class(coshaderShaders)
bpy.utils.register_class(RendermanCoshader)
'''

# BBM addition end
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

#BBM addition begin

def sp_shaderlist_to_string(scene, rm):
    # XXX def shader_list_items(self, context, type):
    defaults = [('null', 'None', '')]
    shader_list = defaults + [ (s, s, '') for s in shaders_in_path(scene, None, shader_type='shader')]
    

def old_sp_shaderlist_to_string( rm ):
    try:
        wrld_coshaders = bpy.context.scene.world.renderman.coshaders
        coshader_names = [(cosh.name) for cosh in wrld_coshaders]
        if not rm.id_data.name == 'World': # if we're in a material or light, include the local coshaders as well.
            obj_coshaders = rm.coshaders
            obj_coshaders_names = [(cosh.name) for cosh in obj_coshaders]
		    # Need to remove duplicates. The material coshader will win over the world ones if they shader same handle.
            coshader_names = obj_coshaders_names + list(set(coshader_names) - set(obj_coshaders_names))
        coshader_names = ['null'] + coshader_names
        return [(name, name, '') for name in coshader_names ]
    except AttributeError:
        return []

#BBM addition end

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
        return (None, None)
        
    try:
        output = subprocess.check_output(["shaderinfo", "-t", filename]).decode().split('\n')
        output_d = subprocess.check_output(["shaderinfo", "-d", filename]).decode().split('\n')
    except subprocess.CalledProcessError:
        return (None, None)
    
    output = [l.replace('\r', '').split(',') for l in output if l != '']

    # note:
    # shaderinfo -t parameters are offset by 3
    # shaderinfo -d parameters offset by 1
    param_data = []
    output_d = output_d[1:]
    for i,l in enumerate(output[3:]):
        param_data.append( {'name': l[0],
                            'data_type': l[3],
                            'default': l[6],
                            'array': ('shader[' in output_d[i])
                            } )
    shader_name = output[0]
    shader_type = output[1]

    return shader_type, param_data


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
		# BBM replaced
        #return update_noop
		# by
        return None
		# not a biggie, just to get rid of the "ValueError: the return value must be None" output

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
class ShaderParameter(object):
    
	# BBM replace
    #def __init__(self, name="", data_type="", value=None, shader_type="", length=1):
	# by
    def __init__(self, name="", data_type="", value=None, shader_type="", length=1, is_coshader=False, is_array=False):
	# BBM replace end
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
        self.meta['shader_input'] = False
        self.meta['data_type'] = data_type
        self.meta['array'] = is_array

		# BBM addition begin
        self.is_coshader = is_coshader
        self.is_array = is_array
		# BBM addition end

    @classmethod
    def fromParamObject(self, obj, name):
        sp = self()

        prop = getattr(obj, name)

        typename = type(prop).__name__
        rnatypename = obj.rna_type.properties[name].type
        subtypename = obj.rna_type.properties[name].subtype

        sp.pyname = name
        sp.name = pyname_to_slname(name)
        sp.value = prop
        sp.meta = obj.meta[sp.pyname] if sp.pyname in obj.meta.keys() else ''

        sp.is_array = obj.is_array[sp.pyname] if sp.pyname in obj.is_array.keys() else ''
        sp.is_coshader = obj.is_coshader[sp.pyname] if sp.pyname in obj.is_coshader.keys() else ''
        
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
        elif rnatypename == 'INT':
            sp.data_type = 'float'
        elif rnatypename == 'COLLECTION':
            sp.data_type = 'string'
            sp.gadgettype = 'optionmenu'
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


        return sp

    def __repr__(self):
        return "shader %s type: %s data_type: %s, value: %s, length: %s" %  \
            (self.name, self.shader_type, self.data_type, self.value, self.length)


# Get a list of ShaderParameters from a shader file on disk
def get_parameters_shaderinfo(shader_path_list, shader_name, data_type):
    parameters = []

    sdl_type, sdl_param_data = get_3dl_shaderinfo(shader_path_list, shader_name)
    if sdl_param_data is None:
        print("shader %s not found in path. \n" % shader_name)
        return '', parameters

    # return empty if shader is not the requested type
    if data_type != '':
        if sdl_type == 'volume':
            if data_type not in ('atmosphere', 'interior', 'exterior'):
                return '', parameters
        elif sdl_type != data_type:
            return '', parameters

    # add parameters for this shader
    for param in sdl_param_data:
        length = 1
        is_coshader = False

        if param['data_type'] == 'float':
            default = [float(c) for c in param['default'].split(' ')]
            length = len(default)
            if length == 1:
                default = default[0]
        elif param['data_type'] in ('color', 'point', 'vector'):
            default = [float(c) for c in param['default'].split(' ')]
        elif param['data_type'] == 'string':
            default = str(param['default'])
        elif param['data_type'] == 'shader':
            is_coshader = True
            default = ""
        
        else:   # XXX support other parameter types
            continue

        sp = ShaderParameter(param['name'], param['data_type'], default, sdl_type, is_coshader=is_coshader, is_array=param['array'])
        
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
                    elif v_items[0] == 'meta':      # XXX ?????
                        sp.meta['meta_annotation'] = v_items[1]
                        sp.update = update_parameter(an_name, v_items[1])

    return shader_name, parameters


def get_shader_pointerproperty(ptr, shader_type):
	# BBM addition begin
    # if not hasattr(ptr, "%s_shaders" % shader_type): # world coshaders
    #     ptr = ptr.coshaders[ptr.coshaders_index]
    # BBM addition end
	
    stored_shaders = getattr(ptr, "%s_shaders" % shader_type)
    if stored_shaders.active == '':
        return None
    
    try:
        return stored_shaders.parameters  # XXXX
        # shaderpointer = getattr(stored_shaders, stored_shaders.active)
        # return shaderpointer
    except AttributeError:
        return None

def rna_to_propnames(ptr):
    return [n for n in ptr.bl_rna.properties.keys() if n not in ptr.bl_rna.base.properties.keys() ]        

def ptr_to_shaderparameters(scene, sptr):
    parameters = []
    for p in rna_to_propnames(sptr):
        prop = getattr(sptr, p)
        
        typename = type(prop).__name__
        rnatypename = sptr.rna_type.properties[p].type
        subtypename = sptr.rna_type.properties[p].subtype

        if sptr.rna_type.properties[p].is_hidden:
            continue
        # BBM addition begin
        if p.startswith('bl_hidden'):
            continue
        # BBM addition end
        
        sp = ShaderParameter()
        sp.pyname = p
        sp.name = pyname_to_slname(p)
        sp.value = prop
        sp.meta = sptr.meta[sp.pyname] if sp.pyname in sptr.meta.keys() else ''
        # BBM addition begin
        sp.is_array = sptr.is_array[sp.pyname] if sp.pyname in sptr.is_array.keys() else ''
        sp.is_coshader = sptr.is_coshader[sp.pyname] if sp.pyname in sptr.is_coshader.keys() else ''
        # BBM addition end
        
        #print(sp.name, sp.meta)

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
        #BBM addition begin
        elif rnatypename == 'INT':
            sp.data_type = 'float'
        elif rnatypename == 'COLLECTION':
            sp.data_type = 'string'
            sp.gadgettype = 'optionmenu'
        #BBM addition end
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

# Get a list of ShaderParameters from properties stored in an idblock
def rna_to_shaderparameters(scene, rmptr, shader_type):
    parameters = []
    
    sptr = get_shader_pointerproperty(rmptr, shader_type)

    if sptr == None:
        return parameters
    
    return ptr_to_shaderparameters(scene, sptr)

def class_add_parameters(new_class, shaderparameters):
    parameter_names = []

    new_class.meta = {}
    # BBM addition begin
    new_class.is_array = {}
    new_class.is_coshader = {}
    # BBM addition end
    
    # Generate RNA properties for each shader parameter  
    for sp in shaderparameters:
        options = {'ANIMATABLE'}

        parameter_names.append( sp.pyname )
        
        new_class.meta[sp.pyname] = sp.meta
        # BBM addition begin
        new_class.is_array[sp.pyname] = sp.is_array
        new_class.is_coshader[sp.pyname] = sp.is_coshader
        # BBM addition end
        
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
            
            # BBM Addition begin
            elif sp.gadgettype.startswith('intfield'):
                setattr(new_class, sp.pyname, bpy.props.IntProperty(name=sp.label, default=int(sp.value),
                                        options=options, description=sp.hint, update=sp.update))
                                        
            elif sp.gadgettype.startswith('intslider'):
                setattr(new_class, sp.pyname, bpy.props.IntProperty(name=sp.label, default=int(sp.value),
                                        min=int(sp.min), max=int(sp.max), subtype="FACTOR",
                                        options=options, description=sp.hint, update=sp.update))
            # BBM add end
            
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
        '''
        #BBM addition begin
        elif sp.data_type == 'shader':
            if sp.is_array == 0:
                setattr(new_class, sp.pyname, bpy.props.EnumProperty(name=sp.label, items=sp_shaderlist_to_string( scene, rmptr ),
                                        options=options, description=sp.hint, update=sp.update))
        
            else:
                setattr(new_class, sp.pyname, bpy.props.CollectionProperty(name=sp.label, type=RendermanCoshader, options=options, description=sp.hint))
                setattr(new_class , 'bl_hidden_%s_index' % sp.pyname, bpy.props.IntProperty(name=sp.label, default=int(-1), subtype="FACTOR",
                                        options=options, description=sp.hint, update=sp.update))
                setattr(new_class, 'bl_hidden_%s_menu' % sp.pyname, bpy.props.EnumProperty(name=sp.label, items=sp_shaderlist_to_string( scene, rmptr ),
                                        options=options, description=sp.hint, update=sp.update))
        '''

    return parameter_names

def shader_class_name(shader_name):
    return '%sParams' % shader_name[:21]

# rewrite! yay!
def shader_class(scene, name):
    class_name = shader_class_name(name)
    if class_name in locals().keys():
        return locals()[class_name]

    path_list = get_path_list(scene.renderman, 'shader')
    name, parameters = get_parameters_shaderinfo(path_list, name, '')

    new_class = type(class_name, (bpy.types.PropertyGroup,), {})
    new_class.shader_name = name
    new_class.prop_names = class_add_parameters(new_class, parameters)

    bpy.utils.register_class(new_class)
    return new_class

def shaderparameters_from_class(param_object):
    parameters = []
    for p in param_object.prop_names:
        sp = ShaderParameter.fromParamObject(param_object, p)
        parameters.append( sp )

    return parameters

def rna_type_initialise(scene, rmptr, shader_type, replace_existing):

    init_env(scene)
    
    # BBM addition begin
    # account for world coshaders (path different from Lamps and Objects)
    #if rmptr.id_data.name == 'World':
    #    stored_shaders = rmptr.coshaders
    #    shader_index = rmptr.coshaders_index
    #    shader_paths = get_path_list(scene.renderman, 'shader')
    #    name, parameters = get_parameters_shaderinfo(shader_paths, stored_shaders[shader_index], shader_type)
    #else:
    # BBM addition end
    
    # check to see if this blender data type holds this shader type
    try:
        stored_shaders = getattr(rmptr, "%s_shaders" % shader_type)
    except AttributeError:
        print(rmptr, shader_type, 'doesnt hold this type')
        return

    # if the type exists and we are overwriting existing, delete all existing rna properties so we can start fresh
    if replace_existing:
        sptr = get_shader_pointerproperty(rmptr, shader_type)
        
        if sptr is not None:
            for p in rna_to_propnames(sptr):
                exec('del bpy.types.%s.%s' % (sptr.rna_type.name, p))

                # BBM replaced begin
                #exec('del bpy.types.%s.%s' % (sptr.rna_type.name, p)):
				# by
                # try:
                #     exec('del bpy.types.%s.%s' % (sptr.rna_type.name, p))
                # except:
                #     pass
				# BBM replaced end - ok, I got errors here, don't know why quite honestly
        
            # delete the pointerproperty that's the instance of the idproperty group
            # for this shader, from the shaders collection
            # assuming it's the active shader, similar logic to get_shader_pointerproperty
            # BBM replaced begin
            #exec('del bpy.types.%s.%s' % (stored_shaders.rna_type.name, stored_shaders.active))
			#by
            try:
                exec('del bpy.types.%s.%s' % (stored_shaders.rna_type.name, stored_shaders.active))
            except:
                pass
    
    shader_paths = get_path_list(scene.renderman, 'shader')
    name, parameters = get_parameters_shaderinfo(shader_paths, stored_shaders.active, shader_type)

    if name == '':
        print('no name')
        return

    # Generate an RNA Property group for this shader, limiting name length for rna specs
    new_class = type('%sShdSettings' % name[:21], (bpy.types.PropertyGroup,), {})
    bpy.utils.register_class(new_class)

    # Add parameters to Shader pointerproperty
    setattr(type(stored_shaders), "parameters", bpy.props.PointerProperty(type=new_class, name=name) )

    new_class.meta = {}
	# BBM addition begin
    new_class.is_array = {}
    new_class.is_coshader = {}
	# BBM addition end
    
    # Generate RNA properties for each shader parameter  
    for sp in parameters:
        options = {'ANIMATABLE'}
        
        new_class.meta[sp.pyname] = sp.meta
		# BBM addition begin
        new_class.is_array[sp.pyname] = sp.is_array
        new_class.is_coshader[sp.pyname] = sp.is_coshader
		# BBM addition end
		
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
			
			# BBM Addition begin
            elif sp.gadgettype.startswith('intfield'):
                setattr(new_class, sp.pyname, bpy.props.IntProperty(name=sp.label, default=int(sp.value),
                                        options=options, description=sp.hint, update=sp.update))
										
            elif sp.gadgettype.startswith('intslider'):
                setattr(new_class, sp.pyname, bpy.props.IntProperty(name=sp.label, default=int(sp.value),
                                        min=int(sp.min), max=int(sp.max), subtype="FACTOR",
                                        options=options, description=sp.hint, update=sp.update))
			# BBM add end
			
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
        
        #BBM addition begin
        elif sp.data_type == 'shader':
            if sp.is_array == 0:
                setattr(new_class, sp.pyname, bpy.props.EnumProperty(name=sp.label, items=sp_shaderlist_to_string( scene, rmptr ),
                                        options=options, description=sp.hint, update=sp.update))
            else:
                setattr(new_class, sp.pyname, bpy.props.CollectionProperty(name=sp.label, type=RendermanCoshader, options=options, description=sp.hint))
                setattr(new_class , 'bl_hidden_%s_index' % sp.pyname, bpy.props.IntProperty(name=sp.label, default=int(-1), subtype="FACTOR",
                                        options=options, description=sp.hint, update=sp.update))
                setattr(new_class, 'bl_hidden_%s_menu' % sp.pyname, bpy.props.EnumProperty(name=sp.label, items=sp_shaderlist_to_string( scene, rmptr ),
                                        options=options, description=sp.hint, update=sp.update))

		#BBM addition end

        


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
    
    idblocks = list(bpy.data.materials) + list(bpy.data.lamps) + list(bpy.data.worlds)
    ptrs = [ getattr(id, "renderman") for id in idblocks ]
    
    for id in bpy.data.worlds:
        rm = getattr(id, "renderman")
        ptrs.append(getattr(rm, "integrator"))
        #ptrs.extend((getattr(rm, "gi_primary"), getattr(rm, "gi_secondary")))
    
    # material surface coshaders
    #for mat in bpy.data.materials:
    #    ptrs.extend( (coshader for coshader in mat.renderman.coshaders) )
	# BBM addition begin
    #for lgt in bpy.data.lamps:
    #    ptrs.extend( (coshader for coshader in lgt.renderman.coshaders) )
    #for wld in bpy.data.worlds:
    #    ptrs.extend( (coshader for coshader in wld.renderman.coshaders) )
	# BBM addition end
    
	#BBM repalce
    #shader_types = ('surface', 'displacement', 'interior', 'atmosphere', 'light')
	#by
    shader_types = ('surface', 'displacement', 'interior', 'atmosphere', 'light', 'shader')
	#BBM replace end
    
    # iterate over all data that can have shaders
    for rmptr in ptrs:
    
        for shader_type in shader_types:
            # only initialise types that haven't already been initialised - safest by default and at render time
            #if not shader_type_initialised(rmptr, shader_type):
            rna_type_initialise(scene, rmptr, shader_type, False)
    
    