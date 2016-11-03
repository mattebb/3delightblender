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

converted_nodes = {}
report = None

def convert_cycles_node(nt, node, location=None):
    node_type = node.bl_idname
    if node.name in converted_nodes:
        return nt.nodes[converted_nodes[node.name]]

    elif node_type == 'ShaderNodeGroup':
        node_name = node.bl_idname
        rman_node = nt.nodes.new(node_name)
        if location:
            rman_node.location = location
        convert_node_group(nt, node, rman_node)
        converted_nodes[node.name] = rman_node.name
        return rman_node
    elif node_type in node_map.keys():
        rman_name, convert_func = node_map[node_type]
        node_name = rman_name + 'PatternNode'
        rman_node = nt.nodes.new(node_name)
        if location:
            rman_node.location = location
        convert_func(nt, node, rman_node)
        converted_nodes[node.name] = rman_node.name
        return rman_node
    # else this is just copying the osl node!
    # TODO make this an RMAN osl node
    elif node_type != 'NodeUndefined':
        node_name = node.bl_idname
        rman_node = nt.nodes.new(node_name)
        if location:
            rman_node.location = location
        copy_cycles_node(nt, node, rman_node)
        converted_nodes[node.name] = rman_node.name
        return rman_node
    else:
        report({'ERROR'}, 'Error converting node %s of type %s.' % (node.name, node_type))
        return None
        

def convert_cycles_input(nt, socket, rman_node, param_name):
    if socket.is_linked:
        location = rman_node.location - (socket.node.location - socket.links[0].from_node.location)
        node = convert_cycles_node(nt, socket.links[0].from_node, location)
        if node:
            #find the appropriate socket to hook up. 
            input = rman_node.inputs[param_name]
            if socket.links[0].from_socket.name in node.outputs:
                nt.links.new(node.outputs[socket.links[0].from_socket.name], input)
            else:
                for output in node.outputs:
                    from .nodes import is_same_type
                    if output.type == input.type or is_same_type(input, output):
                        nt.links.new(output, input)
                        break
                else:
                    nt.links.new(node.outputs[0], rman_node.inputs[param_name])

    elif hasattr(socket, 'default_value'):
        if hasattr(rman_node, 'renderman_node_type'):
            if type(getattr(rman_node, param_name)).__name__ == 'Color':
                setattr(rman_node, param_name, socket.default_value[:3])
            else:
                setattr(rman_node, param_name, socket.default_value)
        else:
            #this is a cycles node
            rman_node.inputs[param_name].default_value = socket.default_value

#########  other node conversion methods  ############
def convert_tex_image_node(nt, cycles_node, rman_node):
    if cycles_node.image:
        if cycles_node.image.packed_file:
            cycles_node.image.unpack()
        setattr(rman_node, 'filename', cycles_node.image.filepath)
    
    # can't link a vector to a manifold :(
    #if cycles_node.inputs['Vector'].is_linked:
    #    convert_cycles_input(nt, cycles_node.inputs['Vector'], rman_node, 'manifold')

def convert_tex_coord_node(nt, cycles_node, rman_node):
    return

def convert_mix_rgb_node(nt, cycles_node, rman_node):
    setattr(rman_node, 'clampOutput', cycles_node.use_clamp)
    convert_cycles_input(nt, cycles_node.inputs['Color1'], rman_node, 'bottomRGB')
    convert_cycles_input(nt, cycles_node.inputs['Color2'], rman_node, 'topRGB')
    convert_cycles_input(nt, cycles_node.inputs['Fac'], rman_node, 'topA')
    conversion  = {'MIX': '10',
                'ADD': '19', 
                'MULTIPLY': '18', 
                'SUBTRACT': '25', 
                'SCREEN': '23',
                'DIVIDE': '7',
                'DIFFERENCE': '5',
                'DARKEN': '3',
                'LIGHTEN': '12',
                'OVERLAY': '20',
                'DODGE': '15',
                'BURN': '14', 
                'HUE': '11',
                'SATURATION': '22',
                'VALUE': '17',
                'COLOR': '0',
                'SOFT_LIGHT': '24',
                'LINEAR_LIGHT': '16'}
    setattr(rman_node, 'operation', conversion[cycles_node.blend_type])

