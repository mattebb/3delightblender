# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 - 2021 Pixar
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
from .rfb_utils import filepath_utils
from .rfb_utils import texture_utils
from .rman_bl_nodes import __BL_NODES_MAP__

converted_nodes = {}
report = None
__CURRENT_MATERIAL__ = None


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
    elif node_type in ['ShaderNodeRGBCurve', 'ShaderNodeVectorCurve']:
        node_name = node.bl_idname
        rman_node = nt.nodes.new(node_name)
        if location:
            rman_node.location = location
        convert_rgb_curve_node(nt, node, rman_node)
        converted_nodes[node.name] = rman_node.name
        return rman_node
    elif node_type in node_map.keys():
        rman_name, convert_func = node_map[node_type]
        node_name = __BL_NODES_MAP__.get(rman_name, None)
        rman_node = nt.nodes.new(node_name)
        if location:
            rman_node.location = location
        convert_func(nt, node, rman_node)
        converted_nodes[node.name] = rman_node.name
        return rman_node
    elif node_type in ['ShaderNodeAddShader', 'ShaderNodeMixShader']:
        i = 0 if node.bl_idname == 'ShaderNodeAddShader' else 1
        node1 = node.inputs[
            0 + i].links[0].from_node if node.inputs[0 + i].is_linked else None
        node2 = node.inputs[
            1 + i].links[0].from_node if node.inputs[1 + i].is_linked else None

        if node.bl_idname == 'ShaderNodeAddShader':      
            node_name = __BL_NODES_MAP__.get('LamaAdd')  
            add = nt.nodes.new(node_name)
            if location:
                add.location = location            

            # make a new node for each
            rman_node1 = convert_cycles_bsdf(nt, add, node1, 0)
            rman_node2 = convert_cycles_bsdf(nt, add, node2, 1)

            nt.links.new(rman_node1.outputs["Bxdf"],
                        add.inputs['material1'])        
            nt.links.new(rman_node2.outputs["Bxdf"],
                        add.inputs['material2'])   

            setattr(add, "weight1", 0.5)    
            setattr(add, "weight2", 0.5)

            return add                      

        elif node.bl_idname == 'ShaderNodeMixShader': 
            node_name = __BL_NODES_MAP__.get('LamaMix')
            mixer = nt.nodes.new(node_name)
            if location:
                mixer.location = location

            convert_cycles_input(
                nt, node.inputs['Fac'], mixer, 'mix')

            # make a new node for each
            rman_node1 = convert_cycles_bsdf(nt, mixer, node1, 0)
            rman_node2 = convert_cycles_bsdf(nt, mixer, node2, 1)

            nt.links.new(rman_node1.outputs["Bxdf"],
                        mixer.inputs['material1'])        
            nt.links.new(rman_node2.outputs["Bxdf"],
                        mixer.inputs['material2'])          

            return mixer        


    elif node_type in bsdf_map.keys():
        rman_name, convert_func = bsdf_map[node_type]
        if not convert_func:
            return None

        rman_node = convert_func(nt, node)
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
        report({'ERROR'}, 'Error converting node %s of type %s.' %
               (node.name, node_type))
        return None

def set_color_space(nt, socket, rman_node, node, param_name, in_socket):
    ## FIXME: figure out a better way when we need to set
    ## colorspace to data
    from .rfb_utils import shadergraph_utils

    if node.bl_label in ['PxrTexture'] and shadergraph_utils.is_socket_float_type(in_socket):
        setattr(node, 'filename_colorspace', 'data')    


