from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_group import RmanSgGroup
from ..rfb_utils import transform_utils
from ..rfb_utils import object_utils
from mathutils import Matrix
import math

class RmanEmptyTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)

    def export_object_primvars(self, ob, rman_sg_node):
        pass        

    def update_transform(self, ob, rman_sg_group):
        pass

    def update_transform_sample(self, ob, rman_sg_group, index, seg):
        pass

    def update_transform_num_samples(self, rman_sg_group, motion_steps):
        pass

    def export(self, ob, db_name=""):
        sg_group = self.rman_scene.sg_scene.CreateGroup(db_name)
        rman_sg_group = RmanSgGroup(self.rman_scene, sg_group, db_name)
        return rman_sg_group   