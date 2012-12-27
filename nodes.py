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

# Derived from the NodeTree base type, similar to Menu, Operator, Panel, etc.
class RendermanShaderTree(bpy.types.NodeTree):
    '''A node tree comprised of renderman co-shader nodes'''
    bl_idname = 'RendermanShaderTree'
    bl_label = 'Renderman Shader Tree'
    bl_icon = 'TEXTURE_SHADED'

    nodetypes = []

    @classmethod
    def poll(cls, context):
        # Typical shader node test for compatible render engine setting
        return context.scene.render.engine == '3DELIGHT_RENDER'

    # Return a node tree from the context to be used in the editor
    @classmethod
    def get_from_context(cls, context):
        ob = context.active_object
        if ob:
            ma = ob.active_material
            if ma != None: 
                nt_name = ma.renderman.nodetree
                if ma and nt_name != '':
                    return bpy.data.node_groups[ma.renderman.nodetree], ma, ma

        return (None, None, None)
    
    def draw_add_menu(self, context, layout):
        add_nodetype(layout, OutputShaderNode)
        
        for nt in self.nodetypes:
            add_nodetype(layout, nt)

# Custom socket type
class RendermanShaderSocket(bpy.types.NodeSocket):
    '''Renderman co-shader input/output'''
    bl_idname = 'RendermanShaderSocket'
    bl_label = 'Renderman Shader Socket'
    bl_color = (1.0, 0.2, 0.2, 0.75)

    ui_open = bpy.props.BoolProperty(name='UI Open')

    # Optional function for drawing the socket input value
    def draw_value(self, context, layout, node):
        layout.label(self.name)


class RendermanShaderArraySocket(bpy.types.NodeSocket):
    '''Renderman co-shader array input/output'''
    bl_idname = 'RendermanShaderArraySocket'
    bl_label = 'Renderman Shader Array Socket'
    bl_color = (1.0, 0.2, 0.5, 0.75)

    ui_open = bpy.props.BoolProperty(name='UI Open')

    # Optional function for drawing the socket input value
    def draw_value(self, context, layout, node):
        layout.label(self.name)


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


# Generate dynamic types

def generate_node_type(scene, name):
    ''' Dynamically generate a node type from shader '''

    path_list = get_path_list(scene.renderman, 'shader')
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

        layout.operator('node.refresh_shader_parameters', icon='FILE_REFRESH')

        for sp in [p for p in parameters if p.meta['array']]:
            row = layout.row(align=True)
            row.label(sp.name)
            row.operator("node.add_array_socket", text='', icon='ZOOMIN').array_name = sp.name
            row.operator("node.remove_array_socket", text='', icon='ZOOMOUT').array_name = sp.name
    
    def draw_buttons_ext(self, context, layout):
        #layout.operator('node.refresh_shader_parameters', icon='FILE_REFRESH')

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

    RendermanShaderTree.nodetypes.append( ntype )







def node_shader_handle(nt, node):
    return '%s_%s' % (nt.name, node.name)

def socket_node_input(nt, socket):
    return next((l.from_node for l in nt.links if l.to_socket == socket), None)

def socket_socket_input(nt, socket):
    #if not socket.is_linked:
    #    return None
    return next((l.from_socket for l in nt.links if l.to_socket == socket and socket.is_linked), None)

def linked_sockets(sockets):
    if sockets == None:
        return []
    return [i for i in sockets if i.is_linked == True]



# UI



def draw_nodes_recursive(layout, context, ntree, input_name='Surface'):
    out = next((n for n in ntree.nodes if n.type == 'OutputShaderNode'), None)
    if out is None: return

    socket = next((s for s in out.inputs if s.name == input_name), None)
    node = socket_node_input(ntree, socket)

    split = layout.split(0.35)
    split.label(socket.name+':')
    split.operator_menu_enum("node.add_input_node", "node_type", text=node.bl_label)

    draw_nodes_rec(layout, context, ntree, node)


