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
import xml.etree.ElementTree as ET

import nodeitems_utils
from nodeitems_utils import NodeCategory, NodeItem

from .shader_parameters import class_generate_properties
from .shader_parameters import node_add_inputs
from .shader_parameters import node_add_outputs
from .util import args_files_in_path
from .util import get_path_list
from .util import rib

from operator import attrgetter, itemgetter
import os.path

NODE_LAYOUT_SPLIT = 0.5

# Shortcut for node type menu
def add_nodetype(layout, nodetype):
    layout.operator("node.add_node", text=nodetype.bl_label).type = nodetype.bl_rna.identifier


# Default Types

class RendermanPatternGraph(bpy.types.NodeTree):
    '''A node tree comprised of renderman nodes'''
    bl_idname = 'RendermanPatternGraph'
    bl_label = 'Renderman Pattern Graph'
    bl_icon = 'TEXTURE_SHADED'
    nodetypes = {}

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == 'PRMAN_RENDER'

    # Return a node tree from the context to be used in the editor
    @classmethod
    def get_from_context(cls, context):
        ob = context.active_object
        if ob and ob.type not in {'LAMP', 'CAMERA'}:
            ma = ob.active_material
            if ma != None: 
                nt_name = ma.renderman.nodetree
                if nt_name != '':
                    return bpy.data.node_groups[ma.renderman.nodetree], ma, ma
        elif ob and ob.type == 'LAMP':
            la = ob.data
            nt_name = la.renderman.nodetree
            if nt_name != '':
                return bpy.data.node_groups[la.renderman.nodetree], la, la
        return (None, None, None)
    
    #def draw_add_menu(self, context, layout):
    #    add_nodetype(layout, OutputShaderNode)
    #    for nt in self.nodetypes.values():
    #        add_nodetype(layout, nt)


class RendermanSocket:
    ui_open = bpy.props.BoolProperty(name='UI Open', default=True)
    # Optional function for drawing the socket input value
    def draw_value(self, context, layout, node):
        layout.prop(node, self.name)

    def draw_color(self, context, node):
        return (0.1, 1.0, 0.2, 0.75)

    def draw(self, context, layout, node, text):
        if self.is_linked or self.is_output:
            layout.label(text)
        else:
            layout.prop(node, self.name)
        

#socket types (need this just for the ui_open)
class RendermanNodeSocketFloat(bpy.types.NodeSocketFloat, RendermanSocket):
    '''Renderman float input/output'''
    bl_idname = 'RendermanNodeSocketFloat'
    bl_label = 'Renderman Float Socket'
    
    def draw_color(self, context, node):
        return (0.5, .5, 0.5, 0.75)

class RendermanNodeSocketInt(bpy.types.NodeSocketInt, RendermanSocket):
    '''Renderman int input/output'''
    bl_idname = 'RendermanNodeSocketInt'
    bl_label = 'Renderman Int Socket'
    
    def draw_color(self, context, node):
        return (1.0, 1.0, 1.0, 0.75)

class RendermanNodeSocketString(bpy.types.NodeSocketString, RendermanSocket):
    '''Renderman string input/output'''
    bl_idname = 'RendermanNodeSocketString'
    bl_label = 'Renderman String Socket'

class RendermanNodeSocketStruct(bpy.types.NodeSocketString, RendermanSocket):
    '''Renderman struct input/output'''
    bl_idname = 'RendermanNodeSocketStruct'
    bl_label = 'Renderman Struct Socket'
    
    struct_type = bpy.props.StringProperty(default='')

class RendermanNodeSocketColor(bpy.types.NodeSocketColor, RendermanSocket):
    '''Renderman color input/output'''
    bl_idname = 'RendermanNodeSocketColor'
    bl_label = 'Renderman Color Socket'
    
    def draw_color(self, context, node):
        return (1.0, 1.0, .5, 0.75)

class RendermanNodeSocketVector(bpy.types.NodeSocketVector, RendermanSocket):
    '''Renderman vector input/output'''
    bl_idname = 'RendermanNodeSocketVector'
    bl_label = 'Renderman Vector Socket'
    
    def draw_color(self, context, node):
        return (.2, .2, 1.0, 0.75)

# Custom socket type for connecting shaders
class RendermanShaderSocket(bpy.types.NodeSocketShader, RendermanSocket):
    '''Renderman shader input/output'''
    bl_idname = 'RendermanShaderSocket'
    bl_label = 'Renderman Shader Socket'
    def draw_value(self, context, layout, node):
        layout.label(self.name)

    def draw_color(self, context, node):
        return (0.1, 1.0, 0.2, 0.75)

    def draw(self, context, layout, node, text):
        layout.label(text)
        pass

