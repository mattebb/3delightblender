from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_particles import RmanSgParticles
from ..rman_utils import object_utils
from ..rman_utils import transform_utils

import bpy
import math

def valid_particle(pa, valid_frames):
    return pa.die_time >= valid_frames[-1] and pa.birth_time <= valid_frames[0]

class RmanParticlesTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'EMITTER' 

    def get_particles(self, ob, psys, valid_frames=None):
        P = []
        rot = []
        width = []

        valid_frames = (self.rman_scene.bl_scene.frame_current,
                        self.rman_scene.bl_scene.frame_current) if valid_frames is None else valid_frames
        
        for pa in [p for p in psys.particles if valid_particle(p, valid_frames)]:
            P.extend(pa.location)
            rot.extend(pa.rotation)

            if pa.alive_state != 'ALIVE':
                width.append(0.0)
            else:
                width.append(pa.size)
        return (P, rot, width)    

    def get_primvars_particle(self, primvar, psys, subframes, sample):
        rm = psys.settings.renderman
        cfra = self.rman_scene.bl_scene.frame_current

        for p in rm.prim_vars:
            pvars = []

            if p.data_source in ('VELOCITY', 'ANGULAR_VELOCITY'):
                if p.data_source == 'VELOCITY':
                    for pa in \
                            [p for p in psys.particles if valid_particle(p, subframes)]:
                        pvars.extend(pa.velocity)
                elif p.data_source == 'ANGULAR_VELOCITY':
                    for pa in \
                            [p for p in psys.particles if valid_particle(p, subframes)]:
                        pvars.extend(pa.angular_velocity)

                primvar.SetFloatArrayDetail(p.name, pvars, 3, "uniform", sample)

            elif p.data_source in \
                    ('SIZE', 'AGE', 'BIRTH_TIME', 'DIE_TIME', 'LIFE_TIME', 'ID'):
                if p.data_source == 'SIZE':
                    for pa in \
                            [p for p in psys.particles if valid_particle(p, subframes)]:
                        pvars.append(pa.size)
                elif p.data_source == 'AGE':
                    for pa in \
                            [p for p in psys.particles if valid_particle(p, subframes)]:
                        pvars.append((cfra - pa.birth_time) / pa.lifetime)
                elif p.data_source == 'BIRTH_TIME':
                    for pa in \
                            [p for p in psys.particles if valid_particle(p, subframes)]:
                        pvars.append(pa.birth_time)
                elif p.data_source == 'DIE_TIME':
                    for pa in \
                            [p for p in psys.particles if valid_particle(p, subframes)]:
                        pvars.append(pa.die_time)
                elif p.data_source == 'LIFE_TIME':
                    for pa in \
                            [p for p in psys.particles if valid_particle(p, subframes)]:
                        pvars.append(pa.lifetime)
                elif p.data_source == 'ID':
                    pvars = [id for id, p in psys.particles.items(
                    ) if valid_particle(p, subframes)]
                
                primvar.SetFloatDetail(p.name, pvars, "varying", sample)         

    def export(self, ob, psys, db_name):

        sg_node = self.rman_scene.sg_scene.CreatePoints(db_name)
        rman_sg_particles = RmanSgParticles(self.rman_scene, sg_node, db_name)

        self.update(ob, psys, rman_sg_particles)

        return rman_sg_particles

    def export_deform_sample(self, rman_sg_particles, ob, psys, time_samples, time_sample):
        rm = psys.settings.renderman
        P, rot, width = self.get_particles(ob, psys)

        m = ob.matrix_world.inverted_safe()
        P = transform_utils.transform_points(m, P)
        if (len(P) < 3):
            return

        primvar = rman_sg_particles.sg_node.GetPrimVars()
        
        if time_samples:        
            primvar.SetTimeSamples( time_samples )

        primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, P, "vertex", time_sample)

        rman_sg_particles.sg_node.SetPrimVars(primvar)     


    def update(self, ob, psys, rman_sg_particles):

        rm = psys.settings.renderman
        P, rot, width = self.get_particles(ob, psys)

        m = ob.matrix_world.inverted_safe()
        P = transform_utils.transform_points(m, P)
        if (len(P) < 3):
            return

        nm_pts = int(len(P)/3)
        rman_sg_particles.sg_node.Define(nm_pts)          

        primvar = rman_sg_particles.sg_node.GetPrimVars()
        primvar.Clear()
        primvar.SetTimeSamples([])

        nm_pts = -1

        self.get_primvars_particle(primvar,  psys, [self.rman_scene.bl_scene.frame_current], 0)      
        

        primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, P, "vertex")                   
        if rm.constant_width:
            primvar.SetFloatDetail(self.rman_scene.rman.Tokens.Rix.k_constantwidth, width, "constant")
        else:
            primvar.SetFloatDetail(self.rman_scene.rman.Tokens.Rix.k_width, width, "vertex")                     

        #primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_displacementbound_sphere, ob.renderman.displacementbound)
        rman_sg_particles.sg_node.SetPrimVars(primvar)

        # Attach material
        mat_idx = psys.settings.material - 1
        if mat_idx < len(ob.material_slots):
            mat = ob.material_slots[mat_idx].material
            mat_db_name = object_utils.get_db_name(mat)
            rman_sg_material = self.rman_scene.rman_materials.get(mat_db_name, None)
            if rman_sg_material:
                rman_sg_particles.sg_node.SetMaterial(rman_sg_material.sg_node)          