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

import os
import subprocess
import bpy
import re
import sys

from .util import init_env
from .util import get_path_list
from .util import path_list_convert
from .util import path_win_to_unixy
from .util import user_path
from .util import get_sequence_path

from .util import args_files_in_path



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


def sp_optionmenu_to_string(options):
    return [(opt.attrib['value'], opt.attrib['name'], 
            '') for opt in options.findall('string')]


# Custom socket type
class RendermanNodeSocket(bpy.types.NodeSocket):
    bl_idname = 'RendermanNodeSocket'
    bl_label = 'Renderman Node'

    default_value = None
    value = None
    ui_open = None
    is_array = False

    # Optional function for drawing the socket input value
    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label( text)
        else:
            layout.prop( self, "value", text = text)

    def draw_color( self, context, node):
        return (0.8, 0.8, 0.5, 1)

#some args have 1.0f, some dont.  Python doesn't know what to do!
def parse_float(fs):
    return float(fs[:-1]) if 'f' in fs else float(fs)


def class_generate_properties(node, parent_name, shaderparameters):
    prop_names = []
    prop_meta = {}

    for sp in shaderparameters:
        if sp.tag == 'page':
            sub_params = []
            #don't add the sub group to prop names, 
            #they'll be gotten through recursion
            for sub_param in sp.findall('param'):
                name,meta,prop = generate_property(sub_param)
                #another fix for sloppy args files
                if name == sp.attrib['name']:
                    name = name + '_prop'
                sub_params.append(name)
                prop_meta[name] = meta
                setattr(node, name, prop)
            prop_names.append(sp.attrib['name'])
            prop_meta[sp.attrib['name']] = {'renderman_type':'page'}
            setattr(node, sp.attrib['name'], sub_params)
            ui_label = "%s_ui_open" % sp.attrib['name']
            setattr(node, ui_label, bpy.props.BoolProperty(name=ui_label, 
                    default=True))
        else:
            name,meta,prop = generate_property(sp)
            prop_names.append(name)
            prop_meta[name] = meta
            setattr(node, name, prop)

    setattr(node, 'prop_names', prop_names)
    setattr(node, 'prop_meta', prop_meta)