class RendermanPropertyGroup(bpy.types.PropertyGroup):
    ui_open = bpy.props.BoolProperty(name='UI Open', default=True)

# Base class for all custom nodes in this tree type.
# Defines a poll function to enable instantiation.
class RendermanShadingNode(bpy.types.Node):
    bl_label = 'Output'

    #all the properties of a shader will go here, also inputs/outputs 
    #on connectable props will have the same name
    #node_props = None
    def draw_buttons(self, context, layout):
        self.draw_nonconnectable_props(context, layout, self.prop_names)

    def draw_buttons_ext(self, context, layout):
        self.draw_nonconnectable_props(context, layout, self.prop_names)

    def draw_nonconnectable_props(self, context, layout, prop_names):
        for prop_name in prop_names:
            prop_meta = self.prop_meta[prop_name]
            if prop_name not in self.inputs:
                if prop_meta['renderman_type'] == 'page':
                    prop = getattr(self, prop_name)
                    self.draw_nonconnectable_props(context, layout, prop)
                else:
                    layout.prop(self,prop_name)
            


    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == 'RendermanPatternGraph'

    
    #     # for sp in [p for p in args.params if p.meta['array']]:
    #     #     row = layout.row(align=True)
    #     #     row.label(sp.name)
    #     #     row.operator("node.add_array_socket", text='', icon='ZOOMIN').array_name = sp.name
    #     #     row.operator("node.remove_array_socket", text='', icon='ZOOMOUT').array_name = sp.name
    
    # def draw_buttons_ext(self, context, layout):
    #     row = layout.row(align=True)
    #     row.label("buttons ext")
    #     layout.operator('node.refresh_shader_parameters', icon='FILE_REFRESH')
    #     #print(self.prop_names)
    #     # for p in self.prop_names:
    #     #     layout.prop(self, p)
    #     # for p in self.prop_names:
    #     #     split = layout.split(NODE_LAYOUT_SPLIT)
    #     #     split.label(p+':')
    #     #     split.prop(self, p, text='')

class RendermanOutputNode(RendermanShadingNode):
    bl_label = 'Output'
    renderman_node_type = 'output'
    bl_icon = 'MATERIAL'
    def init(self, context):
        input = self.inputs.new('RendermanShaderSocket', 'Bxdf')
        input = self.inputs.new('RendermanShaderSocket', 'Light')
        input = self.inputs.new('RendermanShaderSocket', 'Displacement')
        #input.default_value = bpy.props.EnumProperty(items=[('PxrDisney', 'PxrDisney', 
        #    '')])

    def draw_buttons(self, context, layout):
        return

    def draw_buttons_ext(self, context, layout):
        return
        

# Final output node, used as a dummy to find top level shaders
class RendermanBxdfNode(RendermanShadingNode):
    bl_label = 'Bxdf'
    renderman_node_type = 'bxdf'

class RendermanDisplacementNode(RendermanShadingNode):
    bl_label = 'Displacement'
    renderman_node_type = 'displacement'

# Final output node, used as a dummy to find top level shaders
class RendermanPatternNode(RendermanShadingNode):
    bl_label = 'Texture'
    renderman_node_type = 'pattern'

class RendermanLightNode(RendermanShadingNode):
    bl_label = 'Output'
    renderman_node_type = 'light'

