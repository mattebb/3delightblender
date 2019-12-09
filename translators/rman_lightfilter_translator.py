from .rman_translator import RmanTranslator
from ..rman_utils import property_utils
from ..rman_utils import transform_utils
from ..rman_sg_nodes.rman_sg_node import RmanSgNode
import math
import bpy                    

class RmanLightFilterTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'FILTER'  

    def export(self, ob, db_name):

        light_filter = ob

        light_filter_sg = None

        if light_filter.data.name in self.rman_scene.rman_objects:
            lightf_filter_sg = self.rman_scene.rman_objects[light_filter.name]
        else:

            filter_plugin = light_filter.data.renderman.get_light_node()  

            lightfilter_name = light_filter.data.renderman.get_light_node_name()
            light_filter_sg = self.rman_scene.rman.SGManager.RixSGShader("LightFilter", lightfilter_name, light_filter.name)
            rman_sg_node = RmanSgNode(self.rman_scene, light_filter_sg, "")
            property_utils.property_group_to_rixparams(filter_plugin, rman_sg_node, light_filter_sg, light=ob.data)

            coordsys_name = "%s_coordsys" % light_filter.name
            rixparams = light_filter_sg.params
            rixparams.SetString("coordsys", coordsys_name)

            self.rman_scene.rman_objects[light_filter.name] = light_filter_sg
                        
            coordsys = self.rman_scene.sg_scene.CreateGroup(coordsys_name)
            m = transform_utils.convert_matrix( light_filter.matrix_world )
            coordsys.SetTransform(m)
            self.rman_scene.sg_scene.Root().AddChild(coordsys)
            #light_sg.AddCoordinateSystem(coordsys)

            self.rman_scene.rman_objects[coordsys_name] = coordsys

        return light_filter_sg
            