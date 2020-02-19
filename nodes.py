# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 - 2017 Pixar
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
import _cycles
from bpy.app.handlers import persistent

import xml.etree.ElementTree as ET

import tempfile
import nodeitems_utils
import shutil
import subprocess

from bpy.props import *
from nodeitems_utils import NodeCategory, NodeItem

from .shader_parameters import class_generate_properties
from .shader_parameters import node_add_inputs
from .shader_parameters import node_add_outputs
from .shader_parameters import socket_map
from .shader_parameters import update_conditional_visops
from .util import args_files_in_path
from .util import get_path_list
from .util import rib
from .util import debug
from .util import user_path
from .util import get_real_path
from .util import readOSO
from .cycles_convert import *
from .rman_utils import texture_utils
from .rman_utils import filepath_utils
from .rman_utils import prefs_utils
from .rfb_logger import rfb_log
from .rman_bl_nodes import rman_bl_nodes_shaders

from operator import attrgetter, itemgetter
import os.path
from time import sleep
import traceback


NODE_LAYOUT_SPLIT = 0.5

# Generate dynamic types

def set_rix_param(params, param_type, param_name, val, is_reference=False):
    if is_reference:
        if param_type == "float":
            params.ReferenceFloat(param_name, val)
        elif param_type == "int":
            params.ReferenceInteger(param_name, val)
        elif param_type == "color":
            params.ReferenceColor(param_name, val)
        elif param_type == "point":
            params.ReferencePoint(param_name, val)            
        elif param_type == "vector":
            params.ReferenceVector(param_name, val)
        elif param_type == "normal":
            params.ReferenceNormal(param_name, val)             
    else:        
        if param_type == "float":
            params.SetFloat(param_name, val)
        elif param_type == "int":
            params.SetInteger(param_name, val)
        elif param_type == "color":
            params.SetColor(param_name, val)
        elif param_type == "string":
            params.SetString(param_name, val)
        elif param_type == "point":
            params.SetPoint(param_name, val)                            
        elif param_type == "vector":
            params.SetVector(param_name, val)
        elif param_type == "normal":
            params.SetNormal(param_name, val)


def generate_node_type(prefs, name, args):
    ''' Dynamically generate a node type from pattern '''

    nodeType = args.find("shaderType/tag").attrib['value']
    typename = '%s%sNode' % (name, nodeType.capitalize())
    nodeDict = {'bxdf': rman_bl_nodes_shaders.RendermanBxdfNode,
                'pattern': rman_bl_nodes_shaders.RendermanPatternNode,
                'displacement': rman_bl_nodes_shaders.RendermanDisplacementNode,
                'light': rman_bl_nodes_shaders.RendermanLightNode}
    if nodeType not in nodeDict.keys():
        return
    ntype = type(typename, (nodeDict[nodeType],), {})
    ntype.bl_label = name
    ntype.typename = typename

    inputs = [p for p in args.findall('./param')] + \
        [p for p in args.findall('./page')]
    outputs = [p for p in args.findall('.//output')]

    def init(self, context):
        if self.renderman_node_type == 'bxdf':
            self.outputs.new('RendermanShaderSocket', "Bxdf").type = 'SHADER'
            #socket_template = self.socket_templates.new(identifier='Bxdf', name='Bxdf', type='SHADER')
            node_add_inputs(self, name, self.prop_names)
            node_add_outputs(self)
            # if this is PxrLayerSurface set the diffusegain to 0.  The default
            # of 1 is unintuitive
            if self.plugin_name == 'PxrLayerSurface':
                self.diffuseGain = 0
        elif self.renderman_node_type == 'light':
            # only make a few sockets connectable
            node_add_inputs(self, name, self.prop_names)
            self.outputs.new('RendermanShaderSocket', "Light")
        elif self.renderman_node_type == 'displacement':
            # only make the color connectable
            self.outputs.new('RendermanShaderSocket', "Displacement")
            node_add_inputs(self, name, self.prop_names)
        # else pattern
        elif name == "PxrOSL":
            self.outputs.clear()
        else:
            node_add_inputs(self, name, self.prop_names)
            node_add_outputs(self)

        if name == "PxrRamp":
            node_group = bpy.data.node_groups.new(
                'PxrRamp_nodegroup', 'ShaderNodeTree')
            node_group.nodes.new('ShaderNodeValToRGB')
            node_group.use_fake_user = True
            self.node_group = node_group.name
        update_conditional_visops(self)


    def free(self):
        if name == "PxrRamp":
            bpy.data.node_groups.remove(bpy.data.node_groups[self.node_group])

    ntype.init = init
    ntype.free = free
    
    if "__annotations__" not in ntype.__dict__:
            setattr(ntype, "__annotations__", {})

    if name == 'PxrRamp':
        ntype.__annotations__['node_group'] = StringProperty('color_ramp', default='')

    ntype.__annotations__['plugin_name'] = StringProperty(name='Plugin Name',
                                       default=name, options={'HIDDEN'})
    # lights cant connect to a node tree in 20.0
    class_generate_properties(ntype, name, inputs + outputs)
    if nodeType == 'light':
        ntype.__annotations__['light_shading_rate'] = FloatProperty(
            name="Light Shading Rate",
            description="Shading Rate for this light.  \
                Leave this high unless detail is missing",
            default=100.0)
        ntype.__annotations__['light_primary_visibility'] = BoolProperty(
            name="Light Primary Visibility",
            description="Camera visibility for this light",
            default=True)

    bpy.utils.register_class(ntype)

    return typename, ntype


# UI
def find_node_input(node, name):
    for input in node.inputs:
        if input.name == name:
            return input

    return None


def find_node(material, nodetype):
    if material and material.node_tree:
        ntree = material.node_tree

        active_output_node = None
        for node in ntree.nodes:
            if getattr(node, "bl_idname", None) == nodetype:
                if getattr(node, "is_active_output", True):
                    return node
                if not active_output_node:
                    active_output_node = node
        return active_output_node

    return None


def find_node_input(node, name):
    for input in node.inputs:
        if input.name == name:
            return input

    return None


def panel_node_draw(layout, context, id_data, output_type, input_name):
    ntree = id_data.node_tree

    node = find_node(id_data, output_type)
    if not node:
        layout.label(text="No output node")
    else:
        input = find_node_input(node, input_name)
        #layout.template_node_view(ntree, node, input)
        draw_nodes_properties_ui(layout, context, ntree)

    return True


def is_renderman_nodetree(material):
    return find_node(material, 'RendermanOutputNode')


def draw_nodes_properties_ui(layout, context, nt, input_name='Bxdf',
                             output_node_type="output"):
    output_node = next((n for n in nt.nodes
                        if hasattr(n, 'renderman_node_type') and n.renderman_node_type == output_node_type), None)
    if output_node is None:
        return

    socket = output_node.inputs[input_name]
    node = socket_node_input(nt, socket)

    layout.context_pointer_set("nodetree", nt)
    layout.context_pointer_set("node", output_node)
    layout.context_pointer_set("socket", socket)

    split = layout.split(factor=0.35)
    split.label(text=socket.name + ':')

    if socket.is_linked:
        # for lights draw the shading rate ui.

        split.operator_menu_enum("node.add_%s" % input_name.lower(),
                                 "node_type", text=node.bl_label)
    else:
        split.operator_menu_enum("node.add_%s" % input_name.lower(),
                                 "node_type", text='None')

    if node is not None:
        draw_node_properties_recursive(layout, context, nt, node)


