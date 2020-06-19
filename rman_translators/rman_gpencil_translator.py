from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_gp import RmanSgGreaseP
from ..rman_utils import object_utils
from ..rman_utils import string_utils
from ..rfb_logger import rfb_log
from mathutils import Vector, Matrix

import bpy
import math
import numpy as np

_BIAS_ = 0.0000001
_ADJUST_POINT_ = False
_ADJUST_IN_NORMAL_DIR_FOR_FILLS_ = False

class RmanGPencilTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'GPENCIL' 


    def export_object_primvars(self, ob, rman_sg_node):
        pass


    def export(self, ob, db_name):
        prim_type = object_utils._detect_primitive_(ob)
        
        sg_node = self.rman_scene.sg_scene.CreateGroup(db_name)
        rman_sg_gpencil = RmanSgGreaseP(self.rman_scene, sg_node, db_name)

        return rman_sg_gpencil

    def update(self, ob, rman_sg_gpencil):
        for c in [ rman_sg_gpencil.sg_node.GetChild(i) for i in range(0, rman_sg_gpencil.sg_node.GetNumChildren())]:
            rman_sg_gpencil.sg_node.RemoveChild(c)
            self.rman_scene.sg_scene.DeleteDagNode(c)        
        
        self._get_strokes_(ob, rman_sg_gpencil)     

        return True    

    def _create_mesh(self, ob, i, lyr, stroke, rman_sg_gpencil, rman_sg_material, adjust_point=False):

        gp_ob = ob.data     

        pts = stroke.points
        nverts = []
        verts = []
        st = []

        mesh_sg = self.rman_scene.sg_scene.CreateMesh('%s-MESH-%d' % (lyr.info, i))

        # get points
        num_pts = len(pts)
        P = np.zeros(num_pts*3, dtype=np.float32)
        pts.foreach_get('co', P)
        P = np.reshape(P, (num_pts, 3))
        P = P.tolist()

        if hasattr(pts[0], 'uv_fill'):
            st = np.zeros(num_pts*2, dtype=np.float32)
            pts.foreach_get('uv_fill', st)
            st = np.reshape(st, (num_pts, 2))
            st = st.tolist()                

        for t in stroke.triangles:
            nverts.append(3)
            verts.append(t.v1)
            verts.append(t.v2)
            verts.append(t.v3)       

            if adjust_point:

                if _ADJUST_IN_NORMAL_DIR_FOR_FILLS_:
                    # move each point in the normal direction a little bit
                    # for fills                
                    p1 = Vector(pts[t.v1].co)
                    p2 = Vector(pts[t.v2].co)
                    p3 = Vector(pts[t.v3].co)
                    vec1 = p1 - p2
                    vec2 = p1 - p3
                    normal = vec2.cross(vec1).normalized()
                    epsilon = normal * i * _BIAS_

                    P[t.v1] = Vector(P[t.v1]) + epsilon
                    P[t.v2] = Vector(P[t.v2]) + epsilon
                    P[t.v3] = Vector(P[t.v3]) + epsilon

                else:
                    # get camera position
                    cam_pos, rot, sca = self.rman_scene.main_camera.bl_camera.matrix_world.decompose()

                    epsilon = i * _BIAS_
                    P[t.v1] = Vector(P[t.v1]) + ((cam_pos - Vector(P[t.v1])).normalized() * epsilon)
                    P[t.v2] = Vector(P[t.v2]) + ((cam_pos - Vector(P[t.v2])).normalized() * epsilon)
                    P[t.v3] = Vector(P[t.v3]) + ((cam_pos - Vector(P[t.v3])).normalized() * epsilon)


        num_polygons = len(stroke.triangles)
        num_verts = len(verts)
        mesh_sg.Define( num_polygons, num_pts, num_verts )
                            
        primvar = mesh_sg.GetPrimVars()
        primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, P, "vertex")

        primvar.SetIntegerDetail(self.rman_scene.rman.Tokens.Rix.k_Ri_nvertices, nverts, "uniform")
        primvar.SetIntegerDetail(self.rman_scene.rman.Tokens.Rix.k_Ri_vertices, verts, "facevarying")  
        if st:
            primvar.SetFloatArrayDetail("st", st, 2, "vertex")  
        mesh_sg.SetPrimVars(primvar)
        if rman_sg_material:
            mesh_sg.SetMaterial(rman_sg_material.sg_fill_mat)         
        rman_sg_gpencil.sg_node.AddChild(mesh_sg)     

    def _create_points(self, ob, i, lyr, stroke, rman_sg_gpencil, rman_sg_material, adjust_point=False):
        gp_ob = ob.data 

        num_pts = len(stroke.points)
        points = np.zeros(num_pts*3, dtype=np.float32)
        widths = np.zeros(num_pts, dtype=np.float32)
        stroke.points.foreach_get('co', points)
        stroke.points.foreach_get('pressure', widths)

        points = np.reshape(points, (num_pts, 3))
        points = points.tolist()    

        if adjust_point:
            cam_pos, rot, sca = self.rman_scene.main_camera.bl_camera.matrix_world.decompose()
            for j, pt in enumerate(points):
                epsilon = i * _BIAS_            
                points[j] = Vector(pt) + ((cam_pos - Vector(pt)).normalized() * epsilon)              
        
        width_factor = 0.0012 * stroke.line_width
        widths = widths * width_factor #0.03
        widths = widths.tolist()

        points_sg = self.rman_scene.sg_scene.CreatePoints("%s-DOTS-%d" % (lyr.info, i))
        i += 1                
        points_sg.Define(num_pts)
        primvar = points_sg.GetPrimVars()

        primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, points, "vertex")  
        primvar.SetFloatDetail(self.rman_scene.rman.Tokens.Rix.k_width, widths, "vertex")              
                    
        points_sg.SetPrimVars(primvar)

        # Attach material
        if rman_sg_material:
            points_sg.SetMaterial(rman_sg_material.sg_stroke_mat)          

        rman_sg_gpencil.sg_node.AddChild(points_sg)                     
        
    def _create_curve(self, ob, i, lyr, stroke, rman_sg_gpencil, rman_sg_material, adjust_point=False):
        gp_ob = ob.data       

        vertsArray = []
        num_pts = len(stroke.points)
        points = np.zeros(num_pts*3, dtype=np.float32)
        widths = np.zeros(num_pts, dtype=np.float32)
        stroke.points.foreach_get('co', points)
        stroke.points.foreach_get('pressure', widths)

        points = np.reshape(points, (num_pts, 3))
        points = points.tolist()        
        
        width_factor = 0.00083 * stroke.line_width
        widths = widths * width_factor #0.05
        widths = widths.tolist()

        # double the first and last
        points = points[:1] + \
            points + points[-1:]

        if len(points) < 4:
            # not enough points to be a curve. export as points
            self._create_points(ob, i, lyr, stroke, rman_sg_gpencil, rman_sg_material, adjust_point=adjust_point)
            return

        if adjust_point:
            cam_pos, rot, sca = self.rman_scene.main_camera.bl_camera.matrix_world.decompose()            
            for j, pt in enumerate(points):
                epsilon = i * _BIAS_            
                points[j] = Vector(pt) + ((cam_pos - Vector(pt)).normalized() * epsilon)            

        widths = widths[:1] + widths + widths[-1:]
        vertsArray.append(len(points))

        curves_sg = self.rman_scene.sg_scene.CreateCurves("%s-STROKE-%d" % (lyr.info, i))
        i += 1                
        curves_sg.Define(self.rman_scene.rman.Tokens.Rix.k_cubic, "nonperiodic", "catmull-rom", len(vertsArray), len(points))
        primvar = curves_sg.GetPrimVars()

        primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, points, "vertex")                
        primvar.SetIntegerDetail(self.rman_scene.rman.Tokens.Rix.k_Ri_nvertices, vertsArray, "uniform")
        primvar.SetIntegerDetail("index", range(len(vertsArray)), "uniform")

        primvar.SetFloatDetail(self.rman_scene.rman.Tokens.Rix.k_width, widths, "vertex")
                    
        curves_sg.SetPrimVars(primvar)

        # Attach material
        if rman_sg_material:
            curves_sg.SetMaterial(rman_sg_material.sg_stroke_mat)          

        rman_sg_gpencil.sg_node.AddChild(curves_sg)    

    def _get_strokes_(self, ob, rman_sg_gpencil):

        gp_ob = ob.data

        j = 0
        for nm,lyr in gp_ob.layers.items():
            if lyr.hide:
                continue

            frame = lyr.active_frame
            if not frame:
                continue
            for i, stroke in enumerate(frame.strokes):
                j += i
                mat =  gp_ob.materials[stroke.material_index]
                if mat.grease_pencil.hide:
                    continue      
                rman_sg_material = self.rman_scene.rman_materials.get(mat.original, None)

                if len(stroke.triangles) > 0 and rman_sg_material.sg_fill_mat:
                    self._create_mesh(ob, j, lyr, stroke, rman_sg_gpencil, rman_sg_material, adjust_point=_ADJUST_POINT_) 
                    if rman_sg_material.sg_stroke_mat:
                        if mat.grease_pencil.mode in ['DOTS', 'BOX']:
                            self._create_points(ob, j, lyr, stroke, rman_sg_gpencil, rman_sg_material, adjust_point=_ADJUST_POINT_)
                        else:
                            self._create_curve(ob, j, lyr, stroke, rman_sg_gpencil, rman_sg_material, adjust_point=_ADJUST_POINT_)                        

                else:
                    if mat.grease_pencil.mode in ['DOTS', 'BOX']:
                        self._create_points(ob, j, lyr, stroke, rman_sg_gpencil, rman_sg_material, adjust_point=_ADJUST_POINT_)
                    else:
                        self._create_curve(ob, j, lyr, stroke, rman_sg_gpencil, rman_sg_material, adjust_point=_ADJUST_POINT_)               
                i +=1
            j += 1