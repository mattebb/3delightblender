from ..rman_utils import transform_utils
from ..rman_utils import property_utils
from ..rman_utils import string_utils
import os

class RmanTranslator(object):
    '''
    RmanTranslator and subclasses are responsible for taking a Blender object/material and converting
    them to the equivalent RixSceneGraph node. The scene graph nodes are wrapped in a thin layer RmanSgNode
    class corresponding to their type. The flow should be something like:

        db_name = 'FOOBAR' # unique datablock name
        rman_sg_node = translator.export(ob, db_name) # create an RmanSgNode node
        # set primvars on geo
        translator.update(ob, rman_sg_node)        
        .
        .
        # ob is a deforming object, export object at time_sample
        translator.export_deform_sample(rman_sg_node, ob, time_sample)
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

    def export_deform_sample(self, rman_sg_node, ob, time_sample):
        pass

    def update(self, ob, rman_sg_node):
        pass

    def export_transform(self, ob, sg_node):
        m = ob.matrix_local if ob.parent and ob.parent_type == "object" and ob.type != 'LIGHT'\
                else ob.matrix_world

        v = transform_utils.convert_matrix(m)

        sg_node.SetTransform( v )        

    def export_object_primvars(self, ob, rman_sg_node):
        if not rman_sg_node.sg_node:
            return
        rm = ob.renderman
        rm_scene = self.rman_scene.bl_scene.renderman
        primvars = rman_sg_node.sg_node.GetPrimVars()

        # set any properties marked primvar in the config file
        for prop_name, meta in rm.prop_meta.items():
            if 'primvar' not in meta:
                continue

            val = getattr(rm, prop_name)
            if not val:
                continue

            if 'inheritable' in meta:
                if float(val) == meta['inherit_true_value']:
                    if hasattr(rm_scene, prop_name):
                        val = getattr(rm_scene, prop_name)

            ri_name = meta['primvar']
            is_array = False
            array_len = -1
            if 'arraySize' in meta:
                is_array = True
                array_len = meta['arraySize']
            param_type = meta['renderman_type']
            property_utils.set_rix_param(primvars, param_type, ri_name, val, is_reference=False, is_array=is_array, array_len=array_len)                

        rman_sg_node.sg_node.SetPrimVars(primvars)

    def export_object_attributes(self, ob, rman_sg_node):

        name = ob.name_full
        rm = ob.renderman
        attrs = rman_sg_node.sg_node.GetAttributes()

        # set any properties marked riattr in the config file
        for prop_name, meta in rm.prop_meta.items():
            if 'riattr' not in meta:
                continue
            
            val = getattr(rm, prop_name)
            if 'inheritable' in meta:
                cond = meta['inherit_true_value']
                if isinstance(cond, str):
                    node = rm
                    if exec(cond):
                        continue
                elif float(val) == cond:
                    continue

            ri_name = meta['riattr']
            is_array = False
            array_len = -1
            if 'arraySize' in meta:
                is_array = True
                array_len = meta['arraySize']
            param_type = meta['renderman_type']
            property_utils.set_rix_param(attrs, param_type, ri_name, val, is_reference=False, is_array=is_array, array_len=array_len)             

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

        if hasattr(ob, 'color'):
            attrs.SetColor('user:Cs', ob.color[:3])   

        if self.rman_scene.rman_bake and self.rman_scene.bl_scene.renderman.rman_bake_illum_filename == 'BAKEFILEATTR':
            filePath = ob.renderman.bake_filename_attr
            if filePath != '':
                # check for {EXT} token, we'll add that later when we're doing displays
                if filePath.endswith('.{EXT}'):
                    filePath.replace('.{EXT}', '')
                else:
                    tokens = os.path.splitext(filePath)
                    if tokens[1] != '':
                        filePath = tokens[0]
                filePath = string_utils.expand_string(filePath,
                                                frame=self.rman_scene.bl_frame_current,
                                                asFilePath=True)                
                attrs.SetString('user:bake_filename_attr', filePath)

        rman_sg_node.sg_node.SetAttributes(attrs) 
    