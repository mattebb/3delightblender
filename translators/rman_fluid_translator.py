from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_fluid import RmanSgFluid
from ..rman_utils import filepath_utils
from ..rman_utils import transform_utils
from ..rman_utils import string_utils
import bpy
import os

def locate_openVDB_cache(cache_dir, frameNum):
    if not bpy.data.is_saved:
        return None
    cacheDir = os.path.join(bpy.path.abspath(cache_dir), 'data')
    if not os.path.exists(cacheDir):
        return None
    for f in os.listdir(cacheDir):
        if os.path.splitext(f)[1] != '.vdb':
            continue
        if 'density' in f and "%04d" % frameNum in f:
            return os.path.join(cacheDir, f)

    return None

class RmanFluidTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'FLUID' 

    def export(self, ob, db_name):

        sg_node = self.rman_scene.sg_scene.CreateVolume(db_name)
        rman_sg_fluid = RmanSgFluid(self.rman_scene, sg_node, db_name)

        return rman_sg_fluid

    def export_deform_sample(self, rman_sg_fluid, ob, time_sample):
        pass


    def update(self, ob, rman_sg_fluid):
        rm = ob.renderman

        fluid_modifier = None
        for mod in ob.modifiers:
            if mod.type == "FLUID":
                fluid_modifier = mod
                break
        fluid_data = fluid_modifier.domain_settings
        # the original object has the modifier too.
        if not fluid_data:
            return

        rman_sg_fluid.sg_node.Define(0,0,0)
        if fluid_data.cache_data_format == 'OPENVDB':
            pass
            # for now, read the grids directly from the domain settings.
            # the vdb files exported from manta don't seem to follow naming conventions. 
            # ex: the name of the density grid seems to be different per grid?
            #self.update_fluid_openvdb(ob, rman_sg_fluid, fluid_data)
        
        self.update_fluid(ob, rman_sg_fluid, fluid_data)

    def update_fluid_openvdb(self, ob, rman_sg_fluid, fluid_data):
        cacheFile = locate_openVDB_cache(fluid_data.cache_directory, self.rman_scene.bl_frame_current)
        if not cacheFile:
            debug('error', "Please save and export OpenVDB files before rendering.")
            return

        primvar = rman_sg_fluid.sg_node.GetPrimVars()
        primvar.SetString(self.rman_scene.rman.Tokens.Rix.k_Ri_type, "blobbydso:impl_openvdb")
        primvar.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_Bound, transform_utils.convert_ob_bounds(ob.bound_box), 6)
        primvar.SetStringArray(self.rman_scene.rman.Tokens.Rix.k_blobbydso_stringargs, [cacheFile, "density:fogvolume"], 2)

        primvar.SetFloatDetail("density", [], "varying")
        primvar.SetFloatDetail("flame", [], "varying")        
        primvar.SetColorDetail("color", [], "varying")                  
        rman_sg_fluid.sg_node.SetPrimVars(primvar)             


    def update_fluid(self, ob, rman_sg_fluid, fluid_data):

        fluid_res = fluid_data.domain_resolution
        rman_sg_fluid.sg_node.Define(fluid_res[0], fluid_res[1], fluid_res[2])

        primvar = rman_sg_fluid.sg_node.GetPrimVars()
        primvar.SetString(self.rman_scene.rman.Tokens.Rix.k_Ri_type, "box")
        primvar.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_Bound, transform_utils.convert_ob_bounds(ob.bound_box), 6)

        primvar.SetFloatDetail("density", fluid_data.density_grid, "varying")
        primvar.SetFloatDetail("flame", fluid_data.flame_grid, "varying")   
        primvar.SetFloatDetail("heat", fluid_data.heat_grid, "varying")
        primvar.SetColorDetail("color", [item for index, item in enumerate(fluid_data.color_grid) if index % 4 != 0], "varying")
        primvar.SetVectorDetail("velocity", [item for index, item in enumerate(fluid_data.velocity_grid) if index % 4 != 0], "varying")

        rman_sg_fluid.sg_node.SetPrimVars(primvar)     