# Generate dynamic types
def generate_node_type(prefs, name, args):
    ''' Dynamically generate a node type from pattern '''

    nodeType = args.find("shaderType/tag").attrib['value']
    typename = '%s%sNode' % (name, nodeType.capitalize())
    nodeDict = {'bxdf':RendermanBxdfNode, 
                'pattern': RendermanPatternNode,
                'displacement': RendermanDisplacementNode,
                'light': RendermanLightNode}
    ntype = type(typename, (nodeDict[nodeType],), {})
    ntype.bl_label = name
    ntype.typename = typename
    
    inputs = [p for p in args.findall('./param')] + \
        [p for p in args.findall('./page')]
    outputs = [p for p in args.findall('.//output')]

    def init(self, context):
        if self.renderman_node_type == 'bxdf':
            self.outputs.new('RendermanShaderSocket', "Bxdf")
            node_add_inputs(self, name, inputs)
            node_add_outputs(self, outputs)
        elif self.renderman_node_type == 'light':
            #only make a few sockets connectable
            connectable_sockets = ['lightColor', 'intensity', 'exposure', 
                                    'sunTint', 'skyTint', 'envTint']
            light_inputs = [p for p in inputs \
                            if p.attrib['name'] in connectable_sockets]
            node_add_inputs(self, name, light_inputs)
            self.outputs.new('RendermanShaderSocket', "Light")
        elif self.renderman_node_type == 'displacement':
            #only make the color connectable
            self.outputs.new('RendermanShaderSocket', "Displacement")
            node_add_inputs(self, name, inputs)
        #else pattern
        else:
            node_add_inputs(self, name, inputs)
            node_add_outputs(self, outputs)

    ntype.init = init
    #ntype.draw_buttons = draw_buttons
    #ntype.draw_buttons_ext = draw_buttons_ext
    
    ntype.plugin_name = bpy.props.StringProperty(name='Plugin Name', 
                            default=name, options={'HIDDEN'})
    #ntype.prop_names = class_add_properties(ntype, [p for p in args.findall('./param')])
    #lights cant connect to a node tree in 20.0
    class_generate_properties(ntype, name, inputs)

    if nodeType == 'light':
        ntype.light_shading_rate = bpy.props.FloatProperty(
            name="Light Shading Rate",
            description="Shading Rate for this light.  Leave this high unless detail is missing",
            default=100.0)
        ntype.light_primary_visibility = bpy.props.BoolProperty(
            name="Light Primary Visibility",
            description="Camera visibility for this light",
            default=True)

    #print(ntype, ntype.bl_rna.identifier)
    bpy.utils.register_class(ntype)
    
    RendermanPatternGraph.nodetypes[typename] = ntype


# UI
def find_node_input(node, name):
    for input in node.inputs:
        if input.name == name:
            return input

    return None

def draw_nodes_properties_ui(layout, context, nt, input_name='Bxdf', 
                            output_node_type="output"):
    output_node = next((n for n in nt.nodes \
                        if n.renderman_node_type == output_node_type), None)
    if output_node is None: 
        return

    socket = output_node.inputs[input_name]
    node = socket_node_input(nt, socket)

    layout.context_pointer_set("nodetree", nt)
    layout.context_pointer_set("node", output_node)
    layout.context_pointer_set("socket", socket)

    if input_name == 'Light' and node is not None and socket.is_linked:
        layout.prop(node, 'light_primary_visibility')
        layout.prop(node, 'light_shading_rate')
    split = layout.split(0.35)
    split.label(socket.name+':')
    
    if socket.is_linked:
        #for lights draw the shading rate ui.
        
        split.operator_menu_enum("node.add_%s" % input_name.lower(), 
                                "node_type", text=node.bl_label)
    else:
        split.operator_menu_enum("node.add_%s" % input_name.lower(), 
                                "node_type", text='None')

    if node is not None:
        draw_node_properties_recursive(layout, context, nt, node)

def node_shader_handle(nt, node):
    return '%s_%s' % (nt.name, node.name)

def socket_node_input(nt, socket):
    return next((l.from_node for l in nt.links if l.to_socket == socket), None)

def socket_socket_input(nt, socket):
    return next((l.from_socket for l in nt.links if l.to_socket == socket \
                and socket.is_linked), None)

def linked_sockets(sockets):
    if sockets == None:
        return []
    return [i for i in sockets if i.is_linked == True]