#map args params to props
def generate_property(sp):
    options = {'ANIMATABLE'}
    param_name = sp.attrib['name']
    renderman_name = param_name
    #blender doesn't like names with __ but we save the 
    #"renderman_name with the real one"
    if param_name[0] == '_':
        param_name = param_name[1:]
    if param_name[0] == '_':
        param_name = param_name[1:]
    
    param_label = sp.attrib['label'] if 'label' in sp.attrib else param_name
    param_widget = sp.attrib['widget'].lower() if 'widget' in sp.attrib \
        else 'default'

    param_type = 'float' #for default. Some args files are sloppy
    if 'type' in sp.attrib:
        param_type = sp.attrib['type']
    param_help = ""
    param_default = sp.attrib['default'] if 'default' in sp.attrib else None
    
    prop_meta = sp.attrib
    renderman_type = param_type
    prop = None

    if 'coshaderPort' in prop_meta and prop_meta['coshaderPort'] == 'True':
        param_type = 'shader'

    #I guess multiline tooltips never worked
    for s in sp:
        if s.tag == 'help' and s.text:
            lines = s.text.split('\n')
            for line in lines:
                param_help = param_help + line.strip(' \t\n\r')
            
    if param_type == 'float':
        if 'arraySize' in sp.attrib.keys():
            param_default = tuple(float(f) for f in \
                sp.attrib['default'].split(','))
            prop = bpy.props.FloatVectorProperty(name=param_label, 
                        default=param_default, precision=3,
                        size=len(param_default),
                        description=param_help)

        else:
            param_default = parse_float(param_default)
            if param_widget == 'checkbox':
                prop = bpy.props.BoolProperty(name=param_label, 
                    default=bool(param_default), description=param_help)
                                                
            elif param_widget == 'mapper':
                prop = bpy.props.EnumProperty(name=param_label, 
                    items=sp_optionmenu_to_string(\
                        sp.find("hintdict[@name='options']")),
                    default=sp.attrib['default'],
                    description=param_help)
                
            else:
                param_min = parse_float(sp.attrib['min']) if 'min' \
                    in sp.attrib else sys.float_info.min
                param_max = parse_float(sp.attrib['max']) if 'max' \
                    in sp.attrib else sys.float_info.max
                param_min = parse_float(sp.attrib['slidermin']) if 'slidermin' \
                    in sp.attrib else param_min
                param_max = parse_float(sp.attrib['slidermax']) if 'slidermax' \
                    in sp.attrib else param_max
                prop = bpy.props.FloatProperty(name=param_label, 
                        default=param_default, precision=3,
                        min=param_min, max=param_max,
                        description=param_help)
        renderman_type = 'float'
            
    elif param_type == 'int' or param_type == 'integer':
        param_default = int(param_default) if param_default else 0
        if param_widget == 'checkbox':
            prop = bpy.props.BoolProperty(name=param_label, 
                default=bool(param_default), description=param_help)

                                            
        elif param_widget == 'mapper':
            prop = bpy.props.EnumProperty(name=param_label, 
                    items=sp_optionmenu_to_string(\
                            sp.find("hintdict[@name='options']")),
                            default=sp.attrib['default'],
                            description=param_help )
        else:
            param_min = int(sp.attrib['min']) if 'min' in sp.attrib else 0
            param_max = int(sp.attrib['max']) if 'max' in sp.attrib else 2**31-1
            prop = bpy.props.IntProperty(name=param_label, 
                    default=param_default, 
                    min=param_min,
                    max=param_max,
                    description=param_help)
        renderman_type = 'int'
            
    elif param_type == 'color':
        if param_default == 'null':
            param_default = '0 0 0'
        param_default = [float(c) for c in \
            param_default.replace(',', ' ').split()]
        prop = bpy.props.FloatVectorProperty(name=param_label, 
                                    default=param_default, size=3,
                                    subtype="COLOR",
                                    soft_min = 0.0, soft_max = 1.0,
                                    description=param_help)
        renderman_type = 'color'
    elif param_type == 'shader':
        param_default = ''
        prop = bpy.props.StringProperty(name=param_label, 
                            default=param_default, 
                            description=param_help)
        renderman_type = 'string'

    elif param_type == 'string' or param_type == 'struct':
        if param_default == None:
            param_default = ''
        #if '__' in param_name:
        #    param_name = param_name[2:]
        if param_widget == 'fileinput':
            prop = bpy.props.StringProperty(name=param_label, 
                            default=param_default, subtype="FILE_PATH",
                            description=param_help)
        elif param_widget == 'mapper':
            prop = bpy.props.EnumProperty(name=param_label, 
                    default=param_default, description=param_help, 
                    items=sp_optionmenu_to_string(\
                        sp.find("hintdict[@name='options']")))
        elif param_widget == 'popup':
            options = [(o, o, '') for o in sp.attrib['options'].split('|')]
            prop = bpy.props.EnumProperty(name=param_label, 
                    default=param_default, description=param_help, 
                    items=options)
        else:
            prop = bpy.props.StringProperty(name=param_label, 
                            default=param_default, 
                            description=param_help)
        renderman_type = param_type
                                    
    elif param_type == 'vector' or param_type == 'normal':
        if param_default == None:
            param_default = '0 0 0'
        param_default = [float(v) for v in param_default.split()]
        prop = bpy.props.FloatVectorProperty(name=param_label, 
                                    default=param_default, size=3,
                                    subtype="EULER",
                                    description=param_help)
        renderman_type = param_type
    elif param_type == 'int[2]':
        param_type = 'int'
        param_default = tuple(int(i) for i in sp.attrib['default'].split(','))
        is_array = 2
        prop = bpy.props.IntVectorProperty(name=param_label, 
                                    default=param_default, size=2,
                                    description=param_help)
        renderman_type = 'int'
        prop_meta['arraySize'] = 2
    
    prop_meta['renderman_type'] = renderman_type
    prop_meta['renderman_name'] = renderman_name
    return (param_name, prop_meta, prop)

#map types in args files to socket types
socket_map = {
    'float':'RendermanNodeSocketFloat',
    'color':'RendermanNodeSocketColor',
    'string':'RendermanNodeSocketString',
    'int':'RendermanNodeSocketInt', 
    'integer':'RendermanNodeSocketInt', 
    'struct':'RendermanNodeSocketStruct',
    'normal':'RendermanNodeSocketVector',
    'vector':'RendermanNodeSocketVector'
}

#add input sockets
def node_add_inputs(node, node_name, shaderparameters):
    for sp in shaderparameters:
        #if this is a page recursively add inputs
        if sp.tag == 'page':
            node_add_inputs(node, node_name, sp.findall('param'))
            continue
        #if this is not connectable don't add socket
        tags = sp.find('tags')
        if tags and tags.find('tag').attrib['value'] == "__nonconnection" or \
            ("connectable" in sp.attrib and \
                sp.attrib['connectable'].lower() == 'false'):
            continue

        param_type = 'float'
        if 'type' in sp.attrib.keys():
            param_type = sp.attrib['type']
        param_name = sp.attrib['name']
        socket = node.inputs.new(socket_map[param_type], param_name)
        socket.link_limit = 1
        
        #for struct type look for the type of connection
        if param_type == 'struct' and tags:
            tag = tags.findall('tag')[-1]
            if 'and' in tag.attrib['value']:
                socket.struct_type = tag.attrib['value'].split()[-1]
            else:
                socket.struct_type = tag.attrib['value']

#add output sockets
def node_add_outputs(node, shaderparameters):
    
    # Generate RNA properties for each shader parameter  
    for sp in shaderparameters:
        param_name = sp.attrib['name']
        tag = sp.find('*/tag')
        socket = node.outputs.new(socket_map[tag.attrib['value']], param_name)

        #for struct type look for the type of connection
        if tag.attrib['value'] == 'struct':
            socket.struct_type = sp.findall('*/tag')[-1].attrib['value']


    