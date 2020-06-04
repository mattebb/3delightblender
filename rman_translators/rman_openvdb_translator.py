from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_openvdb import RmanSgOpenVDB
from ..rman_utils import filepath_utils
from ..rman_utils import transform_utils
from ..rman_utils import string_utils

class RmanOpenVDBTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'VOLUME' 

    def export(self, ob, db_name):

        sg_node = self.rman_scene.sg_scene.CreateVolume(db_name)
        sg_node.Define(0,0,0)
        rman_sg_openvdb = RmanSgOpenVDB(self.rman_scene, sg_node, db_name)

        return rman_sg_openvdb

    def export_deform_sample(self, rman_sg_openvdb, ob, time_sample):
        pass


    def update(self, ob, rman_sg_openvdb):
        db = ob.data

        if db.filepath == '':
            return

        openvdb_file = filepath_utils.get_real_path(db.filepath)
        grids = db.grids

        active_index = grids.active_index

        bounds = transform_utils.convert_ob_bounds(ob.bound_box)
        primvar = rman_sg_openvdb.sg_node.GetPrimVars()

        primvar.SetString(self.rman_scene.rman.Tokens.Rix.k_Ri_type, "blobbydso:impl_openvdb")
        primvar.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_Bound, string_utils.convert_val(bounds), 6)

        for i, grid in enumerate(grids):
            if i == active_index:
                primvar.SetStringArray(self.rman_scene.rman.Tokens.Rix.k_blobbydso_stringargs, [openvdb_file, "%s:fogvolume" % grid.name], 2)

            if grid.data_type in ['FLOAT', 'DOUBLE']:
                primvar.SetFloatDetail(grid.name, [], "varying")
            elif grid.data_type in ['VECTOR_FLOAT', 'VECTOR_DOUBLE', 'VECTOR_INT']:
                primvar.SetVectorDetail(grid.name, [], "varying")
            elif grid.data_type in ['INT', 'INT64']:
                primvar.SetIntegerDetail(grid.name, [], "varying")

        rman_sg_openvdb.sg_node.SetPrimVars(primvar)         
