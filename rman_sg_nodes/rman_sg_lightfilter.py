from .rman_sg_node import RmanSgNode

class RmanSgLightFilter(RmanSgNode):

    def __init__(self, rman_scene, sg_node, db_name):
        super().__init__(rman_scene, sg_node, db_name)
        self.matrix_world = None
        self.coord_sys = ''
        self.sg_filter_node = None
        self.lights_list = list() # list of lights referencing this light filter

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

    @property
    def sg_filter_node(self):
        return self.__sg_filter_node

    @sg_filter_node.setter
    def sg_filter_node(self, sg_filter_node):
        self.__sg_filter_node = sg_filter_node    

    @property
    def lights_list(self):
        return self.__lights_list

    @lights_list.setter
    def lights_list(self, lights_list):
        self.__lights_list = lights_list                             