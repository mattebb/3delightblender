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

    def export_object_primvars(self, ob, rman_sg_node):
        pass

    def export_object_attributes(self, ob, rman_sg_node):

        # Adds external RIB to object_attributes
        name = ob.name_full
        rm = ob.renderman
        attrs = rman_sg_node.sg_node.GetAttributes()

        # Add ID
        if name != "":            
            obj_id = len(self.rman_scene.obj_hash.keys())
            self.rman_scene.obj_hash[obj_id] = name
            attrs.SetInteger(self.rman_scene.rman.Tokens.Rix.k_identifier_id, obj_id)

        rman_sg_node.sg_node.SetAttributes(attrs)    

    def export_light_filters(self, ob, rman_sg_node, rm):
        light_filters = []
        multLFs = []
        maxLFs = []
        minLFs = []
        screenLFs = []
        rman_sg_node.sg_node.SetLightFilter([])
        for lf in rm.light_filters:
            light_filter = lf.linked_filter_ob
            if light_filter:
                # check to make sure this light filter is still in the scene
                if not self.rman_scene.bl_scene.objects.get(light_filter.name, None):
                    lf.name = 'Not Set'
                    continue
                light_filter_sg = None

                light_filter_db_name = object_utils.get_db_name(light_filter)                
                rman_sg_lightfilter = self.rman_scene.rman_objects.get(light_filter.original)
                if not rman_sg_lightfilter:
                    rman_sg_lightfilter = self.export(light_filter, light_filter_db_name)
                elif not isinstance(rman_sg_lightfilter, RmanSgLightFilter):
                    # We have a type mismatch. Delete this scene graph node and re-export
                    # it as a RmanSgLightFilter
                    for k,rman_sg_group in rman_sg_lightfilter.instances.items():
                        self.rman_scene.get_root_sg_node().RemoveChild(rman_sg_group.sg_node)
                    rman_sg_lightfilter.instances.clear() 
                    del rman_sg_lightfilter
                    self.rman_scene.rman_objects.pop(light_filter.original)
                    rman_sg_lightfilter = self.export(light_filter, light_filter_db_name)
                self.update(light_filter, rman_sg_lightfilter)
                light_filters.append(rman_sg_lightfilter.sg_filter_node)
                if ob.original not in rman_sg_lightfilter.lights_list:
                    rman_sg_lightfilter.lights_list.append(ob.original)

                # check which, if any, combineMode this light filter wants
                lightfilter_node = light_filter.data.renderman.get_light_node()
                instance_name = rman_sg_lightfilter.sg_filter_node.handle.CStr()
                combineMode = getattr(lightfilter_node, 'combineMode', '')
                if combineMode == 'mult':
                    multLFs.append(instance_name)
                elif combineMode == 'max':
                    maxLFs.append(instance_name)
                elif combineMode == 'min':
                    minLFs.append(instance_name)
                elif combineMode == 'screen':
                    screenLFs.append(instance_name)

        if len(light_filters) > 1:
            # create a combiner node
            combiner = self.rman_scene.rman.SGManager.RixSGShader("LightFilter", 'PxrCombinerLightFilter', '%s-PxrCombinerLightFilter' % (rman_sg_node.db_name))
            if multLFs:
                combiner.params.SetLightFilterReferenceArray("mult", multLFs, len(multLFs))
            if maxLFs:
                combiner.params.SetLightFilterReferenceArray("max", maxLFs, len(maxLFs))                
            if minLFs:
                combiner.params.SetLightFilterReferenceArray("min", minLFs, len(minLFs))                
            if screenLFs:
                combiner.params.SetLightFilterReferenceArray("screen", screenLFs, len(screenLFs))      
            light_filters.append(combiner)                                        

        if len(light_filters) > 0:
            rman_sg_node.sg_node.SetLightFilter(light_filters)                 

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
            
        # check if this light filter belongs to a light link
        for ll in self.rman_scene.bl_scene.renderman.light_links:
            if ll.light_ob == ob:
                rixparams.SetString("linkingGroups", ob.name)
                break