def socket_node_input(nt, socket):
    return next((l.from_node for l in nt.links if l.to_socket == socket), None)

def socket_socket_input(nt, socket):
    return next((l.from_socket for l in nt.links if l.to_socket == socket and socket.is_linked),
                None)


def linked_sockets(sockets):
    if sockets is None:
        return []
    return [i for i in sockets if i.is_linked]


def draw_node_properties_recursive(layout, context, nt, node, level=0):

    def indented_label(layout, label, level):
        for i in range(level):
            layout.label(text='', icon='BLANK1')
        if label:
            layout.label(text=label)

    layout.context_pointer_set("node", node)
    layout.context_pointer_set("nodetree", nt)

    def draw_props(prop_names, layout, level):
        for prop_name in prop_names:
            # skip showing the shape for PxrStdAreaLight
            if prop_name in ["lightGroup", "rman__Shape", "coneAngle", "penumbraAngle"]:
                continue

            if prop_name == "codetypeswitch":
                row = layout.row()
                if node.codetypeswitch == 'INT':
                    row.prop_search(node, "internalSearch",
                                    bpy.data, "texts", text="")
                elif node.codetypeswitch == 'EXT':
                    row.prop(node, "shadercode")
            elif prop_name == "internalSearch" or prop_name == "shadercode" or prop_name == "expression":
                pass
            else:
                prop_meta = node.prop_meta[prop_name]
                prop = getattr(node, prop_name)

                if 'widget' in prop_meta and prop_meta['widget'] == 'null' or \
                        'hidden' in prop_meta and prop_meta['hidden']:
                    continue

                # else check if the socket with this name is connected
                socket = node.inputs[prop_name] if prop_name in node.inputs \
                    else None
                layout.context_pointer_set("socket", socket)

                if socket and socket.is_linked:
                    input_node = socket_node_input(nt, socket)
                    icon = 'DISCLOSURE_TRI_DOWN' if socket.ui_open \
                        else 'DISCLOSURE_TRI_RIGHT'

                    split = layout.split(factor=NODE_LAYOUT_SPLIT)
                    row = split.row()
                    indented_label(row, None, level)
                    row.prop(socket, "ui_open", icon=icon, text='',
                             icon_only=True, emboss=False)
                    label = prop_meta.get('label', prop_name)
                    row.label(text=label + ':')
                    if ('type' in prop_meta and prop_meta['type'] == 'vstruct') or prop_name == 'inputMaterial':
                        split.operator_menu_enum("node.add_layer", "node_type",
                                                 text=input_node.bl_label, icon="LAYER_USED")
                    elif prop_meta['renderman_type'] == 'struct':
                        split.operator_menu_enum("node.add_manifold", "node_type",
                                                 text=input_node.bl_label, icon="LAYER_USED")
                    elif prop_meta['renderman_type'] == 'normal':
                        split.operator_menu_enum("node.add_bump", "node_type",
                                                 text=input_node.bl_label, icon="LAYER_USED")
                    else:
                        split.operator_menu_enum("node.add_pattern", "node_type",
                                                 text=input_node.bl_label, icon="LAYER_USED")

                    if socket.ui_open:
                        draw_node_properties_recursive(layout, context, nt,
                                                       input_node, level=level + 1)

                else:
                    row = layout.row(align=True)
                    if prop_meta['renderman_type'] == 'page':
                        ui_prop = prop_name + "_uio"
                        ui_open = getattr(node, ui_prop)
                        icon = 'DISCLOSURE_TRI_DOWN' if ui_open \
                            else 'DISCLOSURE_TRI_RIGHT'

                        split = layout.split(factor=NODE_LAYOUT_SPLIT)
                        row = split.row()
                        for i in range(level):
                            row.label(text='', icon='BLANK1')

                        row.prop(node, ui_prop, icon=icon, text='',
                                 icon_only=True, emboss=False)
                        sub_prop_names = list(prop)
                        if node.bl_idname in {"PxrSurfaceBxdfNode", "PxrLayerPatternNode"}:
                            for pn in sub_prop_names:
                                if pn.startswith('enable'):
                                    row.prop(node, pn, text='')
                                    sub_prop_names.remove(pn)
                                    break

                        row.label(text=prop_name.split('.')[-1] + ':')

                        if ui_open:
                            draw_props(sub_prop_names, layout, level + 1)

                    else:
                        indented_label(row, None, level)
                        # indented_label(row, socket.name+':')
                        # don't draw prop for struct type
                        if "Subset" in prop_name and prop_meta['type'] == 'string':
                            row.prop_search(node, prop_name, bpy.data.scenes[0].renderman,
                                            "object_groups")
                        else:
                            if prop_meta['renderman_type'] != 'struct':
                                row.prop(node, prop_name, slider=True)
                            else:
                                row.label(text=prop_meta['label'])
                        if prop_name in node.inputs:
                            if ('type' in prop_meta and prop_meta['type'] == 'vstruct') or prop_name == 'inputMaterial':
                                row.operator_menu_enum("node.add_layer", "node_type",
                                                       text='', icon="LAYER_USED")
                            elif prop_meta['renderman_type'] == 'struct':
                                row.operator_menu_enum("node.add_manifold", "node_type",
                                                       text='', icon="LAYER_USED")
                            elif prop_meta['renderman_type'] == 'normal':
                                row.operator_menu_enum("node.add_bump", "node_type",
                                                       text='', icon="LAYER_USED")
                            else:
                                row.operator_menu_enum("node.add_pattern", "node_type",
                                                       text='', icon="LAYER_USED")

    # if this is a cycles node do something different
    if not hasattr(node, 'plugin_name') or node.bl_idname == 'PxrOSLPatternNode':
        node.draw_buttons(context, layout)
        for input in node.inputs:
            if input.is_linked:
                input_node = socket_node_input(nt, input)
                icon = 'DISCLOSURE_TRI_DOWN' if input.show_expanded \
                    else 'DISCLOSURE_TRI_RIGHT'

                split = layout.split(factor=NODE_LAYOUT_SPLIT)
                row = split.row()
                indented_label(row, None, level)
                row.prop(input, "show_expanded", icon=icon, text='',
                         icon_only=True, emboss=False)
                row.label(text=input.name + ':')
                split.operator_menu_enum("node.add_pattern", "node_type",
                                         text=input_node.bl_label, icon="LAYER_USED")

                if input.show_expanded:
                    draw_node_properties_recursive(layout, context, nt,
                                                   input_node, level=level + 1)

            else:
                row = layout.row(align=True)
                indented_label(row, None, level)
                # indented_label(row, socket.name+':')
                # don't draw prop for struct type
                if input.hide_value:
                    row.label(text=input.name)
                else:
                    row.prop(input, 'default_value',
                             slider=True, text=input.name)
                row.operator_menu_enum("node.add_pattern", "node_type",
                                       text='', icon="LAYER_USED")
    else:
        if node.plugin_name == 'PxrRamp':
            dummy_nt = bpy.data.node_groups[node.node_group]
            if dummy_nt:
                layout.template_color_ramp(
                    dummy_nt.nodes['ColorRamp'], 'color_ramp')
        draw_props(node.prop_names, layout, level)
    layout.separator()


