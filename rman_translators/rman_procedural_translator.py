from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_procedural import RmanSgProcedural

class RmanProceduralTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'DYNAMIC_LOAD_DSO' 

    def export(self, ob, db_name):

        sg_node = self.rman_scene.sg_scene.CreateProcedural(db_name)
        sg_node.Define("DynamicLoad", None)
        rman_sg_procedural = RmanSgProcedural(self.rman_scene, sg_node, db_name)

        return rman_sg_procedural

    def export_deform_sample(self, rman_sg_procedural, ob, time_sample):
        pass


    def update(self, ob, rman_sg_procedural):
        rm = ob.renderman
        path_dso = rm.path_dso
        bounds = (-100000, 100000, -100000, 100000, -100000, 100000 )

        primvar = rman_sg_procedural.sg_node.GetPrimVars()
        primvar.SetString(self.rman_scene.rman.Tokens.Rix.k_dsoname, path_dso)
        primvar.SetString(self.rman_scene.rman.Tokens.Rix.k_data, rm.path_dso_initial_data )
        primvar.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_bound, bounds, 6)

        rman_sg_procedural.sg_node.SetPrimVars(primvar)        
