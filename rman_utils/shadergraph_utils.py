from . import color_utils

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

def get_node_name(node, mat_name):
    return "%s.%s" % (mat_name, node.name.replace(' ', ''))

def linked_sockets(sockets):
    if sockets is None:
        return []
    return [i for i in sockets if i.is_linked]

# do we need to convert this socket?
def do_convert_socket(from_socket, to_socket):
    if not to_socket:
        return False
    return (is_float_type(from_socket) and is_float3_type(to_socket)) or \
        (is_float3_type(from_socket) and is_float_type(to_socket))

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

def convert_grease_pencil_mat(mat, nt, output):
    if mat.grease_pencil.show_stroke:
        col =  mat.grease_pencil.color[:3]
        col = color_utils.linearizeSRGB(col)
        alpha = mat.grease_pencil.color[3]

        bxdf = nt.nodes.new('PxrConstantBxdfNode')
        bxdf.location = output.location
        bxdf.location[0] -= 300
        bxdf.emitColor = col
        bxdf.presence = alpha
        nt.links.new(bxdf.outputs[0], output.inputs[0])    
    elif mat.grease_pencil.show_fill:
        gp_mat = mat.grease_pencil
        fill_style = gp_mat.fill_style
        col = gp_mat.fill_color[:3]
        col = color_utils.linearizeSRGB(col)
        alpha = gp_mat.fill_color[3]
        mix_color = gp_mat.mix_color[:3]
        mix_alpha = gp_mat.mix_color[3]    
  
        bxdf = nt.nodes.new('PxrConstantBxdfNode')
        bxdf.location = output.location
        bxdf.location[0] -= 300
        bxdf.emitColor = col
        bxdf.presence = alpha
        nt.links.new(bxdf.outputs[0], output.inputs[0])    
