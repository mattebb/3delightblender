# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2012 Matt Ebb
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

import nodeitems_utils
from nodeitems_utils import NodeCategory, NodeItem

from .shader_parameters import class_add_parameters
from .shader_parameters import get_parameters_shaderinfo
from .shader_parameters import ptr_to_shaderparameters
from .shader_scan import shaders_in_path
from .util import get_path_list
from .util import rib

NODE_LAYOUT_SPLIT = 0.5

# Shortcut for node type menu
def add_nodetype(layout, nodetype):
    layout.operator("node.add_node", text=nodetype.bl_label).type = nodetype.bl_rna.identifier


# Default Types

class RendermanShaderTree(bpy.types.NodeTree):
    '''A node tree comprised of renderman co-shader nodes'''
    bl_idname = 'RendermanShaderTree'
    bl_label = 'Renderman Shader Tree'
    bl_icon = 'TEXTURE_SHADED'
    nodetypes = {}

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == '3DELIGHT_RENDER'

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
    
    def draw_add_menu(self, context, layout):
        add_nodetype(layout, OutputShaderNode)
        for nt in self.nodetypes.values():
            add_nodetype(layout, nt)

# Custom socket type
class RendermanShaderSocket(bpy.types.NodeSocket):
    '''Renderman co-shader input/output'''
    bl_idname = 'RendermanShaderSocket'
    bl_label = 'Renderman Shader Socket'
    
    ui_open = bpy.props.BoolProperty(name='UI Open')

    # Optional function for drawing the socket input value
    def draw_value(self, context, layout, node):
        layout.label(self.name)

    def draw_color(self, context, node):
        return (0.1, 1.0, 0.2, 0.75)

    def draw(self, context, layout, node, text):
        layout.label(text)
        pass


class RendermanShaderArraySocket(bpy.types.NodeSocket):
    '''Renderman co-shader array input/output'''
    bl_idname = 'RendermanShaderArraySocket'
    bl_label = 'Renderman Shader Array Socket'
    
    ui_open = bpy.props.BoolProperty(name='UI Open')

    # Optional function for drawing the socket input value
    def draw_value(self, context, layout, node):
        layout.label(self.name)

    def draw_color(self, context, node):
        return (0.1, 1.0, 0.5, 0.75)

    def draw(self, a,b,c,d):
        pass


# Base class for all custom nodes in this tree type.
# Defines a poll function to enable instantiation.
class RendermanShaderNode:
    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == 'RendermanShaderTree'


# Final output node, used as a dummy to find top level shaders
class OutputShaderNode(bpy.types.Node, RendermanShaderNode):
    bl_label = 'Output'
    def init(self, context):
        self.inputs.new('RendermanShaderSocket', "Surface")
        self.inputs.new('RendermanShaderSocket', "Displacement")
        self.inputs.new('RendermanShaderSocket', "Interior")
        self.inputs.new('RendermanShaderSocket', "Atmosphere")

class OutputLightShaderNode(bpy.types.Node, RendermanShaderNode):
    bl_label = 'Output'
    def init(self, context):
        self.inputs.new('RendermanShaderSocket', "LightSource")
        

# Generate dynamic types

