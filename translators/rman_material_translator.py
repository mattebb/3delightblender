from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_material import RmanSgMaterial
from ..rman_utils import string_utils
from ..rman_utils import property_utils
from ..rfb_logger import rfb_log

import bpy

class RmanMaterialTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'MATERIAL'

    def export(self, mat, db_name):

        sg_material = self.rman_scene.sg_scene.CreateMaterial(db_name)
        rman_sg_material = RmanSgMaterial(self.rman_scene, sg_material, db_name)
        self.update(mat, rman_sg_material)
        return rman_sg_material

    def update(self, mat, rman_sg_material):

        rm = mat.renderman
        succeed = False
        
        if mat.node_tree:
            succeed = self.export_shader_nodetree(mat, rman_sg_material, handle=rman_sg_material.db_name)

        if not succeed:
            succeed = self.export_simple_shader(mat, rman_sg_material, mat_handle=rman_sg_material.db_name)                
        
             
    def export_shader_nodetree(self, id, rman_sg_material, handle):

        if id and id.node_tree:

            if property_utils.is_renderman_nodetree(id):
                portal = type(
                    id).__name__ == 'AreaLight' and id.renderman.renderman_type == 'PORTAL'

                nt = id.node_tree

                out = next((n for n in nt.nodes if hasattr(n, 'renderman_node_type') and
                            n.renderman_node_type == 'output'),
                        None)
                if out is None:
                    return False

                # bxdf
                socket = out.inputs[0]
                if socket.is_linked:
                    bxdfList = []
                    for sub_node in property_utils.gather_nodes(socket.links[0].from_node):
                        shader_sg_nodes = self.shader_node_sg(sub_node, rman_sg_material, mat_name=handle,
                                    portal=portal)
                        for s in shader_sg_nodes:
                            bxdfList.append(s) 
                    if bxdfList:
                        rman_sg_material.sg_node.SetBxdf(bxdfList)         

                # light
                if len(out.inputs) > 1:
                    socket = out.inputs[1]
                    if socket.is_linked:
                        for sub_node in property_utils.gather_nodes(socket.links[0].from_node):
                            shader_sg_nodes = self.shader_node_sg(sub_node, rman_sg_material, mat_name=handle, portal=portal)

                            shader_sg_node = shader_sg_nodes[0]
                            if shader_sg_node.name.CStr() == "PxrMeshLight":
                                rman_sg_material.sg_node.SetLight(shader_sg_node)
                                break                                   

                # displacement
                if len(out.inputs) > 2:
                    socket = out.inputs[2]
                    if socket.is_linked:
                        dispList = []
                        for sub_node in property_utils.gather_nodes(socket.links[0].from_node):
                            shader_sg_nodes = self.shader_node_sg(sub_node, rman_sg_material, mat_name=handle,
                                        portal=portal)
                            for s in shader_sg_nodes:
                                dispList.append(s) 
                        if dispList:
                            rman_sg_material.sg_node.SetDisplace(dispList)  

                return True                        
                    
            elif property_utils.find_node(id, 'ShaderNodeOutputMaterial'):
                rfb_log().error("Error Material %s needs a RenderMan BXDF" % id.name)
                return False

        return False

    def export_simple_shader(self, mat, rman_sg_material, mat_handle=''):
        rm = mat.renderman
        # if rm.surface_shaders.active == '' or not rpass.surface_shaders: return
        name = mat_handle
        if name == '':
            name = 'material.%s' % mat.name_full

        bxdf_name = '%s.PxrDisney' % name
        sg_node = self.rman_scene.rman.SGManager.RixSGShader("Bxdf", "PxrDisney", bxdf_name)
        rix_params = sg_node.params
        rix_params.SetColor('baseColor', string_utils.convert_val(mat.diffuse_color, 'color'))
        rix_params.SetFloat('specular', mat.specular_intensity )
        #FIXME if mat.emit:
        #    rix_params.SetColor("emitColor", string_utils.convert_val(mat.diffuse_color, 'color'))
        #
        #if mat.subsurface_scattering:
        #    rix_params.SetFloat("subsurface", mat.subsurface_scattering.scale)
        #    rix_params.SetColor("subsurfaceColor", string_utils.convert_val(mat.subsurface_scattering.color))
       
        rman_sg_material.sg_node.SetBxdf([sg_node])        

        return True

    def shader_node_sg(self, node, rman_sg_material, mat_name, portal=False):
 
        sg_node = None

        if type(node) == type(()):
            shader, from_node, from_socket = node
            input_type = 'float' if shader == 'PxrToFloat3' else 'color'
            node_name = 'convert_%s.%s' % (property_utils.get_node_name(
                from_node, mat_name), property_utils.get_socket_name(from_node, from_socket))
            if from_node.bl_idname == 'ShaderNodeGroup':
                node_name = 'convert_' + property_utils.get_output_param_str(
                    from_node, mat_name, from_socket).replace(':', '.')
                    
            val = property_utils.get_output_param_str(from_node, mat_name, from_socket)
            sg_node = self.rman_scene.rman.SGManager.RixSGShader("Pattern", shader, node_name)
            rix_params = sg_node.params       
            if input_type == 'color':
                rix_params.ReferenceColor('input', val)
            else:
                rix_params.ReferenceFloat('input', val)            
                    
            return [sg_node]
        #elif not hasattr(node, 'renderman_node_type'):
    
         #   return translate_cycles_node(sg_scene, rman, node, mat_name)

        instance = mat_name + '.' + node.name

        if not hasattr(node, 'renderman_node_type'):
            return

        if node.renderman_node_type == "pattern":
            if node.bl_label == 'PxrOSL':
                shader = node.shadercode 
                if shader:
                    sg_node = self.rman_scene.rman.SGManager.RixSGShader("Pattern", shader, instance)
                    
            else:
                sg_node = self.rman_scene.rman.SGManager.RixSGShader("Pattern", node.bl_label, instance)
        elif node.renderman_node_type == "light":
            light_group_name = ''            
            for lg in self.rman_scene.bl_scene.renderman.light_groups:
                if mat_name in lg.members.keys():
                    light_group_name = lg.name
                    break

            light_name = node.bl_label
            sg_node = self.rman_scene.rman.SGManager.RixSGShader("Light", node.bl_label, mat_name)

        elif node.renderman_node_type == "lightfilter":

            light_name = node.bl_label
        elif node.renderman_node_type == "displacement":
            sg_node = self.rman_scene.rman.SGManager.RixSGShader("Displacement", node.bl_label, instance)
        else:
            sg_node = self.rman_scene.rman.SGManager.RixSGShader("Bxdf", node.bl_label, instance)        

        if sg_node:
            property_utils.property_group_to_rixparams(node, rman_sg_material, sg_node, light=None, mat_name=mat_name)

        return [sg_node]        