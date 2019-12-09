from .rman_sg_node import RmanSgNode

class RmanSgMaterial(RmanSgNode):

    def __init__(self, rman_scene, sg_node, db_name):
        super().__init__(rman_scene, sg_node, db_name)