def draw_node_properties_recursive(layout, context, nt, node, level=0):

    def indented_label(layout, label):
        for i in range(level):
            layout.label('',icon='BLANK1')
        layout.label(label)
    
    layout.context_pointer_set("node", node)
    layout.context_pointer_set("nodetree", nt)
    
    def draw_props(prop_names, layout):
        for prop_name in prop_names:
            prop_meta = node.prop_meta[prop_name]
            prop = getattr(node, prop_name)
            
            #else check if the socket with this name is connected
            socket = node.inputs[prop_name] if prop_name in node.inputs \
                 else None
            layout.context_pointer_set("socket", socket)
            
            if socket and socket.is_linked:
                input_node = socket_node_input(nt, socket)
                icon = 'TRIA_DOWN' if socket.ui_open \
                    else 'TRIA_RIGHT'
                
                split = layout.split(NODE_LAYOUT_SPLIT)
                row = split.row()
                row.prop(socket, "ui_open", icon=icon, text='', 
                        icon_only=True, emboss=False)            
                indented_label(row, socket.name+':')
                split.operator_menu_enum("node.add_pattern", "node_type", 
                    text=input_node.bl_label, icon='DOT')

                if socket.ui_open:
                    draw_node_properties_recursive(layout, context, nt, 
                        input_node, level=level+1)

            else:
                row = layout.row()
                #split = layout.split(NODE_LAYOUT_SPLIT)
                if prop_meta['renderman_type'] == 'page':
                    ui_prop = prop_name + "_ui_open"
                    ui_open = getattr(node, ui_prop)
                    icon = 'TRIA_DOWN' if ui_open \
                        else 'TRIA_RIGHT'

                    split = layout.split(NODE_LAYOUT_SPLIT)
                    row = split.row()
                    row.prop(node, ui_prop, icon=icon, text='', 
                            icon_only=True, emboss=False)            
                    indented_label(row, prop_name+':')
                    
                    if ui_open:
                        draw_props(prop, layout)
                else:
                    row.label('', icon='BLANK1')
                    #indented_label(row, socket.name+':')
                    #don't draw prop for struct type
                    row.prop(node, prop_name)
                    if prop_name in node.inputs:
                        row.operator_menu_enum("node.add_pattern", "node_type", 
                            text='', icon='DOT')
    
    draw_props(node.prop_names, layout)
    layout.separator()

    

# Operators
#connect the pattern nodes in some sensible manner (color output to color input etc)
#TODO more robust
def link_node(nt, from_node, in_socket):
    out_socket = None
    #first look for resultF/resultRGB
    if type(in_socket).__name__ in ['RendermanNodeSocketColor', 
                                    'RendermanNodeSocketVector']:
        out_socket = from_node.outputs.get('resultRGB', 
            next((s for s in from_node.outputs \
                if type(s).__name__ == 'RendermanNodeSocketColor'), None))
    elif type(in_socket).__name__ == 'RendermanNodeSocketStruct':
        out_socket = from_node.outputs.get('result', None) 
    else:
        out_socket = from_node.outputs.get('resultF', 
            next((s for s in from_node.outputs \
                if type(s).__name__ == 'RendermanNodeSocketFloat'), None))

    if out_socket:
        nt.links.new(out_socket, in_socket)

#bass class for operator to add a node
class Add_Node:
    '''
    For generating cycles-style ui menus to add new nodes,
    connected to a given input socket.
    '''
    def get_type_items(self, context):
        items = []
        for nodetype in RendermanPatternGraph.nodetypes.values():
            if nodetype.renderman_node_type == self.input_type.lower():
                items.append((nodetype.typename, nodetype.bl_label, 
                        nodetype.bl_label))
        items = sorted(items, key=itemgetter(1))
        items.append(('REMOVE', 'Remove', 
                        'Remove the node connected to this socket'))
        items.append(('DISCONNECT', 'Disconnect', 
                        'Disconnect the node connected to this socket'))
        return items

    node_type = bpy.props.EnumProperty(name="Node Type",
        description='Node type to add to this socket',
        items=get_type_items)


    def execute(self, context):
        new_type = self.properties.node_type
        if new_type == 'DEFAULT':
            return {'CANCELLED'}

        nt = context.nodetree
        node = context.node
        socket = context.socket
        input_node = socket_node_input(nt, socket)

        if new_type == 'REMOVE':
            nt.nodes.remove(input_node)
            return {'FINISHED'}

        if new_type == 'DISCONNECT':
            link = next((l for l in nt.links if l.to_socket == socket), None)
            nt.links.remove(link)
            return {'FINISHED'}

        # add a new node to existing socket
        if input_node is None:
            newnode = nt.nodes.new(new_type)
            newnode.location = node.location
            newnode.location[0] -= 300
            newnode.selected = False
            if self.input_type == 'Pattern':
                link_node(nt, newnode, socket)
            else:
                nt.links.new(newnode.outputs[self.input_type], socket)

        # replace input node with a new one
        else:
            newnode = nt.nodes.new(new_type)
            input = socket
            old_node = input.links[0].from_node
            if self.input_type == 'Pattern':
                link_node(nt, newnode, socket)
            else:
                nt.links.new(newnode.outputs[self.input_type], socket)
            newnode.location = old_node.location
            
            nt.nodes.remove(old_node)
        return {'FINISHED'}