def convert_node_group(nt, cycles_node, rman_node):
    rman_nt = bpy.data.node_groups.new(rman_node.name, 'ShaderNodeTree')
    rman_node.node_tree = rman_nt
    cycles_nt = cycles_node.node_tree

    # create the output node
    cycles_output_node = next((n for n in cycles_nt.nodes if n.bl_idname == 'NodeGroupOutput'), None)
    if cycles_output_node:
        rman_output_node = rman_nt.nodes.new('NodeGroupOutput')
        rman_output_node.location = cycles_output_node.location
       
        #tree outputs
        for tree_output in cycles_nt.outputs:
            out_type = tree_output.__class__.__name__.replace('Interface', '')
            rman_nt.outputs.new(out_type, tree_output.name)
    # create the input node
    cycles_input_node = next((n for n in cycles_nt.nodes if n.bl_idname == 'NodeGroupInput'), None)
    if cycles_input_node:
        rman_input_node = rman_nt.nodes.new('NodeGroupInput')
        rman_input_node.location = cycles_input_node.location
        #tree outputs
        for tree_input in cycles_nt.inputs:
            input_type = tree_input.__class__.__name__.replace('Interface', '')
            rman_nt.input.new(input_type, tree_input.name)
        
        converted_nodes[cycles_input_node.name] = rman_input_node.name
    
    # now connect up outputs
    if cycles_output_node:
        for input in cycles_output_node.inputs:
            convert_cycles_input(rman_nt, input, rman_output_node, input.name)


    # find the output node
    #cycles_output_node = next((n for n in cycles_nt.nodes if n.bl_idname == 'NodeGroupOutput'), None)
    #if cycles_output_node:
    #    rman_output_node = rman_nt.nodes.new('NodeGroupOutput')
    #    rman_output_node.location = cycles_output_node.location
    #    for input in cycles_output_node.inputs:
    #        rman_output_node.inputs.new(input.name, input.bl_idname)
    #        convert_cycles_input(rman_nt, input, rman_output_node, input.name)

    return

def convert_bump_node(nt, cycles_node, rman_node):
    print("TODO convert bump node")
    return

def convert_normal_map_node(nt, cycles_node, rman_node):
    convert_cycles_input(nt, cycles_node.inputs['Strength'], rman_node, 'bumpScale')
    convert_cycles_input(nt, cycles_node.inputs['Color'], rman_node, 'inputRGB')
    return

def copy_cycles_node(nt, cycles_node, rman_node):
    print("copying %s node" % cycles_node.bl_idname)
    # TODO copy props
    for input in cycles_node.inputs:
        convert_cycles_input(nt, input, rman_node, input.name)
    return

#########  BSDF conversion methods  ############
def convert_diffuse_bsdf(nt, node, rman_node):
    inputs = node.inputs
    setattr(rman_node, 'enableDiffuse', True)
    setattr(rman_node, 'diffuseGain', 1.0)
    convert_cycles_input(nt, inputs['Color'], rman_node, "diffuseColor")
    convert_cycles_input(nt, inputs['Roughness'], rman_node, "diffuseRoughness")
    convert_cycles_input(nt, inputs['Normal'], rman_node, "diffuseBumpNormal")

