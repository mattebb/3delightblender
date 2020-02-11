from .rman_sg_node import RmanSgNode

class RmanSgQuadric(RmanSgNode):

    def __init__(self, rman_scene, sg_node, db_name):
        super().__init__(rman_scene, sg_node, db_name)
        self.matrix_world = None
        self.quadric_type = 'SPHERE'

    @property
    def matrix_world(self):
        return self.__matrix_world

    @matrix_world.setter
    def matrix_world(self, mtx):
        self.__matrix_world = mtx

    @property
    def quadric_type(self):
        return self.__quadric_type

    @quadric_type.setter
    def quadric_type(self, quadric_type):
        self.__quadric_type = quadric_type          