def generate_node_type(prefs, name):
    ''' Dynamically generate a node type from shader '''

    path_list = get_path_list(prefs, 'shader')
    name, parameters = get_parameters_shaderinfo(path_list, name, '')

    # print('generating node: %s' % name)

    typename = '%sShaderNode' % name[:16]
    ntype = type(typename, (bpy.types.Node, RendermanShaderNode), {})
    ntype.bl_label = name
    ntype.typename = typename

    def init(self, context):
        self.outputs.new('RendermanShaderSocket', "Shader")
        for sp in [p for p in parameters if p.data_type == 'shader']:
            if sp.meta['array']:
                self.inputs.new('RendermanShaderArraySocket', sp.name)
            else:
                self.inputs.new('RendermanShaderSocket', sp.name)

    def draw_buttons(self, context, layout):
        #for p in self.prop_names:
        #    layout.prop(self, p)

        for sp in [p for p in parameters if p.meta['array']]:
            row = layout.row(align=True)
            row.label(sp.name)
            row.operator("node.add_array_socket", text='', icon='ZOOMIN').array_name = sp.name
            row.operator("node.remove_array_socket", text='', icon='ZOOMOUT').array_name = sp.name
    
    def draw_buttons_ext(self, context, layout):
        layout.operator('node.refresh_shader_parameters', icon='FILE_REFRESH')

        for p in self.prop_names:
            split = layout.split(NODE_LAYOUT_SPLIT)
            split.label(p+':')
            split.prop(self, p, text='')

    ntype.init = init
    ntype.draw_buttons = draw_buttons
    ntype.draw_buttons_ext = draw_buttons_ext
    
    ntype.shader_name = bpy.props.StringProperty(name='Shader Name', default=name, options={'HIDDEN'})
    ntype.prop_names = class_add_parameters(ntype, [p for p in parameters if p.data_type != 'shader'])
    bpy.utils.register_class(ntype)

    print(ntype, ntype.bl_rna.identifier)

    RendermanShaderTree.nodetypes[typename] = ntype


def node_shader_handle(nt, node):
    return '%s_%s' % (nt.name, node.name)

def socket_node_input(nt, socket):
    return next((l.from_node for l in nt.links if l.to_socket == socket), None)

def socket_socket_input(nt, socket):
    return next((l.from_socket for l in nt.links if l.to_socket == socket and socket.is_linked), None)

def linked_sockets(sockets):
    if sockets == None:
        return []
    return [i for i in sockets if i.is_linked == True]



# UI

def draw_nodes_properties_ui(layout, context, ntree, input_name='Surface', output_node='OutputShaderNode'):
    out = next((n for n in ntree.nodes if n.type == output_node), None)
    if out is None: return

    socket = next((s for s in out.inputs if s.name == input_name), None)
    node = socket_node_input(ntree, socket)

    layout.context_pointer_set("nodetree", ntree)
    layout.context_pointer_set("node", out)
    layout.context_pointer_set("socket", socket)

    split = layout.split(0.35)
    split.label(socket.name+':')
    if socket.is_linked:
        split.operator_menu_enum("node.add_input_node", "node_type", text=node.bl_label)
    else:
        split.operator_menu_enum("node.add_input_node", "node_type", text='None')

    if node is not None:
        draw_node_properties_recursive(layout, context, ntree, node)


def draw_node_properties_recursive(layout, context, nt, node, level=0):

    def indented_label(layout, label):
        for i in range(level):
            layout.label('',icon='BLANK1')
        layout.label(label)
    
    # node properties
    for p in node.prop_names:
        split = layout.split(NODE_LAYOUT_SPLIT)
        row = split.row()
        indented_label(row, p+':')
        split.prop(node, p, text='')

    layout.context_pointer_set("node", node)
    node.draw_buttons(context, layout)

    # node shader inputs
    for socket in node.inputs:
        layout.context_pointer_set("socket", socket)
        
        if socket.is_linked:
            input_node = socket_node_input(nt, socket)
            icon = 'DISCLOSURE_TRI_DOWN' if socket.ui_open else 'DISCLOSURE_TRI_RIGHT'
            
            split = layout.split(NODE_LAYOUT_SPLIT)
            row = split.row()
            row.prop(socket, "ui_open", icon=icon, text='', icon_only=True, emboss=False)            
            indented_label(row, socket.name+':')
            split.operator_menu_enum("node.add_input_node", "node_type", text=input_node.bl_label)

            if socket.ui_open:
                draw_node_properties_recursive(layout, context, nt, input_node, level=level+1)

        else:
            split = layout.split(NODE_LAYOUT_SPLIT)
            row = split.row()
            row.label('', icon='BLANK1')
            indented_label(row, socket.name+':')
            split.operator_menu_enum("node.add_input_node", "node_type", text='None')
            
    layout.separator()

    

