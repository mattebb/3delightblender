from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_gp import RmanSgGreaseP
from ..rman_utils import object_utils
from ..rman_utils import string_utils
from ..rfb_logger import rfb_log

import bpy
import math
import numpy as np

class RmanGPencilTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'GPENCIL' 


    def export_object_primvars(self, ob, sg_node):
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

    def _triangles(self, ob, lyr, stroke, rman_sg_gpencil):
        # This code path makes one mesh for each triangle

        gp_ob = ob.data
        mat =  gp_ob.materials[stroke.material_index]
        if mat.grease_pencil.hide:
            return
        mat_db_name = object_utils.get_db_name(mat)
        rman_sg_material = self.rman_scene.rman_materials.get(mat_db_name, None)            

        i = 0
        pts = stroke.points
        for t in stroke.triangles:
            mesh_sg = self.rman_scene.sg_scene.CreateMesh('%s-TRIANGLE-%d' % (lyr.info, i))
            P = []
            mesh_sg.Define( 1, 3, 3 )
                            
            primvar = mesh_sg.GetPrimVars()
                        
            P.append( pts[t.v1].co )
            P.append( pts[t.v2].co )
            P.append( pts[t.v3].co )
            st = []
            st.extend(t.uv1)
            st.extend(t.uv2)
            st.extend(t.uv3)

            primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, P, "vertex")

            primvar.SetIntegerDetail(self.rman_scene.rman.Tokens.Rix.k_Ri_nvertices, [3], "uniform")
            primvar.SetIntegerDetail(self.rman_scene.rman.Tokens.Rix.k_Ri_vertices, [0,1,2], "facevarying") 
            primvar.SetFloatArrayDetail("st", st, 2, "vertex")

            mesh_sg.SetPrimVars(primvar)

            # Attach material
            if rman_sg_material:
                mesh_sg.SetMaterial(rman_sg_material.sg_node)  


            rman_sg_gpencil.sg_node.AddChild(mesh_sg)  
            i += 1     

    def _create_mesh(self, ob, i, lyr, stroke, rman_sg_gpencil):

        gp_ob = ob.data
        mat =  gp_ob.materials[stroke.material_index]
        if mat.grease_pencil.hide:
            return
        mat_db_name = object_utils.get_db_name(mat)
        rman_sg_material = self.rman_scene.rman_materials.get(mat_db_name, None)            

        pts = stroke.points
        nverts = []
        verts = []
        st = []

        num_pts = len(pts)
        P = np.zeros(num_pts*3, dtype=np.float32)
        pts.foreach_get('co', P)
        P = P.tolist()

        mesh_sg = self.rman_scene.sg_scene.CreateMesh('%s-MESH-%d' % (lyr.info, i))
        for t in stroke.triangles:
            nverts.append(3)
            verts.append(t.v1)
            verts.append(t.v2)
            verts.append(t.v3)
            st.extend(t.uv1)
            st.extend(t.uv2)
            st.extend(t.uv3)            

        num_polygons = len(stroke.triangles)
        num_verts = len(verts)
        mesh_sg.Define( num_polygons, num_pts, num_verts )
                            
        primvar = mesh_sg.GetPrimVars()
        primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, P, "vertex")

        primvar.SetIntegerDetail(self.rman_scene.rman.Tokens.Rix.k_Ri_nvertices, nverts, "uniform")
        primvar.SetIntegerDetail(self.rman_scene.rman.Tokens.Rix.k_Ri_vertices, verts, "facevarying")  
        primvar.SetFloatArrayDetail("st", st, 2, "facevarying")  
        mesh_sg.SetPrimVars(primvar)
        if rman_sg_material:
            mesh_sg.SetMaterial(rman_sg_material.sg_node)         
        rman_sg_gpencil.sg_node.AddChild(mesh_sg)     
        
    def _create_curve(self, ob, i, lyr, stroke, rman_sg_gpencil):
        gp_ob = ob.data        

        mat =  gp_ob.materials[stroke.material_index]
        if mat.grease_pencil.hide:
            return
        mat_db_name = object_utils.get_db_name(mat)
        rman_sg_material = self.rman_scene.rman_materials.get(mat_db_name, None) 

        points = []
        vertsArray = []
        widths = []
                    
        for pt in stroke.points:
            points.append(pt.co)
            widths.append(float(1/stroke.line_width) * 3 * pt.pressure)

        if len(points) < 1:
            return

        # double the first and last
        points = points[:1] + \
            points + points[-1:]
        widths = widths[:1] + widths + widths[-1:]
        vertsInCurve = len(points)

        # catmull-rom requires at least 4 vertices
        if vertsInCurve < 4:
            return

        vertsArray.append(vertsInCurve)

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
            curves_sg.SetMaterial(rman_sg_material.sg_node)          

        rman_sg_gpencil.sg_node.AddChild(curves_sg)                  

    def _get_strokes_(self, ob, rman_sg_gpencil):

        gp_ob = ob.data

        for nm,lyr in gp_ob.layers.items():
            if lyr.hide:
                continue
            for frame in lyr.frames:
                for i, stroke in enumerate(frame.strokes):
                    if len(stroke.triangles) > 0:
                        self._create_mesh(ob, i, lyr, stroke, rman_sg_gpencil)
                    else:
                        self._create_curve(ob, i, lyr, stroke, rman_sg_gpencil)