# Operators
# connect the pattern nodes in some sensible manner (color output to color input etc)
# TODO more robust
def link_node(nt, from_node, in_socket):
    out_socket = None
    # first look for resultF/resultRGB
    if type(in_socket).__name__ in ['RendermanNodeSocketColor',
                                    'RendermanNodeSocketVector']:
        out_socket = from_node.outputs.get('resultRGB',
                                           next((s for s in from_node.outputs
                                                 if type(s).__name__ == 'RendermanNodeSocketColor'), None))
    elif type(in_socket).__name__ == 'RendermanNodeSocketStruct':
        out_socket = from_node.outputs.get('pxrMaterialOut', None)
        if not out_socket:
            out_socket = from_node.outputs.get('result', None)

    else:
        out_socket = from_node.outputs.get('resultF',
                                           next((s for s in from_node.outputs
                                                 if type(s).__name__ == 'RendermanNodeSocketFloat'), None))

    if out_socket:
        nt.links.new(out_socket, in_socket)



# return if this param has a vstuct connection or linked independently


def is_vstruct_or_linked(node, param):
    meta = node.prop_meta[param]

    if 'vstructmember' not in meta.keys():
        return node.inputs[param].is_linked
    elif param in node.inputs and node.inputs[param].is_linked:
        return True
    else:
        vstruct_name, vstruct_member = meta['vstructmember'].split('.')
        if node.inputs[vstruct_name].is_linked:
            from_socket = node.inputs[vstruct_name].links[0].from_socket
            vstruct_from_param = "%s_%s" % (
                from_socket.identifier, vstruct_member)
            return vstruct_conditional(from_socket.node, vstruct_from_param)
        else:
            return False

# tells if this param has a vstuct connection that is linked and
# conditional met


def is_vstruct_and_linked(node, param):
    meta = node.prop_meta[param]

    if 'vstructmember' not in meta.keys():
        return False
    else:
        vstruct_name, vstruct_member = meta['vstructmember'].split('.')
        if node.inputs[vstruct_name].is_linked:
            from_socket = node.inputs[vstruct_name].links[0].from_socket
            # if coming from a shader group hookup across that
            if from_socket.node.bl_idname == 'ShaderNodeGroup':
                ng = from_socket.node.node_tree
                group_output = next((n for n in ng.nodes if n.bl_idname == 'NodeGroupOutput'),
                                    None)
                if group_output is None:
                    return False

                in_sock = group_output.inputs[from_socket.name]
                if len(in_sock.links):
                    from_socket = in_sock.links[0].from_socket
            vstruct_from_param = "%s_%s" % (
                from_socket.identifier, vstruct_member)
            return vstruct_conditional(from_socket.node, vstruct_from_param)
        else:
            return False

# gets the value for a node walking up the vstruct chain


def get_val_vstruct(node, param):
    if param in node.inputs and node.inputs[param].is_linked:
        from_socket = node.inputs[param].links[0].from_socket
        return get_val_vstruct(from_socket.node, from_socket.identifier)
    elif is_vstruct_and_linked(node, param):
        return True
    else:
        return getattr(node, param)

# parse a vstruct conditional string and return true or false if should link


def vstruct_conditional(node, param):
    if not hasattr(node, 'shader_meta') and not hasattr(node, 'output_meta'):
        return False
    meta = getattr(
        node, 'shader_meta') if node.bl_idname == "PxrOSLPatternNode" else node.output_meta
    if param not in meta:
        return False
    meta = meta[param]
    if 'vstructConditionalExpr' not in meta.keys():
        return True

    expr = meta['vstructConditionalExpr']
    expr = expr.replace('connect if ', '')
    set_zero = False
    if ' else set 0' in expr:
        expr = expr.replace(' else set 0', '')
        set_zero = True

    tokens = expr.split()
    new_tokens = []
    i = 0
    num_tokens = len(tokens)
    while i < num_tokens:
        token = tokens[i]
        prepend, append = '', ''
        while token[0] == '(':
            token = token[1:]
            prepend += '('
        while token[-1] == ')':
            token = token[:-1]
            append += ')'

        if token == 'set':
            i += 1
            continue

        # is connected change this to node.inputs.is_linked
        if i < num_tokens - 2 and tokens[i + 1] == 'is'\
                and 'connected' in tokens[i + 2]:
            token = "is_vstruct_or_linked(node, '%s')" % token
            last_token = tokens[i + 2]
            while last_token[-1] == ')':
                last_token = last_token[:-1]
                append += ')'
            i += 3
        else:
            i += 1
        if hasattr(node, token):
            token = "get_val_vstruct(node, '%s')" % token

        new_tokens.append(prepend + token + append)

    if 'if' in new_tokens and 'else' not in new_tokens:
        new_tokens.extend(['else', 'False'])
    return eval(" ".join(new_tokens))

# Rib export

gains_to_enable = {
    'diffuseGain': 'enableDiffuse',
    'specularFaceColor': 'enablePrimarySpecular',
    'specularEdgeColor': 'enablePrimarySpecular',
    'roughSpecularFaceColor': 'enableRoughSpecular',
    'roughSpecularEdgeColor': 'enableRoughSpecular',
    'clearcoatFaceColor': 'enableClearCoat',
    'clearcoatEdgeColor': 'enableClearCoat',
    'iridescenceFaceGain': 'enableIridescence',
    'iridescenceEdgeGain': 'enableIridescence',
    'fuzzGain': 'enableFuzz',
    'subsurfaceGain': 'enableSubsurface',
    'singlescatterGain': 'enableSingleScatter',
    'singlescatterDirectGain': 'enableSingleScatter',
    'refractionGain': 'enableGlass',
    'reflectionGain': 'enableGlass',
    'glowGain': 'enableGlow',
}

# generate param list

