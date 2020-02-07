# Translators
from .translators.rman_camera_translator import RmanCameraTranslator
from .translators.rman_light_translator import RmanLightTranslator
from .translators.rman_mesh_translator import RmanMeshTranslator
from .translators.rman_material_translator import RmanMaterialTranslator
from .translators.rman_hair_translator import RmanHairTranslator
from .translators.rman_group_translator import RmanGroupTranslator
from .translators.rman_points_translator import RmanPointsTranslator
from .translators.rman_quadric_translator import RmanQuadricTranslator
from .translators.rman_blobby_translator import RmanBlobbyTranslator
from .translators.rman_particles_translator import RmanParticlesTranslator
from .translators.rman_procedural_translator import RmanProceduralTranslator
from .translators.rman_dra_translator import RmanDraTranslator
from .translators.rman_runprogram_translator import RmanRunProgramTranslator
from .translators.rman_openvdb_translator import RmanOpenVDBTranslator
from .translators.rman_gpencil_translator import RmanGPencilTranslator

# utils
from .rman_utils import object_utils
from .rman_utils import transform_utils
from .rman_utils import property_utils
from .rman_utils import transform_utils
from .rman_utils import display_utils
from .rman_utils import string_utils
from .rman_utils import texture_utils
from .rman_utils import filepath_utils
from .rman_utils import scene_utils
from .rman_utils import prefs_utils

from .rfb_logger import rfb_log
from .rman_sg_nodes.rman_sg_node import RmanSgNode

import bpy
import os

