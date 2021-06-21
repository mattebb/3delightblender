from ..rfb_utils import transform_utils
from ..rfb_utils import property_utils
from ..rfb_utils import string_utils
from ..rfb_utils import object_utils
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

    def set_primvar_times(self, motion_steps, primvar):
        # take the motion steps, sort it and 
        # normalize it to lie between 0 and 1
        times = []
        sorted_steps = sorted(list(motion_steps))
        delta = -sorted_steps[0]
        for m in sorted_steps:
            times.append(m + delta)
        primvar.SetTimes(times)

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

    def export_object_id(self, ob, rman_sg_node, ob_inst):
        name = ob.name_full
        attrs = rman_sg_node.sg_node.GetAttributes()
        rman_type = object_utils._detect_primitive_(ob)

        # Add ID
        if name != "":            
            persistent_id = ob_inst.persistent_id[0]
            if persistent_id == 0:
                persistent_id = hash(ob.name_full) % 10**8                   
            self.rman_scene.obj_hash[persistent_id] = name
            attrs.SetInteger(self.rman_scene.rman.Tokens.Rix.k_identifier_id, persistent_id)

            if rman_type in [
                    'DELAYED_LOAD_ARCHIVE',
                    'ALEMBIC',
                    'PROCEDURAL_RUN_PROGRAM',
                    'DYNAMIC_LOAD_DSO'
                ]:
                procprimid = float(hash(rman_sg_node.db_name) % 10**8 )
                attrs.SetFloat('user:procprimid', procprimid)  

        rman_sg_node.sg_node.SetAttributes(attrs)      

    def export_object_attributes(self, ob, rman_sg_node):

        name = ob.name_full
        rm = ob.renderman
        attrs = rman_sg_node.sg_node.GetAttributes()

        # set any properties marked riattr in the config file
        for prop_name, meta in rm.prop_meta.items():
            if 'riattr' not in meta:
                continue

            ri_name = meta['riattr']            
            val = getattr(rm, prop_name)
            if 'inheritable' in meta:
                cond = meta['inherit_true_value']
                if isinstance(cond, str):
                    node = rm
                    if exec(cond):
                        attrs.Remove(ri_name)
                        continue
                elif float(val) == cond:
                    attrs.Remove(ri_name)
                    continue

            is_array = False
            array_len = -1
            if 'arraySize' in meta:
                is_array = True
                array_len = meta['arraySize']
            param_type = meta['renderman_type']
            property_utils.set_rix_param(attrs, param_type, ri_name, val, is_reference=False, is_array=is_array, array_len=array_len)            

        obj_groups_str = "World"
        obj_groups_str += "," + name
        lpe_groups_str = "*"
        for obj_group in self.rman_scene.bl_scene.renderman.object_groups:
            for member in obj_group.members:
                if member.ob_pointer == ob:
                    obj_groups_str += ',' + obj_group.name
                    lpe_groups_str += ',' + obj_group.name
                    break
        attrs.SetString(self.rman_scene.rman.Tokens.Rix.k_grouping_membership, obj_groups_str)

        # add to trace sets
        if lpe_groups_str != '*':                       
            attrs.SetString(self.rman_scene.rman.Tokens.Rix.k_identifier_lpegroup, lpe_groups_str)
      
        # for each light link do illuminates
        exclude_subset = []
        lightfilter_subset = []

        for subset in rm.rman_lighting_excludesubset:
            nm = string_utils.sanitize_node_name(subset.light_ob.name)
            exclude_subset.append(nm)

        for subset in rm.rman_lightfilter_subset:
            nm = string_utils.sanitize_node_name(subset.light_ob.name)
            lightfilter_subset.append(nm)            

        if exclude_subset:
            attrs.SetString(self.rman_scene.rman.Tokens.Rix.k_lighting_excludesubset, ' '. join(exclude_subset) )
        else:
            attrs.SetString(self.rman_scene.rman.Tokens.Rix.k_lighting_excludesubset, '')

        if lightfilter_subset:
            attrs.SetString(self.rman_scene.rman.Tokens.Rix.k_lightfilter_subset, ' ' . join(lightfilter_subset))
        else:
            attrs.SetString(self.rman_scene.rman.Tokens.Rix.k_lightfilter_subset, '')

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
    