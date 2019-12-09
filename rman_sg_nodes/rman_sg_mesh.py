from .rman_sg_node import RmanSgNode

class RmanSgMesh(RmanSgNode):

    def __init__(self, rman_scene, sg_node, db_name):
        super().__init__(rman_scene, sg_node, db_name)
        self.matrix_world = None
        self.npolys = -1 
        self.npoints = -1
        self.nverts = -1
        self.is_subdiv = False

    @property
    def matrix_world(self):
        return self.__matrix_world

    @matrix_world.setter
    def matrix_world(self, mtx):
        self.__matrix_world = mtx

    @property
    def npolys(self):
        return self.__npolys

    @npolys.setter
    def npolys(self, npolys):
        self.__npolys = npolys

    @property
    def npoints(self):
        return self.__npoints

    @npoints.setter
    def npoints(self, npoints):
        self.__npoints = npoints

    @property
    def nverts(self):
        return self.__nverts

    @nverts.setter
    def nverts(self, nverts):
        self.__nverts = nverts 

    @property
    def is_subdiv(self):
        return self.__is_subdiv

    @is_subdiv.setter
    def is_subdiv(self, is_subdiv):
        self.__is_subdiv = is_subdiv                                 