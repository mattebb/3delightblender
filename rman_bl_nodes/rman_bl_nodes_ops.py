from bpy.props import EnumProperty, StringProperty
from operator import attrgetter, itemgetter
from .. import rman_bl_nodes
import bpy

def socket_node_input(nt, socket):
    return next((l.from_node for l in nt.links if l.to_socket == socket), None)

def socket_socket_input(nt, socket):
    return next((l.from_socket for l in nt.links if l.to_socket == socket and socket.is_linked),
                None)


def linked_sockets(sockets):
    if sockets is None:
        return []
    return [i for i in sockets if i.is_linked]

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

class NODE_OT_add_node:

    '''
    For generating cycles-style ui menus to add new nodes,
    connected to a given input socket.
    '''

    def get_type_items(self, context):
        items = []
        # if this is a pattern input do columns!
        if self.input_type.lower() == 'pattern':
            i = 0
            for pattern_cat, patterns in rman_bl_nodes.__RMAN_NODE_CATEGORIES__.items():
                if not pattern_cat.startswith('patterns_'):
                    continue
                pattern_cat = pattern_cat.split('_')[1]
                if pattern_cat.lower() in ['pxrsurface', 'script', 'manifold', 'bump', 'displace']:
                    continue
                if len(patterns[1]) < 1:
                    continue
                items.append(('', pattern_cat, pattern_cat, '', 0))

                for node_item in patterns[1]:
                    nodetype = rman_bl_nodes.__RMAN_NODE_TYPES__[node_item.nodetype]
                    items.append((nodetype.typename, nodetype.bl_label,
                                nodetype.bl_label))                
                items.append(('', '', '', '', 0))
            items.append(('REMOVE', 'Remove',
                          'Remove the node connected to this socket', '', i + 1))
            items.append(('DISCONNECT', 'Disconnect',
                          'Disconnect the node connected to this socket', '', i + 2))

        elif self.input_type.lower() in ['pxrsurface', 'manifold', 'bump']:
            pattern_key = 'patterns_%s' % self.input_type.lower()

            patterns = rman_bl_nodes.__RMAN_NODE_CATEGORIES__[pattern_key][1]
            for node_item in patterns:
                nodetype = rman_bl_nodes.__RMAN_NODE_TYPES__[node_item.nodetype]
                items.append((nodetype.typename, nodetype.bl_label,
                              nodetype.bl_label))

            items.append(('REMOVE', 'Remove',
                          'Remove the node connected to this socket'))
            items.append(('DISCONNECT', 'Disconnect',
                          'Disconnect the node connected to this socket'))
        else:
            for nodetype in rman_bl_nodes.__RMAN_NODE_TYPES__.values():
                if self.input_type.lower() == 'light' and nodetype.renderman_node_type == 'light':
                    if nodetype.__name__ == 'PxrMeshLightLightNode':
                        items.append((nodetype.typename, nodetype.bl_label,
                                      nodetype.bl_label))
                elif nodetype.renderman_node_type == self.input_type.lower():
                    items.append((nodetype.typename, nodetype.bl_label,
                                  nodetype.bl_label))
            items = sorted(items, key=itemgetter(1))
            items.append(('REMOVE', 'Remove',
                          'Remove the node connected to this socket'))
            items.append(('DISCONNECT', 'Disconnect',
                          'Disconnect the node connected to this socket'))
        return items

    node_type: EnumProperty(name="Node Type",
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
            if self.input_type in ['Pattern', 'PxrSurface', 'Manifold', 'Bump']:
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
            active_material = context.active_object.active_material
            newnode.update_mat(active_material)
            nt.nodes.remove(old_node)
        return {'FINISHED'}


class NODE_OT_add_bxdf(bpy.types.Operator, NODE_OT_add_node):

    '''
    For generating cycles-style ui menus to add new bxdfs,
    connected to a given input socket.
    '''

    bl_idname = 'node.add_bxdf'
    bl_label = 'Add Bxdf Node'
    bl_description = 'Connect a Bxdf to this socket'
    input_type: StringProperty(default='Bxdf')


class NODE_OT_add_displacement(bpy.types.Operator, NODE_OT_add_node):

    '''
    For generating cycles-style ui menus to add new nodes,
    connected to a given input socket.
    '''

    bl_idname = 'node.add_displacement'
    bl_label = 'Add Displacement Node'
    bl_description = 'Connect a Displacement shader to this socket'
    input_type: StringProperty(default='Displacement')


class NODE_OT_add_light(bpy.types.Operator, NODE_OT_add_node):

    '''
    For generating cycles-style ui menus to add new nodes,
    connected to a given input socket.
    '''

    bl_idname = 'node.add_light'
    bl_label = 'Add Light Node'
    bl_description = 'Connect a Light shader to this socket'
    input_type: StringProperty(default='Light')


class NODE_OT_add_pattern(bpy.types.Operator, NODE_OT_add_node):

    '''
    For generating cycles-style ui menus to add new nodes,
    connected to a given input socket.
    '''

    bl_idname = 'node.add_pattern'
    bl_label = 'Add Pattern Node'
    bl_description = 'Connect a Pattern to this socket'
    input_type: StringProperty(default='Pattern')


class NODE_OT_add_layer(bpy.types.Operator, NODE_OT_add_node):
    '''
    For generating cycles-style ui menus to add new nodes,
    connected to a given input socket.
    '''

    bl_idname = 'node.add_layer'
    bl_label = 'Add Layer Node'
    bl_description = 'Connect a PxrLayer'
    input_type: StringProperty(default='PxrSurface')


class NODE_OT_add_manifold(bpy.types.Operator, NODE_OT_add_node):
    '''
    For generating cycles-style ui menus to add new nodes,
    connected to a given input socket.
    '''

    bl_idname = 'node.add_manifold'
    bl_label = 'Add Manifold Node'
    bl_description = 'Connect a Manifold'
    input_type: StringProperty(default='Manifold')


class NODE_OT_add_bump(bpy.types.Operator, NODE_OT_add_node):
    '''
    For generating cycles-style ui menus to add new nodes,
    connected to a given input socket.
    '''

    bl_idname = 'node.add_bump'
    bl_label = 'Add Bump Node'
    bl_description = 'Connect a bump node'
    input_type: StringProperty(default='Bump')

classes = [
    NODE_OT_add_bxdf,
    NODE_OT_add_displacement,
    NODE_OT_add_light,
    NODE_OT_add_pattern,
    NODE_OT_add_layer,
    NODE_OT_add_manifold,
    NODE_OT_add_bump,
]

def register():
    
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)        