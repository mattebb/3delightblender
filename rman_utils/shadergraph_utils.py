from . import color_utils
from . import filepath_utils
import math

def is_renderman_nodetree(material):
    return find_node(material, 'RendermanOutputNode')

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
    return "%s_%s" % (mat_name, node.name.replace(' ', ''))

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

def find_integrator_node(world):
    '''Find and return the integrator node from the world nodetree

    Arguments:
        world (bpy.types.World) - Blender world object

    Returns:
        (RendermanIntegratorNode) - the integrator ShadingNode
    '''
    rm = world.renderman
    if not world.renderman.use_renderman_node:
        return None
    
    output = find_node(world, 'RendermanIntegratorsOutputNode')
    if output:
        socket = output.inputs[0]
        if socket.is_linked:
            return socket.links[0].from_node

    return None

def find_displayfilter_nodes(world):
    '''Find and return all display filter nodes from the world nodetree

    Arguments:
        world (bpy.types.World) - Blender world object

    Returns:
        (list) - list of display filter nodes
    '''  
    df_nodes = []      
    if not world.renderman.use_renderman_node:
        return df_nodes 

    output = find_node(world, 'RendermanDisplayfiltersOutputNode')
    if output:
        for i, socket in enumerate(output.inputs):
            if socket.is_linked:
                bl_df_node = socket.links[0].from_node
                df_nodes.append(bl_df_node)   

    return df_nodes      

def find_samplefilter_nodes(world):
    '''Find and return all sample filter nodes from the world nodetree

    Arguments:
        world (bpy.types.World) - Blender world object

    Returns:
        (list) - list of sample filter nodes
    '''    
    sf_nodes = []
    if not world.renderman.use_renderman_node:
        return sf_nodes 

    output = find_node(world, 'RendermanSamplefiltersOutputNode')
    if output:
        for i, socket in enumerate(output.inputs):
            if socket.is_linked:
                bl_sf_node = socket.links[0].from_node
                sf_nodes.append(bl_sf_node)   

    return sf_nodes

def _convert_grease_pencil_stroke_texture(mat, nt, output):
    gp_mat = mat.grease_pencil
    col =  gp_mat.color[:3]
    col = color_utils.linearizeSRGB(col)
    alpha = gp_mat.color[3]

    bl_image = gp_mat.stroke_image
    bxdf = nt.nodes.new('PxrConstantBxdfNode')
    bxdf.location = output.location
    bxdf.location[0] -= 300
    bxdf.emitColor = col
    bxdf.presence = alpha
    nt.links.new(bxdf.outputs[0], output.inputs[0])

    if not bl_image:
        bxdf.emitColor = [0.0, 0.0, 0.0, 1.0]
    else:
        real_file = filepath_utils.get_real_path(bl_image.filepath)
        manifold = nt.nodes.new('PxrManifold2DPatternNode')
        manifold.angle = -math.degrees(gp_mat.pattern_angle)
        manifold.scaleS = gp_mat.pattern_scale[0]
        manifold.scaleT = gp_mat.pattern_scale[1]
        manifold.offsetS = gp_mat.texture_offset[0]
        manifold.offsetT = gp_mat.texture_offset[1]
        manifold.invertT = 1

        texture = nt.nodes.new('PxrTexturePatternNode')
        texture.filename = real_file
        texture.linearize = 1
        nt.links.new(manifold.outputs[0], texture.inputs[3])  

        if gp_mat.use_stroke_pattern:
            bxdf.emitColor = col
        elif gp_mat.use_stroke_texture_mix:
            mix = nt.nodes.new('PxrMixPatternNode')
            mix.color2 = col
            mix.mix = gp_mat.mix_stroke_factor
            nt.links.new(texture.outputs[0], mix.inputs[0])
            nt.links.new(mix.outputs[0], bxdf.inputs[0])
        else:
            nt.links.new(texture.outputs[0], bxdf.inputs[0])
            params.ReferenceColor("emitColor", '%s:resultRGB' % texture_handle)
        nt.links.new(texture.outputs[4], bxdf.inputs[1])              

