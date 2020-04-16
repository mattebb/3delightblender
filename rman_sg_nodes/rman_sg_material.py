from .rman_sg_node import RmanSgNode

class RmanSgMaterial(RmanSgNode):

    def __init__(self, rman_scene, sg_node, db_name):
        super().__init__(rman_scene, sg_node, db_name)

        self.has_meshlight = False

    @property
    def has_meshlight(self):
        return self.__has_meshlight

    @has_meshlight.setter
    def has_meshlight(self, has_meshlight):
        self.__has_meshlight = has_meshlight        