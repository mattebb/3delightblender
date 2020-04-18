from .rman_translator import RmanTranslator
from ..rman_utils import property_utils
from ..rman_utils import transform_utils
from ..rman_utils import object_utils
from ..rman_sg_nodes.rman_sg_lightfilter import RmanSgLightFilter
import bpy                    

class RmanLightFilterTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'LIGHTFILTER'  

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

        lightfilter_shader = ob.data.renderman.get_light_node_name()  
        sg_group = self.rman_scene.sg_scene.CreateGroup(db_name)

        sg_filter_node = self.rman_scene.rman.SGManager.RixSGShader("LightFilter", lightfilter_shader, '%s-%s' % (db_name, lightfilter_shader))
        rman_sg_lightfilter = RmanSgLightFilter(self.rman_scene, sg_group, db_name)
        rman_sg_lightfilter.sg_filter_node = sg_filter_node
        rman_sg_lightfilter.coord_sys = db_name

        rman_group_translator = self.rman_scene.rman_translators['GROUP']

        rman_group_translator.update_transform(ob, rman_sg_lightfilter)
        self.rman_scene.get_root_sg_node().AddChild(rman_sg_lightfilter.sg_node)
        self.rman_scene.rman_objects[ob.original] = rman_sg_lightfilter
        self.rman_scene.sg_scene.Root().AddCoordinateSystem(rman_sg_lightfilter.sg_node)

        return rman_sg_lightfilter 

    def update(self, ob, rman_sg_lightfilter):
        lightfilter_node = ob.data.renderman.get_light_node()
        property_utils.property_group_to_rixparams(lightfilter_node, rman_sg_lightfilter, rman_sg_lightfilter.sg_filter_node, light=ob.data)
        rixparams = rman_sg_lightfilter.sg_filter_node.params
        rixparams.SetString("coordsys", rman_sg_lightfilter.coord_sys)
            