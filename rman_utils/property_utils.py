from . import texture_utils
from . import string_utils
from ..rfb_logger import rfb_log

def set_rix_param(params, param_type, param_name, val, is_reference=False, is_array=False, array_len=-1):
    if is_array:
        if type == 'float':
            params.SetFloatArray(name, val, array_len)
        elif type == 'int':
            params.SetIntegerArray(name, val, array_len)
        elif type == 'color':
            params.SetColorArray(name, val, array_len/3)
        elif type == 'string':
            params.SetStringArray(name, val, array_len)
    elif is_reference:
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

def is_renderman_nodetree(material):
    return find_node(material, 'RendermanOutputNode')

def set_material_rixparams(node, rman_sg_node, params, mat_name=None):
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
                val = string_utils.convert_val(input.default_value, type_hint=prop_type)
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
                # else output rib
                else:
                    param_type = meta['renderman_type']
                    param_name = meta['renderman_name']

                    val = string_utils.convert_val(prop, type_hint=meta['renderman_type'])
                    set_rix_param(params, param_type, param_name, val, is_reference=False)                          

    else:

        for prop_name, meta in node.prop_meta.items():
            #if prop_name in texture_utils.txmake_options().index:
            #    pass
            #elif node.plugin_name == 'PxrRamp' and prop_name in ['colors', 'positions']:
            #    pass
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
                        rfb().warning('Warning! %s not found on %s' %
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

                        

                    elif 'options' in meta and meta['options'] == 'texture' \
                            and node.bl_idname != "PxrPtexturePatternNode" or \
                            ('widget' in meta and meta['widget'] == 'assetIdInput' and prop_name != 'iesProfile'):

                        val = string_utils.convert_val(texture_utils.get_txmanager().get_txfile_from_id('%s.%s' % (node.name, param_name)), type_hint=meta['renderman_type'])
                        
                        # FIXME: Need a better way to check for a frame variable
                        if '{F' in prop:
                            rman_sg_node.is_frame_sensitive = True
                        else:
                            rman_sg_node.is_frame_sensitive = False                            
                    elif 'arraySize' in meta:
                        isArray = True
                        if type(prop) == int:
                            prop = [prop]
                        val = string_utils.convert_val(prop)
                        arrayLen = len(prop)
                    else:

                        val = string_utils.convert_val(prop, type_hint=meta['renderman_type'])

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

def set_rixparams(node, rman_sg_node, params, light):
    for prop_name, meta in node.prop_meta.items():
        if not hasattr(node, prop_name):
            continue
        prop = getattr(node, prop_name)
        # if property group recurse
        if meta['renderman_type'] == 'page' or prop_name == 'notes' or meta['renderman_type'] == 'enum':
            continue
        else:
            type = meta['renderman_type']
            name = meta['renderman_name']
            # if struct is not linked continue
            if 'arraySize' in meta:
                set_rix_param(params, type, name, string_utils.convert_val(prop), is_reference=False, is_array=True, array_len=len(prop))

            elif ('widget' in meta and meta['widget'] == 'assetIdInput' and prop_name != 'iesProfile'):
                if light:
                    params.SetString(name, texture_utils.get_txmanager().get_txfile_from_id('%s.%s' % (light.name, prop_name)))
                else:
                    params.SetString(name, texture_utils.get_txmanager().get_txfile_from_id('%s.%s' % (node.name, prop_name)))
                
                # FIXME: Need a better way to check for a frame variable
                if '{F' in prop:
                    rman_sg_node.is_frame_sensitive = True
                else:
                    rman_sg_node.is_frame_sensitive = False

            else:
                val = string_utils.convert_val(prop, type_hint=type)
                set_rix_param(params, type, name, val)

        if node.plugin_name in ['PxrBlockerLightFilter', 'PxrRampLightFilter', 'PxrRodLightFilter']:
            rm = light.renderman
            nt = light.node_tree
            if nt and rm.float_ramp_node in nt.nodes.keys():
                knot_param = 'ramp_Knots' if node.plugin_name == 'PxrRampLightFilter' else 'falloff_Knots'
                float_param = 'ramp_Floats' if node.plugin_name == 'PxrRampLightFilter' else 'falloff_Floats'
                params.Remove('%s' % knot_param)
                params.Remove('%s' % float_param)
                float_node = nt.nodes[rm.float_ramp_node]
                curve = float_node.mapping.curves[0]
                knots = []
                vals = []
                # double the start and end points
                knots.append(curve.points[0].location[0])
                vals.append(curve.points[0].location[1])
                for p in curve.points:
                    knots.append(p.location[0])
                    vals.append(p.location[1])
                knots.append(curve.points[-1].location[0])
                vals.append(curve.points[-1].location[1])

                params.SetFloatArray(knot_param, knots, len(knots))
                params.SetFloatArray(float_param, vals, len(vals))

            if nt and rm.color_ramp_node in nt.nodes.keys():
                params.Remove('colorRamp_Knots')
                color_node = nt.nodes[rm.color_ramp_node]
                color_ramp = color_node.color_ramp
                colors = []
                positions = []
                # double the start and end points
                positions.append(float(color_ramp.elements[0].position))
                colors.extend(color_ramp.elements[0].color[:3])
                for e in color_ramp.elements:
                    positions.append(float(e.position))
                    colors.extend(e.color[:3])
                positions.append(
                    float(color_ramp.elements[-1].position))
                colors.extend(color_ramp.elements[-1].color[:3])

                params.SetFloatArray('colorRamp_Knots', positions, len(positions))
                params.SetColorArray('colorRamp_Colors', colors, len(positions))               


def property_group_to_rixparams(node, rman_sg_node, sg_node, light=None, mat_name=None):

    params = sg_node.params
    if mat_name:
        set_material_rixparams(node, rman_sg_node, params, mat_name=mat_name)
    else:
        set_rixparams(node, rman_sg_node, params, light=light)


def portal_inherit_dome_params(portal_node, dome, dome_node, rixparams):

    rixparams.SetString('domeColorMap', string_utils.convert_val(texture_utils.get_txmanager().get_txfile_from_id('%s.lightColorMap' % (dome.name))))

    prop = getattr(portal_node, 'colorMapGamma')
    if string_utils.convert_val(prop) == (1.0, 1.0, 1.0):
        prop = getattr(dome_node, 'colorMapGamma')
        rixparams.SetVector('colorMapGamma', string_utils.convert_val(prop, type_hint='vector'))

    prop = getattr(portal_node, 'colorMapSaturation')
    if string_utils.convert_val(prop) == 1.0:
        prop = getattr(dome_node, 'colorMapSaturation')
        rixparams.SetFloat('colorMapSaturation', string_utils.convert_val(prop, type_hint='float'))

    prop = getattr(portal_node, 'enableTemperature')
    if string_utils.convert_val(prop):
        prop = getattr(dome_node, 'enableTemperature')
        rixparams.SetInteger('enableTemperature', string_utils.convert_val(prop, type_hint='int'))        
        prop = getattr(dome_node, 'temperature')
        rixparams.SetFloat('temperature', string_utils.convert_val(prop, type_hint='float'))   

    prop = getattr(dome_node, 'intensity')
    rixparams.SetFloat('intensity', string_utils.convert_val(prop, type_hint='float'))        
    prop = getattr(dome_node, 'exposure')
    rixparams.SetFloat('exposure', string_utils.convert_val(prop, type_hint='float')) 
    prop = getattr(dome_node, 'specular')
    rixparams.SetFloat('specular', string_utils.convert_val(prop, type_hint='float'))  
    prop = getattr(dome_node, 'diffuse')
    rixparams.SetFloat('diffuse', string_utils.convert_val(prop, type_hint='float'))   
    prop = getattr(dome_node, 'lightColor')
    rixparams.SetColor('lightColor', string_utils.convert_val(prop, type_hint='color')) 