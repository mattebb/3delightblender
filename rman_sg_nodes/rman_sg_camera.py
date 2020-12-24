from .rman_sg_node import RmanSgNode

class RmanSgCamera(RmanSgNode):

    def __init__(self, rman_scene, sg_node, db_name):
        super().__init__(rman_scene, sg_node, db_name)
        self.bl_camera = None
        self.cam_matrix = None
        self.res_width = -1
        self.res_height = -1
        self.rman_fov = -1
        self.view_perspective = None
        self.view_camera_zoom = -1
        self.xaspect = -1
        self.yaspect = -1
        self.aspectratio = -1
        self.lens = -1
        self.sensor = -1
        self.view_camera_offset = -1
        self.shift_x = -1
        self.shift_y = -1
        self.screenwindow = None
        self.sg_coord_sys = None

    @property
    def bl_camera(self):
        return self.__bl_camera

    @bl_camera.setter
    def bl_camera(self, bl_camera):
        self.__bl_camera = bl_camera

    @property
    def cam_matrix(self):
        return self.__cam_matrix

    @cam_matrix.setter
    def cam_matrix(self, mtx):
        self.__cam_matrix = mtx

    @property
    def res_width(self):
        return self.__res_width

    @res_width.setter
    def res_width(self, res_width):
        self.__res_width = res_width

    @property
    def res_height(self):
        return self.__res_height

    @res_height.setter
    def res_height(self, res_height):
        self.__res_height = res_height  

    @property
    def rman_fov(self):
        return self.__rman_fov

    @rman_fov.setter
    def rman_fov(self, rman_fov):
        self.__rman_fov = rman_fov   

    @property
    def view_perspective(self):
        return self.__view_perspective

    @view_perspective.setter
    def view_perspective(self, view_perspective):
        self.__view_perspective = view_perspective      

    @property
    def view_camera_zoom(self):
        return self.__view_camera_zoom

    @view_camera_zoom.setter
    def view_camera_zoom(self, view_camera_zoom):
        self.__view_camera_zoom = view_camera_zoom          

    @property
    def xaspect(self):
        return self.__xaspect

    @xaspect.setter
    def xaspect(self, xaspect):
        self.__xaspect = xaspect  

    @property
    def yaspect(self):
        return self.__yaspect

    @yaspect.setter
    def yaspect(self, yaspect):
        self.__yaspect = yaspect      

    @property
    def aspectratio(self):
        return self.__aspectratio

    @aspectratio.setter
    def aspectratio(self, aspectratio):
        self.__aspectratio = aspectratio            

    @property
    def view_camera_offset(self):
        return self.__view_camera_offset

    @view_camera_offset.setter
    def view_camera_offset(self, view_camera_offset):
        self.__view_camera_offset = view_camera_offset               

    @property
    def sg_coord_sys(self):
        return self.__sg_coord_sys

    @sg_coord_sys.setter
    def sg_coord_sys(self, sg_coord_sys):
        self.__sg_coord_sys = sg_coord_sys         
                                       
