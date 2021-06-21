from .rman_sg_node import RmanSgNode

class RmanSgBlobby(RmanSgNode):

    def __init__(self, rman_scene, sg_node, db_name):
        super().__init__(rman_scene, sg_node, db_name)
        self.matrix_world = None

    @property
    def matrix_world(self):
        return self.__matrix_world

    @matrix_world.setter
    def matrix_world(self, mtx):
        self.__matrix_world = mtx