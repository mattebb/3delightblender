from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_alembic import RmanSgAlembic
#from ..rfb_utils import filepath_utils
from ..rfb_utils import transform_utils
from ..rfb_utils import string_utils
from ..rfb_logger import rfb_log

class RmanAlembicTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'ALEMBIC' 

    def export(self, ob, db_name):

        sg_node = self.rman_scene.sg_scene.CreateProcedural(db_name)
        sg_node.Define("DynamicLoad", None)
        rman_sg_alembic = RmanSgAlembic(self.rman_scene, sg_node, db_name)

        return rman_sg_alembic

    def export_deform_sample(self, rman_sg_alembic, ob, time_sample):
        pass

    def update(self, ob, rman_sg_alembic):
        rm = ob.renderman
        abc_filepath = rm.abc_filepath #filepath_utils.get_real_path(rm.abc_filepath)
        bounds = (-100000, 100000, -100000, 100000, -100000, 100000 )

        primvar = rman_sg_alembic.sg_node.GetPrimVars()
        primvar.SetString(self.rman_scene.rman.Tokens.Rix.k_dsoname, 'AlembicProcPrim')
        primvar.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_bound, bounds, 6)

        shutter_interval = self.rman_scene.bl_scene.renderman.shutter_angle / 360.0
        shutter_open, shutter_close = 0, shutter_interval   
        abc_frame = rm.abc_frame
        if rm.abc_use_scene_frame:
            rman_sg_alembic.is_frame_sensitive = True
            abc_frame = float(self.rman_scene.bl_frame_current)       
        else:
            rman_sg_alembic.is_frame_sensitive = False

        abc_args = "-filename %s -frame %f -fps %f -shutteropen %f -shutterclose %f -ccw" % (abc_filepath, abc_frame, rm.abc_fps, shutter_open, shutter_close)

        primvar.SetString(self.rman_scene.rman.Tokens.Rix.k_data, abc_args)

        rman_sg_alembic.sg_node.SetPrimVars(primvar)        

