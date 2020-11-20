# Translators
from .rman_translators.rman_camera_translator import RmanCameraTranslator
from .rman_translators.rman_light_translator import RmanLightTranslator
from .rman_translators.rman_lightfilter_translator import RmanLightFilterTranslator
from .rman_translators.rman_mesh_translator import RmanMeshTranslator
from .rman_translators.rman_material_translator import RmanMaterialTranslator
from .rman_translators.rman_hair_translator import RmanHairTranslator
from .rman_translators.rman_group_translator import RmanGroupTranslator
from .rman_translators.rman_points_translator import RmanPointsTranslator
from .rman_translators.rman_quadric_translator import RmanQuadricTranslator
from .rman_translators.rman_blobby_translator import RmanBlobbyTranslator
from .rman_translators.rman_particles_translator import RmanParticlesTranslator
from .rman_translators.rman_procedural_translator import RmanProceduralTranslator
from .rman_translators.rman_dra_translator import RmanDraTranslator
from .rman_translators.rman_runprogram_translator import RmanRunProgramTranslator
from .rman_translators.rman_openvdb_translator import RmanOpenVDBTranslator
from .rman_translators.rman_gpencil_translator import RmanGPencilTranslator
from .rman_translators.rman_fluid_translator import RmanFluidTranslator
from .rman_translators.rman_curve_translator import RmanCurveTranslator
from .rman_translators.rman_nurbs_translator import RmanNurbsTranslator
from .rman_translators.rman_volume_translator import RmanVolumeTranslator
from .rman_translators.rman_brickmap_translator import RmanBrickmapTranslator
from .rman_translators.rman_emitter_translator import RmanEmitterTranslator

# utils
from .rfb_utils import object_utils
from .rfb_utils import transform_utils
from .rfb_utils import property_utils
from .rfb_utils import display_utils
from .rfb_utils import string_utils
from .rfb_utils import texture_utils
from .rfb_utils import filepath_utils
from .rfb_utils import scene_utils
from .rfb_utils.prefs_utils import get_pref
from .rfb_utils import shadergraph_utils
from .rfb_utils import color_manager_blender

# config
from .rman_config import __RFB_CONFIG_DICT__ as rfb_config
from . import rman_constants

from .rfb_logger import rfb_log
from .rman_sg_nodes.rman_sg_node import RmanSgNode

import bpy
import os
import sys