def convert_cycles_input(nt, socket, rman_node, param_name):
    if socket.is_linked:
        location = rman_node.location - \
            (socket.node.location - socket.links[0].from_node.location)
        node = convert_cycles_node(nt, socket.links[0].from_node, location)
        if node:
            out_socket = None

            # find the appropriate socket to hook up.
            in_socket = rman_node.inputs[param_name]
            if socket.links[0].from_socket.name in node.outputs:
                out_socket = node.outputs[socket.links[0].from_socket.name]
            else:
                from .rfb_utils import shadergraph_utils
                for output in node.outputs:
                    if shadergraph_utils.is_socket_same_type(in_socket, output):
                        out_socket = output
                        break
                else:
                    output = node.outputs[0]
            
            set_color_space(nt, socket, rman_node, node, param_name, in_socket)
            nt.links.new(out_socket, in_socket)

    elif hasattr(socket, 'default_value'):
        if hasattr(rman_node, 'renderman_node_type'):
            if type(getattr(rman_node, param_name)).__name__ == 'Color':
                setattr(rman_node, param_name, socket.default_value[:3])
            else:
                setattr(rman_node, param_name, socket.default_value)
        else:
            # this is a cycles node
            rman_node.inputs[param_name].default_value = socket.default_value

#########  other node conversion methods  ############


def convert_tex_image_node(nt, cycles_node, rman_node):
    bl_image = cycles_node.image
    if bl_image:
        img_path = texture_utils.get_blender_image_path(bl_image)
        if img_path != '':
            rman_node['filename'] = img_path
            texture_utils.update_texture(rman_node, light=None, mat=__CURRENT_MATERIAL__, ob=None)

    # can't link a vector to a manifold :(
    # if cycles_node.inputs['Vector'].is_linked:
    #    convert_cycles_input(nt, cycles_node.inputs['Vector'], rman_node, 'manifold')


def convert_tex_coord_node(nt, cycles_node, rman_node):
    return

def convert_attribute_node(nt, cycles_node, rman_node):   
    attr = getattr(cycles_node, 'attribute_name', '')
    setattr(rman_node, 'varname', attr)
    if cycles_node.outputs['Vector'].is_linked:
        setattr(rman_node, 'type', 'point')
    elif cycles_node.outputs['Color'].is_linked:
        setattr(rman_node, 'type', 'color')
    else:
        setattr(rman_node, 'type', 'float')        