class NODE_OT_add_bxdf(bpy.types.Operator, Add_Node):
    '''
    For generating cycles-style ui menus to add new bxdfs,
    connected to a given input socket.
    '''

    bl_idname = 'node.add_bxdf'
    bl_label = 'Add Bxdf Node'
    bl_description = 'Connect a Bxdf to this socket'
    input_type = bpy.props.StringProperty(default='Bxdf')

class NODE_OT_add_displacement(bpy.types.Operator, Add_Node):
    '''
    For generating cycles-style ui menus to add new nodes,
    connected to a given input socket.
    '''

    bl_idname = 'node.add_displacement'
    bl_label = 'Add Displacement Node'
    bl_description = 'Connect a Displacement shader to this socket'
    input_type = bpy.props.StringProperty(default='Displacement')

class NODE_OT_add_light(bpy.types.Operator, Add_Node):
    '''
    For generating cycles-style ui menus to add new nodes,
    connected to a given input socket.
    '''

    bl_idname = 'node.add_light'
    bl_label = 'Add Light Node'
    bl_description = 'Connect a Light shader to this socket'
    input_type = bpy.props.StringProperty(default='Light')

class NODE_OT_add_pattern(bpy.types.Operator, Add_Node):
    '''
    For generating cycles-style ui menus to add new nodes,
    connected to a given input socket.
    '''

    bl_idname = 'node.add_pattern'
    bl_label = 'Add Pattern Node'
    bl_description = 'Connect a Pattern to this socket'
    input_type = bpy.props.StringProperty(default='Pattern')


#### Rib export

#generate param list
def gen_params(ri, node):
    params = {}
    for prop_name,meta in node.prop_meta.items():
        prop = getattr(node, prop_name)
        #if property group recurse
        if meta['renderman_type'] == 'page':
            continue
        #if input socket is linked reference that
        elif prop_name in node.inputs and node.inputs[prop_name].is_linked:
            from_socket = node.inputs[prop_name].links[0].from_socket
            shader_node_rib(ri, from_socket.node)
            params['reference %s %s' % (meta['renderman_type'], 
                    meta['renderman_name'])] = \
                ["%s:%s" % (from_socket.node.name, from_socket.identifier)]        
        #else output rib
        else:
            #if struct is not linked continue
            if meta['renderman_type'] == 'struct':
                continue

            if 'options' in meta and meta['options'] == 'texture' or \
                (node.renderman_node_type == 'light' and \
                    'widget' in meta and meta['widget'] == 'fileInput'):
                params['%s %s' % (meta['renderman_type'], 
                        meta['renderman_name'])] = \
                    rib(get_tex_file_name(prop), 
                        type_hint=meta['renderman_type']) 
            elif 'arraySize' in meta:
                params['%s[%d] %s' % (meta['renderman_type'], len(prop), 
                        meta['renderman_name'])] = rib(prop) 
            else:
                params['%s %s' % (meta['renderman_type'], 
                        meta['renderman_name'])] = \
                    rib(prop, type_hint=meta['renderman_type']) 

    return params

# Export to rib
def shader_node_rib(ri, node, handle=None, disp_bound=0.0):
    params = gen_params(ri, node)
    if handle:
        params['__instanceid'] = handle
    if node.renderman_node_type == "pattern":
        ri.Pattern(node.bl_label, node.name, params)
    elif node.renderman_node_type == "light":
        primary_vis = node.light_primary_visibility
        #must be off for light sources
        ri.Attribute("visibility", {'int transmission':0, 'int indirect':0,
                    'int camera':int(primary_vis)})
        ri.ShadingRate(node.light_shading_rate)
        if primary_vis:
            ri.Bxdf("PxrLightEmission", node.name, {'__instanceid': handle})
        params[ri.HANDLEID] = handle
        ri.AreaLightSource(node.bl_label, params)
    elif node.renderman_node_type == "displacement":
        ri.Attribute('displacementbound', {'sphere':disp_bound})
        ri.Displacement(node.bl_label, params)
    else:
        ri.Bxdf(node.bl_label, node.name, params)

#return the output file name if this texture is to be txmade.
def get_tex_file_name(prop):
    if prop != '' and prop.rsplit('.', 1) != 'tex':
        return os.path.basename(prop).rsplit('.', 2)[0] + '.tex'
    else:
        return prop

