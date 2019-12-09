from .rman_translator import RmanTranslator
from .rman_lightfilter_translator import RmanLightFilterTranslator
from ..rman_sg_nodes.rman_sg_light import RmanSgLight
from ..rman_utils import string_utils
from ..rman_utils import property_utils
from ..rman_utils import transform_utils
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

def get_light_group(light_ob, scene):
    scene_rm = scene.renderman
    for lg in scene_rm.light_groups:
        if lg.name != 'All' and light_ob.name in lg.members:
            return lg.name
    return ''                            

class RmanLightTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'LIGHT'  

    def export_object_primvars(self, ob, sg_node):
        pass

    def export_object_attributes(self, ob, sg_node):

        # Adds external RIB to object_attributes
        name = ob.name_full
        rm = ob.renderman
        attrs = sg_node.GetAttributes()

        # Add ID
        if name != "":            
            obj_id = len(self.rman_scene.obj_hash.keys())
            self.rman_scene.obj_hash[obj_id] = name
            attrs.SetInteger(self.rman_scene.rman.Tokens.Rix.k_identifier_id, obj_id)

        sg_node.SetAttributes(attrs)         

    def export(self, ob, db_name):

        light = ob.data
        rm = light.renderman        

        if rm.renderman_type == 'PORTAL':
            if not ob.parent:
                return None
            if ob.parent.type != 'LIGHT'\
                and portal_parent.data.renderman.renderman_type != 'ENV':
                return None

        sg_node = self.rman_scene.sg_scene.CreateAnalyticLight(db_name)                
        rman_sg_light = RmanSgLight(self.rman_scene, sg_node, db_name)
        self.update(ob, rman_sg_light)
        return rman_sg_light

    def update(self, ob, rman_sg_light):

        light = ob.data
        rm = light.renderman  

        group_name=get_light_group(ob, self.rman_scene.bl_scene)
        light_filters = []

        lightfilter_translator = RmanLightFilterTranslator(rman_scene=self.rman_scene)
        
        for lf in rm.light_filters:
            if lf.filter_name in bpy.data.objects:
                light_filter = bpy.data.objects[lf.filter_name]
                light_filter_sg = None

                light_filter_sg = lightfilter_translator.export(light_filter, "")

                if light_filter_sg:
                    light_filters.append(light_filter_sg)

                    coordsys_name = "%s_coordsys" % light_filter.name
                    coordsys = self.rman_scene.rman_objects.get(coordsys_name, None)
                    if coordsys:
                        rman_sg_light.sg_node.AddCoordinateSystem(coordsys)

        if len(light_filters) > 0:
            rman_sg_light.sg_node.SetLightFilter(light_filters)
        
        
        light_shader = rm.get_light_node()

        sg_node = None            
        light_shader_name = ''
        if light_shader:
            light_shader_name = rm.get_light_node_name()

            sg_node = self.rman_scene.rman.SGManager.RixSGShader("Light", light_shader_name , rman_sg_light.db_name)
            property_utils.property_group_to_rixparams(light_shader, rman_sg_light, sg_node, light=light)
            
            rixparams = sg_node.params
            rixparams.SetString('lightGroup',group_name)
            if hasattr(light_shader, 'iesProfile'):
                rixparams.SetString('iesProfile',  bpy.path.abspath(
                    light_shader.iesProfile) )

            if light.type == 'SPOT':
                rixparams.SetFloat('coneAngle', math.degrees(light.spot_size))
                rixparams.SetFloat('coneSoftness',light.spot_blend)
            if light.type in ['SPOT', 'POINT']:
                rixparams.SetInteger('areaNormalize', 1)

            # portal params
            if rm.renderman_type == 'PORTAL':
                portal_parent = ob.parent
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
            names = {'POINT': 'PxrSphereLight', 'SUN': 'PxrEnvDayLight',
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

            attrs = rman_sg_light.sg_node.GetAttributes()
            attrs.SetInteger("visibility:camera", 1)
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
            
        """    
        elif light_shader_name == 'PxrDomeLight':
            rman_sg_light.sg_node.SetOrientTransform(s_orientPxrDomeLight)
        elif light_shader_name == 'PxrEnvDayLight':
            rman_sg_light.sg_node.SetOrientTransform(s_orientPxrEnvDayLight)
            rixparams = sg_node.params
            prop = getattr(light_shader, "sunDirection")
            m = transform_utils.convert_matrix4x4(s_orientPxrEnvDayLightInv)
            sunDirection = m.vTransform(string_utils.convert_val(prop))
            rixparams.SetVector("sunDirection", sunDirection)
        """