# generate rixparam list
def gen_rixparams(node, params, mat_name=None):
    # If node is OSL node get properties from dynamic location.
    if node.bl_idname == "PxrOSLPatternNode":

        if getattr(node, "codetypeswitch") == "EXT":
            prefs = bpy.context.preferences.addons[__package__].preferences
            osl_path = user_path(getattr(node, 'shadercode'))
            FileName = os.path.basename(osl_path)
            FileNameNoEXT,ext = os.path.splitext(FileName)
            out_file = os.path.join(
                user_path(prefs.env_vars.out), "shaders", FileName)
            if ext == ".oso":
                if not os.path.exists(out_file) or not os.path.samefile(osl_path, out_file):
                    if not os.path.exists(os.path.join(user_path(prefs.env_vars.out), "shaders")):
                        os.mkdir(os.path.join(user_path(prefs.env_vars.out), "shaders"))
                    shutil.copy(osl_path, out_file)
        for input_name, input in node.inputs.items():
            prop_type = input.renderman_type
            if input.is_linked:
                to_socket = input
                from_socket = input.links[0].from_socket

                param_type = prop_type
                param_name = input_name

                val = get_output_param_str(from_socket.node, mat_name, from_socket, to_socket)

                set_rix_param(params, param_type, param_name, val, is_reference=True)    

            elif type(input) != RendermanNodeSocketStruct:

                param_type = prop_type
                param_name = input_name
                val = rib(input.default_value, type_hint=prop_type)
                set_rix_param(params, param_type, param_name, val, is_reference=False)                


    # Special case for SeExpr Nodes. Assume that the code will be in a file so
    # that needs to be extracted.
    elif node.bl_idname == "PxrSeExprPatternNode":
        fileInputType = node.codetypeswitch

        for prop_name, meta in node.prop_meta.items():
            if prop_name in ["codetypeswitch", 'filename']:
                pass
            elif prop_name == "internalSearch" and fileInputType == 'INT':
                if node.internalSearch != "":
                    script = bpy.data.texts[node.internalSearch]
                    params.SetString("expression", script.as_string() )
            elif prop_name == "shadercode" and fileInputType == "NODE":
                params.SetString("expression", node.expression)
            else:
                prop = getattr(node, prop_name)
                # if input socket is linked reference that
                if prop_name in node.inputs and \
                        node.inputs[prop_name].is_linked:

                    to_socket = node.inputs[prop_name]
                    from_socket = to_socket.links[0].from_socket
                    from_node = to_socket.links[0].from_node

                    param_type = meta['renderman_type']
                    param_name = meta['renderman_name']

                    val = get_output_param_str(
                            from_socket.node, mat_name, from_socket, to_socket)

                    set_rix_param(params, param_type, param_name, val, is_reference=True)                            
                else:

                    param_type = meta['renderman_type']
                    param_name = meta['renderman_name']

                    val = rib(prop, type_hint=meta['renderman_type'])
                    set_rix_param(params, param_type, param_name, val, is_reference=False)                          

    else:

        for prop_name, meta in node.prop_meta.items():

            if node.plugin_name == 'PxrRamp' and prop_name in ['colors', 'positions']:
                pass

            elif(prop_name in ['sblur', 'tblur', 'notes']):
                pass

            else:
                prop = getattr(node, prop_name)
                # if property group recurse
                if meta['renderman_type'] == 'page':
                    continue
                elif prop_name == 'inputMaterial' or \
                        ('type' in meta and meta['type'] == 'vstruct'):
                    continue

                # if input socket is linked reference that
                elif hasattr(node, 'inputs') and prop_name in node.inputs and \
                        node.inputs[prop_name].is_linked:

                    to_socket = node.inputs[prop_name]
                    from_socket = to_socket.links[0].from_socket
                    from_node = to_socket.links[0].from_node

                    param_type = meta['renderman_type']
                    param_name = meta['renderman_name']

                    if 'arraySize' in meta:
                        pass
                    else:
                        val = get_output_param_str(
                                from_node, mat_name, from_socket, to_socket)

                        set_rix_param(params, param_type, param_name, val, is_reference=True)
                       

                # see if vstruct linked
                elif is_vstruct_and_linked(node, prop_name):
                    vstruct_name, vstruct_member = meta[
                        'vstructmember'].split('.')
                    from_socket = node.inputs[
                        vstruct_name].links[0].from_socket

                    temp_mat_name = mat_name

                    if from_socket.node.bl_idname == 'ShaderNodeGroup':
                        ng = from_socket.node.node_tree
                        group_output = next((n for n in ng.nodes if n.bl_idname == 'NodeGroupOutput'),
                                            None)
                        if group_output is None:
                            return False

                        in_sock = group_output.inputs[from_socket.name]
                        if len(in_sock.links):
                            from_socket = in_sock.links[0].from_socket
                            temp_mat_name = mat_name + '.' + from_socket.node.name

                    vstruct_from_param = "%s_%s" % (
                        from_socket.identifier, vstruct_member)
                    if vstruct_from_param in from_socket.node.output_meta:
                        actual_socket = from_socket.node.output_meta[
                            vstruct_from_param]

                        param_type = meta['renderman_type']
                        param_name = meta['renderman_name']

                        node_meta = getattr(
                            node, 'shader_meta') if node.bl_idname == "PxrOSLPatternNode" else node.output_meta                        
                        node_meta = node_meta.get(vstruct_from_param)
                        is_reference = True
                        val = get_output_param_str(
                               from_socket.node, temp_mat_name, actual_socket)
                        if node_meta:
                            expr = node_meta.get('vstructConditionalExpr')
                            # check if we should connect or just set a value
                            if expr:
                                if expr.split(' ')[0] == 'set':
                                    val = 1
                                    is_reference = False                        
                        set_rix_param(params, param_type, param_name, val, is_reference=is_reference)

                    else:
                        print('Warning! %s not found on %s' %
                              (vstruct_from_param, from_socket.node.name))

                # else output rib
                else:
                    # if struct is not linked continue
                    if meta['renderman_type'] in ['struct', 'enum']:
                        continue

                    param_type = meta['renderman_type']
                    param_name = meta['renderman_name']
                    val = None
                    isArray = False
                    arrayLen = 0

                    # if this is a gain on PxrSurface and the lobe isn't
                    # enabled
                    if node.bl_idname == 'PxrSurfaceBxdfNode' and \
                            prop_name in gains_to_enable and \
                            not getattr(node, gains_to_enable[prop_name]):
                        val = [0, 0, 0] if meta[
                            'renderman_type'] == 'color' else 0
                        #params['%s %s' % (meta['renderman_type'],
                        #                  meta['renderman_name'])] = val

                        

                    elif 'options' in meta and meta['options'] == 'texture' \
                            and node.bl_idname != "PxrPtexturePatternNode" or \
                            ('widget' in meta and meta['widget'] == 'assetIdInput' and prop_name != 'iesProfile'):

                        val = rib(texture_utils.get_tex_file_name(prop), type_hint=meta['renderman_type'])
                    elif 'arraySize' in meta:
                        isArray = True
                        if type(prop) == int:
                            prop = [prop]

                        val = rib(prop)
                        arrayLen = len(prop)
                    else:

                        val = rib(prop, type_hint=meta['renderman_type'])

                    if isArray:
                        pass
                    else:
                        set_rix_param(params, param_type, param_name, val, is_reference=False)                       

    if node.plugin_name == 'PxrRamp':
        nt = bpy.data.node_groups[node.node_group]
        if nt:
            dummy_ramp = nt.nodes['ColorRamp']
            colors = []
            positions = []
            # double the start and end points
            positions.append(float(dummy_ramp.color_ramp.elements[0].position))
            colors.extend(dummy_ramp.color_ramp.elements[0].color[:3])
            for e in dummy_ramp.color_ramp.elements:
                positions.append(float(e.position))
                colors.extend(e.color[:3])
            positions.append(
                float(dummy_ramp.color_ramp.elements[-1].position))
            colors.extend(dummy_ramp.color_ramp.elements[-1].color[:3])

            params.SetFloatArray("colorRamp_Knots", positions, len(positions))
            params.SetColorArray("colorRamp_Colors", colors, len(positions))

            rman_interp_map = { 'LINEAR': 'linear', 'CONSTANT': 'constant'}
            interp = rman_interp_map.get(dummy_ramp.color_ramp.interpolation,'catmull-rom')
            params.SetString("colorRamp_Interpolation", interp )
    return params

def create_rman_surface(nt, parent_node, input_index, node_type="PxrSurfaceBxdfNode"):
    layer = nt.nodes.new(node_type)
    nt.links.new(layer.outputs[0], parent_node.inputs[input_index])
    setattr(layer, 'enableDiffuse', False)

    layer.location = parent_node.location
    layer.diffuseGain = 0
    layer.location[0] -= 300
    return layer

combine_nodes = ['ShaderNodeAddShader', 'ShaderNodeMixShader']

# rman_parent could be PxrSurface or PxrMixer


