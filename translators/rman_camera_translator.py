from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_camera import RmanSgCamera
from ..rman_sg_nodes.rman_sg_node import RmanSgNode
from ..rman_utils import transform_utils
from ..rman_utils import property_utils
import math

def _render_get_resolution_(r):
    xres = int(r.resolution_x * r.resolution_percentage * 0.01)
    yres = int(r.resolution_y * r.resolution_percentage * 0.01)
    return xres, yres    

def _render_get_aspect_(r, camera=None, x=-1, y=-1):
    if x != -1 and y != -1:
        xratio = x * 1.0 / 200.0
        yratio = y * 1.0 / 200.0        
    else:
        xres, yres = _render_get_resolution_(r)
        xratio = xres * r.pixel_aspect_x / 200.0
        yratio = yres * r.pixel_aspect_y / 200.0

    if camera is None or camera.type != 'PERSP':
        fit = 'AUTO'
    else:
        fit = camera.sensor_fit

    if fit == 'HORIZONTAL' or fit == 'AUTO' and xratio > yratio:
        aspectratio = xratio / yratio
        xaspect = aspectratio
        yaspect = 1.0
    elif fit == 'VERTICAL' or fit == 'AUTO' and yratio > xratio:
        aspectratio = yratio / xratio
        xaspect = 1.0
        yaspect = aspectratio
    else:
        aspectratio = xaspect = yaspect = 1.0

    return xaspect, yaspect, aspectratio    

class RmanCameraTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'CAMERA'
        self.s_rightHanded = self.rman_scene.rman.Types.RtMatrix4x4(1.0,0.0,0.0,0.0,
                                                               0.0,1.0,0.0,0.0,
                                                               0.0,0.0,-1.0,0.0,
                                                               0.0,0.0,0.0,1.0) 

    def update_viewport_transform(self, rman_sg_camera):
        mtx = self.rman_scene.context.region_data.view_matrix.inverted()
        v = transform_utils.convert_matrix(mtx)
        if rman_sg_camera.cam_matrix == v:
            return        
        rman_sg_camera.cam_matrix = v
        rman_sg_camera.sg_node.SetTransform( v )            

        camtransform = self.rman_scene.rman.Types.RtMatrix4x4()
        camtransform.Identity()
        rman_sg_camera.sg_node.SetOrientTransform(self.s_rightHanded)          


    def update_transform(self, ob, rman_sg_camera):

        cam = ob.data
        mtx = ob.matrix_world

        v = transform_utils.convert_matrix(mtx)
        if rman_sg_camera.cam_matrix == v:
            return

        rman_sg_camera.cam_matrix = v
        rman_sg_camera.sg_node.SetTransform( v )              

        camtransform = self.rman_scene.rman.Types.RtMatrix4x4()
        camtransform.Identity()
        rman_sg_camera.sg_node.SetOrientTransform(self.s_rightHanded)

    def export_viewport_cam(self, db_name=""):  
        sg_camera = self.rman_scene.sg_scene.CreateCamera(db_name)
        rman_sg_camera = RmanSgCamera(self.rman_scene, sg_camera, db_name)
        self.update_viewport_cam(rman_sg_camera)
        self.update_viewport_transform(rman_sg_camera)  
        return rman_sg_camera            


    def export(self, ob, db_name=""):
        sg_camera = self.rman_scene.sg_scene.CreateCamera(db_name)
        rman_sg_camera = RmanSgCamera(self.rman_scene, sg_camera, db_name)
        self.update(ob, rman_sg_camera)
        self.update_transform(ob, rman_sg_camera)
        return rman_sg_camera        

    def update_viewport_cam(self, rman_sg_camera):
        region = self.rman_scene.context.region
        region_data = self.rman_scene.context.region_data
        width = region.width
        height = region.height
        proj = None

        if (width == rman_sg_camera.res_width) and (height == rman_sg_camera.res_height):
            return
        
        rman_sg_camera.res_width = width
        rman_sg_camera.res_height = height

        options = self.rman_scene.sg_scene.GetOptions()

        if region_data.view_perspective == 'CAMERA':

            ob = self.rman_scene.context.space_data.camera
            cam = ob.data
            
            #xaspect, yaspect, aspectratio = _render_get_aspect_(r, cam, x=width, y=height)
            aspect_ratio = width / height
            lens = cam.lens

            sensor = cam.sensor_height \
                if cam.sensor_fit == 'VERTICAL' else cam.sensor_width

            fov = math.degrees(cam.angle) #+14.0
           
            proj = self.rman_scene.rman.SGManager.RixSGShader("Projection", "PxrCamera", "proj")

            projparams = proj.params          

            """
            offset = tuple(region_data.view_camera_offset)
            x_aspect_comp = 1 if aspect_ratio > 1 else 1 / aspect_ratio
            y_aspect_comp = aspect_ratio if aspect_ratio > 1 else 1
            zoom = 4 / ((math.sqrt(2) + region_data.view_camera_zoom / 50) ** 2)
            horizontal_fit = cam.sensor_fit == 'HORIZONTAL' or \
                     (cam.sensor_fit == 'AUTO' and aspect_ratio > 1)

            if cam.sensor_fit == 'VERTICAL':
                film_height = cam.sensor_height / 1000 * zoom
                film_width = film_height * aspect_ratio
            elif horizontal_fit:
                film_width = cam.sensor_width / 1000 * zoom
                film_height = film_width / aspect_ratio
            else:
                film_height = cam.sensor_width / 1000 * zoom
                film_width = film_height * aspect_ratio

            shift_x = ((offset[0] * 2 + (cam.shift_x * x_aspect_comp)) / zoom) * film_width
            shift_y = ((offset[1] * 2 + (cam.shift_y * y_aspect_comp)) / zoom) * film_height

            projparams.SetFloat("shiftX", cam.shift_x)
            projparams.SetFloat("shiftY", cam.shift_y)
            """

            projparams.SetFloat(self.rman_scene.rman.Tokens.Rix.k_fov, fov)

            """

            if cam.dof.use_dof:
                if cam.dof.focus_object:
                    dof_distance = (ob.location - cam.dof.focus_object.location).length
                else:
                    dof_distance = cam.dof.focus_distance
                if dof_distance > 0.0:
                    projparams.SetFloat(self.rman_scene.rman.Tokens.Rix.k_fStop, cam.dof.aperture_fstop)
                    projparams.SetFloat(self.rman_scene.rman.Tokens.Rix.k_focalLength, (cam.lens * 0.001))
                    projparams.SetFloat(self.rman_scene.rman.Tokens.Rix.k_focalDistance, dof_distance)
            """
            #options.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_ScreenWindow, (-xaspect, xaspect, -yaspect, yaspect), 4)
        elif region_data.view_perspective == 'PERSP':

            ob = self.rman_scene.context.space_data.camera
            cam = ob.data
            
            #xaspect, yaspect, aspectratio = _render_get_aspect_(r, cam, x=width, y=height)
            aspect_ratio = width / height
            lens = cam.lens

            sensor = cam.sensor_height \
                if cam.sensor_fit == 'VERTICAL' else cam.sensor_width

            fov = math.degrees(cam.angle) #+14.0
           
            proj = self.rman_scene.rman.SGManager.RixSGShader("Projection", "PxrCamera", "proj")

            projparams = proj.params          

            """            
            offset = tuple(region_data.view_camera_offset)
            x_aspect_comp = 1 if aspect_ratio > 1 else 1 / aspect_ratio
            y_aspect_comp = aspect_ratio if aspect_ratio > 1 else 1
            zoom = 4 / ((math.sqrt(2) + region_data.view_camera_zoom / 50) ** 2)
            horizontal_fit = cam.sensor_fit == 'HORIZONTAL' or \
                     (cam.sensor_fit == 'AUTO' and aspect_ratio > 1)

            if cam.sensor_fit == 'VERTICAL':
                film_height = cam.sensor_height / 1000 * zoom
                film_width = film_height * aspect_ratio
            elif horizontal_fit:
                film_width = cam.sensor_width / 1000 * zoom
                film_height = film_width / aspect_ratio
            else:
                film_height = cam.sensor_width / 1000 * zoom
                film_width = film_height * aspect_ratio

            shift_x = ((offset[0] * 2 + (cam.shift_x * x_aspect_comp)) / zoom) * film_width
            shift_y = ((offset[1] * 2 + (cam.shift_y * y_aspect_comp)) / zoom) * film_height

            projparams.SetFloat("shiftX", cam.shift_x)
            projparams.SetFloat("shiftY", cam.shift_y)
            """

            projparams.SetFloat(self.rman_scene.rman.Tokens.Rix.k_fov, fov)

            """

            if cam.dof.use_dof:
                if cam.dof.focus_object:
                    dof_distance = (ob.location - cam.dof.focus_object.location).length
                else:
                    dof_distance = cam.dof.focus_distance
                if dof_distance > 0.0:
                    projparams.SetFloat(self.rman_scene.rman.Tokens.Rix.k_fStop, cam.dof.aperture_fstop)
                    projparams.SetFloat(self.rman_scene.rman.Tokens.Rix.k_focalLength, (cam.lens * 0.001))
                    projparams.SetFloat(self.rman_scene.rman.Tokens.Rix.k_focalDistance, dof_distance)
            """
            #options.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_ScreenWindow, (-xaspect, xaspect, -yaspect, yaspect), 4)            
        options.SetIntegerArray(self.rman_scene.rman.Tokens.Rix.k_Ri_FormatResolution, (width, height), 2)
        options.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_FormatPixelAspectRatio, 1.0)                     


        self.rman_scene.sg_scene.SetOptions(options)

        rman_sg_camera.sg_node.SetProjection(proj)

        prop = rman_sg_camera.sg_node.GetProperties()
        rman_sg_camera.sg_node.SetProperties(prop)            
        rman_sg_camera.sg_node.SetRenderable(True)         

    def update(self, ob, rman_sg_camera):

        r = self.rman_scene.bl_scene.render
        cam = ob.data
        rm = self.rman_scene.bl_scene.renderman

        xaspect, yaspect, aspectratio = _render_get_aspect_(r, cam)

        options = self.rman_scene.sg_scene.GetOptions()

        if self.rman_scene.bl_scene.render.use_border and not self.rman_scene.bl_scene.render.use_crop_to_border:
            min_x = self.rman_scene.bl_scene.render.border_min_x
            max_x = self.rman_scene.bl_scene.render.border_max_x
            if (min_x >= max_x):
                min_x = 0.0
                max_x = 1.0
            min_y = 1.0 - self.rman_scene.bl_scene.render.border_min_y
            max_y = 1.0 - self.rman_scene.bl_scene.render.border_max_y
            if (min_y >= max_y):
                min_y = 0.0
                max_y = 1.0

            options.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_CropWindow, (min_x, max_x, min_y, max_y), 4)

        proj = None

        if cam.renderman.projection_type != 'none':
            # use pxr Camera
            if cam.renderman.get_projection_name() == 'PxrCamera':
                lens = cam.lens
                sensor = cam.sensor_height \
                    if cam.sensor_fit == 'VERTICAL' else cam.sensor_width
                fov = 360.0 * \
                    math.atan((sensor * 0.5) / lens / aspectratio) / math.pi
            proj = self.rman_scene.rman.SGManager.RixSGShader("Projection", "PxrCamera", "proj")
            projparams = proj.params
            projparams.SetFloat("fov", fov )     
            rman_sg_node = RmanSgNode(self.rman_scene, proj, "")                           
            property_utils.property_group_to_rixparams(cam.renderman.get_projection_node(), rman_sg_node, proj)
        elif cam.type == 'PERSP':

            lens = cam.lens

            sensor = cam.sensor_height \
                if cam.sensor_fit == 'VERTICAL' else cam.sensor_width

            fov = 360.0 * math.atan((sensor * 0.5) / lens / aspectratio) / math.pi

            #proj = self.rman_scene.rman.SGManager.RixSGShader("Projection", "PxrPerspective", "proj")            
            proj = self.rman_scene.rman.SGManager.RixSGShader("Projection", "PxrCamera", "proj")

            projparams = proj.params
            
            # 3.6 chosen arbitrarily via trial-and-error
            projparams.SetFloat("shiftX", cam.shift_x * 3.6)
            projparams.SetFloat("shiftY", cam.shift_y * 3.6)               

            projparams.SetFloat(self.rman_scene.rman.Tokens.Rix.k_fov, fov)

            if cam.dof.use_dof:
                if cam.dof.focus_object:
                    dof_distance = (ob.location - cam.dof.focus_object.location).length
                else:
                    dof_distance = cam.dof.focus_distance
                if dof_distance > 0.0:
                    projparams.SetFloat(self.rman_scene.rman.Tokens.Rix.k_fStop, cam.dof.aperture_fstop)
                    projparams.SetFloat(self.rman_scene.rman.Tokens.Rix.k_focalLength, (cam.lens * 0.001))
                    #projparams.SetFloat(self.rman_scene.rman.Tokens.Rix.k_focalLength, (cam.lens))
                    projparams.SetFloat(self.rman_scene.rman.Tokens.Rix.k_focalDistance, dof_distance)
                
                     
        elif cam.type == 'PANO':
            proj = self.rman_scene.rman.SGManager.RixSGShader("Projection", "PxrSphereCamera", "proj")
            projparams = proj.params
            projparams.SetFloat("hsweep", 360)
            projparams.SetFloat("vsweep", 180)           
        else:
            lens = cam.ortho_scale
            xaspect = xaspect * lens / (aspectratio * 2.0)
            yaspect = yaspect * lens / (aspectratio * 2.0)
            proj = self.rman_scene.rman.SGManager.RixSGShader("Projection", "PxrOrthographic", "proj")

        # convert the crop border to screen window, flip y
        resolution = _render_get_resolution_(self.rman_scene.bl_scene.render)
        if self.rman_scene.bl_scene.render.use_border and self.rman_scene.bl_scene.render.use_crop_to_border:
            screen_min_x = -xaspect + 2.0 * self.rman_scene.bl_scene.render.border_min_x * xaspect
            screen_max_x = -xaspect + 2.0 * self.rman_scene.bl_scene.render.border_max_x * xaspect
            screen_min_y = -yaspect + 2.0 * (self.rman_scene.bl_scene.render.border_min_y) * yaspect
            screen_max_y = -yaspect + 2.0 * (self.rman_scene.bl_scene.render.border_max_y) * yaspect

            options.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_ScreenWindow, (screen_min_x, screen_max_x, screen_min_y, screen_max_y), 4)

            res_x = resolution[0] * (self.rman_scene.bl_scene.render.border_max_x -
                                    self.rman_scene.bl_scene.render.border_min_x)
            res_y = resolution[1] * (self.rman_scene.bl_scene.render.border_max_y -
                                    self.rman_scene.bl_scene.render.border_min_y)

            options.SetIntegerArray(self.rman_scene.rman.Tokens.Rix.k_Ri_FormatResolution, (int(res_x), int(res_y)), 2)
            options.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_FormatPixelAspectRatio, 1.0)        
        else:            
            if cam.type == 'PANO':
                options.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_ScreenWindow, (-1, 1, -1, 1), 4)
            else:
                options.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_ScreenWindow, (-xaspect, xaspect, -yaspect, yaspect), 4)
            options.SetIntegerArray(self.rman_scene.rman.Tokens.Rix.k_Ri_FormatResolution, (resolution[0], resolution[1]), 2)
            options.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_FormatPixelAspectRatio, 1.0)

        self.rman_scene.sg_scene.SetOptions(options)

        rman_sg_camera.sg_node.SetProjection(proj)

        prop = rman_sg_camera.sg_node.GetProperties()

        # clipping planes         
        prop.SetFloat(self.rman_scene.rman.Tokens.Rix.k_nearClip, cam.clip_start)
        prop.SetFloat(self.rman_scene.rman.Tokens.Rix.k_farClip, cam.clip_end)

        # aperture
        prop.SetInteger(self.rman_scene.rman.Tokens.Rix.k_apertureNSides, cam.dof.aperture_blades)
        prop.SetFloat(self.rman_scene.rman.Tokens.Rix.k_apertureAngle, math.degrees(cam.dof.aperture_rotation))
        prop.SetFloat(self.rman_scene.rman.Tokens.Rix.k_apertureRoundness, cam.renderman.aperture_roundness)
        prop.SetFloat(self.rman_scene.rman.Tokens.Rix.k_apertureDensity, cam.renderman.aperture_density)

        prop.SetFloat(self.rman_scene.rman.Tokens.Rix.k_dofaspect, cam.dof.aperture_ratio)    

        rman_sg_camera.sg_node.SetProperties(prop)
        #rman_sg_camera.sg_node.SetRenderable(True)