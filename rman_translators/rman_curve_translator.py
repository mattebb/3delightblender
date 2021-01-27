from .rman_mesh_translator import RmanMeshTranslator
from ..rman_sg_nodes.rman_sg_curve import RmanSgCurve
from ..rfb_utils import object_utils
from ..rfb_utils import string_utils
from ..rfb_utils import property_utils

import bpy
import math

def get_curve(curve):
    P = []
    widths = []
    nvertices = []
    name = ''
    num_curves = len(curve.splines)
    index = []

    for i, spline in enumerate(curve.splines):

        width = []
        for bp in spline.points:
            P.append([bp.co[0], bp.co[1], bp.co[2]])
            w = bp.radius * 0.01
            if w < 0.01:
                w = 0.01
            width.extend( 3 * [w])  

        widths.append(width)
        index.append(i)
        nvertices.append(len(spline.points))
        name = spline.id_data.name
    
    return (P, num_curves, nvertices, widths, index, name)

def get_bezier_curve(curve):
    splines = []

    for spline in curve.splines:
        P = []
        width = []

        for bp in spline.bezier_points:
            P.append(bp.handle_left)
            P.append(bp.co)
            P.append(bp.handle_right)
            width.extend( 3 * [bp.radius * 0.01])

        if spline.use_cyclic_u:
            period = 'periodic'
            # wrap the initial handle around to the end, to begin on the CV
            P = P[1:] + P[:1]
        else:
            period = 'nonperiodic'
            # remove the two unused handles
            P = P[1:-1]
            width = width[1:-1]

        name = spline.id_data.name
        splines.append((P, width, period, name))

    return splines      


def get_is_cyclic(curve):
    if len(curve.splines) < 1:
        return False    
    spline = curve.splines[0]
    return (spline.use_cyclic_u or spline.use_cyclic_v)

def get_curve_type(curve):
    if len(curve.splines) < 1:
        return None
    spline = curve.splines[0]
    # enum in [‘POLY’, ‘BEZIER’, ‘BSPLINE’, ‘CARDINAL’, ‘NURBS’], default ‘POLY’
    return spline.type

class RmanCurveTranslator(RmanMeshTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'CURVE'       

    def export(self, ob, db_name):
        is_mesh = False
        if ob.data.dimensions == '2D':
            sg_node = self.rman_scene.sg_scene.CreateGroup(db_name)
        elif len(ob.data.splines) < 1:
            sg_node = self.rman_scene.sg_scene.CreateMesh(db_name)
            is_mesh = True
        else:
            l = ob.data.extrude + ob.data.bevel_depth
            if l > 0:
                sg_node = self.rman_scene.sg_scene.CreateMesh(db_name)
                is_mesh = True                            
            else:
                sg_node = self.rman_scene.sg_scene.CreateGroup(db_name)

        rman_sg_curve = RmanSgCurve(self.rman_scene, sg_node, db_name)
        rman_sg_curve.is_mesh = is_mesh

        if is_mesh and self.rman_scene.do_motion_blur:
            rman_sg_curve.is_transforming = object_utils.is_transforming(ob)
            rman_sg_curve.is_deforming = object_utils._is_deforming_(ob)

        return rman_sg_curve

    def export_deform_sample(self, rman_sg_curve, ob, time_sample):
        if rman_sg_curve.is_mesh:
            super().export_deform_sample(rman_sg_curve, ob, time_sample)

    def export_object_primvars(self, ob, rman_sg_node):
        if rman_sg_node.is_mesh:
            super().export_object_primvars(ob, rman_sg_node)

    def update(self, ob, rman_sg_curve):

        if rman_sg_curve.is_mesh:
            super().update(ob, rman_sg_curve)
            return True    

        curve_type =  get_curve_type(ob.data)
        if curve_type == 'BEZIER':
            self.update_bezier_curve(ob, rman_sg_curve)
        else:
            self.update_curve(ob, rman_sg_curve)

    def update_curve(self, ob, rman_sg_curve):
        for c in [ rman_sg_curve.sg_node.GetChild(i) for i in range(0, rman_sg_curve.sg_node.GetNumChildren())]:
            rman_sg_curve.sg_node.RemoveChild(c)
            self.rman_scene.sg_scene.DeleteDagNode(c) 

        P, num_curves, nvertices, widths, index, name = get_curve(ob.data)
        num_pts = len(P)
         
        curves_sg = self.rman_scene.sg_scene.CreateCurves(name)
        curves_sg.Define(self.rman_scene.rman.Tokens.Rix.k_linear, 'nonperiodic', "linear", num_curves, num_pts)
        
        primvar = curves_sg.GetPrimVars()
        primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, P, "vertex")   
        primvar.SetIntegerDetail(self.rman_scene.rman.Tokens.Rix.k_Ri_nvertices, nvertices, "uniform")
        if widths:
            primvar.SetFloatDetail(self.rman_scene.rman.Tokens.Rix.k_width, widths, "vertex")
        primvar.SetIntegerDetail("index", index, "uniform")
        curves_sg.SetPrimVars(primvar)     

        rman_sg_curve.sg_node.AddChild(curves_sg)          

    def update_bezier_curve(self, ob, rman_sg_curve):

        for c in [ rman_sg_curve.sg_node.GetChild(i) for i in range(0, rman_sg_curve.sg_node.GetNumChildren())]:
            rman_sg_curve.sg_node.RemoveChild(c)
            self.rman_scene.sg_scene.DeleteDagNode(c)             

        curves = get_bezier_curve(ob.data)
        for P, width, period, name in curves:
            num_pts = len(P)
            if num_pts < 1:
                continue
            curves_sg = self.rman_scene.sg_scene.CreateCurves(name)
            curves_sg.Define(self.rman_scene.rman.Tokens.Rix.k_cubic, period, "bezier", 1, num_pts)
            
            primvar = curves_sg.GetPrimVars()
            primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, P, "vertex")   
            primvar.SetIntegerDetail(self.rman_scene.rman.Tokens.Rix.k_Ri_nvertices, [num_pts], "uniform")
            if width:
                primvar.SetFloatDetail(self.rman_scene.rman.Tokens.Rix.k_width, width, "vertex")
            curves_sg.SetPrimVars(primvar)

            rman_sg_curve.sg_node.AddChild(curves_sg)        