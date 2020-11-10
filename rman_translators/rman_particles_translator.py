from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_particles import RmanSgParticles
from ..rfb_utils import object_utils
from ..rfb_utils import transform_utils

import bpy
import math

class RmanParticlesTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'PARTICLES'  

    def export(self, ob, psys, db_name):

        if psys.settings.type == 'HAIR' and psys.settings.render_type != 'PATH':
            return None   
        if psys.settings.type == 'EMITTER' and psys.settings.render_type == 'OBJECT':
            return None

        self.particles_type = psys.settings.type

        sg_node = self.rman_scene.sg_scene.CreateGroup(db_name)
        rman_sg_particles = RmanSgParticles(self.rman_scene, sg_node, db_name)

        emitter_translator = self.rman_scene.rman_translators['EMITTER']
        emitter_db_name = '%s-EMITTER' % psys.settings.name
        rman_sg_emitter = emitter_translator.export(ob, psys, emitter_db_name)

        hair_translator = self.rman_scene.rman_translators['HAIR']
        hair_db_name = '%s-HAIR' % psys.settings.name
        rman_sg_hair = hair_translator.export(ob, psys, hair_db_name)        

        rman_sg_particles.rman_sg_emitter = rman_sg_emitter
        rman_sg_particles.rman_sg_hair = rman_sg_hair

        return rman_sg_particles

    def set_motion_steps(self, rman_sg_particles, motion_steps):
        rman_sg_particles.motion_steps = motion_steps
        rman_sg_particles.rman_sg_emitter.motion_steps = motion_steps
        rman_sg_particles.rman_sg_hair.motion_steps = motion_steps

    def export_deform_sample(self, rman_sg_particles, ob, psys, time_sample):
        emitter_translator = self.rman_scene.rman_translators['EMITTER']
        hair_translator = self.rman_scene.rman_translators['HAIR']        

        if psys.settings.type == 'EMITTER' and psys.settings.render_type != 'OBJECT':
            emitter_translator.export_deform_sample(rman_sg_particles.rman_sg_emitter, ob, psys, time_sample)
        elif psys.settings.type == 'HAIR' and psys.settings.render_type == 'PATH':
            #hair_translator.export_deform_sample(rman_sg_particles.rman_sg_hair, ob, psys, time_sample)
            pass


    def clear_children(self, ob, psys, rman_sg_particles):
        if rman_sg_particles.sg_node:        
            for c in [ rman_sg_particles.sg_node.GetChild(i) for i in range(0, rman_sg_particles.sg_node.GetNumChildren())]:
                rman_sg_particles.sg_node.RemoveChild(c)
                self.rman_scene.sg_scene.DeleteDagNode(c)                

    def update(self, ob, psys, rman_sg_particles):

        if psys.settings.type == 'HAIR' and psys.settings.render_type == 'PATH':
            hair_translator = self.rman_scene.rman_translators['HAIR']
            hair_translator.update(ob, psys, rman_sg_particles.rman_sg_hair)
            if rman_sg_particles.rman_sg_hair.sg_node:
                rman_sg_particles.sg_node.AddChild(rman_sg_particles.rman_sg_hair.sg_node)

            if self.particles_type == 'EMITTER':
                rman_sg_particles.sg_node.RemoveChild(rman_sg_particles.rman_sg_emitter.sg_node)
            self.particles_type = psys.settings.type

        elif psys.settings.type == 'EMITTER' and psys.settings.render_type != 'OBJECT':
            emitter_translator = self.rman_scene.rman_translators['EMITTER']  
            emitter_translator.update(ob, psys, rman_sg_particles.rman_sg_emitter)
            if rman_sg_particles.rman_sg_emitter.sg_node:
                rman_sg_particles.sg_node.AddChild(rman_sg_particles.rman_sg_emitter.sg_node)
            if self.particles_type == 'HAIR':
                rman_sg_particles.sg_node.RemoveChild(rman_sg_particles.rman_sg_hair.sg_node)                
            self.particles_type = psys.settings.type