from ..rman_utils import transform_utils

class RmanTranslator(object):
    '''
    RmanTranslator and subclasses are responsible for taking a Blender object/material and converting
    them to the equivalent RixSceneGraph node. The scene graph nodes are wrapped in a thin layer RmanSgNode
    class corresponding to their type. The flow should be something like:

        db_name = 'FOOBAR' # unique datablock name
        rman_sg_node = translator.export(ob, db_name) # convert object and return an RmanSgNode node
        .
        .
        # ob is a deforming object, export object at time_sample
        translator.export_deform_sample(rman_sg_node, ob, time_samples, time_sample)
        .
        .
        # ob has changed
        translator.update(ob, rman_sg_node)

    Attributes:
        rman_scene (RmanScene) - pointer back to RmanScene instance
    '''

    def __init__(self, rman_scene):
        self.rman_scene = rman_scene

    @property
    def rman_scene(self):
        return self.__rman_scene

    @rman_scene.setter
    def rman_scene(self, rman_scene):
        self.__rman_scene = rman_scene        

    def export(self, ob, db_name):
        pass

    def export_deform_sample(self, rman_sg_node, ob, time_samples, time_sample):
        pass

    def update(self, ob, rman_sg_node):
        pass

    def export_transform(self, ob, sg_node):
        m = ob.matrix_local if ob.parent and ob.parent_type == "object" and ob.type != 'LIGHT'\
                else ob.matrix_world

        v = transform_utils.convert_matrix(m)

        sg_node.SetTransform( v )        

    def export_object_primvars(self, ob, sg_node):
        rm = ob.renderman
        primvars = sg_node.GetPrimVars()

        if rm.shading_override:
            primvars.SetFloat(self.rman_scene.rman.Tokens.Rix.k_dice_micropolygonlength, rm.shadingrate)
            primvars.SetFloat(self.rman_scene.rman.Tokens.Rix.k_dice_watertight, rm.watertight)

        if rm.raytrace_override:                
            primvars.SetInteger(self.rman_scene.rman.Tokens.Rix.k_trace_displacements, rm.raytrace_tracedisplacements)
            primvars.SetFloat(self.rman_scene.rman.Tokens.Rix.k_trace_autobias, rm.raytrace_autobias)
            primvars.SetFloat(self.rman_scene.rman.Tokens.Rix.k_trace_bias, rm.raytrace_bias)
            primvars.SetInteger(self.rman_scene.rman.Tokens.Rix.k_trace_samplemotion, rm.raytrace_samplemotion)

        primvars.SetFloat(self.rman_scene.rman.Tokens.Rix.k_displacementbound_sphere, rm.displacementbound)
        sg_node.SetPrimVars(primvars)

    def export_object_attributes(self, ob, sg_node):

        name = ob.name_full
        rm = ob.renderman
        attrs = sg_node.GetAttributes()

        # Add ID
        if name != "":            
            obj_id = len(self.rman_scene.obj_hash.keys())
            self.rman_scene.obj_hash[obj_id] = name
            attrs.SetInteger(self.rman_scene.rman.Tokens.Rix.k_identifier_id, obj_id)

        obj_groups_str = "World"
        obj_groups_str += "," + name
        lpe_groups_str = "*"
        for obj_group in self.rman_scene.bl_scene.renderman.object_groups:
            if ob.name in obj_group.members.keys():
                obj_groups_str += ',' + obj_group.name
                lpe_groups_str += ',' + obj_group.name

        attrs.SetString(self.rman_scene.rman.Tokens.Rix.k_grouping_membership, obj_groups_str)

        # add to trace sets
        if lpe_groups_str != '*':                       
            attrs.SetString(self.rman_scene.rman.Tokens.Rix.k_identifier_lpegroup, lpe_groups_str)

        # visibility attributes
        attrs.SetInteger("visibility:transmission", int(ob.renderman.visibility_trace_transmission))
        attrs.SetInteger("visibility:indirect", int(ob.renderman.visibility_trace_indirect))
        attrs.SetInteger("visibility:camera", int(ob.renderman.visibility_camera))

        attrs.SetInteger(self.rman_scene.rman.Tokens.Rix.k_Ri_Matte, ob.renderman.matte)

        # ray tracing attributes
        #attrs.SetInteger(self.rman_scene.rman.Tokens.Rix.k_trace_intersectpriority, ob.renderman.raytrace_intersectpriority)
        #attrs.SetFloat(self.rman_scene.rman.Tokens.Rix.k_shade_indexofrefraction, ob.renderman.raytrace_ior)

        attrs.SetInteger(self.rman_scene.rman.Tokens.Rix.k_trace_holdout, ob.renderman.holdout)

        if ob.renderman.raytrace_override:
            attrs.SetInteger(self.rman_scene.rman.Tokens.Rix.k_trace_maxdiffusedepth, ob.renderman.raytrace_maxdiffusedepth)
            attrs.SetInteger(self.rman_scene.rman.Tokens.Rix.k_trace_maxspeculardepth, ob.renderman.raytrace_maxspeculardepth)
            attrs.SetInteger(self.rman_scene.rman.Tokens.Rix.k_trace_intersectpriority, ob.renderman.raytrace_intersectpriority)

        
        # light linking
        # get links this is a part of
        ll_str = "obj_object>%s" % ob.name
        lls = [ll for ll in self.rman_scene.bl_scene.renderman.ll if ll_str in ll.name]
        # get links this is a group that is a part of
        for group in self.rman_scene.bl_scene.renderman.object_groups:
            if ob.name in group.members.keys():
                ll_str = "obj_group>%s" % group.name
                lls += [ll for ll in self.rman_scene.bl_scene.renderman.ll if ll_str in ll.name]

        # for each light link do illuminates
        exclude_subset = []
        lightfilter_subset = []
        for link in lls:
            strs = link.name.split('>')

            scene_lights = [l.name for l in self.rman_scene.bl_scene.objects if l.type == 'LIGHT']
            light_names = [strs[1]] if strs[0] == "lg_light" else \
                self.rman_scene.bl_scene.renderman.light_groups[strs[1]].members.keys()
            if strs[0] == 'lg_group' and strs[1] == 'All':
                light_names = scene_lights
            for light_name in light_names:
                if link.illuminate != "DEFAULT" and light_name in self.rman_scene.bl_scene.objects:
                    light_ob = self.rman_scene.bl_scene.objects[light_name]
                    light = light_ob.data
                    if light.renderman.renderman_type == 'FILTER':
                        # for each light this is a part of do enable light filter
                        filter_name = light_name
                        for light_nm in scene_lights:
                            if filter_name in self.rman_scene.bl_scene.objects[light_nm].data.renderman.light_filters.keys():
                                if link.illuminate == 'ON':
                                    lightfilter_subset.append(filter_name)
                    else:
                        if not link.illuminate == 'ON':
                            exclude_subset.append(light_name)

        if exclude_subset:
            attrs.SetString(self.rman_scene.rman.Tokens.Rix.k_lighting_excludesubset, ' '. join(exclude_subset) )

        if lightfilter_subset:
            attrs.SetString(self.rman_scene.rman.Tokens.Rix.k_lightfilter_subset, ' ' . join(lightfilter_subset))

        user_attr = {}
        for i in range(8):
            name = 'MatteID%d' % i
            if getattr(rm, name) != [0.0, 0.0, 0.0]:
                attrs.SetColor('user:%s' % name, getattr(rm, name))

        if hasattr(ob, 'color'):
            attrs.SetColor('user:Cs', ob.color[:3])   

        sg_node.SetAttributes(attrs) 
    