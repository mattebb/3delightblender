from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_brickmap import RmanSgBrickmap

import bpy

class RmanBrickmapTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'BRICKMAP'       

    def export(self, ob, db_name):

        sg_node = self.rman_scene.sg_scene.CreateGeometry(db_name)
        sg_node.SetGeometry(self.rman_scene.rman.Tokens.Rix.k_Ri_BrickMap)
        rman_sg_brickmap = RmanSgBrickmap(self.rman_scene, sg_node, db_name)

        return rman_sg_brickmap

    def export_deform_sample(self, rman_sg_brickmap, ob, time_sample):
        pass

    def update(self, ob, rman_sg_brickmap):       
        primvar = rman_sg_brickmap.sg_node.GetPrimVars()
        rm = ob.renderman
        bkm_filepath = rm.bkm_filepath 
        primvar.SetString("filename", bkm_filepath)
        rman_sg_brickmap.sg_node.SetPrimVars(primvar)        