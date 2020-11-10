from .rman_translator import RmanTranslator
from .rman_lightfilter_translator import RmanLightFilterTranslator
from ..rman_sg_nodes.rman_sg_light import RmanSgLight
from ..rman_sg_nodes.rman_sg_lightfilter import RmanSgLightFilter
from ..rfb_utils import string_utils
from ..rfb_utils import property_utils
from ..rfb_utils import transform_utils
from ..rfb_utils import object_utils
from ..rfb_utils import scene_utils
from ..rfb_logger import rfb_log
from mathutils import Matrix
import math
import bpy

s_orientTransform = [0, 0, -1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1]

s_orientPxrLight = [-1.0, 0.0, -0.0, 0.0,
                    -0.0, -1.0, -0.0, 0.0,
                    0.0, 0.0, -1.0, 0.0,
                    0.0, 0.0, 0.0, 1.0]

s_orientPxrDomeLight = [0.0, 0.0, -1.0, 0.0,
                       -1.0, -0.0, 0.0, 0.0,
                        0.0, 1.0, 0.0, 0.0,
                        0.0, 0.0, 0.0, 1.0]

s_orientPxrEnvDayLight = [-0.0, 0.0, -1.0, 0.0,
                        1.0, 0.0, -0.0, -0.0,
                        -0.0, 1.0, 0.0, 0.0,
                        0.0, 0.0, 0.0, 1.0]

s_orientPxrEnvDayLightInv = [-0.0, 1.0, -0.0, 0.0,
                            -0.0, 0.0, 1.0, -0.0,
                            -1.0, -0.0, 0.0, -0.0,
                            0.0, -0.0, -0.0, 1.0]

def find_portal_dome_parent(portal):  
    dome = None
    parent = portal.parent
    while parent:
        if parent.type == 'LIGHT' and hasattr(parent.data, 'renderman'): 
            rm = parent.data.renderman
            if rm.renderman_light_role == 'RMAN_LIGHT' and rm.get_light_node_name() == 'PxrDomeLight':
                dome = parent
                break
        parent = parent.parent
    return dome                   

class RmanLightTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'LIGHT'  

    def export_object_primvars(self, ob, rman_sg_node):
        pass

    def export_object_attributes(self, ob, rman_sg_node):
        pass

    def export(self, ob, db_name):

        light = ob.data
        rm = light.renderman        

        if rm.get_light_node_name() == 'PxrPortalLight':
            if not ob.parent:
                return None
            if ob.parent.type != 'LIGHT'\
                and portal_parent.data.renderman.get_light_node_name() != 'PxrDomeLight':
                return None

        sg_node = self.rman_scene.sg_scene.CreateAnalyticLight(db_name)                
        rman_sg_light = RmanSgLight(self.rman_scene, sg_node, db_name)
        if self.rman_scene.do_motion_blur:
            rman_sg_light.is_transforming = object_utils.is_transforming(ob)
        return rman_sg_light

    def update_light_filters(self, ob, rman_sg_light):
        light = ob.data
        rm = light.renderman      
        lightfilter_translator = self.rman_scene.rman_translators['LIGHTFILTER']
        lightfilter_translator.export_light_filters(ob, rman_sg_light, rm)

    def update(self, ob, rman_sg_light):

        light = ob.data
        rm = light.renderman  

        # light filters
        self.update_light_filters(ob, rman_sg_light)
        
        light_shader = rm.get_light_node()

        sg_node = None            
        light_shader_name = ''
        if light_shader:
            light_shader_name = rm.get_light_node_name()

            sg_node = self.rman_scene.rman.SGManager.RixSGShader("Light", light_shader_name , rman_sg_light.db_name)
            property_utils.property_group_to_rixparams(light_shader, rman_sg_light, sg_node, light=light)
            
            rixparams = sg_node.params

            # portal params
            if rm.get_light_node_name() == 'PxrPortalLight':
                portal_parent = find_portal_dome_parent(ob) #ob.parent
                if portal_parent:
                    parent_node = portal_parent.data.renderman.get_light_node()

                    rixparams.SetString('portalName', rman_sg_light.db_name)
                    property_utils.portal_inherit_dome_params(light_shader, portal_parent, parent_node, rixparams)

                    orient_mtx = Matrix()
                    orient_mtx[0][0] = s_orientPxrLight[0]
                    orient_mtx[1][0] = s_orientPxrLight[1]
                    orient_mtx[2][0] = s_orientPxrLight[2]
                    orient_mtx[3][0] = s_orientPxrLight[3]

                    orient_mtx[0][1] = s_orientPxrLight[4]
                    orient_mtx[1][1] = s_orientPxrLight[5]
                    orient_mtx[2][1] = s_orientPxrLight[6]
                    orient_mtx[3][1] = s_orientPxrLight[7]

                    orient_mtx[0][2] = s_orientPxrLight[8]
                    orient_mtx[1][2] = s_orientPxrLight[9]
                    orient_mtx[2][2] = s_orientPxrLight[10]
                    orient_mtx[3][2] = s_orientPxrLight[11]

                    orient_mtx[0][3] = s_orientPxrLight[12]
                    orient_mtx[1][3] = s_orientPxrLight[13]
                    orient_mtx[2][3] = s_orientPxrLight[14]
                    orient_mtx[3][3] = s_orientPxrLight[15]
                    
                    portal_mtx = orient_mtx @ Matrix(ob.matrix_world)                   
                    dome_mtx = Matrix(portal_parent.matrix_world)
                    dome_mtx.invert()
                    mtx = portal_mtx @ dome_mtx  
                    
                    rixparams.SetMatrix('portalToDome', transform_utils.convert_matrix4x4(mtx) )
                else:
                    rfb_log().error('Could not find a dome light parent for: %s' % ob.name)
            

            rman_sg_light.sg_node.SetLight(sg_node)

            primary_vis = rm.light_primary_visibility
            attrs = rman_sg_light.sg_node.GetAttributes()
            attrs.SetInteger("visibility:camera", int(primary_vis))
            attrs.SetInteger("visibility:transmission", 0)
            attrs.SetInteger("visibility:indirect", 0)
            obj_groups_str = "World,%s" % rman_sg_light.db_name
            attrs.SetString(self.rman_scene.rman.Tokens.Rix.k_grouping_membership, obj_groups_str)

            rman_sg_light.sg_node.SetAttributes(attrs)

        else:
            names = {'POINT': 'PxrSphereLight', 'SUN': 'PxrDistantLight',
                    'SPOT': 'PxrDiskLight', 'HEMI': 'PxrDomeLight', 'AREA': 'PxrRectLight'}
            light_shader_name = names[light.type]
            exposure = light.energy / 200.0
            if light.type == 'SUN':
                exposure = 0
            sg_node = self.rman_scene.rman.SGManager.RixSGShader("Light", light_shader_name , "light")
            rixparams = sg_node.params
            rixparams.SetFloat("exposure", exposure)
            rixparams.SetColor("lightColor", string_utils.convert_val(light.color))
            if light.type not in ['HEMI', 'SUN']:
                rixparams.SetInteger('areaNormalize', 1)

            rman_sg_light.sg_node.SetLight(sg_node)

            primary_vis = rm.light_primary_visibility
            attrs = rman_sg_light.sg_node.GetAttributes()
            attrs.SetInteger("visibility:camera", int(primary_vis))
            attrs.SetInteger("visibility:transmission", 0)
            attrs.SetInteger("visibility:indirect", 0)
            obj_groups_str = "World,%s" % rman_sg_light.db_name
            attrs.SetString(self.rman_scene.rman.Tokens.Rix.k_grouping_membership, obj_groups_str)

                     
            rman_sg_light.sg_node.SetAttributes(attrs)              

        if  light_shader_name in ("PxrRectLight", 
                                "PxrDiskLight",
                                "PxrPortalLight",
                                "PxrSphereLight",
                                "PxrDistantLight",
                                "PxrPortalLight",
                                "PxrCylinderLight"):

            rman_sg_light.sg_node.SetOrientTransform(s_orientPxrLight)  

        elif light_shader_name == 'PxrEnvDayLight':    
            m = Matrix.Rotation(math.radians(-90.0), 4, 'Z')
            rman_sg_light.sg_node.SetOrientTransform(transform_utils.convert_matrix4x4(m))    
        elif light_shader_name == 'PxrDomeLight':
            m = Matrix.Identity(4)            
            rman_sg_light.sg_node.SetOrientTransform(transform_utils.convert_matrix4x4(m))