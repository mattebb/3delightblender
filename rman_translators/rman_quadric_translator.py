from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_quadric import RmanSgQuadric

class RmanQuadricTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'QUADRIC' 

    def export(self, ob, db_name):

        sg_node = self.rman_scene.sg_scene.CreateQuadric(db_name)
        rman_sg_quadric = RmanSgQuadric(self.rman_scene, sg_node, db_name)

        return rman_sg_quadric

    def export_deform_sample(self, rman_sg_quadric, ob, time_sample):
        pass


    def update(self, ob, rman_sg_quadric):
        rm = ob.renderman
        quadric_type = rm.rman_quadric_type
        rman_sg_quadric.quadric_type = quadric_type
        primvar = rman_sg_quadric.sg_node.GetPrimVars()     
        primvar.Clear()
        if quadric_type == 'SPHERE':
            rman_sg_quadric.sg_node.SetGeometry(self.rman_scene.rman.Tokens.Rix.k_Ri_Sphere)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_radius, rm.quadric_radius)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_zmin, rm.quadric_zmin)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_zmax, rm.quadric_zmax)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_thetamax, rm.quadric_sweepangle)
    
        elif quadric_type == 'CYLINDER':
            rman_sg_quadric.sg_node.SetGeometry(self.rman_scene.rman.Tokens.Rix.k_Ri_Cylinder)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_radius, rm.quadric_radius)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_zmin, rm.quadric_zmin)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_zmax, rm.quadric_zmax)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_thetamax, rm.quadric_sweepangle)

        elif quadric_type == 'CONE':
            rman_sg_quadric.sg_node.SetGeometry(self.rman_scene.rman.Tokens.Rix.k_Ri_Cone)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_radius, rm.quadric_radius)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_height, rm.quadric_cone_height)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_thetamax, rm.quadric_sweepangle)

        elif quadric_type == 'DISK':
            rman_sg_quadric.sg_node.SetGeometry(self.rman_scene.rman.Tokens.Rix.k_Ri_Disk)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_radius, rm.quadric_radius)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_height, rm.quadric_disk_height)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_thetamax, rm.quadric_sweepangle)

        elif quadric_type == 'TORUS':
            rman_sg_quadric.sg_node.SetGeometry(self.rman_scene.rman.Tokens.Rix.k_Ri_Torus)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_majorradius, rm.quadric_majorradius)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_minorradius, rm.quadric_minorradius)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_phimin, rm.quadric_phimin)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_phimax, rm.quadric_phimax)            
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_thetamax, rm.quadric_sweepangle)

        rman_sg_quadric.sg_node.SetPrimVars(primvar)        
