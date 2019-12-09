from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_dra import RmanSgDra
from ..rman_utils import filepath_utils

class RmanDraTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'DELAYED_LOAD_ARCHIVE' 

    def export(self, ob, db_name):

        sg_node = self.rman_scene.sg_scene.CreateProcedural(db_name)
        sg_node.Define("DelayedReadArchive", None)
        rman_sg_dra = RmanSgDra(self.rman_scene, sg_node, db_name)

        self.update(ob, rman_sg_dra)

        return rman_sg_dra

    def export_deform_sample(self, rman_sg_dra, ob, time_samples, time_sample):
        pass


    def update(self, ob, rman_sg_dra):
        rm = ob.renderman
        path_archive = filepath_utils.get_real_path(rm.path_archive)
        bounds = (-100000, 100000, -100000, 100000, -100000, 100000 )

        primvar = rman_sg_dra.sg_node.GetPrimVars()
        primvar.SetString(self.rman_scene.rman.Tokens.Rix.k_filename, path_archive)
        primvar.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_bound, bounds, 6)

        rman_sg_dra.sg_node.SetPrimVars(primvar)        
