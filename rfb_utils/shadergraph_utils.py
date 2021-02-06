from . import color_utils
from . import filepath_utils
from . import string_utils
from . import object_utils
from ..rman_constants import RMAN_STYLIZED_FILTERS, RMAN_STYLIZED_PATTERNS, RMAN_UTILITY_PATTERN_NAMES
import math

def is_renderman_nodetree(material):
    return find_node(material, 'RendermanOutputNode')

def is_mesh_light(ob):
    '''Checks to see if ob is a RenderMan mesh light

    Args:
    ob (bpy.types.Object) - Object caller wants to check.

    Returns:
    (bpy.types.Node) - the PxrMeshLight node if this is a mesh light. Else, returns None.
    '''
        
    #mat = getattr(ob, 'active_material', None)
    mat = object_utils.get_active_material(ob)
    if not mat:
        return None
    output = is_renderman_nodetree(mat)
    if not output:
        return None
    if len(output.inputs) > 1:
        socket = output.inputs[1]
        if socket.is_linked:
            node = socket.links[0].from_node
            if node.bl_label == 'PxrMeshLight':
                return node 

    return None   

def is_rman_light(ob, include_light_filters=True):
    '''Checks to see if ob is a RenderMan light

    Args:
    ob (bpy.types.Object) - Object caller wants to check.
    include_light_filters (bool) - whether or not light filters should be included

    Returns:
    (bpy.types.Node) - the shading node, else returns None.
    '''   
    return get_light_node(ob, include_light_filters=include_light_filters)

def get_rman_light_properties_group(ob):
    '''Return the RendermanLightSettings properties
    for this object. 

    Args:
    ob (bpy.types.Object) - Object caller wants to get the RendermanLightSettings for.

    Returns:
    (RendermanLightSettings) - RendermanLightSettings object
    '''

    if ob.type == 'LIGHT':
        return ob.data.renderman
    else:
        #mat = ob.active_material
        mat = object_utils.get_active_material(ob)
        if mat:
            return mat.renderman_light

    return None

def get_light_node(ob, include_light_filters=True):
    '''Return the shading node for this light object. 

    Args:
    ob (bpy.types.Object) - Object caller is interested in.
    include_light_filters (bool) - whether or not light filters should be included    

    Returns:
    (bpy.types.Node) - The associated shading node for ob
    '''

    if ob.type == 'LIGHT':
        if hasattr(ob.data, 'renderman'):
            if include_light_filters:
                return ob.data.renderman.get_light_node()
            elif ob.data.renderman.renderman_light_role == 'RMAN_LIGHT':
                return ob.data.renderman.get_light_node()
    else:
        return is_mesh_light(ob)

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
    node_name = string_utils.sanitize_node_name('%s_%s' % (mat_name, node.name))
    return node_name

def linked_sockets(sockets):
    if sockets is None:
        return []
    return [i for i in sockets if i.is_linked]

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

def find_node_from_nodetree(ntree, nodetype):
    active_output_node = None
    for node in ntree.nodes:
        if getattr(node, "bl_idname", None) == nodetype:
            if getattr(node, "is_active_output", True):
                return node
            if not active_output_node:
                active_output_node = node
    return active_output_node

    return None

def is_soloable_node(node):
    is_soloable = False
    node_type = getattr(node, 'renderman_node_type', '')
    if node_type in ('pattern', 'bxdf'):
        if node.bl_label in ['PxrLayer', 'PxrLayerMixer']:
            is_soloable = False
        else:
            is_soloable = True
    return is_soloable

def find_soloable_node(ntree):
    selected_node = None
    for n in ntree.nodes:
        node_type = getattr(n, 'renderman_node_type', '')
        if n.select and node_type in ('pattern', 'bxdf'):
            if n.bl_label in ['PxrLayer', 'PxrLayerMixer']:
                continue
            selected_node = n
            break    
    return selected_node    

def find_selected_pattern_node(ntree):
    selected_node = None
    for n in ntree.nodes:
        node_type = getattr(n, 'renderman_node_type', '')
        if n.select and node_type == 'pattern':
            if n.bl_label in ['PxrLayer', 'PxrLayerMixer']:
                continue
            selected_node = n
            break    
    return selected_node

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

def find_projection_node(camera):
    '''Find the projection node, if any

    Arguments:
        camera (bpy.types.Camera) - Camera object

    Returns:
        (bpy.types.ShaderNode) - projection node
    '''    
    projection_node = None
    nt = camera.data.renderman.rman_nodetree
    if nt:
        output = find_node_from_nodetree(nt, 'RendermanProjectionsOutputNode')
        socket = output.inputs[0]
    
        if socket.is_linked:
            projection_node = socket.links[0].from_node  

    return projection_node       