class RmanScene(object):
    '''
    The RmanScene handles translating the Blender scene. It also handles changes
    to the scene during interactive rendering.

    Attributes:
        rman_render (RmanRender) - pointer back to the current RmanRender object
        rman () - rman python module
        sg_scene (RixSGSCene) - the RenderMan scene graph object
        context (bpy.types.Context) - the current Blender context object
        depsgraph (bpy.types.Depsgraph) - the Blender dependency graph
        bl_scene (bpy.types.Scene) - the current Blender scene object
        bl_frame_current (int) - the current Blender frame
        bl_view_layer (bpy.types.ViewLayer) - the current Blender view layer
        rm_rl (RendermanRenderLayerSettings) - the current rman layer 
        do_motion_blur (bool) - user requested for motion blur
        rman_bake (bool) - user requested a bake render
        is_interactive (bool) - whether we are in interactive mode
        external_render (bool) - whether we are exporting for external (RIB) renders
        is_viewport_render (bool) - whether we are rendering into Blender's viewport
        scene_solo_light (bool) - user has solo'd a light (all other lights are muted)
        rman_materials (dict) - dictionary of scene's materials
        rman_objects (dict) - dictionary of all objects
        rman_translators (dict) - dictionary of all RmanTranslator(s)
        rman_particles (dict) - dictionary of all particle systems used
        rman_cameras (dict) - dictionary of all cameras in the scene
        obj_hash (dict) - dictionary of hashes to objects ( for object picking )
        motion_steps (set) - the full set of motion steps for the scene, including 
                            overrides from individual objects
        main_camera (RmanSgCamera) - pointer to the main scene camera
        current_ob (list) - current selected objects
        current_ob_db_name (list) - unique datablock names for current selected
                                    objects
    '''

    def __init__(self, rman_render=None):
        self.rman_render = rman_render
        self.rman = rman_render.rman
        self.sg_scene = None
        self.context = None
        self.depsgraph = None
        self.bl_scene = None
        self.bl_frame_current = None
        self.bl_view_layer = None
        self.rm_rl = None 

        self.do_motion_blur = False
        self.rman_bake = False
        self.is_interactive = False
        self.external_render = False
        self.is_viewport_render = False
        self.scene_solo_light = False
        self.scene_any_lights = False
        self.current_ob = []
        self.current_ob_db_name = []

        self.rman_materials = dict()
        self.rman_objects = dict()
        self.rman_translators = dict()
        self.rman_particles = dict()
        self.rman_cameras = dict()
        self.obj_hash = dict() 
        self.moving_objects = dict()
        self.processed_obs = dict()

        self.motion_steps = set()
        self.main_camera = None
        self.world_df_node = None

        self.create_translators()     

    def create_translators(self):

        self.rman_translators['CAMERA'] = RmanCameraTranslator(rman_scene=self)
        self.rman_translators['LIGHT'] = RmanLightTranslator(rman_scene=self)
        self.rman_translators['MATERIAL'] = RmanMaterialTranslator(rman_scene=self)       
        self.rman_translators['HAIR'] = RmanHairTranslator(rman_scene=self) 
        self.rman_translators['GROUP'] = RmanGroupTranslator(rman_scene=self)
        self.rman_translators['POINTS'] = RmanPointsTranslator(rman_scene=self)
        self.rman_translators['META'] = RmanBlobbyTranslator(rman_scene=self)
        self.rman_translators['EMITTER'] = RmanParticlesTranslator(rman_scene=self)
        self.rman_translators['DYNAMIC_LOAD_DSO'] = RmanProceduralTranslator(rman_scene=self)
        self.rman_translators['DELAYED_LOAD_ARCHIVE'] = RmanDraTranslator(rman_scene=self)
        self.rman_translators['PROCEDURAL_RUN_PROGRAM'] = RmanRunProgramTranslator(rman_scene=self)
        self.rman_translators['OPENVDB'] = RmanOpenVDBTranslator(rman_scene=self)
        self.rman_translators['GPENCIL'] = RmanGPencilTranslator(rman_scene=self)

        mesh_translator = RmanMeshTranslator(rman_scene=self)
        self.rman_translators['POLYGON_MESH'] = mesh_translator
        self.rman_translators['SUBDIVISION_MESH'] = mesh_translator
        self.rman_translators['MESH'] = mesh_translator

        quadric_translator = RmanQuadricTranslator(rman_scene=self)
        for prim in ['SPHERE', 'CYLINDER', 'CONE', 'DISK', 'TORUS']:
            self.rman_translators[prim] = quadric_translator

    def _find_renderman_layer(self):
        self.rm_rl = None
        rm = self.bl_scene.renderman
            
        for l in rm.render_layers:
            if l.render_layer == self.bl_view_layer.name:
                self.rm_rl = l
                break                  

    def reset(self):
        # clear out dictionaries etc.
        self.rman_materials = dict()
        self.rman_objects = dict()
        self.rman_particles = dict()
        self.rman_cameras = dict()        
        self.obj_hash = dict() 
        self.motion_steps = set()       
        self.moving_objects = dict()
        self.processed_obs = dict()
        self.current_ob = []
        self.current_ob_db_name = []        

    def export_for_final_render(self, depsgraph, sg_scene, bl_view_layer, is_external=False):
        self.sg_scene = sg_scene
        self.context = bpy.context #None
        self.bl_scene = depsgraph.scene_eval
        self.bl_view_layer = bl_view_layer
        self._find_renderman_layer()
        self.depsgraph = depsgraph
        self.external_render = is_external
        self.is_interactive = False
        self.is_viewport_render = False
        self.do_motion_blur = self.bl_scene.renderman.motion_blur
        self.rman_bake = (self.bl_scene.renderman.hider_type == 'BAKE')

        self.export()

    def export_for_interactive_render(self, context, depsgraph, sg_scene):
        self.sg_scene = sg_scene
        self.context = context
        self.bl_view_layer = context.view_layer
        self.bl_scene = depsgraph.scene_eval        
        self._find_renderman_layer()
        self.depsgraph = depsgraph
        self.external_render = False
        self.is_interactive = True
        self.is_viewport_render = False
        
        if self.bl_scene.renderman.render_into == 'blender':
            self.is_viewport_render = True

        self.do_motion_blur = False

        self.export()         

    def export_for_rib_selection(self, context, sg_scene):
        self.reset()
        self.bl_scene = context.scene
        self.bl_frame_current = self.bl_scene.frame_current
        self.sg_scene = sg_scene
        self.context = context
        self.bl_view_layer = context.view_layer
        self._find_renderman_layer()        
        
        self.depsgraph = context.evaluated_depsgraph_get()
        ob = context.active_object
        self.export_materials([m for m in self.depsgraph.ids if isinstance(m, bpy.types.Material)])
        self.export_data_blocks([ob])
        self.export_instances(obj_selected=ob)

    def export(self):

        self.reset()

        # update variables
        string_utils.set_var('scene', self.bl_scene.name)
        string_utils.set_var('layer', self.bl_view_layer.name)

        self.bl_frame_current = self.bl_scene.frame_current
        self.scene_any_lights = self._scene_has_lights()

        rfb_log().debug("Calling export_materials()")
        #self.export_materials(bpy.data.materials)
        self.export_materials([m for m in self.depsgraph.ids if isinstance(m, bpy.types.Material)])
                
        rfb_log().debug("Calling txmake_all()")
        texture_utils.get_txmanager().rman_scene = self  
        texture_utils.get_txmanager().txmake_all(blocking=True)
        
        rfb_log().debug("Calling export_data_blocks()")
        self.export_data_blocks(bpy.data.objects)
        #self.export_data_blocks([x for x in self.depsgraph.ids if isinstance(x, bpy.types.Object)])

        self.export_searchpaths() 
        self.export_global_options()     
        self.export_hider()
        self.export_integrator()
        self.export_cameras([c for c in self.depsgraph.objects if isinstance(c.data, bpy.types.Camera)])
        
        if self.is_viewport_render:
            # For now, when rendering into Blender's viewport, create 
            # a simple Ci,a display
            self.export_viewport_display()
        else:
            self.export_displays()


        self.export_samplefilters()
        self.export_displayfilters()

        if self.do_motion_blur:
            rfb_log().debug("Calling export_instances_motion()")
            self.export_instances_motion()
        else:
            rfb_log().debug("Calling export_instances()")
            self.export_instances()

        if self.is_interactive:
            self.check_solo_light()

            if self.is_viewport_render:
                self.export_viewport_stats()

    def export_materials(self, materials):
        for mat in materials:   
            db_name = object_utils.get_db_name(mat)        
            rman_sg_material = self.rman_translators['MATERIAL'].export(mat, db_name)
            if rman_sg_material:                
                self.rman_materials[db_name] = rman_sg_material         
            
    def export_data_blocks(self, data_blocks):
        for obj in data_blocks:
            if obj.type not in ('ARMATURE', 'CURVE', 'CAMERA'):
                ob = obj.evaluated_get(self.depsgraph)           
                self.export_data_block(ob) 

    def export_data_block(self, db_ob):
        obj = bpy.data.objects.get(db_ob.name, None)

        if obj and obj.type not in ('ARMATURE', 'CURVE', 'CAMERA'):
            ob = obj.evaluated_get(self.depsgraph)            
            rman_type = object_utils._detect_primitive_(ob)  
            db_name = object_utils.get_db_name(ob, rman_type=rman_type)
            if rman_type == 'LIGHT':
                if ob.data.renderman.renderman_type == 'FILTER':
                    # skip if this is a light filter
                    # these will be exported when we do regular lights
                    return
                elif ob.data.renderman.renderman_type == 'ENV':
                    # check if there are portals attached to this light
                    # if there are, skip
                    any_portals = False
                    for c in obj.children:
                        if c.type == 'LIGHT' and c.data.renderman.renderman_type == 'PORTAL':
                            any_portals = True
                            break
                    if any_portals:
                        return  

            translator =  self.rman_translators.get(rman_type, None)
            if not translator:
                return

            rman_sg_node = None
            if db_name in self.rman_objects:
                return
            rman_sg_node = translator.export(ob, db_name)
            if not rman_sg_node:
                return
            translator.export_object_primvars(ob, rman_sg_node.sg_node)
            self.rman_objects[db_name] = rman_sg_node 

            if rman_type in ['POLYGON_MESH', 'SUBDIVISION_MESH', 'POINTS']:
                # Deal with any particles now. Particles are children to mesh nodes.
                subframes = scene_utils._get_subframes_(2, self.bl_scene)
                self.motion_steps.update(subframes)
                for psys in ob.particle_systems:
                    psys_translator = self.rman_translators[psys.settings.type]
                    if psys.settings.type == 'HAIR' and psys.settings.render_type == 'PATH':
                        hair_db_name = object_utils.get_db_name(ob, psys=psys)
                        rman_sg_hair_node = psys_translator.export(ob, psys, hair_db_name)
                        rman_sg_hair_node.motion_steps = subframes
                        psys_translator.update(ob, psys, rman_sg_hair_node)
                        if rman_sg_hair_node.sg_node:
                            rman_sg_node.sg_node.AddChild(rman_sg_hair_node.sg_node)                               
                        self.rman_particles[hair_db_name] = rman_sg_hair_node
                    elif psys.settings.type == 'EMITTER' and psys.settings.render_type != 'OBJECT':
                        psys_db_name = object_utils.get_db_name(ob, psys=psys)
                        rman_sg_particles_node = psys_translator.export(ob, psys, psys_db_name)
                        rman_sg_particles_node.motion_steps = subframes
                        psys_translator.update(ob, psys, rman_sg_particles_node)
                        if rman_sg_particles_node.sg_node:
                            rman_sg_node.sg_node.AddChild(rman_sg_particles_node.sg_node)  
                        self.rman_particles[psys_db_name] = rman_sg_particles_node                         

            # motion blur
            if rman_sg_node.is_transforming or rman_sg_node.is_deforming:
                mb_segs = self.bl_scene.renderman.motion_segments
                if ob.renderman.motion_segments_override:
                    mb_segs = ob.renderman.motion_segments
                if mb_segs > 1:
                    subframes = scene_utils._get_subframes_(mb_segs, self.bl_scene)
                    rman_sg_node.motion_steps = subframes
                    self.motion_steps.update(subframes)
                    self.moving_objects[ob.name_full] = ob
                else:
                    rman_sg_node.is_transforming = False
                    rman_sg_node.is_deforming = False

    def _scene_has_lights(self):
        return (len([x for x in self.bl_scene.objects if x.type == 'LIGHT']) > 0)        

    def _export_instance(self, ob_inst, seg=None):
   
        group_db_name = object_utils.get_group_db_name(ob_inst) 
        rman_group_translator = self.rman_translators['GROUP']
        parent_sg_node = None
        if ob_inst.is_instance:
            ob = ob_inst.instance_object
            parent = ob_inst.parent
            if parent.type == "EMPTY" and parent.is_instancer:
                parent_db_name = object_utils.get_db_name(parent)
                parent_sg_node = self.rman_objects.get(parent_db_name, None)
                if not parent_sg_node:
                    parent_sg_node = rman_group_translator.export(parent, parent_db_name)
                    self.rman_objects[parent_db_name] = parent_sg_node    

        else:
            ob = ob_inst.object 
         
        if ob.type in ('ARMATURE', 'CURVE', 'CAMERA'):
            return                          

        rman_type = object_utils._detect_primitive_(ob)

        if ob.type == "EMPTY" and ob.is_instancer:
            empty_db_name = object_utils.get_db_name(ob)
            rman_sg_node = self.rman_objects.get(empty_db_name, None)
            if not rman_sg_node:
                rman_sg_node = rman_group_translator.export(ob, empty_db_name)
                self.rman_objects[empty_db_name] = rman_sg_node    
        else:
            db_name = object_utils.get_db_name(ob, rman_type=rman_type)          
            if db_name == '':
                return

            if rman_type == "META":
                # only add the meta instance that matches the family name
                if ob.name_full != object_utils.get_meta_family(ob):
                    return

            rman_sg_node = self.rman_objects.get(db_name, None)           
            if not rman_sg_node:
                return
            if group_db_name in rman_sg_node.instances:
                # we've already added this instance
                return

            translator = self.rman_translators.get(rman_type, None)
            if translator:
                if db_name not in self.processed_obs:
                    translator.update(ob, rman_sg_node)
                    self.processed_obs[db_name] = ob

            if rman_sg_node.sg_node is None:
                return

            rman_sg_group = rman_group_translator.export(ob, group_db_name)
            rman_sg_group.sg_node.AddChild(rman_sg_node.sg_node)
            
            if rman_type != "META":
                # meta/blobbies are already in world space. Their instances don't need to
                # set a transform.
                if rman_sg_node.is_transforming:
                    rman_group_translator.update_transform_num_samples(rman_sg_group, rman_sg_node.motion_steps )
                    rman_group_translator.update_transform_sample(ob_inst, rman_sg_group, 0, seg )
                else:
                    rman_group_translator.update_transform(ob_inst, rman_sg_group)

            self.sg_scene.Root().AddChild(rman_sg_group.sg_node)
            self.rman_objects[group_db_name] = rman_sg_group

            # object attrs             
            if translator:
                translator.export_object_attributes(ob, rman_sg_group.sg_node)  

            self.attach_material(ob, rman_sg_group.sg_node)

            # add instance to the RmanSgNode
            if parent_sg_node:
                parent_sg_node.instances[group_db_name] = rman_sg_group 
            else:
                rman_sg_node.instances[group_db_name] = rman_sg_group         

    def export_instances(self, obj_selected=None):
        objFound = False
        for ob_inst in self.depsgraph.object_instances:
            if obj_selected:
                if objFound:
                    break

                if ob_inst.is_instance:
                    if ob_inst.instance_object.name == obj_selected:
                        objFound = True
                elif ob_inst.object.name == obj_selected.name:
                        objFound = True

                if not objFound:
                    continue

            self._export_instance(ob_inst)  

    def attach_material(self, ob, group):
        for mat in object_utils._get_used_materials_(ob): 
            if not mat:
                continue
            mat_db_name = object_utils.get_db_name(mat)
            rman_sg_material = self.rman_materials.get(mat_db_name, None)
            if rman_sg_material and rman_sg_material.sg_node:
                group.SetMaterial(rman_sg_material.sg_node)        

    def export_instances_motion(self, obj_selected=None):
        actual_subframes = []
        origframe = self.bl_scene.frame_current

        mb_segs = self.bl_scene.renderman.motion_segments
        origframe = self.bl_scene.frame_current
        #actual_subframes = [origframe + subframe for subframe in subframes]        

        motion_steps = sorted(list(self.motion_steps))

        first_sample = False
        for samp, seg in enumerate(motion_steps):
            first_sample = (samp == 0)
            if seg < 0.0:
                self.rman_render.bl_engine.frame_set(origframe - 1, subframe=1.0 + seg)
            else:
                self.rman_render.bl_engine.frame_set(origframe, subframe=seg)  

            self.depsgraph.update()

            total = len(self.depsgraph.object_instances)
            objFound = False
            
            # update camera
            if not first_sample and self.main_camera.is_transforming and seg in self.main_camera.motion_steps:
                cam_translator =  self.rman_translators['CAMERA']
                cam_translator.update_transform(self.depsgraph.scene_eval.camera, self.main_camera, samp)

            for i, ob_inst in enumerate(self.depsgraph.object_instances):  
                if obj_selected:
                    if objFound:
                        break

                    if ob_inst.is_instance:
                        if ob_inst.instance_object.name == obj_selected:
                            objFound = True
                    elif ob_inst.object.name == obj_selected.name:
                            objFound = True

                    if not objFound:
                        continue       

                if first_sample:
                    # for the first motion sample use _export_instance()
                    self._export_instance(ob_inst, seg=seg)  
                    continue  

                if ob_inst.is_instance:
                    ob = ob_inst.instance_object.original  
                else:
                    ob = ob_inst.object

                if ob.type not in ['MESH']:
                    continue

                group_db_name = object_utils.get_group_db_name(ob_inst)

                rman_type = object_utils._detect_primitive_(ob)
                db_name = object_utils.get_db_name(ob, rman_type=rman_type)              
                if db_name == '':
                    continue

                # deal with particles first
                for psys in ob.particle_systems:
                    psys_translator = self.rman_translators[psys.settings.type]
                    psys_db_name = object_utils.get_db_name(ob, psys=psys)
                    rman_psys_node = self.rman_particles.get(psys_db_name, None)
                    if not rman_psys_node:
                        continue
                    if not seg in rman_psys_node.motion_steps:
                        continue
                    if psys.settings.type == 'HAIR' and psys.settings.render_type == 'PATH':
                        # for now, we won't deal with deforming hair
                        continue
                    elif psys.settings.type == 'EMITTER' and psys.settings.render_type != 'OBJECT':
                        psys_translator.export_deform_sample(rman_psys_node, ob, psys, samp)                  

                if ob.name_full not in self.moving_objects:
                    continue

                rman_sg_node = self.rman_objects.get(db_name, None)
                if not rman_sg_node:
                    continue
                
                if not seg in rman_sg_node.motion_steps:
                    continue

                if rman_sg_node.is_transforming:
                    rman_sg_group = rman_sg_node.instances.get(group_db_name, None)
                    if rman_sg_group:
                        rman_group_translator = self.rman_translators['GROUP']
                        rman_group_translator.update_transform_num_samples(rman_sg_group, rman_sg_node.motion_steps ) # should have been set in _export_instances()                       
                        rman_group_translator.update_transform_sample( ob_inst, rman_sg_group, samp, seg)

                if rman_sg_node.is_deforming:
                    translator = self.rman_translators.get(rman_type, None)
                    if translator:
                        translator.export_deform_sample(rman_sg_node, ob, samp)                     

        self.rman_render.bl_engine.frame_set(origframe, subframe=0)  

    def check_solo_light(self):
        if self.bl_scene.renderman.solo_light:
            self.update_solo_light(self.context)
        else:
            self.update_un_solo_light(self.context)                

    def export_searchpaths(self):
        # TODO 
        # RMAN_ARCHIVEPATH,
        # RMAN_DISPLAYPATH, RMAN_PROCEDURALPATH, and RMAN_DSOPATH (combines procedurals and displays)
        
        # get cycles shader directory
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        cycles_shader_dir = os.path.join(cur_dir, '..', 'cycles', 'shader' )

        options = self.sg_scene.GetOptions()
        RMAN_SHADERPATH = os.environ.get('RMAN_SHADERPATH', '')
        options.SetString(self.rman.Tokens.Rix.k_searchpath_shader, '.:%s:%s:@' % (cycles_shader_dir, RMAN_SHADERPATH))
        RMAN_TEXTUREPATH = os.environ.get('RMAN_TEXTUREPATH', '')
        options.SetString(self.rman.Tokens.Rix.k_searchpath_texture, '.:%s:@' % RMAN_TEXTUREPATH)
        RMAN_RIXPLUGINPATH = os.environ.get('RMAN_RIXPLUGINPATH', '')
        options.SetString(self.rman.Tokens.Rix.k_searchpath_rixplugin, '.:%s:@' % RMAN_RIXPLUGINPATH)
        self.sg_scene.SetOptions(options)

    def export_hider(self):
        options = self.sg_scene.GetOptions()
        if self.rman_bake:
            options.SetString(self.rman.Tokens.Rix.k_hider_type, self.rman.Tokens.Rix.k_bake)
        else:
            rm = self.bl_scene.renderman
            pv = rm.pixel_variance

            options.SetInteger(self.rman.Tokens.Rix.k_hider_maxsamples, rm.max_samples)
            options.SetInteger(self.rman.Tokens.Rix.k_hider_minsamples, rm.min_samples)
            options.SetInteger(self.rman.Tokens.Rix.k_hider_incremental, rm.incremental)

            if self.is_interactive:
                options.SetInteger(self.rman.Tokens.Rix.k_hider_decidither, rm.hider_decidither)
                options.SetInteger(self.rman.Tokens.Rix.k_hider_maxsamples, rm.preview_max_samples)
                options.SetInteger(self.rman.Tokens.Rix.k_hider_minsamples, rm.preview_min_samples)
                options.SetInteger(self.rman.Tokens.Rix.k_hider_incremental, 1)
                pv = rm.preview_pixel_variance

            if (not self.external_render and rm.render_into == 'blender') or rm.enable_checkpoint:
                options.SetInteger(self.rman.Tokens.Rix.k_hider_incremental, 1)

            options.SetFloat(self.rman.Tokens.Rix.k_hider_darkfalloff, rm.dark_falloff)

            if not rm.sample_motion_blur:
                options.SetInteger(self.rman.Tokens.Rix.k_hider_samplemotion, 0)

            options.SetFloat(self.rman.Tokens.Rix.k_Ri_PixelVariance, pv)

            dspys_dict = display_utils.get_dspy_dict(self)
            anyDenoise = False
            for dspy,params in dspys_dict['displays'].items():
                if params['denoise']:
                    anyDenoise = True
            if anyDenoise:
                options.SetString(self.rman.Tokens.Rix.k_hider_pixelfiltermode, 'importance')

        self.sg_scene.SetOptions(options)  

    def export_global_options(self):
        rm = self.bl_scene.renderman
        options = self.sg_scene.GetOptions()

        # threads
        options.SetInteger(self.rman.Tokens.Rix.k_threads, rm.threads)

        # cache sizes
        options.SetInteger(self.rman.Tokens.Rix.k_limits_geocachememory, rm.geo_cache_size * 100)
        options.SetInteger(self.rman.Tokens.Rix.k_limits_opacitycachememory, rm.opacity_cache_size * 100)
        options.SetInteger(self.rman.Tokens.Rix.k_limits_texturememory, rm.texture_cache_size * 100)

        options.SetInteger(self.rman.Tokens.Rix.k_checkpoint_asfinal, int(rm.asfinal))

        options.SetInteger("user:osl:lazy_builtins", 1)
        options.SetInteger("user:osl:lazy_inputs", 1)
        
        # Set frame number 
        options.SetInteger(self.rman.Tokens.Rix.k_Ri_Frame, self.bl_scene.frame_current)

        # Stats
        if not self.is_interactive and rm.use_statistics:
            options.SetInteger(self.rman.Tokens.Rix.k_statistics_endofframe, 1)
            options.SetString(self.rman.Tokens.Rix.k_statistics_xmlfilename, 'stats.%04d.xml' % self.bl_scene.frame_current)

        # LPE Tokens for PxrSurface
        options.SetString("lpe:diffuse2", "Diffuse,HairDiffuse")
        options.SetString("lpe:diffuse3", "Subsurface")
        options.SetString("lpe:specular2", "Specular,HairSpecularR")
        options.SetString("lpe:specular3", "RoughSpecular,HairSpecularTRT")
        options.SetString("lpe:specular4", "Clearcoat")
        options.SetString("lpe:specular5", "Iridescence")
        options.SetString("lpe:specular6", "Fuzz,HairSpecularGLINTS")
        options.SetString("lpe:specular7", "SingltScatter,HairSpecularTT")
        options.SetString("lpe:specular8", "Glass")
        options.SetString("lpe:user2", "Albedo,DiffuseAlbedo,SubsurfaceAlbedo,HairAlbedo")

        # Set bucket shape
        bucket_order = rm.bucket_shape.lower()
        bucket_orderorigin = []
        if rm.enable_checkpoint and not self.is_interactive:
            bucket_order = 'horizontal'
            ri.Option("bucket", {"string order": ['horizontal']})

        elif rm.bucket_shape == 'SPIRAL':
            settings = self.bl_scene.render

            if rm.bucket_sprial_x <= settings.resolution_x and rm.bucket_sprial_y <= settings.resolution_y:
                if rm.bucket_sprial_x == -1:
                    halfX = settings.resolution_x / 2                    
                    bucket_orderorigin = [int(halfX), rm.bucket_sprial_y]

                elif rm.bucket_sprial_y == -1:
                    halfY = settings.resolution_y / 2
                    bucket_orderorigin = [rm.bucket_sprial_y, int(halfY)]
                else:
                    bucket_orderorigin = [rm.bucket_sprial_x, rm.bucket_sprial_y]

        options.SetString(self.rman.Tokens.Rix.k_bucket_order, bucket_order)
        if bucket_orderorigin:
            options.SetFloatArray(self.rman.Tokens.Rix.k_bucket_orderorigin, bucket_orderorigin, 2)

        # Shutter
        if rm.motion_blur:
            shutter_interval = rm.shutter_angle / 360.0
            shutter_open, shutter_close = 0, 1
            if rm.shutter_timing == 'CENTER':
                shutter_open, shutter_close = 0 - .5 * \
                    shutter_interval, 0 + .5 * shutter_interval
            elif rm.shutter_timing == 'PRE':
                shutter_open, shutter_close = 0 - shutter_interval, 0
            elif rm.shutter_timing == 'POST':
                shutter_open, shutter_close = 0, shutter_interval
            options.SetFloatArray(self.rman.Tokens.Rix.k_Ri_Shutter, (shutter_open, shutter_close), 2)        

        self.sg_scene.SetOptions(options)        

    def export_integrator(self):
        rm = self.bl_scene.renderman
        integrator = rm.integrator

        integrator_settings = getattr(rm, "%s_settings" % integrator)
        integrator_sg = self.rman.SGManager.RixSGShader("Integrator", integrator, "integrator")
        rman_sg_node = RmanSgNode(self, integrator_sg, "")
        property_utils.property_group_to_rixparams(integrator_settings, rman_sg_node, integrator_sg)         
        self.sg_scene.SetIntegrator(integrator_sg) 

    def export_cameras(self, bl_cameras):

        main_cam = self.depsgraph.scene_eval.camera
        cam_translator =  self.rman_translators['CAMERA']
       
        if self.is_viewport_render:
            db_name = 'main_camera'
            self.main_camera = cam_translator.export_viewport_cam(db_name)
            self.main_camera.sg_node.SetRenderable(1)
            self.sg_scene.Root().AddChild(self.main_camera.sg_node)

            # add camera so we don't mistake it for a new obj
            db_name = object_utils.get_db_name(main_cam)
            self.rman_cameras[db_name] = self.main_camera
            self.rman_objects[db_name] = self.main_camera  
            self.processed_obs[db_name] = self.main_camera          
        else:
            for cam in bl_cameras:
                db_name = object_utils.get_db_name(cam)
                rman_sg_camera = cam_translator.export(cam, db_name)
                if cam == main_cam:
                    self.main_camera = rman_sg_camera 
                    if self.main_camera.is_transforming:
                        self.motion_steps.update(self.main_camera.motion_steps)             
                self.rman_cameras[db_name] = rman_sg_camera
                self.rman_objects[db_name] = rman_sg_camera
                self.sg_scene.Root().AddChild(rman_sg_camera.sg_node)

        # For now, make the main camera the 'primary' dicing camera
        self.main_camera.sg_node.SetRenderable(1)
        

    def export_displayfilters(self):
        if not self.scene_any_lights:
            # if there are no lights, use the world color for the background
            if not self.world_df_node:
                self.world_df_node = self.rman.SGManager.RixSGShader("DisplayFilter", "PxrBackgroundDisplayFilter", "__rman_world_df")
            params = self.world_df_node.params
            params.SetColor("backgroundColor", self.bl_scene.world.color[:3])
            self.sg_scene.SetDisplayFilter([self.world_df_node])
            return
        elif self.world_df_node:
            self.world_df_node = None

        rm = self.bl_scene.renderman
        display_filter_names = []
        displayfilters_list = []

        for i, df in enumerate(rm.display_filters):
            df_name = df.name
            if df.name == "":
                df_name = "rman_displayfilter_filter%d" % i

            df_node = self.rman.SGManager.RixSGShader("DisplayFilter", df.get_filter_name(), df_name)
            rman_sg_node = RmanSgNode(self, df_node, "")
            property_utils.property_group_to_rixparams(df.get_filter_node(), rman_sg_node, df_node)
            display_filter_names.append(df_name)
            displayfilters_list.append(df_node)

        if len(display_filter_names) > 1:
            df_name = "rman_displayfilter_combiner"
            df_node = None
            if df_name in self.sg_nodes_dict:
                df_node = self.sg_nodes_dict[df_name]
            else:
                df_node = self.rman.SGManager.RixSGShader("DisplayFilter", "PxrDisplayFilterCombiner", df_name)
            params = df_node.params
            params.ReferenceDisplayFilterArray("filter", display_filter_names, len(display_filter_names))
            displayfilters_list.append(df_node)

        self.sg_scene.SetDisplayFilter(displayfilters_list)        

    def export_samplefilters(self):
        rm = self.bl_scene.renderman
        sample_filter_names = []        
        samplefilters_list = list()

        for i, sf in enumerate(rm.sample_filters):
            sf_name = sf.name
            if sf.name == "":
                sf_name = "rman_samplefilter_filter%d" % i

            sf_node = self.rman.SGManager.RixSGShader("SampleFilter", sf.get_filter_name(), sf_name)
            rman_sg_node = RmanSgNode(self, sf_node, "")
            property_utils.property_group_to_rixparams(sf.get_filter_node(), rman_sg_node, sf_node)
            sample_filter_names.append(sf_name)
            samplefilters_list.append(sf_node)

        if rm.do_holdout_matte != "OFF" and not self.is_viewport_render:
            sf_node = self.rman.SGManager.RixSGShader("SampleFilter", "PxrShadowFilter", "rm_PxrShadowFilter_shadows")
            params = sf_node.params
            params.SetString("occludedAov", "occluded")
            params.SetString("unoccludedAov", "holdoutMatte")
            if rm.do_holdout_matte == "ALPHA":
                params.SetString("shadowAov", "a")
            else:
                params.SetString("shadowAov", "holdoutMatte")

            sample_filter_names.append("rm_PxrShadowFilter_shadows")
            samplefilters_list.append(sf_node)     

        if len(sample_filter_names) > 1:
            sf_name = "rman_samplefilter_combiner"
            sf_node = self.rman.SGManager.RixSGShader("SampleFilter", "PxrSampleFilterCombiner", sf_name)
            params = sf_node.params
            params.ReferenceDisplayFilterArray("filter", display_filter_names, len(display_filter_names))

            samplefilters_list.append(sf_node)

        self.sg_scene.SetSampleFilter(samplefilters_list) 

    def export_viewport_display(self):
        rm = self.bl_scene.renderman
        sg_displays = []
        displaychannels = []
        display_driver = 'blender'

        dspy_chan_Ci = self.rman.SGManager.RixSGDisplayChannel('color', 'Ci')
        dspy_chan_a = self.rman.SGManager.RixSGDisplayChannel('float', 'a')

        self.sg_scene.SetDisplayChannel([dspy_chan_Ci, dspy_chan_a])
        display = self.rman.SGManager.RixSGShader("Display", display_driver, 'blender_viewport')
        display.params.SetString("mode", 'Ci,a')
        self.main_camera.sg_node.SetDisplay(display)

    def export_displays(self):
        rm = self.bl_scene.renderman
        sg_displays = []
        displaychannels = []
        display_driver = None
        cams_to_dspys = dict()

        dspys_dict = display_utils.get_dspy_dict(self)
        for chan_name, chan_params in dspys_dict['channels'].items():
            chan_type = chan_params['channelType']['value']
            chan_source = chan_params['channelSource']['value']
            chan_remap_a = chan_params['remap_a']['value']
            chan_remap_b = chan_params['remap_b']['value']
            chan_remap_c = chan_params['remap_c']['value']
            chan_exposure = chan_params['exposure']['value']
            chan_filter = chan_params['filter']['value']
            chan_filterwidth = chan_params['filterwidth']['value']
            chan_statistics = chan_params['statistics']['value']
            displaychannel = self.rman.SGManager.RixSGDisplayChannel(chan_type, chan_name)
            if chan_source:
                if "lpe" in chan_source:
                    displaychannel.params.SetString(self.rman.Tokens.Rix.k_source, '%s %s' % (chan_type, chan_source))                                
                else:
                    displaychannel.params.SetString(self.rman.Tokens.Rix.k_source, chan_source)

            displaychannel.params.SetFloatArray("exposure", chan_exposure, 2)
            displaychannel.params.SetFloatArray("remap", [chan_remap_a, chan_remap_b, chan_remap_c], 3)

            if chan_filter != 'default':
                displaychannel.params.SetString("filter", chan_filter)
                displaychannel.params.SetFloatArray("filterwidth", chan_filterwidth, 2 )

            if chan_statistics and chan_statistics != 'none':
                displaychannel.params.SetString("statistics", chan_statistics)                               
            displaychannels.append(displaychannel)

        for dspy,dspy_params in dspys_dict['displays'].items():
            display_driver = dspy_params['driverNode']
            dspy_file_name = dspy_params['filePath']
            display = self.rman.SGManager.RixSGShader("Display", display_driver, dspy_file_name)
            channels = ','.join(dspy_params['params']['displayChannels'])
            display.params.SetString("mode", channels)
            if display_driver == "it":
                dspy_info = display_utils.make_dspy_info(self.bl_scene)
                port = self.rman_render.it_port
                dspy_callback = "dspyRender"
                if self.is_interactive:
                    dspy_callback = "dspyIPR"
                display.params.SetString("dspyParams", 
                                        "%s -port %d -crop 1 0 1 0 -notes %s" % (dspy_callback, port, dspy_info))

            if display_driver == 'openexr':
                if rm.use_metadata:
                    display_utils.export_metadata(self.bl_scene, display.params)
                if not dspy_params['denoise']:
                    display.params.SetInteger("asrgba", 1)
                
            camera = dspy_params['camera']
            if camera is None:
                cam_dspys = cams_to_dspys.get(self.main_camera.db_name, list())
                cam_dspys.append(display)
                cams_to_dspys[self.main_camera.db_name] = cam_dspys
            else:
                db_name = object_utils.get_db_name(camera)
                if db_name not in self.rman_cameras:
                    cam_dspys = cams_to_dspys.get(self.main_camera.db_name, list())
                    cam_dspys.append(display)
                    cams_to_dspys[self.main_camera.db_name] = cam_dspys
                else:
                    cam_dspys = cams_to_dspys.get(db_name, list())
                    cam_dspys.append(display)
                    cams_to_dspys[db_name] = cam_dspys

        for db_name,cam_dspys in cams_to_dspys.items():
            cam = self.rman_cameras.get(db_name, None)
            if not cam:
                continue
            if cam != self.main_camera:
                cam.sg_node.SetRenderable(2)
            cam.sg_node.SetDisplay(cam_dspys)

        self.sg_scene.SetDisplayChannel(displaychannels)  

    def export_viewport_stats(self, integrator=''):
        rm = self.bl_scene.renderman
        if integrator == '':
            integrator = rm.integrator

        self.rman_render.bl_engine.update_stats('RenderMan (Stats)', 
                                                '\nIntegrator: %s\nMin Samples: %d\nMax Samples: %d\nInteractive Refinement: %d' % (integrator, rm.min_samples, rm.max_samples, rm.hider_decidither))

