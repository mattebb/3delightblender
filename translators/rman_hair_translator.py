from .rman_translator import RmanTranslator
from ..rman_utils import transform_utils
from ..rman_utils import object_utils
from ..rman_sg_nodes.rman_sg_hair import RmanSgHair
from mathutils import Vector
import math
import bpy    
   

class RmanHairTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'HAIR'  

    def export(self, ob, psys, db_name):

        sg_node = self.rman_scene.sg_scene.CreateGroup(db_name)
        rman_sg_hair = RmanSgHair(self.rman_scene, sg_node, db_name)

        self.update(ob, psys, rman_sg_hair)
        return rman_sg_hair


    def update(self, ob, psys, rman_sg_hair):
        for c in [ rman_sg_hair.sg_node.GetChild(i) for i in range(0, rman_sg_hair.sg_node.GetNumChildren())]:
            rman_sg_hair.sg_node.RemoveChild(c)
            self.rman_scene.sg_scene.DeleteDagNode(c)

        curves = self._get_strands_(ob, psys)
        i = 0
        for vertsArray, points, widthString, widths, scalpS, scalpT in curves:
            curves_sg = self.rman_scene.sg_scene.CreateCurves("%s-%d" % (psys.name, i))
            i += 1                
            curves_sg.Define(self.rman_scene.rman.Tokens.Rix.k_cubic, "nonperiodic", "catmull-rom", len(vertsArray), int(len(points)/3))
            primvar = curves_sg.GetPrimVars()

            pts = list( zip(*[iter(points)]*3 ) )
            primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, pts, "vertex")                
            primvar.SetIntegerDetail(self.rman_scene.rman.Tokens.Rix.k_Ri_nvertices, vertsArray, "uniform")
            primvar.SetIntegerDetail("index", range(len(vertsArray)), "uniform")

            if widthString == self.rman_scene.rman.Tokens.Rix.k_constantwidth:
                primvar.SetFloatDetail(widthString, widths, "constant")
            else:
                primvar.SetFloatDetail(widthString, widths, "vertex")

            if len(scalpS):
                primvar.SetFloatDetail("scalpS", scalpS, "uniform")                
                primvar.SetFloatDetail("scalpT", scalpT, "uniform")
                    
            curves_sg.SetPrimVars(primvar)

            rman_sg_hair.sg_node.AddChild(curves_sg)   

        # Attach material
        mat_idx = psys.settings.material - 1
        if mat_idx < len(ob.material_slots):
            mat = ob.material_slots[mat_idx].material
            mat_db_name = object_utils.get_db_name(mat)
            rman_sg_material = self.rman_scene.rman_materials.get(mat_db_name, None)
            if rman_sg_material:
                rman_sg_hair.sg_node.SetMaterial(rman_sg_material.sg_node)  

    def _get_strands_(self, ob, psys):

        psys_modifier = None
        for mod in ob.modifiers:
            if hasattr(mod, 'particle_system') and mod.particle_system == psys:
                psys_modifier = mod
                break

        tip_width = psys.settings.tip_radius * psys.settings.radius_scale
        base_width = psys.settings.root_radius * psys.settings.radius_scale

        conwidth = (tip_width == base_width)
        steps = 2 ** psys.settings.render_step
        if conwidth:
            widthString = self.rman_scene.rman.Tokens.Rix.k_constantwidth
            hair_width = base_width
        else:
            widthString = self.rman_scene.rman.Tokens.Rix.k_width
            hair_width = []

        num_parents = len(psys.particles)
        num_children = len(psys.child_particles)
        total_hair_count = num_parents + num_children
        export_st = psys.settings.renderman.export_scalp_st and psys_modifier and len(
            ob.data.uv_layers) > 0

        curve_sets = []

        points = []

        vertsArray = []
        scalpS = []
        scalpT = []
        nverts = 0
        no = 0
        
        for pindex in range(total_hair_count):
            if psys.settings.child_type != 'NONE' and pindex < num_parents:
                continue

            strand_points = []
            # walk through each strand
            for step in range(0, steps + 1):           
                pt = psys.co_hair(ob, particle_no=pindex, step=step)

                if pt.length_squared == 0:
                    # this strand ends prematurely                    
                    break
                

                # put points in object space
                m = ob.matrix_world.inverted_safe()
                pt = Vector(transform_utils.transform_points( m, pt))

                strand_points.extend(pt)

            if len(strand_points) > 1:
                # double the first and last
                strand_points = strand_points[:3] + \
                    strand_points + strand_points[-3:]
                vertsInStrand = len(strand_points) // 3

                # catmull-rom requires at least 4 vertices
                if vertsInStrand < 4:
                    continue

                # for varying width make the width array
                if not conwidth:
                    decr = (base_width - tip_width) / (vertsInStrand - 2)
                    hair_width.extend([base_width] + [(base_width - decr * i)
                                                    for i in range(vertsInStrand - 2)] +
                                    [tip_width])

                # add the last point again
                points.extend(strand_points)
                vertsArray.append(vertsInStrand)
                nverts += vertsInStrand

                # get the scalp S
                if export_st:
                    if pindex >= num_parents:
                        particle = psys.particles[
                            (pindex - num_parents) % num_parents]
                    else:
                        particle = psys.particles[pindex]
                    st = psys.uv_on_emitter(psys_modifier, particle, pindex)
                    scalpS.append(st[0])
                    scalpT.append(st[1])

            # if we get more than 100000 vertices, export ri.Curve and reset.  This
            # is to avoid a maxint on the array length
            if nverts > 100000:
                curve_sets.append(
                    (vertsArray, points, widthString, hair_width, scalpS, scalpT))

                nverts = 0
                points = []
                vertsArray = []
                if not conwidth:
                    hair_width = []
                scalpS = []
                scalpT = []

        if nverts > 0:
            curve_sets.append((vertsArray, points, widthString,
                            hair_width, scalpS, scalpT))

        return curve_sets              
            