def convert_cycles_bsdf(nt, rman_parent, node, input_index):

    # if mix or add pass both to parent
    if node.bl_idname in combine_nodes:
        i = 0 if node.bl_idname == 'ShaderNodeAddShader' else 1

        node1 = node.inputs[
            0 + i].links[0].from_node if node.inputs[0 + i].is_linked else None
        node2 = node.inputs[
            1 + i].links[0].from_node if node.inputs[1 + i].is_linked else None

        if not node1 and not node2:
            return
        elif not node1:
            convert_cycles_bsdf(nt, rman_parent, node2, input_index)
        elif not node2:
            convert_cycles_bsdf(nt, rman_parent, node1, input_index)

        # if ones a combiner or they're of the same type and not glossy we need
        # to make a mixer
        elif node.bl_idname == 'ShaderNodeMixShader' or node1.bl_idname in combine_nodes \
                or node2.bl_idname in combine_nodes or \
                node1.bl_idname == 'ShaderNodeGroup' or node2.bl_idname == 'ShaderNodeGroup' \
                or (bsdf_map[node1.bl_idname][0] == bsdf_map[node2.bl_idname][0]):
            mixer = nt.nodes.new('PxrLayerMixerPatternNode')
            # if parent is output make a pxr surface first
            nt.links.new(mixer.outputs["pxrMaterialOut"],
                         rman_parent.inputs[input_index])
            offset_node_location(rman_parent, mixer, node)

            # set the layer masks
            if node.bl_idname == 'ShaderNodeAddShader':
                mixer.layer1Mask = .5
            else:
                convert_cycles_input(
                    nt, node.inputs['Fac'], mixer, 'layer1Mask')

            # make a new node for each
            convert_cycles_bsdf(nt, mixer, node1, 0)
            convert_cycles_bsdf(nt, mixer, node2, 1)

        # this is a heterogenous mix of add
        else:
            if rman_parent.plugin_name == 'PxrLayerMixer':
                old_parent = rman_parent
                rman_parent = create_rman_surface(nt, rman_parent, input_index,
                                                  'PxrLayerPatternNode')
                offset_node_location(old_parent, rman_parent, node)
            convert_cycles_bsdf(nt, rman_parent, node1, 0)
            convert_cycles_bsdf(nt, rman_parent, node2, 1)

    # else set lobe on parent
    elif 'Bsdf' in node.bl_idname or node.bl_idname == 'ShaderNodeSubsurfaceScattering':
        if rman_parent.plugin_name == 'PxrLayerMixer':
            old_parent = rman_parent
            rman_parent = create_rman_surface(nt, rman_parent, input_index,
                                              'PxrLayerPatternNode')
            offset_node_location(old_parent, rman_parent, node)

        node_type = node.bl_idname
        bsdf_map[node_type][1](nt, node, rman_parent)
    # if we find an emission node, naively make it a meshlight
    # note this will only make the last emission node the light
    elif node.bl_idname == 'ShaderNodeEmission':
        output = next((n for n in nt.nodes if hasattr(n, 'renderman_node_type') and
                       n.renderman_node_type == 'output'),
                      None)
        meshlight = nt.nodes.new("PxrMeshLightLightNode")
        nt.links.new(meshlight.outputs[0], output.inputs["Light"])
        meshlight.location = output.location
        meshlight.location[0] -= 300
        convert_cycles_input(
            nt, node.inputs['Strength'], meshlight, "intensity")
        if node.inputs['Color'].is_linked:
            convert_cycles_input(
                nt, node.inputs['Color'], meshlight, "textureColor")
        else:
            setattr(meshlight, 'lightColor', node.inputs[
                    'Color'].default_value[:3])

    else:
        rman_node = convert_cycles_node(nt, node)
        nt.links.new(rman_node.outputs[0], rman_parent.inputs[input_index])


def convert_cycles_displacement(nt, surface_node, displace_socket):
    # for now just do bump
    if displace_socket.is_linked:
        bump = nt.nodes.new("PxrBumpPatternNode")
        nt.links.new(bump.outputs[0], surface_node.inputs['bumpNormal'])
        bump.location = surface_node.location
        bump.location[0] -= 200
        bump.location[1] -= 100

        convert_cycles_input(nt, displace_socket, bump, "inputBump")

    # return
    # if displace_socket.is_linked:
    #    displace = nt.nodes.new("PxrDisplaceDisplacementNode")
    #    nt.links.new(displace.outputs[0], output_node.inputs['Displacement'])
    #    displace.location = output_node.location
    #    displace.location[0] -= 200
    #    displace.location[1] -= 100

    #    setattr(displace, 'dispAmount', .01)
    #    convert_cycles_input(nt, displace_socket, displace, "dispScalar")


# could make this more robust to shift the entire nodetree to below the
# bounds of the cycles nodetree
def set_ouput_node_location(nt, output_node, cycles_output):
    output_node.location = cycles_output.location
    output_node.location[1] -= 500


def offset_node_location(rman_parent, rman_node, cycles_node):
    linked_socket = next((sock for sock in cycles_node.outputs if sock.is_linked),
                         None)
    rman_node.location = rman_parent.location
    if linked_socket:
        rman_node.location += (cycles_node.location -
                               linked_socket.links[0].to_node.location)


def convert_cycles_nodetree(id, output_node, reporter):
    # find base node
    from . import cycles_convert
    cycles_convert.converted_nodes = {}
    nt = id.node_tree
    reporter({'INFO'}, 'Converting material ' + id.name + ' to RenderMan')
    cycles_output_node = find_node(id, 'ShaderNodeOutputMaterial')
    if not cycles_output_node:
        reporter({'WARNING'}, 'No Cycles output found ' + id.name)
        return False

    # if no bsdf return false
    if not cycles_output_node.inputs[0].is_linked:
        reporter({'WARNING'}, 'No Cycles bsdf found ' + id.name)
        return False

    # set the output node location
    set_ouput_node_location(nt, output_node, cycles_output_node)

    # walk tree
    cycles_convert.report = reporter
    begin_cycles_node = cycles_output_node.inputs[0].links[0].from_node
    # if this is an emission use PxrLightEmission
    if begin_cycles_node.bl_idname == "ShaderNodeEmission":
        meshlight = nt.nodes.new("PxrMeshLightLightNode")
        nt.links.new(meshlight.outputs[0], output_node.inputs["Light"])
        offset_node_location(output_node, meshlight, begin_cycles_node)
        convert_cycles_input(nt, begin_cycles_node.inputs[
                             'Strength'], meshlight, "intensity")
        if begin_cycles_node.inputs['Color'].is_linked:
            convert_cycles_input(nt, begin_cycles_node.inputs[
                                 'Color'], meshlight, "textureColor")
        else:
            setattr(meshlight, 'lightColor', begin_cycles_node.inputs[
                    'Color'].default_value[:3])
        bxdf = nt.nodes.new('PxrBlackBxdfNode')
        nt.links.new(bxdf.outputs[0], output_node.inputs["Bxdf"])
    else:
        base_surface = create_rman_surface(nt, output_node, 0)
        offset_node_location(output_node, base_surface, begin_cycles_node)
        convert_cycles_bsdf(nt, base_surface, begin_cycles_node, 0)
        convert_cycles_displacement(
            nt, base_surface, cycles_output_node.inputs[2])
    return True

