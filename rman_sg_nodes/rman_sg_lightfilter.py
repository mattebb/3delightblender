from .rman_sg_node import RmanSgNode

class RmanSgLightFilter(RmanSgNode):

    def __init__(self, rman_scene, sg_node, db_name):
        super().__init__(rman_scene, sg_node, db_name)
        self.matrix_world = None
        self.coord_sys = ''

    @property
    def matrix_world(self):
        return self.__matrix_world

    @matrix_world.setter
    def matrix_world(self, mtx):
        self.__matrix_world = mtx  

    @property
    def coord_sys(self):
        return self.__coord_sys

    @coord_sys.setter
    def coord_sys(self, coord_sys):
        self.__coord_sys = coord_sys         