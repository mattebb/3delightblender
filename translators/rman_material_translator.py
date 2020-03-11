from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_material import RmanSgMaterial
from ..rman_utils import string_utils
from ..rman_utils import property_utils
from ..rman_utils import shadergraph_utils
from ..rman_utils import color_utils
from ..rman_utils import gpmaterial_utils

from ..rfb_logger import rfb_log
from ..rman_cycles_convert import _CYCLES_NODE_MAP_
import math

import bpy

# hack!!!
current_group_node = None

class RmanMaterialTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'MATERIAL'

    def export(self, mat, db_name):

        sg_material = self.rman_scene.sg_scene.CreateMaterial(db_name)
        rman_sg_material = RmanSgMaterial(self.rman_scene, sg_material, db_name)
        self.update(mat, rman_sg_material)
        return rman_sg_material

    def update(self, mat, rman_sg_material, time_sample=0):

        rm = mat.renderman
        succeed = False

        if mat.grease_pencil:
            if not mat.node_tree or not shadergraph_utils.is_renderman_nodetree(mat):
                self.export_shader_grease_pencil(mat, rman_sg_material, handle=rman_sg_material.db_name )
                return

        if mat.node_tree:
            succeed = self.export_shader_nodetree(mat, rman_sg_material, handle=rman_sg_material.db_name)

        if not succeed:
            succeed = self.export_simple_shader(mat, rman_sg_material, mat_handle=rman_sg_material.db_name)     

    def export_shader_grease_pencil(self, mat, rman_sg_material, handle):
        gp_mat = mat.grease_pencil

        if gp_mat.show_stroke:
            stroke_style = gp_mat.stroke_style

            if stroke_style == 'SOLID':
                gpmaterial_utils.gp_material_stroke_solid(mat, self.rman_scene.rman, rman_sg_material, handle)
            elif stroke_style == 'TEXTURE':
                gpmaterial_utils.gp_material_stroke_texture(mat, self.rman_scene.rman, rman_sg_material, handle)
            
        elif gp_mat.show_fill:
            fill_style = gp_mat.fill_style

            if fill_style == 'TEXTURE':                                 
                gpmaterial_utils.gp_material_fill_texture(mat, self.rman_scene.rman, rman_sg_material, handle)
            elif fill_style == 'CHECKER':
                gpmaterial_utils.gp_material_fill_checker(mat, self.rman_scene.rman, rman_sg_material, handle)

            elif fill_style == 'GRADIENT':
                gpmaterial_utils.gp_material_fill_gradient(mat, self.rman_scene.rman, rman_sg_material, handle)
            else:
                gpmaterial_utils.gp_material_fill_solid(mat, self.rman_scene.rman, rman_sg_material, handle)
             
    def export_shader_nodetree(self, id, rman_sg_material, handle):

        if id and id.node_tree:

            if shadergraph_utils.is_renderman_nodetree(id):
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
                    for sub_node in shadergraph_utils.gather_nodes(socket.links[0].from_node):
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
                        for sub_node in shadergraph_utils.gather_nodes(socket.links[0].from_node):
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
                        for sub_node in shadergraph_utils.gather_nodes(socket.links[0].from_node):
                            shader_sg_nodes = self.shader_node_sg(sub_node, rman_sg_material, mat_name=handle,
                                        portal=portal)
                            for s in shader_sg_nodes:
                                dispList.append(s) 
                        if dispList:
                            rman_sg_material.sg_node.SetDisplace(dispList)  

                return True                        
                    
            elif shadergraph_utils.find_node(id, 'ShaderNodeOutputMaterial'):
                rfb_log().debug("Error Material %s needs a RenderMan BXDF" % id.name)
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

    def translate_node_group(self, rman_sg_material, group_node, mat_name):
        ng = group_node.node_tree
        out = next((n for n in ng.nodes if n.bl_idname == 'NodeGroupOutput'),
                None)
        if out is None:
            return

        nodes_to_export = shadergraph_utils.gather_nodes(out)
        global current_group_node
        current_group_node = group_node
        sg_nodes = []
        for node in nodes_to_export:
            sg_nodes += self.shader_node_sg(node, rman_sg_material, mat_name=(mat_name + '_' + group_node.name))
        current_group_node = None
        return sg_nodes        

    def translate_cycles_node(self, rman_sg_material, node, mat_name):
        if node.bl_idname == 'ShaderNodeGroup':
            return self.translate_node_group(rman_sg_material, node, mat_name)

        if node.bl_idname not in _CYCLES_NODE_MAP_.keys():
            print('No translation for node of type %s named %s' %
                (node.bl_idname, node.name))
            return []

        mapping = _CYCLES_NODE_MAP_[node.bl_idname]

        sg_node = self.rman_scene.rman.SGManager.RixSGShader("Pattern", mapping, shadergraph_utils.get_node_name(node, mat_name))
        params = sg_node.params      
        
        for in_name, input in node.inputs.items():
            param_name = "%s" % shadergraph_utils.get_socket_name(node, input)
            param_type = "%s" % shadergraph_utils.get_socket_type(node, input)
            if input.is_linked:
                link = input.links[0]
                val = property_utils.get_output_param_str(
                    link.from_node, mat_name, link.from_socket, input)

                property_utils.set_rix_param(params, param_type, param_name, val, is_reference=True)                

            else:
                val = string_utils.convert_val(input.default_value,
                                type_hint=shadergraph_utils.get_socket_type(node, input))
                # skip if this is a vector set to 0 0 0
                if input.type == 'VECTOR' and val == [0.0, 0.0, 0.0]:
                    continue

                property_utils.set_rix_param(params, param_type, param_name, val, is_reference=False)

        ramp_size = 256
        if node.bl_idname == 'ShaderNodeValToRGB':
            colors = []
            alphas = []

            for i in range(ramp_size):
                c = node.color_ramp.evaluate(float(i) / (ramp_size - 1.0))
                colors.extend(c[:3])
                alphas.append(c[3])

            params.SetColorArray('ramp_color', colors, ramp_size)
            params.SetFloatArray('ramp_alpha', alphas, ramp_size)

        elif node.bl_idname == 'ShaderNodeVectorCurve':
            colors = []
            node.mapping.initialize()
            r = node.mapping.curves[0]
            g = node.mapping.curves[1]
            b = node.mapping.curves[2]

            for i in range(ramp_size):
                v = float(i) / (ramp_size - 1.0)
                colors.extend([r.evaluate(v), g.evaluate(v), b.evaluate(v)])

            params.SetColorArray('ramp', colors, ramp_size)

        elif node.bl_idname == 'ShaderNodeRGBCurve':
            colors = []
            node.mapping.initialize()
            c = node.mapping.curves[0]
            r = node.mapping.curves[1]
            g = node.mapping.curves[2]
            b = node.mapping.curves[3]

            for i in range(ramp_size):
                v = float(i) / (ramp_size - 1.0)
                c_val = c.evaluate(v)
                colors.extend([r.evaluate(v) * c_val, g.evaluate(v)
                            * c_val, b.evaluate(v) * c_val])


            params.SetColorArray('ramp', colors, ramp_size)
    
        return [sg_node]        

    def shader_node_sg(self, node, rman_sg_material, mat_name, portal=False):
 
        sg_node = None

        if type(node) == type(()):
            shader, from_node, from_socket = node
            input_type = 'float' if shader == 'PxrToFloat3' else 'color'
            node_name = 'convert_%s.%s' % (shadergraph_utils.get_node_name(
                from_node, mat_name), shadergraph_utils.get_socket_name(from_node, from_socket))
            if from_node.bl_idname == 'ShaderNodeGroup':
                node_name = 'convert_' + property_utils.get_output_param_str(
                    from_node, mat_name, from_socket).replace(':', '.')
                    
            val = property_utils.get_output_param_str(from_node, mat_name, from_socket)
            sg_node = self.rman_scene.rman.SGManager.RixSGShader("Pattern", shader, node_name)
            rix_params = sg_node.params       
            if input_type == 'color':
                rix_params.SetColorReference('input', val)
            else:
                rix_params.SetFloatReference('input', val)            
                    
            return [sg_node]
        elif not hasattr(node, 'renderman_node_type'):
            return self.translate_cycles_node(rman_sg_material, node, mat_name)

        instance = mat_name + '_' + node.name

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
        elif node.renderman_node_type == "displace":
            sg_node = self.rman_scene.rman.SGManager.RixSGShader("Displacement", node.bl_label, instance)
        else:
            sg_node = self.rman_scene.rman.SGManager.RixSGShader("Bxdf", node.bl_label, instance)        

        if sg_node:
            property_utils.property_group_to_rixparams(node, rman_sg_material, sg_node, light=None, mat_name=mat_name)

        return [sg_node]        