cycles_node_map = {
    'ShaderNodeAttribute': 'node_attribute',
    'ShaderNodeBlackbody': 'node_checker_blackbody',
    'ShaderNodeTexBrick': 'node_brick_texture',
    'ShaderNodeBrightContrast': 'node_brightness',
    'ShaderNodeTexChecker': 'node_checker_texture',
    'ShaderNodeBump': 'node_bump',
    'ShaderNodeCameraData': 'node_camera',
    'ShaderNodeTexChecker': 'node_checker_texture',
    'ShaderNodeCombineHSV': 'node_combine_hsv',
    'ShaderNodeCombineRGB': 'node_combine_rgb',
    'ShaderNodeCombineXYZ': 'node_combine_xyz',
    'ShaderNodeTexEnvironment': 'node_environment_texture',
    'ShaderNodeFresnel': 'node_fresnel',
    'ShaderNodeGamma': 'node_gamma',
    'ShaderNodeNewGeometry': 'node_geometry',
    'ShaderNodeTexGradient': 'node_gradient_texture',
    'ShaderNodeHairInfo': 'node_hair_info',
    'ShaderNodeInvert': 'node_invert',
    'ShaderNodeHueSaturation': 'node_hsv',
    'ShaderNodeTexImage': 'node_image_texture',
    'ShaderNodeHueSaturation': 'node_hsv',
    'ShaderNodeLayerWeight': 'node_layer_weight',
    'ShaderNodeLightFalloff': 'node_light_falloff',
    'ShaderNodeLightPath': 'node_light_path',
    'ShaderNodeTexMagic': 'node_magic_texture',
    'ShaderNodeMapping': 'node_mapping',
    'ShaderNodeMath': 'node_math',
    'ShaderNodeMixRGB': 'node_mix',
    'ShaderNodeTexMusgrave': 'node_musgrave_texture',
    'ShaderNodeTexNoise': 'node_noise_texture',
    'ShaderNodeNormal': 'node_normal',
    'ShaderNodeNormalMap': 'node_normal_map',
    'ShaderNodeObjectInfo': 'node_object_info',
    'ShaderNodeParticleInfo': 'node_particle_info',
    'ShaderNodeRGBCurve': 'node_rgb_curves',
    'ShaderNodeValToRGB': 'node_rgb_ramp',
    'ShaderNodeSeparateHSV': 'node_separate_hsv',
    'ShaderNodeSeparateRGB': 'node_separate_rgb',
    'ShaderNodeSeparateXYZ': 'node_separate_xyz',
    'ShaderNodeTexSky': 'node_sky_texture',
    'ShaderNodeTangent': 'node_tangent',
    'ShaderNodeTexCoord': 'node_texture_coordinate',
    'ShaderNodeUVMap': 'node_uv_map',
    'ShaderNodeValue': 'node_value',
    'ShaderNodeVectorCurves': 'node_vector_curves',
    'ShaderNodeVectorMath': 'node_vector_math',
    'ShaderNodeVectorTransform': 'node_vector_transform',
    'ShaderNodeTexVoronoi': 'node_voronoi_texture',
    'ShaderNodeTexWave': 'node_wave_texture',
    'ShaderNodeWavelength': 'node_wavelength',
    'ShaderNodeWireframe': 'node_wireframe',
}

def get_mat_name(mat_name):
    return mat_name.replace(' ', '')

def get_node_name(node, mat_name):
    return "%s.%s" % (mat_name, node.name.replace(' ', ''))


def get_socket_name(node, socket):
    if type(socket) == dict:
        return socket['name'].replace(' ', '')
    # if this is a renderman node we can just use the socket name,
    else:
        if not hasattr('node', 'plugin_name'):
            if socket.name in node.inputs and socket.name in node.outputs:
                suffix = 'Out' if socket.is_output else 'In'
                return socket.name.replace(' ', '') + suffix
        return socket.identifier.replace(' ', '')


def get_socket_type(node, socket):
    sock_type = socket.type.lower()
    if sock_type == 'rgba':
        return 'color'
    elif sock_type == 'value':
        return 'float'
    elif sock_type == 'vector':
        return 'point'
    else:
        return sock_type

# do we need to convert this socket?


def do_convert_socket(from_socket, to_socket):
    if not to_socket:
        return False
    return (is_float_type(from_socket) and is_float3_type(to_socket)) or \
        (is_float3_type(from_socket) and is_float_type(to_socket))


def build_output_param_str(mat_name, from_node, from_socket, convert_socket=False):
    from_node_name = get_node_name(from_node, mat_name)
    from_sock_name = get_socket_name(from_node, from_socket)

    # replace with the convert node's output
    if convert_socket:
        if is_float_type(from_socket):
            return "convert_%s.%s:resultRGB" % (from_node_name, from_sock_name)
        else:
            return "convert_%s.%s:resultF" % (from_node_name, from_sock_name)

    else:
        return "%s:%s" % (from_node_name, from_sock_name)


def get_output_param_str(node, mat_name, socket, to_socket=None):
    # if this is a node group, hook it up to the input node inside!
    if node.bl_idname == 'ShaderNodeGroup':
        ng = node.node_tree
        group_output = next((n for n in ng.nodes if n.bl_idname == 'NodeGroupOutput'),
                            None)
        if group_output is None:
            return "error:error"

        in_sock = group_output.inputs[socket.name]
        if len(in_sock.links):
            link = in_sock.links[0]
            return build_output_param_str(mat_name + '.' + node.name, link.from_node, link.from_socket, do_convert_socket(link.from_socket, to_socket))
        else:
            return "error:error"
    if node.bl_idname == 'NodeGroupInput':
        global current_group_node

        if current_group_node is None:
            return "error:error"

        in_sock = current_group_node.inputs[socket.name]
        if len(in_sock.links):
            link = in_sock.links[0]
            return build_output_param_str(mat_name, link.from_node, link.from_socket, do_convert_socket(link.from_socket, to_socket))
        else:
            return "error:error"

    return build_output_param_str(mat_name, node, socket, do_convert_socket(socket, to_socket))

# hack!!!
current_group_node = None

def translate_node_group(sg_scene, rman, group_node, mat_name):
    ng = group_node.node_tree
    out = next((n for n in ng.nodes if n.bl_idname == 'NodeGroupOutput'),
               None)
    if out is None:
        return

    nodes_to_export = gather_nodes(out)
    global current_group_node
    current_group_node = group_node
    sg_nodes = []
    for node in nodes_to_export:
        sg_nodes += shader_node_sg(sg_scene, rman, node, mat_name=(mat_name + '.' + group_node.name))
    current_group_node = None
    return sg_nodes


