from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_points import RmanSgPoints
from ..rman_utils import object_utils
from ..rman_utils import string_utils

import bpy
import math

class RmanPointsTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'POINTS' 

    def export(self, ob, db_name):

        sg_node = self.rman_scene.sg_scene.CreatePoints(db_name)
        rman_sg_points = RmanSgPoints(self.rman_scene, sg_node, db_name)

        self.update(ob, rman_sg_points)

        return rman_sg_points

    def export_deform_sample(self, rman_sg_points, ob, time_samples, time_sample):
        mesh = None
        mesh = ob.to_mesh()

        (nverts, verts, P, N) = object_utils._get_mesh_(mesh, get_normals=False)
        
        # if this is empty continue:
        if nverts == []:
            ob.to_mesh_clear() 
            return None

        npoints = int(len(P)/3)
        rman_sg_points.sg_node.Define( npoints )
        rman_sg_points.npoints = npoints

        primvar = rman_sg_points.sg_node.GetPrimVars()
        
        if time_samples:        
            primvar.SetTimeSamples( time_samples )

        pts = list( zip(*[iter(P)]*3 ) )
        primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, pts, "vertex", time_sample)

        rman_sg_points.sg_node.SetPrimVars(primvar) 

        ob.to_mesh_clear()       

    def update(self, ob, rman_sg_points, input_mesh=None):
        mesh = input_mesh
        rm = ob.renderman
        if not mesh:
            mesh = ob.to_mesh()        

        (nverts, verts, P, N) = object_utils._get_mesh_(mesh, get_normals=False)

        npoints = int(len(P)/3)
        rman_sg_points.sg_node.Define(npoints)
        rman_sg_points.npoints = npoints

        primvar = rman_sg_points.sg_node.GetPrimVars()
        primvar.Clear()      

        pts = list( zip(*[iter(P)]*3 ) )
        primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, pts, "vertex")

        primvar.SetStringDetail("type", rm.primitive_point_type, "uniform")
        primvar.SetFloatDetail(self.rman_scene.rman.Tokens.Rix.k_constantwidth, rm.primitive_point_width, "constant")
            
        #primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_displacementbound_sphere, rm.displacementbound)
        rman_sg_points.sg_node.SetPrimVars(primvar)         

        if not input_mesh:
            ob.to_mesh_clear()           
