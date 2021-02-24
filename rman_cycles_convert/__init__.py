from ..rfb_logger import rfb_log
from .cycles_convert import *
from .cycles_convert import _BSDF_MAP_
from ..rfb_utils import shadergraph_utils
from ..rman_bl_nodes import __BL_NODES_MAP__

_COMBINE_NODES_ = ['ShaderNodeAddShader', 'ShaderNodeMixShader']

def create_rman_surface(nt, parent_node, input_index, node_name=None):
    if not node_name:
        node_name = __BL_NODES_MAP__.get('PxrDisneyBsdf')
    rman_surf = nt.nodes.new(node_name)
    nt.links.new(rman_surf.outputs[0], parent_node.inputs[input_index])

    rman_surf.location = parent_node.location
    rman_surf.location[0] -= 300
    return rman_surf

def convert_cycles_bsdf(nt, rman_parent, node, input_index):

    # if mix or add pass both to parent
    if node.bl_idname in _COMBINE_NODES_:
        i = 0 if node.bl_idname == 'ShaderNodeAddShader' else 1

        node1 = node.inputs[
            0 + i].links[0].from_node if node.inputs[0 + i].is_linked else None
        node2 = node.inputs[
            1 + i].links[0].from_node if node.inputs[1 + i].is_linked else None

        if not node1 and not node2:
            return
        elif not node1:
            rman_node2 = convert_cycles_bsdf(nt, rman_parent, node2, input_index)
            if rman_parent.bl_label == 'LamaSurface':
                nt.links.new(rman_node2.outputs["Bxdf"],
                             rman_parent.inputs['materialFront'])    
            else:
                nt.links.new(rman_node2.outputs["Bxdf"],
                             rman_parent.inputs[input_index])                                  

        elif not node2:
            rman_node1 = convert_cycles_bsdf(nt, rman_parent, node1, input_index)
            if rman_parent.bl_label == 'LamaSurface':
                nt.links.new(rman_node1.outputs["Bxdf"],
                             rman_parent.inputs['materialFront'])  
            else:
                nt.links.new(rman_node1.outputs["Bxdf"],
                             rman_parent.inputs[input_index])                                          

        elif node.bl_idname == 'ShaderNodeAddShader':

            node_name = __BL_NODES_MAP__.get('LamaAdd')
            add = nt.nodes.new(node_name)
            if rman_parent.bl_label == 'LamaSurface':
                nt.links.new(add.outputs["Bxdf"],
                             rman_parent.inputs['materialFront'])
            else:
                nt.links.new(add.outputs["Bxdf"],
                             rman_parent.inputs[input_index])     
            offset_node_location(rman_parent, add, node)

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
            if rman_parent.bl_label == 'LamaSurface':
                nt.links.new(mixer.outputs["Bxdf"],
                             rman_parent.inputs['materialFront'])
            else:
                nt.links.new(mixer.outputs["Bxdf"],
                             rman_parent.inputs[input_index])                
            offset_node_location(rman_parent, mixer, node)

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

    elif 'Bsdf' in node.bl_idname or node.bl_idname == 'ShaderNodeSubsurfaceScattering':
        node_type = node.bl_idname
        rman_node = _BSDF_MAP_[node_type][1](nt, node, rman_parent)
        if rman_parent.bl_label == 'LamaSurface':
            nt.links.new(rman_node.outputs["Bxdf"],
                            rman_parent.inputs['materialFront'])  
            if node.bl_idname == 'ShaderNodeBsdfTransparent':
                setattr(rman_parent, 'presence', 0.0)
        return rman_node

    elif node.bl_idname == 'ShaderNodeEmission':

        node_name = __BL_NODES_MAP__.get('LamaEmission')
        emission = nt.nodes.new(node_name)
        convert_cycles_input(nt, node.inputs['Color'], emission, "color")  
        if not node.inputs['Color'].is_linked and not node.inputs['Strength']:
            emission_color = getattr(emission, 'color')
            emission_color = node.inputs['Strength'] * emission_color
            setattr(emission, 'color', emission_color)    


        if rman_parent.bl_label == 'LamaSurface':
            nt.links.new(emission.outputs["Bxdf"],
                            rman_parent.inputs['materialFront'])
        else:
            nt.links.new(emission.outputs["Bxdf"],
                            rman_parent.inputs[input_index])     
        offset_node_location(rman_parent, emission, node)

        return emission


    else:
        rman_node = convert_cycles_node(nt, node)
        nt.links.new(rman_node.outputs[0], rman_parent.inputs[input_index])
        return rman_node


