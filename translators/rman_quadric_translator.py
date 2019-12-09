from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_quadric import RmanSgQuadric

class RmanQuadricTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'QUADRIC' 

    def export(self, ob, db_name):

        sg_node = self.rman_scene.sg_scene.CreateQuadric(db_name)
        rman_sg_quadric = RmanSgQuadric(self.rman_scene, sg_node, db_name)

        self.update(ob, rman_sg_quadric)

        return rman_sg_quadric

    def export_deform_sample(self, rman_sg_quadric, ob, time_samples, time_sample):
        pass


    def update(self, ob, rman_sg_quadric):
        rm = ob.renderman
        prim = rm.primitive
        primvar = rman_sg_quadric.sg_node.GetPrimVars()     
        if prim == 'SPHERE':
            rman_sg_quadric.sg_node.SetGeometry(self.rman_scene.rman.Tokens.Rix.k_Ri_Sphere)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_radius, rm.primitive_radius)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_zmin, rm.primitive_zmin)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_zmax, rm.primitive_zmax)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_thetamax, rm.primitive_sweepangle)
    
        elif prim == 'CYLINDER':
            rman_sg_quadric.sg_node.SetGeometry(self.rman_scene.rman.Tokens.Rix.k_Ri_Cylinder)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_radius, rm.primitive_radius)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_zmin, rm.primitive_zmin)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_zmax, rm.primitive_zmax)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_thetamax, rm.primitive_sweepangle)

        elif prim == 'CONE':
            rman_sg_quadric.sg_node.SetGeometry(self.rman_scene.rman.Tokens.Rix.k_Ri_Cone)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_radius, rm.primitive_radius)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_height, rm.primitive_height)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_thetamax, rm.primitive_sweepangle)

        elif prim == 'DISK':
            rman_sg_quadric.sg_node.SetGeometry(self.rman_scene.rman.Tokens.Rix.k_Ri_Disk)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_radius, rm.primitive_radius)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_height, rm.primitive_height)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_thetamax, rm.primitive_sweepangle)

        elif prim == 'TORUS':
            rman_sg_quadric.sg_node.SetGeometry(self.rman_scene.rman.Tokens.Rix.k_Ri_Torus)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_majorradius, rm.primitive_majorradius)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_minorradius, rm.primitive_minorradius)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_phimin, rm.primitive_phimin)
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_phimax, rm.primitive_phimax)            
            primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_Ri_thetamax, rm.primitive_sweepangle)

        #primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_displacementbound_sphere, rm.displacementbound)
        rman_sg_quadric.sg_node.SetPrimVars(primvar)        