def convert_mix_rgb_node(nt, cycles_node, rman_node):
    setattr(rman_node, 'clampOutput', cycles_node.use_clamp)
    convert_cycles_input(nt, cycles_node.inputs[
                         'Color1'], rman_node, 'bottomRGB')
    convert_cycles_input(nt, cycles_node.inputs['Color2'], rman_node, 'topRGB')
    convert_cycles_input(nt, cycles_node.inputs['Fac'], rman_node, 'topA')
    conversion = {'MIX': '10',
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
    rman_op = conversion.get(cycles_node.blend_type, '10')
    setattr(rman_node, 'operation', rman_op)


def convert_node_group(nt, cycles_node, rman_node):
    rman_nt = bpy.data.node_groups.new(rman_node.name, 'ShaderNodeTree')
    rman_node.node_tree = rman_nt
    cycles_nt = cycles_node.node_tree
    # save converted nodes to temp
    global converted_nodes
    temp_converted_nodes = converted_nodes
    converted_nodes = {}

    # create the output node
    cycles_output_node = next(
        (n for n in cycles_nt.nodes if n.bl_idname == 'NodeGroupOutput'), None)
    if cycles_output_node:
        rman_output_node = rman_nt.nodes.new('NodeGroupOutput')
        rman_output_node.location = cycles_output_node.location

        # tree outputs
        for tree_output in cycles_nt.outputs:
            out_type = tree_output.__class__.__name__.replace('Interface', '')
            rman_nt.outputs.new(out_type, tree_output.name)
    # create the input node
    cycles_input_node = next(
        (n for n in cycles_nt.nodes if n.bl_idname == 'NodeGroupInput'), None)
    if cycles_input_node:
        rman_input_node = rman_nt.nodes.new('NodeGroupInput')
        rman_input_node.location = cycles_input_node.location
        # tree outputs
        for tree_input in cycles_nt.inputs:
            input_type = tree_input.__class__.__name__.replace('Interface', '')
            rman_nt.inputs.new(input_type, tree_input.name)

        converted_nodes[cycles_input_node.name] = rman_input_node.name

    # now connect up outputs
    if cycles_output_node:
        for input in cycles_output_node.inputs:
            convert_cycles_input(rman_nt, input, rman_output_node, input.name)

    converted_nodes = temp_converted_nodes

    # rename nodes in node_group
    for node in rman_nt.nodes:
        node.name = rman_nt.name + '.' + node.name

    # convert the inputs to the group
    for input in cycles_node.inputs:
        convert_cycles_input(nt, input, rman_node, input.name)

    return


def convert_bump_node(nt, cycles_node, rman_node):
    convert_cycles_input(nt, cycles_node.inputs[
                         'Strength'], rman_node, 'scale')
    convert_cycles_input(nt, cycles_node.inputs[
                         'Height'], rman_node, 'inputBump')
    convert_cycles_input(nt, cycles_node.inputs['Normal'], rman_node, 'inputN')
    return


def convert_normal_map_node(nt, cycles_node, rman_node):
    convert_cycles_input(nt, cycles_node.inputs[
                         'Strength'], rman_node, 'bumpScale')
    convert_cycles_input(nt, cycles_node.inputs[
                         'Color'], rman_node, 'inputRGB')
    return


def convert_rgb_node(nt, cycles_node, rman_node):
    rman_node.inputRGB = cycles_node.outputs[0].default_value[:3]
    return


def convert_node_value(nt, cycles_node, rman_node):
    #rman_node.floatInput1 = cycles_node.outputs[0].default_value
    #rman_node.expression = 'floatInput1'

    val = cycles_node.outputs[0].default_value
    rman_node.input = (val, val, val)

    return


def convert_ramp_node(nt, cycles_node, rman_node):
    convert_cycles_input(nt, cycles_node.inputs['Fac'], rman_node, 'splineMap')
    actual_ramp = bpy.data.node_groups[rman_node.rman_fake_node_group].nodes[0]
    actual_ramp.color_ramp.interpolation = cycles_node.color_ramp.interpolation

    elms = actual_ramp.color_ramp.elements

    e = cycles_node.color_ramp.elements[0]
    elms[0].alpha = e.alpha
    elms[0].position = e.position
    elms[0].color = e.color

    e = cycles_node.color_ramp.elements[-1]
    elms[-1].alpha = e.alpha
    elms[-1].position = e.position
    elms[-1].color = e.color

    for e in cycles_node.color_ramp.elements[1:-1]:
        new_e = actual_ramp.color_ramp.elements.new(e.position)
        new_e.alpha = e.alpha
        new_e.color = e.color

    return

math_map = {
    'ADD': 'floatInput1 + floatInput2',
    'SUBTRACT': 'floatInput1 - floatInput2',
    'MULTIPLY': 'floatInput1 * floatInput2',
    'DIVIDE': 'floatInput1 / floatInput2',
    'SINE': 'sin(floatInput1)',
    'COSINE': 'cos(floatInput1)',
    'TANGENT': 'tan(floatInput1)',
    'ARCSINE': 'asin(floatInput1)',
    'ARCCOSINE': 'acos(floatInput1)',
    'ARCTANGENT': 'atan(floatInput1)',
    'POWER': 'floatInput1 ^ floatInput2',
    'LOGARITHM': 'log(floatInput1)',
    'MINIMUM': 'floatInput1 < floatInput2 ? floatInput1 : floatInput2',
    'MAXIMUM': 'floatInput1 > floatInput2 ? floatInput1 : floatInput2',
    'ROUND': 'round(floatInput1)',
    'LESS_THAN': 'floatInput1 < floatInput2',
    'GREATER_THAN': 'floatInput1 < floatInput2',
    'MODULO': 'floatInput1 % floatInput2',
    'ABSOLUTE': 'abs(floatInput1)',
}


def convert_math_node(nt, cycles_node, rman_node):
    convert_cycles_input(nt, cycles_node.inputs[0], rman_node, 'floatInput1')
    convert_cycles_input(nt, cycles_node.inputs[1], rman_node, 'floatInput2')

    op = cycles_node.operation
    clamp = cycles_node.use_clamp
    expr = math_map[op]
    if clamp:
        expr = 'clamp((%s), 0, 1)' % expr
    rman_node.expression = expr

    return

# this needs a special case to init the stuff


def convert_rgb_curve_node(nt, cycles_node, rman_node):
    for input in cycles_node.inputs:
        convert_cycles_input(nt, input, rman_node, input.name)

    rman_node.mapping.initialize()
    for i, mapping in cycles_node.mapping.curves.items():
        #    new_map = rman_node.mapping.curves.new()
        new_map = rman_node.mapping.curves[i]
        for p in mapping.points:
            new_map.points.new(p.location[0], p.location[1])
    return


def copy_cycles_node(nt, cycles_node, rman_node):
    #print("copying %s node" % cycles_node.bl_idname)
    # TODO copy props
    for input in cycles_node.inputs:
        convert_cycles_input(nt, input, rman_node, input.name)
    return

#########  BSDF conversion methods  ############

def convert_principled_bsdf(nt, node, rman_node):
    inputs = node.inputs

    # INPUTS: ['Base Color', 'Subsurface', 'Subsurface Radius', 
    # 'Subsurface Color', 'Metallic', 'Specular', 'Specular Tint', 
    # 'Roughness', 'Anisotropic', 'Anisotropic Rotation', 'Sheen', 
    # 'Sheen Tint', 'Clearcoat', 'Clearcoat Roughness', 'IOR', 
    # 'Transmission', 'Transmission Roughness', 'Emission', 'Alpha', 
    # 'Normal', 'Clearcoat Normal', 'Tangent']

    convert_cycles_input(nt, inputs['Base Color'], rman_node, "baseColor")
    convert_cycles_input(nt, inputs['Subsurface'], rman_node, "subsurface")
    convert_cycles_input(nt, inputs['Subsurface Color'], rman_node, "subsurfaceColor")
    convert_cycles_input(nt, inputs['Metallic'], rman_node, "metallic")
    convert_cycles_input(nt, inputs['Specular'], rman_node, "specular")
    convert_cycles_input(nt, inputs['Specular Tint'], rman_node, "specularTint")
    convert_cycles_input(nt, inputs['Roughness'], rman_node, "roughness")
    convert_cycles_input(nt, inputs['Anisotropic'], rman_node, "anisotropic")
    convert_cycles_input(nt, inputs['Sheen'], rman_node, "sheen")
    convert_cycles_input(nt, inputs['Sheen Tint'], rman_node, "sheenTint")
    convert_cycles_input(nt, inputs['Clearcoat'], rman_node, "clearcoat")
    convert_cycles_input(nt, inputs['Clearcoat Roughness'], rman_node, "clearcoatGloss")
    convert_cycles_input(nt, inputs['Normal'], rman_node, "bumpNormal")
    
def convert_diffuse_bsdf(nt, node, rman_node):

    inputs = node.inputs    
    diffuse = nt.nodes.new('LamaDiffuseBxdfNode')
    convert_cycles_input(nt, inputs['Color'], diffuse, "color")
    convert_cycles_input(nt, inputs['Roughness'],
                         diffuse, "roughness")
    convert_cycles_input(nt, inputs['Normal'], diffuse, "normal")    

    return diffuse

def convert_glossy_bsdf(nt, node, rman_node):
    inputs = node.inputs    
    conductor = nt.nodes.new('LamaConductorBxdfNode')
    
    convert_cycles_input(nt, inputs['Color'], conductor, "reflectivity")
    convert_cycles_input(nt, inputs['Color'], conductor, "edgeColor")
    convert_cycles_input(nt, inputs['Roughness'],
                         conductor, "roughness")
    convert_cycles_input(
        nt, inputs['Normal'], conductor, "normal")                         

    if type(node).__class__ == 'ShaderNodeBsdfAnisotropic':
        convert_cycles_input(
            nt, inputs['Anisotropy'], conductor, "anisotropy")                         

    return conductor    


def convert_glass_bsdf(nt, node, rman_node):

    inputs = node.inputs    
    dielectric = nt.nodes.new('LamaDielectricBxdfNode')
    setattr(dielectric, 'fresnelMode', "1")
    convert_cycles_input(nt, inputs['Color'], dielectric, "reflectionTint")
    convert_cycles_input(nt, inputs['Roughness'],
                         dielectric, "roughness")
    convert_cycles_input(nt, inputs['IOR'],
                         dielectric, "IOR")       
    convert_cycles_input(nt, inputs['Normal'], dielectric, "normal")                                             

    return dielectric    



def convert_refraction_bsdf(nt, node, rman_node):

    inputs = node.inputs    
    dielectric = nt.nodes.new('LamaDielectricBxdfNode')
    setattr(dielectric, 'fresnelMode', "1")
    convert_cycles_input(nt, inputs['Color'], dielectric, "reflectionTint")
    convert_cycles_input(nt, inputs['Roughness'],
                         dielectric, "roughness")
    convert_cycles_input(nt, inputs['IOR'],
                         dielectric, "IOR")       
    convert_cycles_input(nt, inputs['Normal'], dielectric, "normal")                                             

    return dielectric        


def convert_transparent_bsdf(nt, node, rman_node):

    inputs = node.inputs    
    dielectric = nt.nodes.new('LamaDielectricBxdfNode')
    convert_cycles_input(nt, inputs['Color'], dielectric, "reflectionTint") 
    setattr(dielectric, 'reflectivity', 1.0)
    setattr(dielectric, 'isThin', 1)                                           

    return dielectric            


def convert_translucent_bsdf(nt, node, rman_node):
    inputs = node.inputs    
    translucent = nt.nodes.new('LamaTranslucentBxdfNode')
    convert_cycles_input(nt, inputs['Color'], translucent, "reflectionTint")   
    convert_cycles_input(nt, inputs['Normal'], translucent, "normal")                                             

    return translucent            


def convert_sss_bsdf(nt, node, rman_node):

    inputs = node.inputs    
    sss = nt.nodes.new('LamaSSSBxdfNode')
    convert_cycles_input(nt, inputs['Color'], sss, "color")
    convert_cycles_input(nt, inputs['Radius'],
                         sss, "radius")
    convert_cycles_input(nt, inputs['Scale'],
                         sss, "scale")                         
    convert_cycles_input(nt, inputs['IOR'],
                         sss, "IOR")       
    convert_cycles_input(nt, inputs['Normal'], sss, "normal")                                             

    return sss          


def convert_velvet_bsdf(nt, node, rman_node):
    inputs = node.inputs    
    sheen = nt.nodes.new('LamaSheenBxdfNode')
    convert_cycles_input(nt, inputs['Color'], sheen, "color")      
    convert_cycles_input(nt, inputs['Normal'], sheen, "normal")                                             

    return sheen       


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
    'ShaderNodeMixRGB': ('PxrBlend', convert_mix_rgb_node),
    'ShaderNodeNormalMap': ('PxrNormalMap', convert_normal_map_node),
    'ShaderNodeGroup': ('PxrNodeGroup', convert_node_group),
    'ShaderNodeBump': ('PxrBump', convert_bump_node),
    'ShaderNodeValToRGB': ('PxrRamp', convert_ramp_node),
    'ShaderNodeMath': ('PxrSeExpr', convert_math_node),
    'ShaderNodeRGB': ('PxrHSL', convert_rgb_node),
    #'ShaderNodeValue': ('PxrSeExpr', convert_node_value),
    'ShaderNodeValue': ('PxrToFloat', convert_node_value),
    #'ShaderNodeRGBCurve': ('copy', copy_cycles_node),
    'ShaderNodeAttribute': ('PxrPrimvar', convert_attribute_node)
}