def _convert_grease_pencil_fill_texture(mat, nt, output):

    gp_mat = mat.grease_pencil
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

    bl_image = gp_mat.fill_image

    if not bl_image:
        bxdf.emitColor = [0.0, 0.0, 0.0, 1.0]
    else:
        real_file = filepath_utils.get_real_path(bl_image.filepath)
        manifold = nt.nodes.new('PxrManifold2DPatternNode')
        manifold.angle = -math.degrees(gp_mat.pattern_angle)
        manifold.scaleS = gp_mat.pattern_scale[0]
        manifold.scaleT = gp_mat.pattern_scale[1]
        manifold.offsetS = gp_mat.texture_offset[0]
        manifold.offsetT = gp_mat.texture_offset[1]
        manifold.invertT = 1

        texture = nt.nodes.new('PxrTexturePatternNode')
        texture.filename = real_file
        texture.linearize = 1
        nt.links.new(manifold.outputs[0], texture.inputs[3])

        if gp_mat.use_fill_pattern:
            bxdf.emitColor = col
        elif gp_mat.use_fill_texture_mix:
            mix = nt.nodes.new('PxrMixPatternNode')
            mix.color2 = col
            mix.mix = gp_mat.mix_factor
            nt.links.new(texture.outputs[0], mix.inputs[0])
            nt.links.new(mix.outputs[0], bxdf.inputs[0])
        else:
            nt.links.new(texture.outputs[0], bxdf.inputs[0])
            params.ReferenceColor("emitColor", '%s:resultRGB' % texture_handle)
        nt.links.new(texture.outputs[4], bxdf.inputs[1])
        
def _convert_grease_pencil_fill_checker(mat, nt, output):

    gp_mat = mat.grease_pencil
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

    manifold = nt.nodes.new('PxrManifold2DPatternNode')
    manifold.angle = -math.degrees(gp_mat.pattern_angle)
    manifold.scaleS = (1/gp_mat.pattern_gridsize) * gp_mat.pattern_scale[0]
    manifold.scaleT = (1/gp_mat.pattern_gridsize) * gp_mat.pattern_scale[1]

    checker = nt.nodes.new('PxrCheckerPatternNode')
    checker.colorA = col
    checker.colorB = mix_color

    nt.links.new(manifold.outputs[0], checker.inputs[2])

    checker2 = nt.nodes.new('PxrCheckerPatternNode')
    checker2.colorA = col
    checker2.colorB = mix_color 

    nt.links.new(manifold.outputs[0], checker2.inputs[2])

    float3_1 = nt.nodes.new('PxrToFloat3PatternNode')
    float3_1.input = alpha

    float3_2 = nt.nodes.new('PxrToFloat3PatternNode')
    float3_2.input = mix_alpha

    mix = nt.nodes.new('PxrMixPatternNode')
    nt.links.new(float3_1.outputs[0], mix.inputs[0])
    nt.links.new(float3_2.outputs[0], mix.inputs[1])
    nt.links.new(checker2.outputs[1], mix.inputs[2])

    nt.links.new(checker.outputs[0], bxdf.inputs[0])
    nt.links.new(mix.outputs[0], bxdf.inputs[1])

def convert_grease_pencil_mat(mat, nt, output):
    gp_mat = mat.grease_pencil
    if gp_mat.show_stroke:
        stroke_style = gp_mat.stroke_style
        if stroke_style == 'TEXTURE':
            _convert_grease_pencil_stroke_texture(mat, nt, output)
        else:
            col =  gp_mat.color[:3]
            col = color_utils.linearizeSRGB(col)
            alpha = gp_mat.color[3]

            bxdf = nt.nodes.new('PxrConstantBxdfNode')
            bxdf.location = output.location
            bxdf.location[0] -= 300
            bxdf.emitColor = col
            bxdf.presence = alpha
            nt.links.new(bxdf.outputs[0], output.inputs[0])    
    elif gp_mat.show_fill:
        fill_style = gp_mat.fill_style
        if fill_style == 'CHECKER':
            _convert_grease_pencil_fill_checker(mat, nt, output)
        elif fill_style == 'TEXTURE':
            _convert_grease_pencil_fill_texture(mat, nt, output)
        else:    
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