class RmanScene(object):
    '''
    The RmanScene handles translating the Blender scene. 
    
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
        self.is_swatch_render = False
        self.scene_solo_light = False
        self.scene_any_lights = False
        self.is_xpu = False

        self.rman_materials = dict()
        self.rman_objects = dict()
        self.rman_translators = dict()
        self.rman_particles = dict()
        self.rman_cameras = dict()
        self.obj_hash = dict() 
        self.moving_objects = dict()
        #self.processed_obs = dict()
        self.processed_obs = []

        self.motion_steps = set()
        self.main_camera = None
        self.rman_root_sg_node = None

        self.render_default_light = False
        self.world_df_node = None
        self.default_light = None

        self.viewport_render_res_mult = 1.0

        self.create_translators()     


    def create_translators(self):

        self.rman_translators['CAMERA'] = RmanCameraTranslator(rman_scene=self)
        self.rman_translators['LIGHT'] = RmanLightTranslator(rman_scene=self)
        self.rman_translators['LIGHTFILTER'] = RmanLightFilterTranslator(rman_scene=self)
        self.rman_translators['MATERIAL'] = RmanMaterialTranslator(rman_scene=self)       
        self.rman_translators['HAIR'] = RmanHairTranslator(rman_scene=self) 
        self.rman_translators['GROUP'] = RmanGroupTranslator(rman_scene=self)
        self.rman_translators['POINTS'] = RmanPointsTranslator(rman_scene=self)
        self.rman_translators['META'] = RmanBlobbyTranslator(rman_scene=self)
        self.rman_translators['PARTICLES'] = RmanParticlesTranslator(rman_scene=self)
        self.rman_translators['EMITTER'] = RmanEmitterTranslator(rman_scene=self)
        self.rman_translators['DYNAMIC_LOAD_DSO'] = RmanProceduralTranslator(rman_scene=self)
        self.rman_translators['DELAYED_LOAD_ARCHIVE'] = RmanDraTranslator(rman_scene=self)
        self.rman_translators['PROCEDURAL_RUN_PROGRAM'] = RmanRunProgramTranslator(rman_scene=self)
        self.rman_translators['OPENVDB'] = RmanOpenVDBTranslator(rman_scene=self)
        self.rman_translators['GPENCIL'] = RmanGPencilTranslator(rman_scene=self)
        self.rman_translators['MESH'] = RmanMeshTranslator(rman_scene=self)
        self.rman_translators['QUADRIC'] = RmanQuadricTranslator(rman_scene=self)
        self.rman_translators['FLUID'] = RmanFluidTranslator(rman_scene=self)
        self.rman_translators['CURVE'] = RmanCurveTranslator(rman_scene=self)
        self.rman_translators['NURBS'] = RmanNurbsTranslator(rman_scene=self)
        self.rman_translators['RI_VOLUME'] = RmanVolumeTranslator(rman_scene=self)
        self.rman_translators['BRICKMAP'] = RmanBrickmapTranslator(rman_scene=self)

    def _find_renderman_layer(self):
        self.rm_rl = None
        rm = self.bl_scene.renderman
            
        for l in rm.render_layers:
            if l.render_layer == self.bl_view_layer.name:
                self.rm_rl = l
                break     

    def _update_progress(self, msg, f):
        if self.rman_render.bl_engine:
            try:
                progress = int(f*100)
                self.rman_render.bl_engine.update_stats(msg, "%d%%" % progress)
                #self.rman_render.bl_engine.update_progress(f)
            except:
                rfb_log().debug("Cannot update progress")

    def reset(self):
        # clear out dictionaries etc.
        self.rman_materials.clear()
        self.rman_objects.clear()
        self.rman_particles.clear()
        self.rman_cameras.clear()        
        self.obj_hash.clear() 
        self.motion_steps = set()       
        self.moving_objects.clear()
        
        self.processed_obs.clear()
  
        self.render_default_light = False
        self.world_df_node = None
        self.default_light = None        
        self.viewport_render_res_mult = 1.0  
        self.is_xpu = False  

    def export_for_final_render(self, depsgraph, sg_scene, bl_view_layer, is_external=False):
        self.sg_scene = sg_scene
        self.context = bpy.context
        self.bl_scene = depsgraph.scene_eval
        self.bl_view_layer = bl_view_layer
        self._find_renderman_layer()
        self.depsgraph = depsgraph
        self.external_render = is_external
        self.is_interactive = False
        self.is_viewport_render = False
        self.do_motion_blur = self.bl_scene.renderman.motion_blur
        self.export()

    def export_for_bake_render(self, depsgraph, sg_scene, bl_view_layer, is_external=False):
        self.sg_scene = sg_scene
        self.context = bpy.context
        self.bl_scene = depsgraph.scene_eval
        self.bl_view_layer = bl_view_layer
        self._find_renderman_layer()
        self.depsgraph = depsgraph
        self.external_render = is_external
        self.is_interactive = False
        self.is_viewport_render = False
        self.do_motion_blur = self.bl_scene.renderman.motion_blur
        self.rman_bake = True

        if self.bl_scene.renderman.hider_type == 'BAKE_BRICKMAP_SELECTED':
            self.export_bake_brickmap_selected()
        else:
            self.export_bake_render_scene()

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
        self.rman_bake = False
        
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
        self.rman_bake = False        
        
        self.depsgraph = context.evaluated_depsgraph_get()
        self.export_root_sg_node()
        ob = context.active_object
        self.export_materials([m for m in self.depsgraph.ids if isinstance(m, bpy.types.Material)])
        self.export_data_blocks([ob])
        self.export_instances(obj_selected=ob)

    def export_for_swatch_render(self, depsgraph, sg_scene):
        self.sg_scene = sg_scene
        self.context = bpy.context #None
        self.bl_scene = depsgraph.scene_eval
        self.depsgraph = depsgraph
        self.external_render = False
        self.is_interactive = False
        self.is_viewport_render = False
        self.do_motion_blur = False
        self.rman_bake = False
        self.is_swatch_render = True
        self.export_swatch_render_scene()

    def export(self):

        self.reset()

        self.render_default_light = self.bl_scene.renderman.render_default_light
        self.is_xpu = (self.bl_scene.renderman.renderVariant != 'prman')

        # update variables
        string_utils.set_var('scene', self.bl_scene.name)
        string_utils.set_var('layer', self.bl_view_layer.name)

        self.bl_frame_current = self.bl_scene.frame_current

        rfb_log().debug("Creating root scene graph node")
        self.export_root_sg_node()        

        rfb_log().debug("Calling export_materials()")
        #self.export_materials(bpy.data.materials)
        self.export_materials([m for m in self.depsgraph.ids if isinstance(m, bpy.types.Material)])  
                
        rfb_log().debug("Calling txmake_all()")
        texture_utils.get_txmanager().rman_scene = self  
        texture_utils.get_txmanager().txmake_all(blocking=True)

        self.scene_any_lights = self._scene_has_lights()
        
        rfb_log().debug("Calling export_data_blocks()")
        self.export_data_blocks(bpy.data.objects)
        #self.export_data_blocks([x for x in self.depsgraph.ids if isinstance(x, bpy.types.Object)])

        self.export_searchpaths() 
        self.export_global_options()     
        self.export_hider()
        self.export_integrator()

        self.export_cameras([c for c in self.depsgraph.objects if isinstance(c.data, bpy.types.Camera)])

        # export default light
        self.export_defaultlight()
        self.main_camera.sg_node.AddChild(self.default_light)
        
        self.export_displays()
        self.export_samplefilters()
        self.export_displayfilters()

        if self.do_motion_blur:
            rfb_log().debug("Calling export_instances_motion()")
            self.export_instances_motion()
        else:
            rfb_log().debug("Calling export_instances()")
            self.export_instances()

        self._update_progress("Finished Export", 1.0)            

        if self.is_interactive:
            self.check_solo_light()

            if self.is_viewport_render:
                self.export_viewport_stats()

    def export_bake_render_scene(self):
        self.reset()

        # update variables
        string_utils.set_var('scene', self.bl_scene.name)
        string_utils.set_var('layer', self.bl_view_layer.name)

        self.bl_frame_current = self.bl_scene.frame_current
        rfb_log().debug("Creating root scene graph node")
        self.export_root_sg_node()

        rfb_log().debug("Calling export_materials()")
        self.export_materials([m for m in self.depsgraph.ids if isinstance(m, bpy.types.Material)]) 
                
        rfb_log().debug("Calling txmake_all()")
        texture_utils.get_txmanager().rman_scene = self  
        texture_utils.get_txmanager().txmake_all(blocking=True)

        self.scene_any_lights = self._scene_has_lights()
        
        rm = self.bl_scene.renderman
        rman_root_sg_node = self.get_root_sg_node()
        attrs = rman_root_sg_node.GetAttributes()
        attrs.SetFloat("dice:worlddistancelength", rm.rman_bake_illlum_density)
        rman_root_sg_node.SetAttributes(attrs)                       

        rfb_log().debug("Calling export_data_blocks()")
        self.export_data_blocks(bpy.data.objects)

        self.export_searchpaths() 
        self.export_global_options()     
        self.export_hider()
        self.export_integrator()
        self.export_cameras([c for c in self.depsgraph.objects if isinstance(c.data, bpy.types.Camera)])

        self.export_bake_displays()
        self.export_samplefilters()
        self.export_displayfilters()

        if self.do_motion_blur:
            rfb_log().debug("Calling export_instances_motion()")
            self.export_instances_motion()
        else:
            rfb_log().debug("Calling export_instances()")
            self.export_instances()  

        options = self.sg_scene.GetOptions()
        bake_resolution = int(rm.rman_bake_illlum_res)
        options.SetIntegerArray(self.rman.Tokens.Rix.k_Ri_FormatResolution, (bake_resolution, bake_resolution), 2) 
        self.sg_scene.SetOptions(options)

    def export_bake_brickmap_selected(self):
        self.reset()

        # update variables
        string_utils.set_var('scene', self.bl_scene.name)
        string_utils.set_var('layer', self.bl_view_layer.name)

        self.bl_frame_current = self.bl_scene.frame_current
        rfb_log().debug("Creating root scene graph node")
        self.export_root_sg_node()

        rfb_log().debug("Calling export_materials()")
        self.export_materials([m for m in self.depsgraph.ids if isinstance(m, bpy.types.Material)])
        rfb_log().debug("Calling txmake_all()")
        texture_utils.get_txmanager().rman_scene = self  
        texture_utils.get_txmanager().txmake_all(blocking=True)        

        self.scene_any_lights = self._scene_has_lights()        
                        
        rm = self.bl_scene.renderman
        rman_root_sg_node = self.get_root_sg_node()
        attrs = rman_root_sg_node.GetAttributes()
        attrs.SetFloat("dice:worlddistancelength", rm.rman_bake_illlum_density)
        rman_root_sg_node.SetAttributes(attrs)                            

        self.export_searchpaths() 
        self.export_global_options()     
        self.export_hider()
        self.export_integrator()
        self.export_cameras([c for c in self.depsgraph.objects if isinstance(c.data, bpy.types.Camera)])

        ob = self.context.active_object
        self.export_materials([m for m in self.depsgraph.ids if isinstance(m, bpy.types.Material)])
        objects_needed = [x for x in self.bl_scene.objects if object_utils._detect_primitive_(x) == 'LIGHT']
        objects_needed.append(ob)
        self.export_data_blocks(objects_needed)
        self.export_instances()        

        self.export_samplefilters()
        self.export_displayfilters()

        options = self.sg_scene.GetOptions()
        bake_resolution = int(rm.rman_bake_illlum_res)
        options.SetIntegerArray(self.rman.Tokens.Rix.k_Ri_FormatResolution, (bake_resolution, bake_resolution), 2) 
        self.sg_scene.SetOptions(options)        

        # Display
        display_driver = 'pointcloud'
        dspy_chan_Ci = self.rman.SGManager.RixSGDisplayChannel('color', 'Ci')

        self.sg_scene.SetDisplayChannel([dspy_chan_Ci])
        render_output = '%s.ptc' % ob.renderman.bake_filename_attr
        render_output = string_utils.expand_string(render_output)
        display = self.rman.SGManager.RixSGShader("Display", display_driver, render_output)
        display.params.SetString("mode", 'Ci')
        self.main_camera.sg_node.SetDisplay(display)         
                 
    def export_swatch_render_scene(self):
        self.reset()

        # options
        options = self.sg_scene.GetOptions()
        options.SetInteger(self.rman.Tokens.Rix.k_hider_minsamples, get_pref('rman_preview_renders_minSamples', default=0))
        options.SetInteger(self.rman.Tokens.Rix.k_hider_maxsamples, get_pref('rman_preview_renders_minSamples', default=1))
        options.SetInteger(self.rman.Tokens.Rix.k_hider_incremental, 1)
        options.SetString("adaptivemetric", "variance")
        scale = 100.0 / self.bl_scene.render.resolution_percentage
        w = int(self.bl_scene.render.resolution_x * scale)
        h = int(self.bl_scene.render.resolution_y * scale)
        options.SetIntegerArray(self.rman.Tokens.Rix.k_Ri_FormatResolution, (w, h), 2)
        options.SetFloat(self.rman.Tokens.Rix.k_Ri_PixelVariance, get_pref('rman_preview_renders_pixelVariance', default=0.15))
        options.SetInteger(self.rman.Tokens.Rix.k_threads, -2)
        options.SetString(self.rman.Tokens.Rix.k_bucket_order, 'horizontal')
        self.sg_scene.SetOptions(options)

        # searchpaths
        self.export_searchpaths()      

        # integrator        
        integrator_sg = self.rman.SGManager.RixSGShader("Integrator", "PxrDirectLighting", "integrator")         
        self.sg_scene.SetIntegrator(integrator_sg) 

        # camera
        self.export_cameras([c for c in self.depsgraph.objects if isinstance(c.data, bpy.types.Camera)])

        # Display
        display_driver = 'blender'
        dspy_chan_Ci = self.rman.SGManager.RixSGDisplayChannel('color', 'Ci')
        dspy_chan_a = self.rman.SGManager.RixSGDisplayChannel('float', 'a')

        self.sg_scene.SetDisplayChannel([dspy_chan_Ci, dspy_chan_a])
        display = self.rman.SGManager.RixSGShader("Display", display_driver, 'blender_preview')
        display.params.SetString("mode", 'Ci,a')
        self.main_camera.sg_node.SetDisplay(display)          

        rfb_log().debug("Calling materials()")
        self.export_materials([m for m in self.depsgraph.ids if isinstance(m, bpy.types.Material)])
        rfb_log().debug("Calling export_data_blocks()")
        
        self.export_data_blocks([m for m in self.depsgraph.ids if isinstance(m, bpy.types.Object)])
        self.export_instances()

    def export_root_sg_node(self):
        
        rm = self.bl_scene.renderman
        root_sg = self.get_root_sg_node()
        attrs = root_sg.GetAttributes()

        # set any properties marked riattr in the config file
        for prop_name, meta in rm.prop_meta.items():
            if 'riattr' not in meta:
                continue
            
            val = getattr(rm, prop_name)
            ri_name = meta['riattr']
            is_array = False
            array_len = -1
            if 'arraySize' in meta:
                is_array = True
                array_len = meta['arraySize']
            param_type = meta['renderman_type']         
            property_utils.set_rix_param(attrs, param_type, ri_name, val, is_reference=False, is_array=is_array, array_len=array_len, node=rm)
                           
        root_sg.SetAttributes(attrs)
        
    def get_root_sg_node(self):
        return self.sg_scene.Root()

    def export_materials(self, materials):
        for mat in materials:   
            db_name = object_utils.get_db_name(mat)
            rman_sg_material = self.rman_translators['MATERIAL'].export(mat, db_name)
            if rman_sg_material:                       
                self.rman_materials[mat.original] = rman_sg_material
            
    def export_data_blocks(self, data_blocks):
        total = len(data_blocks)
        for i, obj in enumerate(data_blocks):
            if obj.type not in ('ARMATURE', 'CAMERA'):
                ob = obj.evaluated_get(self.depsgraph)           
                self.export_data_block(ob) 
            rfb_log().debug("   Exported %d/%d data blocks..." % (i, total))
            self._update_progress("Exporting data blocks",i/total)

    def export_data_block(self, db_ob):

        # FIXME? 
        # We currently export a unique geometry/mesh per Object
        # This means we're not actually sharing datablocks per Object, even if they are shared
        # in Blender. We do this for a couple of reasons:
        # 
        # 1. Each object can have different modifiers applied. This includes applying a subdiv and/or bevel modifiers.
        # 2. Each object may want a different number of deformation motion samples
        #
        # This is incredibly wasteful when these don't apply. We could try and detect this case and
        # create a shareable geometry.

        obj = bpy.data.objects.get(db_ob.name, None)
        if not obj and self.is_swatch_render:
            obj = db_ob

        if obj and obj.type not in ('ARMATURE', 'CAMERA'):
            ob = obj.evaluated_get(self.depsgraph)            
            rman_type = object_utils._detect_primitive_(ob)  
            db_name = object_utils.get_db_name(ob, rman_type=rman_type)
            if rman_type == 'LIGHT':
                if ob.data.renderman.renderman_light_role == 'RMAN_LIGHTFILTER':
                    # skip if this is a light filter
                    # these will be exported when we do regular lights
                    return
                elif ob.data.renderman.get_light_node_name() == 'PxrDomeLight':
                    # check if there are portals attached to this light
                    # if there are, skip
                    any_portals = False
                    for c in obj.children:
                        if c.type == 'LIGHT' and c.data.renderman.get_light_node_name() == 'PxrPortalLight':
                            any_portals = True
                            break
                    if any_portals:
                        return  

            translator =  self.rman_translators.get(rman_type, None)
            if not translator:
                return

            rman_sg_node = None
            if ob.original in self.rman_objects:
                return

            rman_sg_node = translator.export(ob, db_name)
            if not rman_sg_node:
                return
            rman_sg_node.rman_type = rman_type
            self.rman_objects[ob.original] = rman_sg_node

            if rman_type in ['MESH', 'POINTS']:
                # Deal with any particles now. Particles are children to mesh nodes.
                subframes = []
                if self.do_motion_blur:
                    subframes = scene_utils._get_subframes_(2, self.bl_scene)
                    self.motion_steps.update(subframes)

                if len(ob.particle_systems) > 0:
                    particles_group_db = ''
                    rman_sg_node.rman_sg_particle_group_node = self.rman_translators['GROUP'].export(None, particles_group_db) 
                    rman_sg_node.sg_node.AddChild(rman_sg_node.rman_sg_particle_group_node.sg_node)                   

                psys_translator = self.rman_translators['PARTICLES']
                for psys in ob.particle_systems:           
                    psys_db_name = '%s' % psys.name
                    rman_sg_particles = psys_translator.export(ob, psys, psys_db_name)    
                    if not rman_sg_particles:
                        continue  
                
                    psys_translator.set_motion_steps(rman_sg_particles, subframes)
                    psys_translator.update(ob, psys, rman_sg_particles)      

                    ob_psys = self.rman_particles.get(ob.original, dict())
                    ob_psys[psys.settings.original] = rman_sg_particles
                    self.rman_particles[ob.original] = ob_psys                       
                    rman_sg_node.rman_sg_particle_group_node.sg_node.AddChild(rman_sg_particles.sg_node)

            # motion blur
            # we set motion steps for this object, even if it's not moving
            # it could be moving as part of a particle system
            mb_segs = self.bl_scene.renderman.motion_segments
            if mb_segs > 1:
                subframes = scene_utils._get_subframes_(mb_segs, self.bl_scene)
                rman_sg_node.motion_steps = subframes
                self.motion_steps.update(subframes)

            if rman_sg_node.is_transforming or rman_sg_node.is_deforming:
                if mb_segs > 1:
                    self.moving_objects[ob.name_full] = ob
                else:
                    rman_sg_node.is_transforming = False
                    rman_sg_node.is_deforming = False

    def export_defaultlight(self):
        if not self.default_light:
            self.default_light = self.sg_scene.CreateAnalyticLight('__defaultlight')
            sg_node = self.rman.SGManager.RixSGShader("Light", 'PxrDistantLight' , "light")
            self.default_light.SetLight(sg_node)
            s_orientPxrLight = [-1.0, 0.0, -0.0, 0.0,
                    -0.0, -1.0, -0.0, 0.0,
                    0.0, 0.0, -1.0, 0.0,
                    0.0, 0.0, 0.0, 1.0]
            self.default_light.SetOrientTransform(s_orientPxrLight)  

        if self.render_default_light and not self.scene_any_lights:
            self.default_light.SetHidden(0)
        else:
            self.default_light.SetHidden(1)

    def _scene_has_lights(self):
        num_lights = len(scene_utils.get_all_lights(self.bl_scene, include_light_filters=False))
        return num_lights > 0       

    def _export_instance(self, ob_inst, seg=None):
   
        group_db_name = object_utils.get_group_db_name(ob_inst) 
        rman_group_translator = self.rman_translators['GROUP']
        parent_sg_node = None
        rman_sg_particles = None
        psys = None
        if ob_inst.is_instance:
            parent = ob_inst.parent
            ob = ob_inst.instance_object
            psys = ob_inst.particle_system
            if psys:
                #particles_db_name = object_utils.get_db_name(parent, psys=psys)
                #rman_sg_particles = self.rman_particles.get(psys.settings.original, None)
                pass
            else:                
                #if parent.type == "EMPTY" and parent.is_instancer:
                if parent.is_instancer:
                    parent_db_name = object_utils.get_db_name(parent)
                    parent_sg_node = self.rman_objects.get(parent.original, None)
                    if not parent_sg_node:
                        parent_sg_node = rman_group_translator.export(parent, parent_db_name)
                        self.rman_objects[parent.original] = parent_sg_node

        else:
            ob = ob_inst.object 
         
        if ob.type in ('ARMATURE', 'CAMERA'):
            return                         

        rman_type = object_utils._detect_primitive_(ob)
        if rman_type == 'LIGHTFILTER':
            # light filters are part of lights, so when light instances
            # are exported, light filterrs should go along with them
            return

        elif ob.type == "EMPTY" and ob.is_instancer:    
            rman_sg_node = self.rman_objects.get(ob.original, None)
            if not rman_sg_node:
                empty_db_name = object_utils.get_db_name(ob)
                rman_sg_node = rman_group_translator.export(ob, empty_db_name)
                self.rman_objects[ob.original] = rman_sg_node
        else:

            if rman_type == "META":
                # only add the meta instance that matches the family name
                if ob.name_full != object_utils.get_meta_family(ob):
                    return
        
            rman_sg_node = self.rman_objects.get(ob.original, None)           
            if not rman_sg_node:
                return

            translator = self.rman_translators.get(rman_type, None)
            if not translator:
                return

            if group_db_name in rman_sg_node.instances:
                # we've already added this instance
                return
            else:

                if not ob.original in self.processed_obs:
                    translator.update(ob, rman_sg_node)
                    translator.export_object_primvars(ob, rman_sg_node)
                    self.processed_obs.append(ob.original)

                rman_sg_group = rman_group_translator.export(ob, group_db_name)
                if ob.is_instancer and ob.instance_type != 'NONE':
                    rman_sg_group.is_instancer = ob.is_instancer
                if rman_sg_node.sg_node is None:
                    # add the group to the root anyways
                    db_name = object_utils.get_db_name(ob, rman_type=rman_type)
                    rman_sg_group.db_name = db_name
                    self.get_root_sg_node().AddChild(rman_sg_group.sg_node)
                    self.rman_objects[ob.original] = rman_sg_group
                    return

                rman_sg_group.sg_node.AddChild(rman_sg_node.sg_node)
                rman_sg_group.rman_sg_node_instance = rman_sg_node

                self.get_root_sg_node().AddChild(rman_sg_group.sg_node)

                # add this instance to rman_sg_node
                rman_sg_node.instances[group_db_name] = rman_sg_group                     

            # object attrs             
            translator.export_object_id(ob, rman_sg_group, ob_inst)
            translator.export_object_attributes(ob, rman_sg_group)  

            # attach material
            if psys:
                self.attach_particle_material(psys, ob, rman_sg_group)
            else:
                self.attach_material(ob, rman_sg_group)                
            
            if rman_type != "META":
                # meta/blobbies are already in world space. Their instances don't need to
                # set a transform.
                if rman_sg_node.is_transforming:
                    rman_group_translator.update_transform_num_samples(rman_sg_group, rman_sg_node.motion_steps )
                    rman_group_translator.update_transform_sample(ob_inst, rman_sg_group, 0, seg )
                elif psys and self.do_motion_blur:
                    rman_group_translator.update_transform_num_samples(rman_sg_group, rman_sg_node.motion_steps )
                    rman_group_translator.update_transform_sample(ob_inst, rman_sg_group, 0, seg )                    
                else:
                    rman_group_translator.update_transform(ob_inst, rman_sg_group)

    def export_instances(self, obj_selected=None):
        objFound = False
        total = len(self.depsgraph.object_instances)
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

            if not ob_inst.show_self:
                continue

            self._export_instance(ob_inst)  
            self._update_progress("Exporting instances", i/total)
            rfb_log().debug("   Exported %d/%d instances..." % (i, total))

    def attach_material(self, ob, rman_sg_node):
        mat = object_utils.get_active_material(ob)
        if mat:
            rman_sg_material = self.rman_materials.get(mat.original, None)
            if rman_sg_material and rman_sg_material.sg_node:
                rman_sg_node.sg_node.SetMaterial(rman_sg_material.sg_node) 
                rman_sg_node.is_meshlight = rman_sg_material.has_meshlight 

        '''
        for mat in object_utils._get_used_materials_(ob): 
            if not mat:
                continue
            mat_db_name = object_utils.get_db_name(mat)
            rman_sg_material = self.rman_materials.get(mat.original, None)
            if rman_sg_material and rman_sg_material.sg_node:
                rman_sg_node.sg_node.SetMaterial(rman_sg_material.sg_node) 
                rman_sg_node.sg_node.is_meshlight = rman_sg_material.has_meshlight       
        '''

    def attach_particle_material(self, psys, ob, group):
        if ob.renderman.rman_material_override:
            mat = ob.renderman.rman_material_override
            rman_sg_material = self.rman_materials.get(mat.original, None)
            if rman_sg_material and rman_sg_material.sg_node:
                group.sg_node.SetMaterial(rman_sg_material.sg_node) 
                group.is_meshlight = rman_sg_material.has_meshlight     
            return

        mat_idx = psys.settings.material - 1
        if mat_idx < len(ob.material_slots):
            mat = ob.material_slots[mat_idx].material
            mat_db_name = object_utils.get_db_name(mat)
            rman_sg_material = self.rman_materials.get(mat.original, None)
            if rman_sg_material:
                group.sg_node.SetMaterial(rman_sg_material.sg_node)                    

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

                if not ob_inst.show_self:
                    continue                    

                if first_sample:
                    # for the first motion sample use _export_instance()
                    self._export_instance(ob_inst, seg=seg)  
                    self._update_progress("Exporting instances (%f)" % seg, i/total)
                    continue  

                rman_group_translator = self.rman_translators['GROUP']
                psys = None
                if ob_inst.is_instance:
                    ob = ob_inst.instance_object.original  
                    psys = ob_inst.particle_system
                else:
                    ob = ob_inst.object

                if ob.name_full not in self.moving_objects and not psys:
                    continue

                if ob.type not in ['MESH']:
                    continue                

                group_db_name = object_utils.get_group_db_name(ob_inst)          

                rman_sg_node = self.rman_objects.get(ob.original, None)
                if not rman_sg_node:
                    continue
                
                if not seg in rman_sg_node.motion_steps:
                    continue

                if rman_sg_node.is_transforming or psys:
                    rman_sg_group = rman_sg_node.instances.get(group_db_name, None)
                    if rman_sg_group:
                        rman_group_translator.update_transform_num_samples(rman_sg_group, rman_sg_node.motion_steps ) # should have been set in _export_instances()                       
                        rman_group_translator.update_transform_sample( ob_inst, rman_sg_group, samp, seg)

                self._update_progress("Exporting instances (%f)" % seg, i/total)

            for ob_original,rman_sg_node in self.rman_objects.items():
                ob = ob_original.evaluated_get(self.depsgraph)
                psys_translator = self.rman_translators['PARTICLES']
                for psys in ob.particle_systems:
                    ob_psys = self.rman_particles.get(ob.original, dict())
                    rman_sg_particles = ob_psys.get(psys.settings.original, None)
                    if rman_sg_particles:
                        if not seg in rman_sg_particles.motion_steps:
                            continue
                        psys_translator.export_deform_sample(rman_sg_particles, ob, psys, samp)                                    

                if rman_sg_node.is_deforming:
                    rman_type = rman_sg_node.rman_type
                    if rman_type == 'MESH':
                        translator = self.rman_translators.get(rman_type, None)
                        if translator:
                            translator.export_deform_sample(rman_sg_node, ob, samp)                     

        self.rman_render.bl_engine.frame_set(origframe, subframe=0)  

    def check_solo_light(self):           
        if self.bl_scene.renderman.solo_light:   
            for light_ob in scene_utils.get_all_lights(self.bl_scene, include_light_filters=False):
                rman_sg_node = self.rman_objects.get(light_ob.original, None)
                if not rman_sg_node:
                    continue
                rm = light_ob.renderman        
                if not rm:
                    continue
                if rm.solo:
                    rman_sg_node.sg_node.SetHidden(0)
                else:
                    rman_sg_node.sg_node.SetHidden(1)  
        else:            
            for light_ob in scene_utils.get_all_lights(self.bl_scene, include_light_filters=False):
                rman_sg_node = self.rman_objects.get(light_ob.original, None)
                if not rman_sg_node:
                    continue
                rm = light_ob.renderman            
                if not rm:
                    continue
                if not light_ob.hide_get():
                    rman_sg_node.sg_node.SetHidden(rm.mute)
                else:
                    rman_sg_node.sg_node.SetHidden(1)                                   

    def export_searchpaths(self):
        # TODO 
        # RMAN_ARCHIVEPATH,
        # RMAN_DISPLAYPATH, RMAN_PROCEDURALPATH, and RMAN_DSOPATH (combines procedurals and displays)
        
        # get cycles shader directory
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        cycles_shader_dir = os.path.join(cur_dir, '..', 'cycles', 'shader' )

        RMAN_SHADERPATH = os.environ.get('RMAN_SHADERPATH', '')
        RMAN_TEXTUREPATH = os.environ.get('RMAN_TEXTUREPATH', '')
        RMAN_RIXPLUGINPATH = os.environ.get('RMAN_RIXPLUGINPATH', '')
        if sys.platform == ("win32"):
            # substitute ; for : in paths
            RMAN_SHADERPATH = RMAN_SHADERPATH.replace(';', ':')
            RMAN_TEXTUREPATH = RMAN_TEXTUREPATH.replace(';', ':')
            RMAN_RIXPLUGINPATH = RMAN_RIXPLUGINPATH.replace(';', ':')

        options = self.sg_scene.GetOptions()
        options.SetString(self.rman.Tokens.Rix.k_searchpath_shader, '.:%s:%s:@' % (cycles_shader_dir, RMAN_SHADERPATH))
        options.SetString(self.rman.Tokens.Rix.k_searchpath_texture, '.:%s:@' % RMAN_TEXTUREPATH)
        options.SetString(self.rman.Tokens.Rix.k_searchpath_rixplugin, '.:%s:@' % RMAN_RIXPLUGINPATH)
        options.SetString(self.rman.Tokens.Rix.k_searchpath_display, '.:@')

        self.sg_scene.SetOptions(options)

    def export_hider(self):
        options = self.sg_scene.GetOptions()
        rm = self.bl_scene.renderman
        if self.rman_bake:
            options.SetString(self.rman.Tokens.Rix.k_hider_type, self.rman.Tokens.Rix.k_bake)
            bakemode = rm.rman_bake_mode.lower()
            primvar_s = rm.rman_bake_illum_primvarS
            if primvar_s == '':
                primvar_s = 's'
            primvar_t = rm.rman_bake_illum_primvarT
            if primvar_t == '':
                primvar_t = 't'
            invert_t = rm.rman_bake_illum_invertT
            options.SetString(self.rman.Tokens.Rix.k_hider_bakemode, bakemode)
            options.SetStringArray(self.rman.Tokens.Rix.k_hider_primvar, (primvar_s, primvar_t), 2) 
            options.SetInteger(self.rman.Tokens.Rix.k_hider_invert, invert_t)
        else:
            pv = rm.ri_pixelVariance

            options.SetInteger(self.rman.Tokens.Rix.k_hider_minsamples, rm.hider_minSamples)
            options.SetInteger(self.rman.Tokens.Rix.k_hider_maxsamples, rm.hider_maxSamples)
            options.SetInteger(self.rman.Tokens.Rix.k_hider_incremental, rm.hider_incremental)

            if self.is_interactive:
                options.SetInteger(self.rman.Tokens.Rix.k_hider_decidither, rm.hider_decidither)
                options.SetInteger(self.rman.Tokens.Rix.k_hider_maxsamples, rm.ipr_hider_minSamples)
                options.SetInteger(self.rman.Tokens.Rix.k_hider_minsamples, rm.ipr_hider_maxSamples)
                options.SetInteger(self.rman.Tokens.Rix.k_hider_incremental, 1)
                pv = rm.ipr_ri_pixelVariance

            if (not self.external_render and rm.render_into == 'blender') or rm.enable_checkpoint:
                options.SetInteger(self.rman.Tokens.Rix.k_hider_incremental, 1)

            if not rm.sample_motion_blur:
                options.SetInteger(self.rman.Tokens.Rix.k_hider_samplemotion, 0)

            options.SetFloat(self.rman.Tokens.Rix.k_Ri_PixelVariance, pv)

            dspys_dict = display_utils.get_dspy_dict(self)
            anyDenoise = False
            for dspy,params in dspys_dict['displays'].items():
                if params['denoise']:
                    anyDenoise = True
                    break
            if anyDenoise:
                options.SetString(self.rman.Tokens.Rix.k_hider_pixelfiltermode, 'importance')

        self.sg_scene.SetOptions(options)  

    def export_global_options(self):
        rm = self.bl_scene.renderman
        options = self.sg_scene.GetOptions()

        # set any properties marked riopt in the config file
        for prop_name, meta in rm.prop_meta.items():
            if 'riopt' not in meta:
                continue
            
            val = getattr(rm, prop_name)
            ri_name = meta['riopt']
            is_array = False
            array_len = -1
            if 'arraySize' in meta:
                is_array = True
                array_len = meta['arraySize']
            param_type = meta['renderman_type']
            property_utils.set_rix_param(options, param_type, ri_name, val, is_reference=False, is_array=is_array, array_len=array_len, node=rm)

        # threads
        if not self.external_render:
            options.SetInteger(self.rman.Tokens.Rix.k_threads, rm.threads)

        # cache sizes
        options.SetInteger(self.rman.Tokens.Rix.k_limits_geocachememory, rm.limits_geocachememory)
        options.SetInteger(self.rman.Tokens.Rix.k_limits_opacitycachememory, rm.limits_opacitycachememory)
        options.SetInteger(self.rman.Tokens.Rix.k_limits_texturememory, rm.limits_texturememory)

        # pixelfilter
        options.SetString(self.rman.Tokens.Rix.k_Ri_PixelFilterName, rm.ri_displayFilter)
        options.SetFloatArray(self.rman.Tokens.Rix.k_Ri_PixelFilterWidth, (rm.ri_displayFilterSize[0], rm.ri_displayFilterSize[1]), 2)

        # checkpointing
        if not self.is_interactive and rm.enable_checkpoint:
            if rm.checkpoint_interval != '':
                interval_tokens = rm.checkpoint_interval.split()
                if len(interval_tokens) > 0:
                    options.SetStringArray(self.rman.Tokens.Rix.k_checkpoint_interval, interval_tokens, len(interval_tokens) )
            if rm.checkpoint_exitat != '':
                exitat_tokens = rm.checkpoint_exitat.split()
                if len(exitat_tokens) > 0:
                    options.SetStringArray(self.rman.Tokens.Rix.k_checkpoint_interval, exitat_tokens, len(exitat_tokens) )

            options.SetInteger(self.rman.Tokens.Rix.k_checkpoint_asfinal, int(rm.checkpoint_asfinal))
        
        # Set frame number 
        options.SetInteger(self.rman.Tokens.Rix.k_Ri_Frame, self.bl_scene.frame_current)

        # Stats
        if not self.is_interactive and rm.use_statistics:
            options.SetInteger(self.rman.Tokens.Rix.k_statistics_endofframe, int(rm.statistics_level))
            options.SetString(self.rman.Tokens.Rix.k_statistics_xmlfilename, 'stats.%04d.xml' % self.bl_scene.frame_current)

        # Set bucket shape
        bucket_order = rm.opt_bucket_order.lower()
        bucket_orderorigin = []
        if rm.enable_checkpoint and not self.is_interactive:
            bucket_order = 'horizontal'
        
        elif rm.opt_bucket_order == 'spiral':
            settings = self.bl_scene.render

            if rm.opt_bucket_sprial_x <= settings.resolution_x and rm.opt_bucket_sprial_y <= settings.resolution_y:
                if rm.opt_bucket_sprial_x == -1:
                    halfX = settings.resolution_x / 2                    
                    bucket_orderorigin = [int(halfX), rm.opt_bucket_sprial_y]

                elif rm.opt_bucket_sprial_y == -1:
                    halfY = settings.resolution_y / 2
                    bucket_orderorigin = [rm.opt_bucket_sprial_y, int(halfY)]
                else:
                    bucket_orderorigin = [rm.opt_bucket_sprial_x, rm.opt_bucket_sprial_y]
        
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

        # dirmaps
        dirmaps = ''
        for k in rfb_config['dirmaps']:
            dirmap = rfb_config['dirmaps'][k]
            d = "[ \"%s\" \"%s\" \"%s\"]" % (dirmap['zone'], dirmap['from'], dirmap['to'])
            dirmaps += d
        if dirmaps:
            options.SetString('searchpath:dirmap', dirmaps)

        # colorspace
        ocioconfig = color_manager_blender.get_config_path()
        ociocolorspacename = color_manager_blender.get_colorspace_name()
        options.SetString('user:ocioconfigpath', ocioconfig)
        options.SetString('user:ociocolorspacename', ociocolorspacename)

        self.sg_scene.SetOptions(options)        

    def export_integrator(self):
        world = self.bl_scene.world
        rm = world.renderman

        bl_integrator_node = shadergraph_utils.find_integrator_node(world)
        if bl_integrator_node:
            integrator_sg = self.rman.SGManager.RixSGShader("Integrator", bl_integrator_node.bl_label, "integrator")
            rman_sg_node = RmanSgNode(self, integrator_sg, "")
            property_utils.property_group_to_rixparams(bl_integrator_node, rman_sg_node, integrator_sg, ob=world)
        else:
            integrator_sg = self.rman.SGManager.RixSGShader("Integrator", "PxrPathTracer", "integrator")

        self.sg_scene.SetIntegrator(integrator_sg) 


    def export_cameras(self, bl_cameras):

        main_cam = self.depsgraph.scene_eval.camera
        cam_translator =  self.rman_translators['CAMERA']
       
        if self.is_viewport_render:
            db_name = 'main_camera'
            self.main_camera = cam_translator.export(None, db_name)
            self.main_camera.sg_node.SetRenderable(1)
            self.sg_scene.Root().AddChild(self.main_camera.sg_node)

            # add camera so we don't mistake it for a new obj
            self.rman_cameras[main_cam.original] = self.main_camera
            
            self.rman_objects[main_cam.original] = self.main_camera
      
            self.processed_obs.append(main_cam.original)
        elif len(bl_cameras) < 1 and self.is_interactive:
            cam = self.context.space_data.camera
            db_name = object_utils.get_db_name(cam)
            rman_sg_camera = cam_translator.export(cam, db_name)
            self.main_camera = rman_sg_camera         
            self.rman_cameras[cam.original] = rman_sg_camera            
            self.rman_objects[cam.original] = rman_sg_camera
            
            self.sg_scene.Root().AddChild(rman_sg_camera.sg_node)            

        else:
            for cam in bl_cameras:
                db_name = object_utils.get_db_name(cam)
                rman_sg_camera = cam_translator.export(cam, db_name)
                if cam == main_cam:
                    self.main_camera = rman_sg_camera 
                    if self.main_camera.is_transforming:
                        self.motion_steps.update(self.main_camera.motion_steps)             

                self.rman_cameras[cam.original] = rman_sg_camera
                
                self.rman_objects[cam.original] = rman_sg_camera
                
                self.sg_scene.Root().AddChild(rman_sg_camera.sg_node)

        # For now, make the main camera the 'primary' dicing camera
        self.main_camera.sg_node.SetRenderable(1)
        

    def export_displayfilters(self):
        rm = self.bl_scene.renderman
        display_filter_names = []
        displayfilters_list = []

        world = self.bl_scene.world

        if not world.renderman.use_renderman_node:
            # put in a default background color, using world color, then bail
            if not self.world_df_node:
                self.world_df_node = self.rman.SGManager.RixSGShader("DisplayFilter", "PxrBackgroundDisplayFilter", "__rman_world_df")
            params = self.world_df_node.params
            params.SetColor("backgroundColor", self.bl_scene.world.color[:3])
            self.sg_scene.SetDisplayFilter([self.world_df_node])            
            return

        for bl_df_node in shadergraph_utils.find_displayfilter_nodes(world):
            if not bl_df_node.is_active:
                continue

            # don't emit stylized filters, if render_rman_stylized is false
            if bl_df_node.bl_label in rman_constants.RMAN_STYLIZED_FILTERS and not rm.render_rman_stylized:
                continue

            df_name = bl_df_node.name
            if df_name == "":
                df_name = "rman_displayfilter_filter%d" % i

            rman_df_node = self.rman.SGManager.RixSGShader("DisplayFilter", bl_df_node.bl_label, df_name)
            rman_sg_node = RmanSgNode(self, rman_df_node, "")
            property_utils.property_group_to_rixparams(bl_df_node, rman_sg_node, rman_df_node, ob=world)
            display_filter_names.append(df_name)
            displayfilters_list.append(rman_df_node)    

        if len(display_filter_names) > 1:
            df_name = "rman_displayfilter_combiner"
            df_node = self.rman.SGManager.RixSGShader("DisplayFilter", "PxrDisplayFilterCombiner", df_name)
            params = df_node.params
            params.SetDisplayFilterReferenceArray("filter", display_filter_names, len(display_filter_names))
            displayfilters_list.append(df_node)

        self.sg_scene.SetDisplayFilter(displayfilters_list)        

    def export_samplefilters(self, sel_chan_name=None):
        rm = self.bl_scene.renderman
        sample_filter_names = []        
        samplefilters_list = list()

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

        world = self.bl_scene.world

        for bl_sf_node in shadergraph_utils.find_samplefilter_nodes(world):
            if not bl_sf_node.is_active:
                continue
            sf_name = bl_sf_node.name
            if sf_name == "":
                sf_name = "rman_samplefilter_filter%d" % i

            rman_sf_node = self.rman.SGManager.RixSGShader("SampleFilter", bl_sf_node.bl_label, sf_name)
            rman_sg_node = RmanSgNode(self, rman_sf_node, "")
            property_utils.property_group_to_rixparams(bl_sf_node, rman_sg_node, rman_sf_node, ob=world)
            sample_filter_names.append(sf_name)
            samplefilters_list.append(rman_sf_node)                    

        if sel_chan_name:
            sf_name = '__RMAN_VIEWPORT_CHANNEL_SELECT__'
            rman_sel_chan_node = self.rman.SGManager.RixSGShader("SampleFilter", "PxrCopyAOVSampleFilter", sf_name)
            params = rman_sel_chan_node.params
            params.SetString("readAov", sel_chan_name)            
            sample_filter_names.append(sf_name)
            samplefilters_list.append(rman_sel_chan_node)             


        if len(sample_filter_names) > 1:
            sf_name = "rman_samplefilter_combiner"
            sf_node = self.rman.SGManager.RixSGShader("SampleFilter", "PxrSampleFilterCombiner", sf_name)
            params = sf_node.params
            params.SetSampleFilterReferenceArray("filter", sample_filter_names, len(sample_filter_names))

            samplefilters_list.append(sf_node)

        self.sg_scene.SetSampleFilter(samplefilters_list) 

    def export_bake_displays(self):
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

        # baking requires we only do one channel per display. So, we create a new display
        # for each channel
        for dspy,dspy_params in dspys_dict['displays'].items():
            if not dspy_params['bake_mode']:
                continue
            display_driver = dspy_params['driverNode']
            channels = (dspy_params['params']['displayChannels'])

            if not dspy_params['bake_mode']:
                # if bake is off for this aov, just render to the null display driver
                dspy_file_name = dspy_params['filePath']
                display = self.rman.SGManager.RixSGShader("Display", "null", dspy_file_name)                
                channels = ','.join(channels)
                display.params.SetString("mode", channels)
                cam_dspys = cams_to_dspys.get(self.main_camera, list())
                cam_dspys.append(display)
                cams_to_dspys[self.main_camera] = cam_dspys                

            else:
                for chan in channels:
                    chan_type = dspys_dict['channels'][chan]['channelType']['value']
                    if chan_type != 'color':
                        # we can only bake color channels
                        continue

                    dspy_file_name = dspy_params['filePath']
                    if rm.rman_bake_illum_filename == 'BAKEFILEATTR':
                        tokens = os.path.splitext(dspy_file_name)
                        if tokens[1] == '':
                            token_dict = {'aov': dspy}
                            dspy_file_name = string_utils.expand_string('%s.{EXT}' % dspy_file_name, 
                                                                        display=display_driver,
                                                                        token_dict=token_dict
                                                                        )
                    else:
                        tokens = os.path.splitext(dspy_file_name)
                        dspy_file_name = '%s.%s%s' % (tokens[0], chan, tokens[1])
                    display = self.rman.SGManager.RixSGShader("Display", display_driver, dspy_file_name)

                    dspydriver_params = dspy_params['dspyDriverParams']
                    if dspydriver_params:
                        display.params.Inherit(dspydriver_params)
                    display.params.SetString("mode", chan)

                    if display_driver == 'openexr':
                        if rm.use_metadata:
                            display_utils.export_metadata(self.bl_scene, display.params)
                        
                    camera = dspy_params['camera']
                    if camera is None:
                        cam_dspys = cams_to_dspys.get(self.main_camera, list())
                        cam_dspys.append(display)
                        cams_to_dspys[self.main_camera] = cam_dspys
                    else:
                        #db_name = object_utils.get_db_name(camera)
                        if camera not in self.rman_cameras:
                            cam_dspys = cams_to_dspys.get(self.main_camera, list())
                            cam_dspys.append(display)
                            cams_to_dspys[self.main_camera] = cam_dspys
                        else:
                            cam_sg_node = self.rman_cameras.get(camera)
                            cam_dspys = cams_to_dspys.get(cam_sg_node, list())
                            cam_dspys.append(display)
                            cams_to_dspys[cam_sg_node] = cam_dspys

        for cam_sg_node,cam_dspys in cams_to_dspys.items():
            #cam = self.rman_cameras.get(db_name, None)
            if not cam_sg_node:
                continue
            if cam_sg_node != self.main_camera:
                cam_sg_node.sg_node.SetRenderable(2)
            cam_sg_node.sg_node.SetDisplay(cam_dspys)

        self.sg_scene.SetDisplayChannel(displaychannels)          

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
            if chan_source and chan_source != '':
                if "lpe" in chan_source:
                    displaychannel.params.SetString(self.rman.Tokens.Rix.k_source, '%s %s' % (chan_type, chan_source))                                
                else:
                    displaychannel.params.SetString(self.rman.Tokens.Rix.k_source, '%s' % (chan_source))

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
            dspydriver_params = dspy_params['dspyDriverParams']
            if dspydriver_params:
                display.params.Inherit(dspydriver_params)
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
                cam_dspys = cams_to_dspys.get(self.main_camera, list())
                cam_dspys.append(display)
                cams_to_dspys[self.main_camera] = cam_dspys
            else:
                #db_name = object_utils.get_db_name(camera)
                if camera not in self.rman_cameras:
                    cam_dspys = cams_to_dspys.get(self.main_camera, list())
                    cam_dspys.append(display)
                    cams_to_dspys[self.main_camera] = cam_dspys
                else:
                    cam_sg_node = self.rman_cameras.get(camera)
                    cam_dspys = cams_to_dspys.get(cam_sg_node, list())
                    cam_dspys.append(display)
                    cams_to_dspys[cam_sg_node] = cam_dspys

        for cam_sg_node,cam_dspys in cams_to_dspys.items():
            #cam = self.rman_cameras.get(db_name, None)
            if not cam_sg_node:
                continue
            if cam_sg_node != self.main_camera:
                cam_sg_node.sg_node.SetRenderable(2)
            cam_sg_node.sg_node.SetDisplay(cam_dspys)

        self.sg_scene.SetDisplayChannel(displaychannels)  

    def export_viewport_stats(self, integrator=''):
        if not self.is_viewport_render:
            return
        rm = self.bl_scene.renderman
        if integrator == '':
            integrator = 'PxrPathTracer'
            world = self.bl_scene.world

            bl_integrator_node = shadergraph_utils.find_integrator_node(world)
            if bl_integrator_node:
                integrator = bl_integrator_node.bl_label
   
        self.rman_render.bl_engine.update_stats('RenderMan (Stats)', 
                                                '\nIntegrator: %s\nMin Samples: %d\nMax Samples: %d\nInteractive Refinement: %d\nResolution Multiplier: %d%%' % (integrator, rm.ipr_hider_minSamples, rm.ipr_hider_maxSamples, rm.hider_decidither, int(self.viewport_render_res_mult*100)))