# Operators

class NODE_OT_add_input_node(bpy.types.Operator):
    '''
    For generating cycles-style ui menus to add new nodes,
    connected to a given input socket.
    '''

    bl_idname = 'node.add_input_node'
    bl_label = 'Add Input Node'

    def node_type_items(self, context):
        items = []
        for nodetype in RendermanShaderTree.nodetypes.values():
            items.append( (nodetype.typename, nodetype.bl_label, nodetype.bl_label) )
        items.append( ('REMOVE', 'Remove', 'Remove the node connected to this socket'))
        items.append( ('DISCONNECT', 'Disconnect', 'Disconnect the node connected to this socket'))
        return items

    node_type = bpy.props.EnumProperty(name="Node Type",
        description='Node type to add to this socket',
        items=node_type_items)

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
            nt.links.new(newnode.outputs[0], socket)

        # replace input node with a new one
        else:
            output_names = []
            for in_socket in node.inputs:
                if socket_node_input(nt, in_socket) == input_node:
                    output_names.append( socket_socket_input(nt, in_socket).name )
                else:
                    output_names.append(None)

            newnode = nt.nodes.new(new_type)
            newnode.location = input_node.location
            nt.nodes.remove(input_node)

            for i, output_name in enumerate(output_names):
                input = node.inputs[i]
                output = next((o for o in newnode.outputs if o.name == output_name), None)
                if output is None:
                    continue
                nt.links.new(output, input)

        return {'FINISHED'}


class NODE_OT_refresh_shader_parameters(bpy.types.Operator):
    bl_idname = 'node.refresh_shader_parameters'
    bl_label = 'Refresh Shader Parameters'
    
    def execute(self, context):
        node = context.node
        for i in node.inputs:
            node.inputs.remove(i)
        for o in node.outputs:
            node.outputs.remove(o)

        node.init(context)
        return {'FINISHED'}
    

def rindex(l, item):
    return len(l)-1 - l[-1::-1].index(item) # slice notation reverses sequence

class NODE_OT_add_array_socket(bpy.types.Operator):
    bl_idname = 'node.add_array_socket'
    bl_label = 'Add Array Socket'

    array_name = bpy.props.StringProperty(name="Array Name",
        description="Name of the shader array to add an additional socket to",
        default="")

    def execute(self, context):
        node = context.node
        array_name = self.properties.array_name
    
        nt = bpy.data.node_groups[context.active_object.material_slots[0].material.renderman.nodetree]

        # copy existing inputs, in order to manipulate
        inputs_data = [{'name':s.name, 'type':s.bl_idname, 'linked_output':socket_socket_input(nt, s)} for s in node.inputs]
        
        # add new input in requested position
        names = [d['name'] for d in inputs_data]
        idx = rindex(names, array_name)
        inputs_data.insert(idx+1, { 'name':inputs_data[idx]['name'], 
                                    'type':inputs_data[idx]['type'],
                                    'linked_output':None
                                    })
        
        # clear old sockets
        for input in node.inputs:
            node.inputs.remove(input)

        # recreate with new ordering, and restore previous links
        for i in inputs_data:
            socket = node.inputs.new(i['type'], i['name'])
            socket.array = True
            if i['linked_output'] is not None:
                nt.links.new(i['linked_output'], socket)

        return {'FINISHED'}

class NODE_OT_remove_array_socket(bpy.types.Operator):
    bl_idname = 'node.remove_array_socket'
    bl_label = 'Remove Array Socket'

    array_name = bpy.props.StringProperty(name="Array Name",
        description="Name of the shader array to add an additional socket to",
        default="")

    def execute(self, context):
        node = context.node
        array_name = self.properties.array_name    
        nt = bpy.data.node_groups[context.active_object.material_slots[0].material.renderman.nodetree]

        last_array_socket = [s for s in node.inputs if s.name == array_name][-1]
        node.inputs.remove(last_array_socket)

        return {'FINISHED'}