### UPDATE METHODS
#------------------------

    def update_view(self, context, depsgraph):
        camera = depsgraph.scene.camera
        rman_sg_camera = self.main_camera
        translator = self.rman_translators['CAMERA']
        with self.rman.SGManager.ScopedEdit(self.sg_scene):
            if self.is_viewport_render:
                translator.update_viewport_cam(rman_sg_camera)
                translator.update_viewport_transform(rman_sg_camera)
            else:
                translator.update_transform(camera, rman_sg_camera)  

    def _scene_updated(self):
        if self.bl_frame_current != self.bl_scene.frame_current:
            # frame changed, update any materials and lights that 
            # are marked as frame sensitive
            self.bl_frame_current = self.bl_scene.frame_current
            material_translator = self.rman_translators["MATERIAL"]
            light_translator = self.rman_translators["LIGHT"]

            with self.rman.SGManager.ScopedEdit(self.sg_scene):  
                for mat in bpy.data.materials:   
                    db_name = object_utils.get_db_name(mat)  
                    rman_sg_material = self.rman_materials.get(db_name, None)
                    if rman_sg_material and rman_sg_material.is_frame_sensitive:
                        material_translator.update(mat, rman_sg_material)

                for o in bpy.data.objects:
                    if o.type == 'LIGHT':                                
                        obj_key = object_utils.get_db_name(o, rman_type='LIGHT') 
                        rman_sg_node = self.rman_objects[obj_key]
                        if rman_sg_node.is_frame_sensitive:
                            light_translator.update(o, rman_sg_node)        

    def _material_updated(self, obj):
        mat = obj.id
        db_name = object_utils.get_db_name(mat)
        rman_sg_material = self.rman_materials.get(db_name, None)
        translator = self.rman_translators["MATERIAL"]
        with self.rman.SGManager.ScopedEdit(self.sg_scene):   
            mat = obj.id              
            if not rman_sg_material:
                rman_sg_material = translator.export(mat, db_name)
                self.rman_materials[db_name] = rman_sg_material
                # Not sure of a better method to do this.
                # There doesn't seem to be an API call to know what objects in the scene
                # have this specific material, so we loop thru all objs
                for ob_inst in self.depsgraph.object_instances:
                    if ob_inst.is_instance:
                        ob = ob_inst.instance_object
                        group_db_name =  object_utils.get_group_db_name(ob_inst) 
                    else:
                        ob = ob_inst.object
                        group_db_name =  object_utils.get_group_db_name(ob_inst) 
                    rman_type = object_utils._detect_primitive_(ob)
                    obj_db_name = object_utils.get_db_name(ob, rman_type=rman_type)
                    rman_sg_node = self.rman_objects.get(obj_db_name, None)
                    if rman_sg_node:
                        for m in object_utils._get_used_materials_(ob):
                            if m == mat:
                                rman_sg_node.instances[group_db_name].SetMaterial(rman_sg_material.sg_node)

            else:
                translator.update(mat, rman_sg_material)   

    def _object_transform_updated(self, obj):
        ob = obj.id         
        rman_type = object_utils._detect_primitive_(ob)
        obj_key = object_utils.get_db_name(ob, rman_type=rman_type) 
        rman_group_translator = self.rman_translators['GROUP']
        with self.rman.SGManager.ScopedEdit(self.sg_scene): 
            if obj.id.is_instancer:
                for ob_inst in self.depsgraph.object_instances:                                
                    if ob_inst.is_instance and ob_inst.parent == ob:     
                        group_db_name = object_utils.get_group_db_name(ob_inst)
                        rman_sg_group = self.rman_objects.get(group_db_name, None)
                        if rman_sg_group:
                            rman_group_translator.update_transform(ob_inst, rman_sg_group)
            else:
                if rman_type == "META":
                    rman_sg_node = self.rman_objects.get(obj_key, None)
                    self.rman_translators['META'].update(ob, rman_sg_node)
                elif rman_type == "CAMERA":
                    rman_sg_node = self.rman_objects.get(obj_key, None)
                    self.rman_translators['CAMERA'].update_transform(ob, rman_sg_node) 
                else:                       
                    rman_sg_node = self.rman_objects.get(obj_key, None) 
                    for k,rman_sg_group in rman_sg_node.instances.items():     
                        for ob_inst in self.depsgraph.object_instances: 
                            group_db_name = object_utils.get_group_db_name(ob_inst)
                            if group_db_name == k:
                                rman_group_translator.update_transform(ob_inst, rman_sg_group)
                                break

    def _obj_geometry_updated(self, obj):
        ob = obj.id
        rman_type = object_utils._detect_primitive_(ob)
        obj_key = object_utils.get_db_name(ob, rman_type=rman_type) 
        rman_sg_node = self.rman_objects[obj_key]
            
        with self.rman.SGManager.ScopedEdit(self.sg_scene):

            if rman_type == 'LIGHT':
                self.rman_translators['LIGHT'].update(ob, rman_sg_node)
                                                    
                if not self.scene_solo_light:
                    # only set if a solo light hasn't been set
                    rman_sg_node.sg_node.SetHidden(ob.data.renderman.mute)
            else:
                translator = self.rman_translators.get(rman_type, None)
                if not translator:
                    return
                translator.update(ob, rman_sg_node)
                group_db_name = object_utils.get_group_db_name(ob)

                for mat in object_utils._get_used_materials_(ob): 
                    if not mat:
                        continue
                    mat_db_name = object_utils.get_db_name(mat)
                    rman_sg_material = self.rman_materials.get(mat_db_name, None)
                    if rman_sg_material:
                        rman_sg_node.instances[group_db_name].sg_node.SetMaterial(rman_sg_material.sg_node)

                if rman_type in ['POLYGON_MESH', 'SUBDIVISION_MESH', 'POINTS']:
                    for psys in ob.particle_systems:
                        psys_translator = self.rman_translators[psys.settings.type]
                        if psys.settings.type == 'HAIR' and psys.settings.render_type == 'PATH':
                            hair_db_name = object_utils.get_db_name(ob, psys=psys)                                        
                            rman_sg_hair_node = self.rman_particles.get(hair_db_name, None)
                            if rman_sg_hair_node:
                                psys_translator.update(ob, psys, rman_sg_hair_node) 
                            else:
                                rman_sg_hair_node = psys_translator.export(ob, psys, hair_db_name)
                                rman_sg_node.sg_node.AddChild(rman_sg_hair_node.sg_node) 
                                self.rman_particles[hair_db_name] = rman_sg_hair_node
                        elif psys.settings.type == 'EMITTER' and psys.settings.render_type != 'OBJECT':
                            psys_db_name = object_utils.get_db_name(ob, psys=psys)
                            rman_sg_particles_node = self.rman_particles.get(psys_db_name, None)
                            if rman_sg_particles_node:
                                psys_translator.update(ob, psys, rman_sg_particles_node)
                            else:
                                rman_sg_particles_node = psys_translator.export(ob, psys, psys_db_name)
                                rman_sg_node.sg_node.AddChild(rman_sg_particles_node.sg_node)  
                                self.rman_particles[psys_db_name] = rman_sg_particles_node           

    def update_scene(self, context, depsgraph):
        new_objs = []
        new_cams = []
        self.depsgraph = depsgraph
        self.bl_scene = depsgraph.scene_eval
        do_delete = False
        delete_obs = []
        for obj in depsgraph.updates:
            ob = obj.id

            if isinstance(obj.id, bpy.types.Scene):
                self._scene_updated()
                # here, we check if an object got deleted
                # by looking at the selected objects
                selected_obs = context.selected_objects
                if selected_obs:
                    for o in selected_obs:
                        rman_type = object_utils._detect_primitive_(o)
                        obj_key = object_utils.get_db_name(o, rman_type=rman_type)  
                        self.current_ob.append(o.name_full)
                        self.current_ob_db_name.append(obj_key)
                else:
                    if self.current_ob:
                        for i,cur_ob in enumerate(self.current_ob):
                            if not self.depsgraph.objects.get(cur_ob):
                                delete_obs.append(self.current_ob_db_name[i])
                                do_delete = True
                    if not do_delete:
                        self.current_ob = []
                        self.current_ob_db_name = []

                continue

            elif isinstance(obj.id, bpy.types.World):
                if self.world_df_node:
                    with self.rman.SGManager.ScopedEdit(self.sg_scene): 
                        self.export_displayfilters()

            elif isinstance(obj.id, bpy.types.Camera):
                #cam = obj.object
                continue

            elif isinstance(obj.id, bpy.types.Material):
                self._material_updated(obj)

            elif isinstance(obj.id, bpy.types.Object):

                rman_type = object_utils._detect_primitive_(ob)
                obj_key = object_utils.get_db_name(ob, rman_type=rman_type)                                

                if obj_key == "":
                    continue

                if obj_key not in self.rman_objects:
                    if ob.type == 'CAMERA' and not self.is_viewport_render:
                        new_cams.append(obj.id)
                    else:
                        new_objs.append(obj.id)
                    continue
                                          
                if obj.is_updated_transform:
                    self._object_transform_updated(obj)

                elif obj.is_updated_geometry:
                    self._obj_geometry_updated(obj)


        # there are new objects
        if new_objs:
            with self.rman.SGManager.ScopedEdit(self.sg_scene): 
                rfb_log().debug("Adding new objects:")
                self.export_data_blocks(new_objs)
                self.export_instances()

                self.scene_any_lights = self._scene_has_lights()
                if self.world_df_node and self.scene_any_lights:
                    self.export_displayfilters()

        # new cameras
        if new_cams and not self.is_viewport_render:
            with self.rman.SGManager.ScopedEdit(self.sg_scene): 
                rfb_log().debug("Adding new cameras:")
                self.export_cameras(new_cams)         

        # delete any objects, if necessary    
        if do_delete:
            rfb_log().debug("Deleting objects")
            with self.rman.SGManager.ScopedEdit(self.sg_scene):
                for obj_key in delete_obs:
                    rman_sg_node = self.rman_objects.get(obj_key, None)
                    if not rman_sg_node:
                        return
                    for k,v in rman_sg_node.instances.items():
                        if v.sg_node:
                            self.sg_scene.DeleteDagNode(v.sg_node)
                        self.rman_objects.pop(k)
                    # For now, don't delete the geometry itself
                    # self.sg_scene.DeleteDagNode(rman_sg_node.sg_node)
                    self.rman_objects.pop(obj_key)    

                self.scene_any_lights = self._scene_has_lights()     
                if not self.scene_any_lights:
                    self.export_displayfilters()

            self.current_ob = []
            self.current_ob_db_name = []       
        
    def update_cropwindow(self, cropwindow=None):
        if cropwindow:
            with self.rman.SGManager.ScopedEdit(self.sg_scene): 
                options = self.sg_scene.GetOptions()
                options.SetFloatArray(self.rman.Tokens.Rix.k_Ri_CropWindow, cropwindow, 4)  
                self.sg_scene.SetOptions(options)           

    def update_integrator(self, context):
        self.bl_scene = context.scene
        with self.rman.SGManager.ScopedEdit(self.sg_scene):
            self.export_integrator() 
            self.export_viewport_stats()

    def update_hider_options(self, context):
        self.bl_scene = context.scene
        with self.rman.SGManager.ScopedEdit(self.sg_scene):
            self.export_hider()
            self.export_viewport_stats()

    def update_viewport_integrator(self, context):
        self.bl_scene = context.scene
        with self.rman.SGManager.ScopedEdit(self.sg_scene):
            rm = self.bl_scene.renderman_viewport
            integrator = rm.viewport_integrator
            integrator_sg = self.rman.SGManager.RixSGShader("Integrator", integrator, "integrator")
            rman_sg_node = RmanSgNode(self, integrator_sg, "")      
            self.sg_scene.SetIntegrator(integrator_sg) 

            rm = self.bl_scene.renderman
            self.export_viewport_stats(integrator=integrator)
 
    def update_material(self, mat):
        db_name = object_utils.get_db_name(mat)
        rman_sg_material = self.rman_materials.get(db_name, None)
        if not rman_sg_material:
            return
        translator = self.rman_translators["MATERIAL"]        
        with self.rman.SGManager.ScopedEdit(self.sg_scene):
            translator.update(mat, rman_sg_material)

    def update_light(self, ob):
        db_name = object_utils.get_db_name(ob)
        rman_sg_light = self.rman_objects.get(db_name, None)
        if not rman_sg_light:
            return
        translator = self.rman_translators["LIGHT"]        
        with self.rman.SGManager.ScopedEdit(self.sg_scene):
            translator.update(ob, rman_sg_light)            

    def update_object_prim_attrs(self, ob):
        rman_type = object_utils._detect_primitive_(ob)
        db_name = object_utils.get_db_name(ob, rman_type=rman_type)
        translator = self.rman_translators.get(rman_type, None)
        rman_sg_node = self.rman_objects.get(db_name, None)
        if translator and rman_sg_node:
            with self.rman.SGManager.ScopedEdit(self.sg_scene):
                translator.update(ob, rman_sg_node)

    def update_solo_light(self, context):
        # solo light has changed
        self.bl_scene = context.scene
        self.scene_solo_light = self.bl_scene.renderman.solo_light
                    
        with self.rman.SGManager.ScopedEdit(self.sg_scene):
            
            for light_ob in [x for x in self.bl_scene.objects if x.type == 'LIGHT']:
                db_name = object_utils.get_db_name(light_ob, rman_type='LIGHT')
                rman_sg_node = self.rman_objects.get(db_name, None)
                if not rman_sg_node:
                    continue
                if light_ob.data.renderman.solo:
                    rman_sg_node.sg_node.SetHidden(0)
                else:
                    rman_sg_node.sg_node.SetHidden(1)  


    def update_un_solo_light(self, context):
        # solo light has changed
        self.bl_scene = context.scene
        self.scene_solo_light = self.bl_scene.renderman.solo_light
                    
        with self.rman.SGManager.ScopedEdit(self.sg_scene):                                         
            for light_ob in [x for x in self.bl_scene.objects if x.type == 'LIGHT']:
                db_name = object_utils.get_db_name(light_ob, rman_type='LIGHT')
                rman_sg_node = self.rman_objects.get(db_name, None)
                if not rman_sg_node:
                    continue
                rman_sg_node.sg_node.SetHidden(light_ob.data.renderman.mute)
