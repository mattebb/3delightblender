converted_nodes = {}
report = None

def convert_cycles_node(nt, node):
    node_type = node.bl_idname
    if node_type in node_map.keys():
        rman_name, convert_func = node_map[node_type]
        if node.name in converted_nodes:
            return nt.nodes[converted_nodes[node.name]]
        else:
            rman_node = nt.nodes.new(rman_name + 'PatternNode')
            convert_func(nt, node, rman_node)
            converted_nodes[node.name] = rman_node.name
            return rman_node
    else:
        report({'WARNING'}, 'No conversion for node type %s' % node_type)
        return None

def convert_cycles_input(nt, socket, rman_node, param_name):
    if socket.is_linked:
        node = convert_cycles_node(nt, socket.links[0].from_node)
        if node:
            location_diff = socket.node.location - socket.links[0].from_node.location
            node.location = rman_node.location - location_diff
            #TODO make this better
            nt.links.new(node.outputs[0], rman_node.inputs[param_name])

    elif hasattr(socket, 'default_value'):
        if type(getattr(rman_node, param_name)).__name__ == 'Color':
            setattr(rman_node, param_name, socket.default_value[:3])
        else:
            setattr(rman_node, param_name, socket.default_value)

#########  other node conversion methods  ############
def convert_tex_image_node(nt, cycles_node, rman_node):
    if cycles_node.image.packed_file:
        cycles_node.image.unpack()
    setattr(rman_node, 'filename', cycles_node.image.filepath)
    convert_cycles_input(nt, cycles_node.inputs['Vector'], rman_node, 'manifold')

def convert_tex_coord_node(nt, cycles_node, rman_node):
    return

#########  BSDF conversion methods  ############
def convert_diffuse_bsdf(nt, node, rman_node):
    inputs = node.inputs
    setattr(rman_node, 'enableDiffuse', True)
    setattr(rman_node, 'diffuseGain', 1.0)
    convert_cycles_input(nt, inputs['Color'], rman_node, "diffuseColor")
    convert_cycles_input(nt, inputs['Roughness'], rman_node, "diffuseRoughness")
    convert_cycles_input(nt, inputs['Normal'], rman_node, "diffuseBumpNormal")

def convert_glossy_bsdf(nt, node, rman_node, spec_lobe):
    inputs = node.inputs
    lobe_name = "PrimarySpecular" if spec_lobe == 'specular' else 'RoughSpecular'
    setattr(rman_node, 'enable' + lobe_name, True)
    if rman_node.plugin_name == 'PxrLayer':
        setattr(rman_node, spec_lobe + 'Gain', 1.0)
    if spec_lobe == 'specular':
        setattr(rman_node, spec_lobe + 'FresnelMode', '1')
    convert_cycles_input(
        nt, inputs['Color'], rman_node, "%sEdgeColor" % spec_lobe)
    convert_cycles_input(
        nt, inputs['Color'], rman_node, "%sFaceColor" % spec_lobe)
    convert_cycles_input(
        nt, inputs['Roughness'], rman_node, "%sRoughness" % spec_lobe)
    convert_cycles_input(
            nt, inputs['Normal'], rman_node, "%sBumpNormal" % spec_lobe)

def convert_glass_bsdf(nt, node, rman_node):
    inputs = node.inputs
    enable_param_name = 'enableRR' if \
        rman_node.plugin_name == 'PxrLayer' else 'enableGlass'
    setattr(rman_node, enable_param_name, True)
    param_prefix = 'rrR' if rman_node.plugin_name == 'PxrLayer' else \
                    'r'
    setattr(rman_node, param_prefix + 'efractionGain', 1.0)
    setattr(rman_node, param_prefix + 'eflectionGain', 1.0)
    convert_cycles_input(nt, inputs['Color'], 
                         rman_node, param_prefix + 'efractionColor')
    param_prefix = 'rr' if rman_node.plugin_name == 'PxrLayer' else \
        'glass'
    convert_cycles_input(nt, inputs['Roughness'], 
                         rman_node, param_prefix + 'Roughness')
    convert_cycles_input(nt, inputs['IOR'], 
                             rman_node, param_prefix + 'Ior')
def convert_refraction_bsdf(nt, node, rman_node):
    inputs = node.inputs
    enable_param_name = 'enableRR' if \
        rman_node.plugin_name == 'PxrLayer' else 'enableGlass'
    setattr(rman_node, enable_param_name, True)
    param_prefix = 'rrR' if rman_node.plugin_name == 'PxrLayer' else \
                    'r'
    setattr(rman_node, param_prefix + 'efractionGain', 1.0)
    convert_cycles_input(nt, inputs['Color'], 
                         rman_node, param_prefix + 'efractionColor')
    param_prefix = 'rr' if rman_node.plugin_name == 'PxrLayer' else \
        'glass'
    convert_cycles_input(nt, inputs['Roughness'], 
                         rman_node, param_prefix + 'Roughness')
    convert_cycles_input(nt, inputs['IOR'], 
                             rman_node, param_prefix + 'Ior')

def convert_transparent_bsdf(nt, node, rman_node):
    inputs = node.inputs
    enable_param_name = 'enableRR' if \
        rman_node.plugin_name == 'PxrLayer' else 'enableGlass'
    setattr(rman_node, enable_param_name, True)
    param_prefix = 'rrR' if rman_node.plugin_name == 'PxrLayer' else \
                    'r'
    setattr(rman_node, param_prefix + 'efractionGain', 1.0)
    convert_cycles_input(nt, inputs['Color'], 
                         rman_node, param_prefix + 'efractionColor')
    param_prefix = 'rr' if rman_node.plugin_name == 'PxrLayer' else \
        'glass'
    setattr(rman_node, param_prefix + 'Ior', 1.0)

def convert_velvet_bsdf(nt, node, rman_node):
    inputs = node.inputs
    setattr(rman_node, 'enableFuzz', True)
    setattr(rman_node, 'fuzzGain', 1.0)
    convert_cycles_input(nt, inputs['Color'], rman_node, "fuzzColor")
    convert_cycles_input(
        nt, inputs['Normal'], rman_node, "fuzzBumpNormal")


bsdf_map = {
    'ShaderNodeBsdfDiffuse': ('diffuse', convert_diffuse_bsdf),
    'ShaderNodeBsdfGlossy': ('specular', convert_glossy_bsdf),
    'ShaderNodeBsdfGlass': ('glass', convert_glass_bsdf),
    'ShaderNodeBsdfRefraction': ('glass', convert_refraction_bsdf),
    'ShaderNodeBsdfTransparent': ('glass', convert_transparent_bsdf),
    'ShaderNodeBsdfVelvet': ('fuzz', convert_velvet_bsdf),
    'ShaderNodeBsdfHair': (None, None)
}

node_map = {
    'ShaderNodeTexImage': ('PxrTexture', convert_tex_image_node),
    'ShaderNodeTexCoord': ('PxrManifold2D', convert_tex_coord_node)
}