def draw_nodes_rec(layout, context, nt, node, level=0):

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

    # not yet 
    layout.context_pointer_set("node", node)
    node.draw_buttons(context, layout)

    # node shader inputs
    for socket in node.inputs:
        layout.context_pointer_set("node", socket_node_input(nt, node))

        if socket.is_linked:
            input_node = socket_node_input(nt, socket)
            icon = 'DISCLOSURE_TRI_DOWN' if socket.ui_open else 'DISCLOSURE_TRI_RIGHT'
            
            split = layout.split(NODE_LAYOUT_SPLIT)
            row = split.row()
            row.prop(socket, "ui_open", icon=icon, text='', icon_only=True, emboss=False)            
            indented_label(row, socket.name+':')
            
            
            split.operator_menu_enum("node.add_input_node", "node_type", text=input_node.bl_label)

            if socket.ui_open:
                draw_nodes_rec(layout, context, nt, input_node, level=level+1)

        else:
            split = layout.split(NODE_LAYOUT_SPLIT)
            row = split.row()
            row.label('', icon='BLANK1')
            indented_label(row, socket.name+':')

            #split.context_pointer_set("node", socket_node_input(nt, node))
            split.operator_menu_enum("node.add_input_node", "node_type", text='None')

    layout.separator()

    

# Operators

class NODE_OT_add_input_node(bpy.types.Operator):
    bl_idname = 'node.add_input_node'
    bl_label = 'Add Input Node'

    def node_type_items(self, context):
        items = [('DEFAULT', 'Default', '')]
        for nodetype in RendermanShaderTree.nodetypes:
            items.append( (nodetype.typename, nodetype.bl_label, nodetype.bl_label) )
        return items

    node_type = bpy.props.EnumProperty(name="Node Type",
        description='Node type to add to this socket',
        items=node_type_items)
    
    def execute(self, context):
        new_type = self.properties.node_type
        if new_type == 'DEFAULT':
            return {'CANCELLED'}

        nt = bpy.data.node_groups[context.active_object.material_slots[0].material.renderman.nodetree]
        node = context.node

        # copy existing inputs, to restore later
        inputs_data = [{'name':s.name, 'type':s.bl_idname, 'linked_output':socket_socket_input(nt, s)} for s in node.inputs]

        nt.nodes.remove(node)

        newnode = nt.nodes.new(new_type)

        # for i in inputs_data:
        #     if i['linked_output'] != None:
        #         for input in newnode.inputs()



        

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

def shader_node_rib(file, scene, nt, node, shader_type='Shader'):    
    file.write('\n')
    file.write('        %s "%s" ' % (shader_type, node.shader_name))
    if shader_type == "Shader":
        file.write('"%s"' % node_shader_handle(nt, node))
    file.write('\n')

    # Export built in parameters
    parameterlist = ptr_to_shaderparameters(scene, node)
    for sp in parameterlist:
        file.write('            "%s %s" %s\n' % (sp.data_type, sp.name, rib(sp.value)))


    # Export shader inputs
    sockets = linked_sockets(node.inputs)
    arrays = [s for s in sockets if s.bl_idname == 'RendermanShaderArraySocket']

    for i, arraysocket in enumerate(arrays):
        # check to see if we've already processed a socket with this name - don't double up
        if [s.name for s in arrays].index(arraysocket.name) < i:
            continue

        arrayinputs = [socket_node_input(nt, s) for s in sockets if s.name == arraysocket.name]
        handles = ['"%s"' % node_shader_handle(nt, n) for n in arrayinputs]
        count = [s.name for s in arrays].count(arraysocket.name)

        file.write('            "string %s[%d]" %s \n' % (arraysocket.name, count, rib(handles)) )

    for socket in [s for s in sockets if s not in arrays]:
        inode = socket_node_input(nt, socket)
        file.write('            "string %s" "%s" \n' % (socket.name, node_shader_handle(nt,inode)))


def node_gather_inputs(nt, node):
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


def export_shader_nodetree(file, scene, mat):
    nt = bpy.data.node_groups[mat.renderman.nodetree]

    out = next((n for n in nt.nodes if n.type == 'OutputShaderNode'), None)
    if out is None: return
    
    # Top level shader types, in output node
    for isocket in linked_sockets(out.inputs):

        inode = socket_node_input(nt, isocket)

        # node inputs to top level shader
        for node in node_gather_inputs(nt, inode):
            shader_node_rib(file, scene, nt, node)

        # top level shader itself
        shader_node_rib(file, scene, nt, inode, shader_type=isocket.name)

        file.write('\n')




def init():
    scene = bpy.data.scenes[0]

    for s in shaders_in_path(scene, None, threaded=False):
        generate_node_type(scene, s)