def translate_cycles_node(sg_scene, rman, node, mat_name):
    if node.bl_idname == 'ShaderNodeGroup':
        return translate_node_group(sg_scene, rman, node, mat_name)

    if node.bl_idname not in cycles_node_map.keys():
        print('No translation for node of type %s named %s' %
              (node.bl_idname, node.name))
        return []

    mapping = cycles_node_map[node.bl_idname]
    #params = {}

    sg_node = rman.SGManager.RixSGShader("Pattern", mapping, get_node_name(node, mat_name))
    params = sg_node.params      
      
    for in_name, input in node.inputs.items():
        param_name = "%s" % get_socket_name(node, input)
        param_type = "%s" % get_socket_type(node, input)
        if input.is_linked:
            link = input.links[0]
            val = get_output_param_str(
                link.from_node, mat_name, link.from_socket, input)

            set_rix_param(params, param_type, param_name, val, is_reference=True)                

        else:
            val = rib(input.default_value,
                            type_hint=get_socket_type(node, input))
            # skip if this is a vector set to 0 0 0
            if input.type == 'VECTOR' and val == [0.0, 0.0, 0.0]:
                continue

            set_rix_param(params, param_type, param_name, val, is_reference=False)

    ramp_size = 256
    if node.bl_idname == 'ShaderNodeValToRGB':
        colors = []
        alphas = []

        for i in range(ramp_size):
            c = node.color_ramp.evaluate(float(i) / (ramp_size - 1.0))
            colors.extend(c[:3])
            alphas.append(c[3])

        params.SetColorArray('ramp_color', colors, ramp_size)
        params.SetFloatArray('ramp_alpha', alphas, ramp_size)

    elif node.bl_idname == 'ShaderNodeVectorCurve':
        colors = []
        node.mapping.initialize()
        r = node.mapping.curves[0]
        g = node.mapping.curves[1]
        b = node.mapping.curves[2]

        for i in range(ramp_size):
            v = float(i) / (ramp_size - 1.0)
            colors.extend([r.evaluate(v), g.evaluate(v), b.evaluate(v)])

        params.SetColorArray('ramp', colors, ramp_size)

    elif node.bl_idname == 'ShaderNodeRGBCurve':
        colors = []
        node.mapping.initialize()
        c = node.mapping.curves[0]
        r = node.mapping.curves[1]
        g = node.mapping.curves[2]
        b = node.mapping.curves[3]

        for i in range(ramp_size):
            v = float(i) / (ramp_size - 1.0)
            c_val = c.evaluate(v)
            colors.extend([r.evaluate(v) * c_val, g.evaluate(v)
                           * c_val, b.evaluate(v) * c_val])


        params.SetColorArray('ramp', colors, ramp_size)

    #print('doing %s %s' % (node.bl_idname, node.name))
    # print(params)
 
    return [sg_node]

# convert shader node to RixSceneGraph node
def shader_node_sg(sg_scene, rman, node, mat_name, portal=False):
    # this is tuple telling us to convert
    sg_node = None

    if type(node) == type(()):
        shader, from_node, from_socket = node
        input_type = 'float' if shader == 'PxrToFloat3' else 'color'
        node_name = 'convert_%s.%s' % (get_node_name(
            from_node, mat_name), get_socket_name(from_node, from_socket))
        if from_node.bl_idname == 'ShaderNodeGroup':
            node_name = 'convert_' + get_output_param_str(
                from_node, mat_name, from_socket).replace(':', '.')
                
        val = get_output_param_str(from_node, mat_name, from_socket)
        sg_node = rman.SGManager.RixSGShader("Pattern", shader, node_name)
        rix_params = sg_node.params       
        if input_type == 'color':
            rix_params.ReferenceColor('input', val)
        else:
            rix_params.ReferenceFloat('input', val)            
                
        return [sg_node]
    elif not hasattr(node, 'renderman_node_type'):
   
        return translate_cycles_node(sg_scene, rman, node, mat_name)

    instance = mat_name + '.' + node.name

    if not hasattr(node, 'renderman_node_type'):
        return

    if node.renderman_node_type == "pattern":
        if node.bl_label == 'PxrOSL':
            shader = node.shadercode #node.plugin_name
            if shader:
                sg_node = rman.SGManager.RixSGShader("Pattern", shader, instance)
                
        else:
            sg_node = rman.SGManager.RixSGShader("Pattern", node.bl_label, instance)
    elif node.renderman_node_type == "light":
        light_group_name = ''
        scene = bpy.context.scene
        for lg in scene.renderman.light_groups:
            if mat_name in lg.members.keys():
                light_group_name = lg.name
                break

        light_name = node.bl_label
        sg_node = rman.SGManager.RixSGShader("Light", node.bl_label, mat_name)

    elif node.renderman_node_type == "lightfilter":
        #params['__instanceid'] = mat_name

        light_name = node.bl_label
    elif node.renderman_node_type == "displacement":
        sg_node = rman.SGManager.RixSGShader("Displacement", node.bl_label, instance)
    else:
        sg_node = rman.SGManager.RixSGShader("Bxdf", node.bl_label, instance)        

    if sg_node:
        rix_params = sg_node.params       
        rix_params = gen_rixparams(node, rix_params, mat_name)

    return [sg_node]


def replace_frame_num(prop):
    frame_num = bpy.data.scenes[0].frame_current
    prop = prop.replace('$f4', str(frame_num).zfill(4))
    prop = prop.replace('$F4', str(frame_num).zfill(4))
    prop = prop.replace('$f3', str(frame_num).zfill(3))
    prop = prop.replace('$F3', str(frame_num).zfill(3))
    return prop

# return the output file name if this texture is to be txmade.


def get_tex_file_name(prop):
    prop = replace_frame_num(prop)
    filename,ext = os.path.splitext(prop)
    if ext == '.tex':
        return prop

    prop = bpy.path.basename(prop)
    part = prop.rpartition('.')
    prop = part[0]
    if prop != '' and part[2].lower() != 'tex':
        _p_ = bpy.context.scene.renderman.path_texture_output
        #
        # just in case there is a leading path separator
        #
        _s_ = "" if _p_.endswith("/") or _p_.endswith("\\") else "/"
        _f_ = "{}{}{}{}".format(_p_, _s_, prop, ".tex")
        return user_path(_f_)
    else:
        return prop


def is_same_type(socket1, socket2):
    return (type(socket1) == type(socket2)) or (is_float_type(socket1) and is_float_type(socket2)) or \
        (is_float3_type(socket1) and is_float3_type(socket2))


def is_float_type(socket):
    # this is a renderman node
    if type(socket) == type({}):
        return socket['renderman_type'] in ['int', 'float']
    elif hasattr(socket.node, 'plugin_name'):
        prop_meta = getattr(socket.node, 'output_meta', [
        ]) if socket.is_output else getattr(socket.node, 'prop_meta', [])
        if socket.name in prop_meta:
            return prop_meta[socket.name]['renderman_type'] in ['int', 'float']

    else:
        return socket.type in ['INT', 'VALUE']


def is_float3_type(socket):
    # this is a renderman node
    if type(socket) == type({}):
        return socket['renderman_type'] in ['int', 'float']
    elif hasattr(socket.node, 'plugin_name'):
        prop_meta = getattr(socket.node, 'output_meta', [
        ]) if socket.is_output else getattr(socket.node, 'prop_meta', [])
        if socket.name in prop_meta:
            return prop_meta[socket.name]['renderman_type'] in ['color', 'vector', 'normal']
    else:
        return socket.type in ['RGBA', 'VECTOR']

# walk the tree for nodes to export


def gather_nodes(node):
    nodes = []
    for socket in node.inputs:
        if socket.is_linked:
            link = socket.links[0]
            for sub_node in gather_nodes(socket.links[0].from_node):
                if sub_node not in nodes:
                    nodes.append(sub_node)

            # if this is a float -> color inset a tofloat3
            if is_float_type(link.from_socket) and is_float3_type(socket):
                convert_node = ('PxrToFloat3', link.from_node,
                                link.from_socket)
                if convert_node not in nodes:
                    nodes.append(convert_node)
            elif is_float3_type(link.from_socket) and is_float_type(socket):
                convert_node = ('PxrToFloat', link.from_node, link.from_socket)
                if convert_node not in nodes:
                    nodes.append(convert_node)

    if hasattr(node, 'renderman_node_type') and node.renderman_node_type != 'output':
        nodes.append(node)
    elif not hasattr(node, 'renderman_node_type') and node.bl_idname not in ['ShaderNodeOutputMaterial', 'NodeGroupInput', 'NodeGroupOutput']:
        nodes.append(node)

    return nodes

def get_textures_for_node(node, matName=""):
    textures = []
    return textures

def get_textures(id):
    textures = []

    return textures