def convert_glossy_bsdf(nt, node, rman_node):
    inputs = node.inputs
    lobe_name = "Specular" if rman_node.plugin_name == 'PxrLayer' else "PrimarySpecular"
    setattr(rman_node, 'enable' + lobe_name, True)
    if rman_node.plugin_name == 'PxrLayer':
        setattr(rman_node, 'specularGain', 1.0)
    #if spec_lobe == 'specular':
    #    setattr(rman_node, spec_lobe + 'FresnelMode', '1')
    convert_cycles_input(
        nt, inputs['Color'], rman_node, "specularEdgeColor")
    convert_cycles_input(
        nt, inputs['Color'], rman_node, "specularFaceColor")
    convert_cycles_input(
        nt, inputs['Roughness'], rman_node, "specularRoughness")
    convert_cycles_input(
            nt, inputs['Normal'], rman_node, "specularBumpNormal")

    if type(node).__class__ == 'ShaderNodeBsdfAnisotropic':
        convert_cycles_input(
            nt, inputs['Anisotropy'], rman_node, "specularAnisotropy")

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
    setattr(rman_node, param_prefix + 'Roughness', 0.0)
    setattr(rman_node, param_prefix + 'Ior', 1.0)

def convert_translucent_bsdf(nt, node, rman_node):
    inputs = node.inputs
    enable = 'enableSinglescatter' if rman_node.plugin_name == 'PxrLayer' else \
                    'enableSingleScatter'
    setattr(rman_node, enable, True)
    setattr(rman_node, 'singlescatterGain', 1.0)
    setattr(rman_node, 'singlescatterMfpColor', [1.0, 1.0, 1.0])
    convert_cycles_input(nt, inputs['Color'], rman_node, "singlescatterColor")

def convert_sss_bsdf(nt, node, rman_node):
    inputs = node.inputs
    setattr(rman_node, 'enableSubsurface', True)
    convert_cycles_input(nt, inputs['Color'], rman_node, "subsurfaceColor")
    convert_cycles_input(nt, inputs['Radius'], rman_node, "subsurfaceDmfpColor")
    convert_cycles_input(nt, inputs['Scale'], rman_node, "subsurfaceDmfp")

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
    'ShaderNodeBsdfAnisotropic': ('specular', convert_glossy_bsdf),
    'ShaderNodeBsdfGlass': ('glass', convert_glass_bsdf),
    'ShaderNodeBsdfRefraction': ('glass', convert_refraction_bsdf),
    'ShaderNodeBsdfTransparent': ('glass', convert_transparent_bsdf),
    'ShaderNodeBsdfTranslucent': ('singlescatter', convert_translucent_bsdf),
    'ShaderNodeBsdfVelvet': ('fuzz', convert_velvet_bsdf),
    'ShaderNodeSubsurfaceScattering': ('subsurface', convert_sss_bsdf),
    'ShaderNodeBsdfHair': (None, None),
    'ShaderNodeEmission': (None, None),
    'ShaderNodeGroup': (None, None)
}

# we only convert the important shaders, all others are copied from cycles osl
node_map = {
    'ShaderNodeTexImage': ('PxrTexture', convert_tex_image_node),
    #'ShaderNodeTexCoord': ('PxrManifold2D', convert_tex_coord_node),
    #'ShaderNodeRGBToBW': ('PxrToFloat', convert_rgb_to_bw_node),
    'ShaderNodeMixRGB': ('PxrBlend', convert_mix_rgb_node),
    #'ShaderNodeTexVoronoi': ('PxrVoronoise', convert_voronoi_node),
    'ShaderNodeNormalMap': ('PxrNormalMap', convert_normal_map_node),
    'ShaderNodeGroup': ('PxrNodeGroup', convert_node_group),
    'ShaderNodeBump': ('PxrBump', convert_bump_node)
    #'ShaderNodeHueSaturation': ('PxrHSL', convert_hsv_node),
    #'ShaderNodeTexNoise': ('copy', copy_cycles_node),
    #'ShaderNodeLayerWeight': ('copy', copy_cycles_node),
    #'ShaderNodeBrightContrast': ('copy', copy_cycles_node),
    #'ShaderNodeMath': ('copy', copy_cycles_node),
    #'ShaderNodeFresnel': ('copy', copy_cycles_node),
    #'ShaderNodeMapping': ('copy', copy_cycles_node),
    #TODO switch val to rgb to pxr ramp
    #'ShaderNodeValToRGB': ('copy', copy_cycles_node),
    #'ShaderNodeRGBCurve': ('copy', copy_cycles_node),
}