#for an input node output all "nodes"
def export_shader_nodetree(ri, id, handle=None, disp_bound=0.0):
	try:
		nt = bpy.data.node_groups[id.renderman.nodetree]
	except:
		nt = None
	if nt:
		if not handle:
			handle = id.name

		out = next((n for n in nt.nodes if n.renderman_node_type == 'output'), 
                    None)
		if out is None: return
		
		ri.ArchiveRecord('comment', "Shader Graph")
		for out_type,socket in out.inputs.items():
			if socket.is_linked:
				shader_node_rib(ri, socket.links[0].from_node, handle=handle, disp_bound=disp_bound)


def get_textures_for_node(node):
    textures = []
    for prop_name,meta in node.prop_meta.items():
        prop = getattr(node, prop_name)
        
        if meta['renderman_type'] == 'page':
            continue
        
        #if input socket is linked reference that
        elif prop_name in node.inputs and node.inputs[prop_name].is_linked:
            from_socket = node.inputs[prop_name].links[0].from_socket
            textures = textures + get_textures_for_node(from_socket.node)
        
        #else return a tuple of in name/outname
        else:
            if ('options' in meta and meta['options'] == 'texture') or \
                (node.renderman_node_type == 'light' and \
                    'widget' in meta and meta['widget'] == 'fileInput'): #fix for sloppy args files
                out_file_name = get_tex_file_name(prop)
                if out_file_name != prop: #if they don't match add this to the list
                    if node.renderman_node_type == 'light' and "Env" in node.bl_label:
                        textures.append((prop, out_file_name, ['-envlatl'])) #no options for now
                    else:
                        textures.append((prop, out_file_name, [])) #no options for now

    return textures
    
def get_textures(id):
    textures = []
    if id.renderman.nodetree == "":
        return textures
    try:
        nt = bpy.data.node_groups[id.renderman.nodetree]
    except:
        nt = None

    if nt:
        out = next((n for n in nt.nodes if n.renderman_node_type == 'output'), 
                    None)
        if out is None: return
        
        for name,inp in out.inputs.items():
            if inp.is_linked:
                textures = textures + \
                    get_textures_for_node(inp.links[0].from_node)
        
    return textures


# our own base class with an appropriate poll function,
# so the categories only show up in our own tree type
class RendermanPatternNodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'RendermanPatternGraph'

classes = [
    RendermanShaderSocket,
    RendermanNodeSocketColor,
    RendermanNodeSocketFloat,
    RendermanNodeSocketInt,
    RendermanNodeSocketString,
    RendermanNodeSocketVector,
    RendermanNodeSocketStruct
]


def register():

    for cls in classes:
        bpy.utils.register_class(cls)
 
    user_preferences = bpy.context.user_preferences
    prefs = user_preferences.addons[__package__].preferences


    #from bpy.app.handlers import persistent

    #@persistent
    #def load_handler(dummy):
    categories = {}

    for name, arg_file in args_files_in_path(prefs, None).items():
        generate_node_type(prefs, name, ET.parse(arg_file).getroot())

    pattern_nodeitems = []
    bxdf_nodeitems = []
    light_nodeitems = []
    for name, node_type in RendermanPatternGraph.nodetypes.items():
        node_item = NodeItem(name, label=node_type.bl_label)
        if node_type.renderman_node_type == 'pattern':
            pattern_nodeitems.append(node_item)
        elif node_type.renderman_node_type == 'bxdf':
            bxdf_nodeitems.append(node_item)
        elif node_type.renderman_node_type == 'light':
            light_nodeitems.append(node_item)
       

    # all categories in a list
    node_categories = [
        # identifier, label, items list
        RendermanPatternNodeCategory("PRMan_output_nodes", "PRMan outputs", 
            items = [RendermanOutputNode]),
        RendermanPatternNodeCategory("PRMan_bxdf", "PRMan Bxdfs",  
            items=sorted(bxdf_nodeitems, key=attrgetter('_label')) ),
        RendermanPatternNodeCategory("PRMan_patterns", "PRMan Patterns",  
            items=sorted(pattern_nodeitems, key=attrgetter('_label')) ),
        RendermanPatternNodeCategory("PRMan_lights", "PRMan Lights",  
            items=sorted(light_nodeitems, key=attrgetter('_label')) )

        ]
    nodeitems_utils.register_node_categories("RENDERMANSHADERNODES", 
        node_categories)

    #bpy.app.handlers.load_post.append(load_handler)
    #bpy.app.handlers.load_pre.append(load_handler)


def unregister():
    nodeitems_utils.unregister_node_categories("RENDERMANSHADERNODES")
    #bpy.utils.unregister_module(__name__)

    for cls in classes:
        bpy.utils.unregister_class(cls)

