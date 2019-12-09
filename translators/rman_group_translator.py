from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_group import RmanSgGroup
from ..rman_utils import transform_utils

class RmanGroupTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)

    def update_transform(self, ob, rman_sg_group):
        rman_sg_group.sg_node.SetTransform( transform_utils.convert_matrix(ob.matrix_world.copy()))

    def export(self, ob, db_name=""):
        sg_group = self.rman_scene.sg_scene.CreateGroup(db_name)
        rman_sg_group = RmanSgGroup(self.rman_scene, sg_group, db_name)
        self.update_transform(ob, rman_sg_group)
        return rman_sg_group   