# Export to rib

def shader_node_rib(file, scene, nt, node, shader_type='Shader', handle=None):
    file.write('\n')

    file.write('        %s "%s" ' % (shader_type, node.shader_name))
    if shader_type == 'Shader':
        file.write('"%s"' % node_shader_handle(nt, node))
    elif shader_type == 'LightSource':
        file.write('"%s"' % handle)
    file.write('\n')

    # Export built in parameters
    parameterlist = ptr_to_shaderparameters(scene, node)
    for sp in parameterlist:
        file.write('            "%s %s" %s\n' % (sp.data_type, sp.name, rib(sp.value)))


    # Export shader inputs
    sockets = linked_sockets(node.inputs)
    arrays = [s for s in sockets if s.bl_idname == 'RendermanShaderArraySocket']

    # export shader array socket shader references
    for i, arraysocket in enumerate(arrays):
        # check to see if we've already processed a socket with this name
        # so we don't double up
        if [s.name for s in arrays].index(arraysocket.name) < i:
            continue

        arrayinputs = [socket_node_input(nt, s) for s in sockets if s.name == arraysocket.name]
        handles = ['"%s"' % node_shader_handle(nt, n) for n in arrayinputs]
        count = [s.name for s in arrays].count(arraysocket.name)

        file.write('            "string %s[%d]" %s \n' % (arraysocket.name, count, rib(handles)) )

    # export remaining non-array socket shader references
    for socket in [s for s in sockets if s not in arrays]:
        inode = socket_node_input(nt, socket)
        file.write('            "string %s" "%s" \n' % (socket.name, node_shader_handle(nt,inode)))


def node_gather_inputs(nt, node):
    '''
    Recursively gather a list of nodes by traversing the node tree backwards
    from an initial node and following the links connected to its inputs
    '''
    input_nodes = []
    
    for isocket in linked_sockets(node.inputs):

        # find input node via searching nodetree.links
        input_node = socket_node_input(nt, isocket)

        # recursively add the current node's inputs to the front of the list
        input_nodes = node_gather_inputs(nt, input_node) + input_nodes

        # and add the current input node itself
        if input_node not in input_nodes:
            input_nodes.append(input_node)
    return input_nodes


def export_shader_nodetree(file, scene, id, output_node='OutputShaderNode', handle=None):
    nt = bpy.data.node_groups[id.renderman.nodetree]

    out = next((n for n in nt.nodes if n.type == output_node), None)
    if out is None: return
    
    # Top level shader types, in output node
    for isocket in linked_sockets(out.inputs):

        inode = socket_node_input(nt, isocket)

        # node inputs to top level shader
        for node in node_gather_inputs(nt, inode):
            shader_node_rib(file, scene, nt, node)

        # top level shader itself
        shader_node_rib(file, scene, nt, inode, shader_type=isocket.name, handle=handle)

        file.write('\n')


# our own base class with an appropriate poll function,
# so the categories only show up in our own tree type
class RendermanShaderNodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'RendermanShaderTree'

def register():
    user_preferences = bpy.context.user_preferences
    prefs = user_preferences.addons[__package__].preferences


    #from bpy.app.handlers import persistent

    #@persistent
    #def load_handler(dummy):
    for s in shaders_in_path(prefs, None, threaded=False):
        generate_node_type(prefs, s)



    nodeitems = [NodeItem(nt) for nt in RendermanShaderTree.nodetypes.keys()]

    # all categories in a list
    node_categories = [
        # identifier, label, items list
        RendermanShaderNodeCategory("SOMENODES", "Some Nodes",  
            items=nodeitems )
        ]
    print( "aasss --", nodeitems )
    nodeitems_utils.register_node_categories("RENDERMANSHADERNODES", node_categories)

    #bpy.app.handlers.load_post.append(load_handler)
    #bpy.app.handlers.load_pre.append(load_handler)


def unregister():
    pass