def find_all_stylized_filters(world):
    nodes = list()
    output = find_node(world, 'RendermanDisplayfiltersOutputNode')
    if not output:
        return nodes   

    for i, socket in enumerate(output.inputs):
        if socket.is_linked:
            link = socket.links[0]
            node = link.from_node    
            if node.bl_label in RMAN_STYLIZED_FILTERS:
                nodes.append(node)

    return nodes
                          
def has_stylized_pattern_node(ob, node=None):
    prop_name = ''
    if not node:
        if len(ob.material_slots) < 1:
            return False
        mat = ob.material_slots[0].material
        nt = mat.node_tree
        output = is_renderman_nodetree(mat)
        if not output:
            return False
        socket = output.inputs[0]
        if not socket.is_linked:
            return False

        link = socket.links[0]
        node = link.from_node 

    for nm in RMAN_UTILITY_PATTERN_NAMES:
        if hasattr(node, nm):
            prop_name = nm

            prop_meta = node.prop_meta[prop_name]
            if prop_meta['renderman_type'] == 'array':
                array_len = getattr(node, '%s_arraylen' % prop_name)
                for i in range(0, array_len):
                    nm = '%s[%d]' % (prop_name, i)
                    sub_prop = getattr(node, nm)
                    if hasattr(node, 'inputs')  and nm in node.inputs and \
                        node.inputs[nm].is_linked: 

                        to_socket = node.inputs[nm]                    
                        from_node = to_socket.links[0].from_node
                        if from_node.bl_label in RMAN_STYLIZED_PATTERNS:
                            return from_node

            elif node.inputs[prop_name].is_linked: 
                to_socket = node.inputs[prop_name]                    
                from_node = to_socket.links[0].from_node
                if from_node.bl_label in RMAN_STYLIZED_PATTERNS:
                    return from_node        

    return False

def create_pxrlayer_nodes(nt, bxdf):
    mixer = nt.nodes.new("PxrLayerMixerPatternOSLNode")
    layer1 = nt.nodes.new("PxrLayerPatternOSLNode")
    layer2 = nt.nodes.new("PxrLayerPatternOSLNode")

    mixer.location = bxdf.location
    mixer.location[0] -= 300

    layer1.location = mixer.location
    layer1.location[0] -= 300
    layer1.location[1] += 300

    layer2.location = mixer.location
    layer2.location[0] -= 300
    layer2.location[1] -= 300

    nt.links.new(mixer.outputs[0], bxdf.inputs[0])
    nt.links.new(layer1.outputs[0], mixer.inputs['baselayer'])
    nt.links.new(layer2.outputs[0], mixer.inputs['layer1'])         

def _convert_grease_pencil_stroke_texture(mat, nt, output):
    gp_mat = mat.grease_pencil
    col =  gp_mat.color[:3]
    # col = color_utils.linearizeSRGB(col)
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

        mix = nt.nodes.new('PxrMixPatternNode')
        mix.color2 = col
        mix.mix = gp_mat.mix_stroke_factor
        nt.links.new(texture.outputs[0], mix.inputs[0])
        nt.links.new(mix.outputs[0], bxdf.inputs[0])

        nt.links.new(texture.outputs[4], bxdf.inputs[1])              

def _convert_grease_pencil_fill_texture(mat, nt, output):

    gp_mat = mat.grease_pencil
    col = gp_mat.fill_color[:3]
    # col = color_utils.linearizeSRGB(col)
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
        manifold.angle = -math.degrees(gp_mat.texture_angle)
        manifold.scaleS = gp_mat.texture_scale[0]
        manifold.scaleT = gp_mat.texture_scale[1]
        manifold.offsetS = gp_mat.texture_offset[0]
        manifold.offsetT = gp_mat.texture_offset[1]
        manifold.invertT = 1

        texture = nt.nodes.new('PxrTexturePatternNode')
        texture.filename = real_file
        texture.linearize = 1
        nt.links.new(manifold.outputs[0], texture.inputs[3])

        mix = nt.nodes.new('PxrMixPatternNode')
        mix.color2 = col
        mix.mix = gp_mat.mix_factor
        nt.links.new(texture.outputs[0], mix.inputs[0])
        nt.links.new(mix.outputs[0], bxdf.inputs[0])            

        nt.links.new(texture.outputs[4], bxdf.inputs[1])
        
def _convert_grease_pencil_fill_checker(mat, nt, output):

    gp_mat = mat.grease_pencil
    col = gp_mat.fill_color[:3]
    # col = color_utils.linearizeSRGB(col)
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
            # col = color_utils.linearizeSRGB(col)
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
            # col = color_utils.linearizeSRGB(col)
            alpha = gp_mat.fill_color[3]
            mix_color = gp_mat.mix_color[:3]
            mix_alpha = gp_mat.mix_color[3]    
    
            bxdf = nt.nodes.new('PxrConstantBxdfNode')
            bxdf.location = output.location
            bxdf.location[0] -= 300
            bxdf.emitColor = col
            bxdf.presence = alpha
            nt.links.new(bxdf.outputs[0], output.inputs[0])    
