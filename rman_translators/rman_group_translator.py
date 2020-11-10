from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_group import RmanSgGroup
from ..rfb_utils import transform_utils
from ..rfb_utils import object_utils
from mathutils import Matrix
import math

class RmanGroupTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)

    def update_transform(self, ob, rman_sg_group):
        if hasattr(ob, 'renderman') and  object_utils._detect_primitive_(ob) == 'LIGHTFILTER':
            m = Matrix(ob.matrix_world)    
            m = m @ Matrix.Rotation(math.radians(90.0), 4, 'X')
            m = m @ Matrix.Rotation(math.radians(90.0), 4, 'Y')
            m = transform_utils.convert_matrix(m)
            rman_sg_group.sg_node.SetTransform(m)     
        else:       
            mtx = transform_utils.convert_matrix(ob.matrix_world.copy())
            rman_sg_group.sg_node.SetTransform( mtx )

    def update_transform_sample(self, ob, rman_sg_group, index, seg):
        mtx = transform_utils.convert_matrix(ob.matrix_world.copy())
        rman_sg_group.sg_node.SetTransformSample( index, mtx, seg)

    def update_transform_num_samples(self, rman_sg_group, motion_steps):
        rman_sg_group.sg_node.SetTransformNumSamples(len(motion_steps))

    def export(self, ob, db_name=""):
        sg_group = self.rman_scene.sg_scene.CreateGroup(db_name)
        rman_sg_group = RmanSgGroup(self.rman_scene, sg_group, db_name)
        return rman_sg_group   