pattern_node_categories_map = {"texture": ["PxrFractal", "PxrBakeTexture", "PxrBakePointCloud", "PxrProjectionLayer", "PxrPtexture", "PxrTexture", "PxrVoronoise", "PxrWorley", "PxrFractalize", "PxrDirt", "PxrLayeredTexture", "PxrMultiTexture"],
                               "bump": ["PxrBump", "PxrNormalMap", "PxrFlakes", "aaOceanPrmanShader", 'PxrAdjustNormal'],
                               "color": ["PxrBlackBody", "PxrHairColor", "PxrBlend", "PxrLayeredBlend", "PxrClamp", "PxrExposure", "PxrGamma", "PxrHSL", "PxrInvert", "PxrMix", "PxrProjectionStack", "PxrRamp", "PxrRemap", "PxrThinFilm", "PxrThreshold", "PxrVary", "PxrChecker", "PxrColorCorrect"],
                               "manifold": ["PxrManifold2D", "PxrRandomTextureManifold", "PxrManifold3D", "PxrManifold3DN", "PxrProjector", "PxrRoundCube", "PxrBumpManifold2D", "PxrTileManifold"],
                               "geometry": ["PxrDot", "PxrCross", "PxrFacingRatio", "PxrTangentField"],
                               "script": ["PxrOSL", "PxrSeExpr"],
                               "utility": ["PxrAttribute", "PxrGeometricAOVs", "PxrMatteID", "PxrPrimvar", "PxrShadedSide", "PxrTee", "PxrToFloat", "PxrToFloat3", "PxrVariable"],
                               "displace": ["PxrDispScalarLayer", 'PxrDispTransform', 'PxrDispVectorLayer'],
                               "layer": ['PxrLayer', 'PxrLayerMixer'],
                               "deprecated": []}
# Node Chatagorization List


def GetPatternCategory(name):
    for cat_name, node_names in pattern_node_categories_map.items():
        if name in node_names:
            return cat_name
    else:
        return 'misc'

# our own base class with an appropriate poll function,
# so the categories only show up in our own tree type


class RendermanPatternNodeCategory(NodeCategory):

    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'ShaderNodeTree'

classes = [
    
    #RendermanShaderSocket,
    #RendermanNodeSocketColor,
    #RendermanNodeSocketFloat,
    #RendermanNodeSocketInt,
    #RendermanNodeSocketString,
    #RendermanNodeSocketVector,
    #RendermanNodeSocketStruct,

    #RendermanNodeSocketInterfaceFloat,
    #RendermanNodeSocketInterfaceInt,
    #RendermanNodeSocketInterfaceStruct,
    #RendermanNodeSocketInterfaceColor,
    #RendermanNodeSocketInterfaceVector,
    #RendermanShaderSocketInterface,
    #RendermanShadingNode,
    #RendermanOutputNode,
    #RendermanBxdfNode,
    #RendermanDisplacementNode,
    #RendermanPatternNode,
    #RendermanLightNode,
    #NODE_OT_add_bxdf,
    #NODE_OT_add_displacement,
    #NODE_OT_add_light,
    #NODE_OT_add_pattern,
    #NODE_OT_add_layer,
    #NODE_OT_add_manifold,
    #NODE_OT_add_bump,
]

nodetypes = {}
pattern_categories = {}

def _call_osltoargs(oslfile, args_file):
    process_args = []
    process_args.append( os.path.join(filepath_utils.guess_rmantree(), 'bin', 'osltoargs') )
    process_args.append(oslfile)
    process_args.append('-o')
    process_args.append(args_file)
    try:
        subprocess.check_output(process_args)
        return True
    except:
        return False


def register():
    
    for cls in classes:
        bpy.utils.register_class(cls)

    user_preferences = bpy.context.preferences
    prefs = user_preferences.addons[__package__].preferences

    categories = {}

    '''
    for name, arg_file in args_files_in_path(prefs, None).items():
        try:
            f,ext = os.path.splitext(arg_file)
            if ext == '.args':
                vals = generate_node_type(prefs, name, ET.parse(arg_file).getroot())
                if vals:
                    typename, nodetype = vals
                    nodetypes[typename] = nodetype
            elif ext == '.oso':
                # this is an OSL file. Use osltoargs to convert to an args file.
                f = os.path.basename(f) + '.args'
                osltoargs = os.path.join( prefs_utils.get_bl_temp_dir(), f)
                _call_osltoargs(arg_file, osltoargs)
                vals = generate_node_type(prefs, name, ET.parse(osltoargs).getroot())
                if vals:
                    typename, nodetype = vals
                    nodetypes[typename] = nodetype                
        except Exception:
            print("Error parsing " + name)
            traceback.print_exc()

    node_cats = {
        'bxdf': ('RenderMan Bxdfs', []),
        'light': ('RenderMan Lights', []),
        'patterns_texture': ('RenderMan Texture Patterns', []),
        'patterns_bump': ('RenderMan Bump Patterns', []),
        'patterns_color': ('RenderMan Color Patterns', []),
        'patterns_manifold': ('RenderMan Manifold Patterns', []),
        'patterns_geometry': ('RenderMan Geometry Patterns', []),
        'patterns_utility': ('RenderMan Utility Patterns', []),
        'patterns_script': ('RenderMan Script Patterns', []),
        'patterns_displace': ('RenderMan Displacement Patterns', []),
        'patterns_layer': ('RenderMan Layers', []),
        'patterns_misc': ('RenderMan Misc Patterns', []),
        'displacement': ('RenderMan Displacements', [])
    }

    rfb_log().debug("Registering RenderMan Shading Nodes:")

    for name, node_type in nodetypes.items():
        node_item = NodeItem(name, label=node_type.bl_label)

        if node_type.renderman_node_type == 'pattern':
            # insert pxr layer in bxdf
            pattern_cat = GetPatternCategory(node_type.bl_label)
            if pattern_cat == 'deprecated':
                continue
            node_cat = 'patterns_' + pattern_cat          
            node_cats[node_cat][1].append(node_item)
            pattern_cat = pattern_cat.capitalize()
            if pattern_cat not in pattern_categories:
                pattern_categories[pattern_cat] = {}
            pattern_categories[pattern_cat][name] = node_type

        elif 'LM' in name and node_type.renderman_node_type == 'bxdf':
            # skip LM materials
            continue
        elif node_type.renderman_node_type == 'light' and 'PxrMeshLight' not in name:
            # skip light nodes
            continue
        else:
            node_cats[node_type.renderman_node_type][1].append(node_item)

        rfb_log().debug("\t%s registered." % name)

    rfb_log().debug("Finished Registering RenderMan Shading Nodes.")

    # all categories in a list
    node_categories = [
        # identifier, label, items list
        RendermanPatternNodeCategory("PRMan_output_nodes", "RenderMan Outputs",
                                     items=[NodeItem('RendermanOutputNode', label=rman_bl_nodes_shaders.RendermanOutputNode.bl_label)]),
    ]

    for name, (desc, items) in node_cats.items():
        node_categories.append(RendermanPatternNodeCategory(name, desc,
                                                            items=sorted(items,
                                                                         key=attrgetter('_label'))))

    nodeitems_utils.register_node_categories("RENDERMANSHADERNODES",
                                             node_categories)
    '''

def unregister():
    nodeitems_utils.unregister_node_categories("RENDERMANSHADERNODES")
    # bpy.utils.unregister_module(__name__)

    for cls in classes:
        bpy.utils.unregister_class(cls)
