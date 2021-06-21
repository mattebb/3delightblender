from .rman_sg_node import RmanSgNode

class RmanSgMaterial(RmanSgNode):

    def __init__(self, rman_scene, sg_node, db_name):
        super().__init__(rman_scene, sg_node, db_name)

        self.has_meshlight = False
        self.is_gp_material = False
        self.sg_stroke_mat = None
        self.sg_fill_mat = None

    @property
    def has_meshlight(self):
        return self.__has_meshlight

    @has_meshlight.setter
    def has_meshlight(self, has_meshlight):
        self.__has_meshlight = has_meshlight      

    @property
    def is_gp_material(self):
        return self.__is_gp_material

    @is_gp_material.setter
    def is_gp_material(self, is_gp_material):
        self.__is_gp_material = is_gp_material   

    @property
    def sg_stroke_mat(self):
        return self.__sg_stroke_mat

    @sg_stroke_mat.setter
    def sg_stroke_mat(self, sg_stroke_mat):
        self.__sg_stroke_mat = sg_stroke_mat            

    @property
    def sg_fill_mat(self):
        return self.__sg_fill_mat

    @sg_fill_mat.setter
    def sg_fill_mat(self, sg_fill_mat):
        self.__sg_fill_mat = sg_fill_mat                                  