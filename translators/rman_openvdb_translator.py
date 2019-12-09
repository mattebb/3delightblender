from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_openvdb import RmanSgOpenVDB
from ..rman_utils import filepath_utils
from ..rman_utils import transform_utils
from ..rman_utils import string_utils

class RmanOpenVDBTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'OPENVDB' 

    def export(self, ob, db_name):

        sg_node = self.rman_scene.sg_scene.CreateVolume(db_name)
        sg_node.Define(0,0,0)
        rman_sg_openvdb = RmanSgOpenVDB(self.rman_scene, sg_node, db_name)

        self.update(ob, rman_sg_openvdb)

        return rman_sg_openvdb

    def export_deform_sample(self, rman_sg_openvdb, ob, time_samples, time_sample):
        pass


    def update(self, ob, rman_sg_openvdb):
        rm = ob.renderman
        openvdb_file = filepath_utils.get_real_path(rm.path_archive)
        if rm.procedural_bounds == 'MANUAL':
            min = rm.procedural_bounds_min
            max = rm.procedural_bounds_max
            bounds = [min[0], max[0], min[1], max[1], min[2], max[2]]
        else:
            bounds = transform_utils.convert_ob_bounds(ob.bound_box)

        primvar = rman_sg_openvdb.sg_node.GetPrimVars()

        primvar.SetString(self.rman_scene.rman.Tokens.Rix.k_Ri_type, "blobbydso:impl_openvdb")
        primvar.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_Bound, string_utils.convert_val(bounds), 6)
        primvar.SetStringArray(self.rman_scene.rman.Tokens.Rix.k_blobbydso_stringargs, [openvdb_file, "density:fogvolume"], 2)
        for channel in rm.openvdb_channels:
            if channel.type == "float":
                primvar.SetFloatDetail(channel.name, [], "varying")
            elif channel.type == "vector":
                primvar.SetVectorDetail(channel.name, [], "varying")
            elif channel.type == "color":    
                primvar.SetColorDetail(channel.name, [], "varying")
            elif channel.type == "normal":    
                primvar.SetNormalDetail(channel.name, [], "varying")    


        rman_sg_openvdb.sg_node.SetPrimVars(primvar)        