def convert_cycles_displacement(nt, surface_node, displace_socket, output_node):

    if displace_socket.is_linked:
       node_name = __BL_NODES_MAP__.get('PxrDisplace')
       displace = nt.nodes.new(node_name)
       nt.links.new(displace.outputs[0], output_node.inputs['Displacement'])
       displace.location = output_node.location
       displace.location[0] -= 200
       displace.location[1] -= 100

       setattr(displace, 'dispAmount', .01)
       convert_cycles_input(nt, displace_socket, displace, "dispVector")
    
def set_ouput_node_location(nt, output_node, cycles_output):
    output_node.location = cycles_output.location
    output_node.location[1] -= 500

def offset_node_location(rman_parent, rman_node, cycles_node):
    linked_socket = next((sock for sock in cycles_node.outputs if sock.is_linked),
                         None)
    rman_node.location = rman_parent.location
    if linked_socket:
        rman_node.location += (cycles_node.location -
                               linked_socket.links[0].to_node.location)    

def convert_cycles_nodetree(id, output_node):
    # find base node
    from . import cycles_convert
    cycles_convert.converted_nodes = {}
    cycles_convert.__CURRENT_MATERIAL__ = id
    nt = id.node_tree
    rfb_log().info('Converting material ' + id.name + ' to RenderMan')
    cycles_output_node = shadergraph_utils.find_node(id, 'ShaderNodeOutputMaterial')
    if not cycles_output_node:
        rfb_log().warning('No Cycles output found ' + id.name)
        return False

    # if no bsdf return false
    if not cycles_output_node.inputs[0].is_linked:
        rfb_log().warning('No Cycles bsdf found ' + id.name)
        return False

    # set the output node location
    set_ouput_node_location(nt, output_node, cycles_output_node)

    # walk tree
    begin_cycles_node = cycles_output_node.inputs[0].links[0].from_node
    # if this is an emission use PxrMeshLight
    if begin_cycles_node.bl_idname == "ShaderNodeEmission":
        node_name = __BL_NODES_MAP__.get('PxrMeshLight')
        meshlight = nt.nodes.new(node_name)
        nt.links.new(meshlight.outputs[0], output_node.inputs["Light"])
        offset_node_location(output_node, meshlight, begin_cycles_node)
        convert_cycles_input(nt, begin_cycles_node.inputs[
                             'Strength'], meshlight, "intensity")
        if begin_cycles_node.inputs['Color'].is_linked:
            convert_cycles_input(nt, begin_cycles_node.inputs[
                                 'Color'], meshlight, "textureColor")
        else:
            setattr(meshlight, 'lightColor', begin_cycles_node.inputs[
                    'Color'].default_value[:3])
        bxdf = nt.nodes.new('PxrBlackBxdfNode')
        nt.links.new(bxdf.outputs[0], output_node.inputs["Bxdf"])
    else:
        if begin_cycles_node.bl_idname == "ShaderNodeBsdfPrincipled":
            # use PxrDisney
            node_name = __BL_NODES_MAP__.get('PxrDisney')
            base_surface = create_rman_surface(nt, output_node, 0, node_name=node_name)
        else:
            node_name = __BL_NODES_MAP__.get('LamaSurface')
            base_surface = create_rman_surface(nt, output_node, 0, node_name=node_name)
            setattr(base_surface, 'computePresence', 1)
            setattr(base_surface, 'computeOpacity', 1)
            setattr(base_surface, 'computeSubsurface', 1)
            setattr(base_surface, 'computeInterior', 1)
        offset_node_location(output_node, base_surface, begin_cycles_node)
        convert_cycles_bsdf(nt, base_surface, begin_cycles_node, 0)
        convert_cycles_displacement(
            nt, base_surface, cycles_output_node.inputs[2], output_node)
        base_surface.update_mat(id)
    return True