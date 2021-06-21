from .rman_sg_node import RmanSgNode

class RmanSgLight(RmanSgNode):

    def __init__(self, rman_scene, sg_node, db_name):
        super().__init__(rman_scene, sg_node, db_name)
        self.matrix_world = None
        self.solo_light = False

    @property
    def matrix_world(self):
        return self.__matrix_world

    @matrix_world.setter
    def matrix_world(self, mtx):
        self.__matrix_world = mtx  

    @property
    def solo_light(self):
        return self.__solo_light

    @solo_light.setter
    def solo_light(self, solo_light):
        self.__solo_light = solo_light          