# Translators
from .translators.rman_camera_translator import RmanCameraTranslator
from .translators.rman_light_translator import RmanLightTranslator
from .translators.rman_lightfilter_translator import RmanLightFilterTranslator
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
from .rman_utils import shadergraph_utils

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
        self.is_swatch_render = False
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
        self.rman_root_sg_node = None

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
        self.rman_translators['EMITTER'] = RmanParticlesTranslator(rman_scene=self)
        self.rman_translators['DYNAMIC_LOAD_DSO'] = RmanProceduralTranslator(rman_scene=self)
        self.rman_translators['DELAYED_LOAD_ARCHIVE'] = RmanDraTranslator(rman_scene=self)
        self.rman_translators['PROCEDURAL_RUN_PROGRAM'] = RmanRunProgramTranslator(rman_scene=self)
        self.rman_translators['OPENVDB'] = RmanOpenVDBTranslator(rman_scene=self)
        self.rman_translators['GPENCIL'] = RmanGPencilTranslator(rman_scene=self)
        self.rman_translators['MESH'] = RmanMeshTranslator(rman_scene=self)
        self.rman_translators['QUADRIC'] = RmanQuadricTranslator(rman_scene=self)

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

        if self.rman_bake:
            self.export_bake_render_scene()
        else:
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

    def export_for_swatch_render(self, depsgraph, sg_scene, render_output):
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
        self.export_swatch_render_scene(render_output)



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

        rfb_log().debug("Creating root scene graph node")
        self.export_root_sg_node()
        
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

    def export_bake_render_scene(self):
        self.reset()

        # update variables
        string_utils.set_var('scene', self.bl_scene.name)
        string_utils.set_var('layer', self.bl_view_layer.name)

        self.bl_frame_current = self.bl_scene.frame_current
        self.scene_any_lights = self._scene_has_lights()

        rfb_log().debug("Calling export_materials()")
        self.export_materials([m for m in self.depsgraph.ids if isinstance(m, bpy.types.Material)])
                
        rfb_log().debug("Calling txmake_all()")
        texture_utils.get_txmanager().rman_scene = self  
        texture_utils.get_txmanager().txmake_all(blocking=True)

        rfb_log().debug("Creating root scene graph node")
        self.export_root_sg_node()
        
        rm = self.bl_scene.renderman
        attrs = self.rman_root_sg_node.sg_node.GetAttributes()
        attrs.SetFloat("dice:worlddistancelength", rm.rman_bake_illlum_density)
        self.rman_root_sg_node.sg_node.SetAttributes(attrs)
        self.sg_scene.Root().AddChild(self.rman_root_sg_node.sg_node)                                

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

    def export_swatch_render_scene(self, render_output):
        self.reset()

        group_db_name = '__RMAN_ROOT_SG_NODE'
        self.rman_root_sg_node = self.rman_translators['GROUP'].export(None, group_db_name)
        self.sg_scene.Root().AddChild(self.rman_root_sg_node.sg_node) 

        # options
        options = self.sg_scene.GetOptions()
        options.SetInteger(self.rman.Tokens.Rix.k_hider_minsamples, 0)
        options.SetInteger(self.rman.Tokens.Rix.k_hider_maxsamples, 4)
        options.SetInteger(self.rman.Tokens.Rix.k_hider_incremental, 0)
        options.SetString("adaptivemetric", "variance")
        scale = 100.0 / self.bl_scene.render.resolution_percentage
        w = int(self.bl_scene.render.resolution_x * scale)
        h = int(self.bl_scene.render.resolution_y * scale)
        options.SetIntegerArray(self.rman.Tokens.Rix.k_Ri_FormatResolution, (w, h), 2)
        options.SetFloat(self.rman.Tokens.Rix.k_Ri_PixelVariance, 0.015)
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
        display_driver = 'openexr'
        dspy_chan_Ci = self.rman.SGManager.RixSGDisplayChannel('color', 'Ci')
        dspy_chan_a = self.rman.SGManager.RixSGDisplayChannel('float', 'a')

        self.sg_scene.SetDisplayChannel([dspy_chan_Ci, dspy_chan_a])
        display = self.rman.SGManager.RixSGShader("Display", display_driver, render_output)
        display.params.SetString("mode", 'Ci,a')
        display.params.SetInteger("asrgba", 1)
        self.main_camera.sg_node.SetDisplay(display)          

        rfb_log().debug("Calling materials()")
        self.export_materials([m for m in self.depsgraph.ids if isinstance(m, bpy.types.Material)])
        rfb_log().debug("Calling export_data_blocks()")
        
        self.export_data_blocks([m for m in self.depsgraph.ids if isinstance(m, bpy.types.Object)])
        self.export_instances()

    def export_root_sg_node(self):
        
        group_db_name = '__RMAN_ROOT_SG_NODE'
        self.rman_root_sg_node = self.rman_translators['GROUP'].export(None, group_db_name)
        rm = self.bl_scene.renderman

        attrs = self.rman_root_sg_node.sg_node.GetAttributes()
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
            property_utils.set_rix_param(attrs, param_type, ri_name, val, is_reference=False, is_array=is_array, array_len=array_len)  

        self.rman_root_sg_node.sg_node.SetAttributes(attrs)
        self.sg_scene.Root().AddChild(self.rman_root_sg_node.sg_node)                                
        
    def get_root_sg_node(self):
        return self.rman_root_sg_node.sg_node

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
        if not obj and self.is_swatch_render:
            obj = db_ob

        if obj and obj.type not in ('ARMATURE', 'CURVE', 'CAMERA'):
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
            if db_name in self.rman_objects:
                return
            rman_sg_node = translator.export(ob, db_name)
            if not rman_sg_node:
                return
            rman_sg_node.rman_type = rman_type
            self.rman_objects[db_name] = rman_sg_node 

            if rman_type in ['MESH', 'POINTS']:
                # Deal with any particles now. Particles are children to mesh nodes.
                subframes = []
                if self.do_motion_blur:
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
                    elif psys.settings.type == 'EMITTER':
                        psys_db_name = object_utils.get_db_name(ob, psys=psys)
                        rman_sg_particles_node = psys_translator.export(ob, psys, psys_db_name)                        
                        if psys.settings.render_type != 'OBJECT':
                            rman_sg_particles_node.motion_steps = subframes
                            psys_translator.update(ob, psys, rman_sg_particles_node)
                            if rman_sg_particles_node.sg_node:
                                rman_sg_node.sg_node.AddChild(rman_sg_particles_node.sg_node)  
                        else:
                            rman_sg_particles_node.is_deforming = False
                            rman_sg_particles_node.is_transforming = False
                            self.sg_scene.Root().AddChild(rman_sg_particles_node.sg_node)                                
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
        return (len([x for x in self.bl_scene.objects if object_utils._detect_primitive_(x) == 'LIGHT']) > 0)        

    def _export_instance(self, ob_inst, seg=None):
   
        group_db_name = object_utils.get_group_db_name(ob_inst) 
        rman_group_translator = self.rman_translators['GROUP']
        parent_sg_node = None
        rman_sg_particles = None
        if ob_inst.is_instance:
            parent = ob_inst.parent
            ob = ob_inst.instance_object
            psys = ob_inst.particle_system
            if psys:
                particles_db_name = object_utils.get_db_name(parent, psys=psys)
                rman_sg_particles = self.rman_particles[particles_db_name]
            else:                
                #if parent.type == "EMPTY" and parent.is_instancer:
                if parent.is_instancer:
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
        if rman_type == 'LIGHTFILTER':
            return
        elif rman_sg_particles:
            db_name = object_utils.get_db_name(ob, rman_type=rman_type)          
            if db_name == '':
                return

            rman_sg_node = self.rman_objects.get(db_name, None)           
            if not rman_sg_node:
                return

            rman_sg_group = rman_group_translator.export(ob, group_db_name)
            rman_sg_group.sg_node.AddChild(rman_sg_node.sg_node)
            rman_group_translator.update_transform(ob_inst, rman_sg_group)

            psys_translator = self.rman_translators[psys.settings.type] 
            self.attach_particle_material(psys, parent, ob, rman_sg_group.sg_node)       
            psys_translator.add_object_instance(rman_sg_particles, rman_sg_group.sg_node)  

            # object attrs             
            psys_translator.export_object_attributes(ob, rman_sg_group.sg_node)                         
      
            self.rman_objects[group_db_name] = rman_sg_group
            rman_sg_node.instances[group_db_name] = rman_sg_group

        elif ob.type == "EMPTY" and ob.is_instancer:
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
                    translator.export_object_primvars(ob, rman_sg_node.sg_node)
                    self.processed_obs[db_name] = ob

            rman_sg_group = rman_group_translator.export(ob, group_db_name)
            rman_sg_group.is_instancer = ob.is_instancer
            if rman_sg_node.sg_node is None:
                # add the group to the root anyways
                rman_sg_group.db_name = db_name
                self.get_root_sg_node().AddChild(rman_sg_group.sg_node)
                self.rman_objects[db_name] = rman_sg_group
                return

            rman_sg_group.sg_node.AddChild(rman_sg_node.sg_node)
            rman_sg_group.rman_sg_node_instance = rman_sg_node
            
            if rman_type != "META":
                # meta/blobbies are already in world space. Their instances don't need to
                # set a transform.
                if rman_sg_node.is_transforming:
                    rman_group_translator.update_transform_num_samples(rman_sg_group, rman_sg_node.motion_steps )
                    rman_group_translator.update_transform_sample(ob_inst, rman_sg_group, 0, seg )
                else:
                    rman_group_translator.update_transform(ob_inst, rman_sg_group)

            self.get_root_sg_node().AddChild(rman_sg_group.sg_node)
            self.rman_objects[group_db_name] = rman_sg_group

            # object attrs             
            if translator:
                translator.export_object_attributes(ob, rman_sg_group.sg_node)  

            self.attach_material(ob, rman_sg_group.sg_node)

            # add instance to the RmanSgNode
            if parent_sg_node:
                parent_sg_node.instances[group_db_name] = rman_sg_group 
                rman_sg_group.rman_sg_group_parent = parent_sg_node

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

    def attach_particle_material(self, psys, ob, inst_ob, group):
        if psys.settings.renderman.use_object_material:
            for mat in object_utils._get_used_materials_(inst_ob): 
                if not mat:
                    continue
                mat_db_name = object_utils.get_db_name(mat)
                rman_sg_material = self.rman_materials.get(mat_db_name, None)
                if rman_sg_material and rman_sg_material.sg_node:
                    group.SetMaterial(rman_sg_material.sg_node) 
        else:
            mat_idx = psys.settings.material - 1
            if mat_idx < len(ob.material_slots):
                mat = ob.material_slots[mat_idx].material
                mat_db_name = object_utils.get_db_name(mat)
                rman_sg_material = self.rman_materials.get(mat_db_name, None)
                if rman_sg_material:
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

                rman_group_translator = self.rman_translators['GROUP']
                if ob_inst.is_instance:
                    ob = ob_inst.instance_object.original  
                else:
                    ob = ob_inst.object

                group_db_name = object_utils.get_group_db_name(ob_inst)          

                if ob.type not in ['MESH']:
                    continue

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
            property_utils.set_rix_param(options, param_type, ri_name, val, is_reference=False, is_array=is_array, array_len=array_len)                

        # threads
        if not self.external_render:
            options.SetInteger(self.rman.Tokens.Rix.k_threads, rm.threads)

        # cache sizes
        options.SetInteger(self.rman.Tokens.Rix.k_limits_geocachememory, rm.limits_geocachememory * 100)
        options.SetInteger(self.rman.Tokens.Rix.k_limits_opacitycachememory, rm.limits_opacitycachememory * 100)
        options.SetInteger(self.rman.Tokens.Rix.k_limits_texturememory, rm.limits_texturememory * 100)

        # pixelfilter
        options.SetString(self.rman.Tokens.Rix.k_Ri_PixelFilterName, rm.ri_displayFilter)
        options.SetFloatArray(self.rman.Tokens.Rix.k_Ri_PixelFilterWidth, (rm.ri_displayFilterSize[0], rm.ri_displayFilterSize[1]), 2)

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

        self.sg_scene.SetOptions(options)        

    def export_integrator(self):
        world = self.bl_scene.world
        rm = world.renderman

        bl_integrator_node = shadergraph_utils.find_integrator_node(world)
        if bl_integrator_node:
            integrator_sg = self.rman.SGManager.RixSGShader("Integrator", bl_integrator_node.bl_label, "integrator")
            rman_sg_node = RmanSgNode(self, integrator_sg, "")
            property_utils.property_group_to_rixparams(bl_integrator_node, rman_sg_node, integrator_sg)
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

        world = self.bl_scene.world
        if not world.renderman.use_renderman_node:
            return

        for bl_df_node in shadergraph_utils.find_displayfilter_nodes(world):
            df_name = bl_df_node.name
            if df_name == "":
                df_name = "rman_displayfilter_filter%d" % i

            rman_df_node = self.rman.SGManager.RixSGShader("DisplayFilter", bl_df_node.bl_label, df_name)
            rman_sg_node = RmanSgNode(self, rman_df_node, "")
            property_utils.property_group_to_rixparams(bl_df_node, rman_sg_node, rman_df_node)
            display_filter_names.append(df_name)
            displayfilters_list.append(rman_df_node)    

        if not display_filter_names:
            return

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
            sf_name = bl_sf_node.name
            if sf_name == "":
                sf_name = "rman_samplefilter_filter%d" % i

            rman_sf_node = self.rman.SGManager.RixSGShader("SampleFilter", bl_sf_node.bl_label, sf_name)
            rman_sg_node = RmanSgNode(self, rman_sf_node, "")
            property_utils.property_group_to_rixparams(bl_sf_node, rman_sg_node, rman_sf_node)
            sample_filter_names.append(sf_name)
            samplefilters_list.append(rman_sf_node)                    

        if not sample_filter_names:
            return            

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
                cam_dspys = cams_to_dspys.get(self.main_camera.db_name, list())
                cam_dspys.append(display)
                cams_to_dspys[self.main_camera.db_name] = cam_dspys                

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
                                                '\nIntegrator: %s\nMin Samples: %d\nMax Samples: %d\nInteractive Refinement: %d' % (integrator, rm.ipr_hider_minSamples, rm.ipr_hider_maxSamples, rm.hider_decidither))

### UPDATE METHODS
#------------------------

    def update_view(self, context, depsgraph):
        camera = depsgraph.scene.camera
        rman_sg_camera = self.main_camera
        translator = self.rman_translators['CAMERA']
        with self.rman.SGManager.ScopedEdit(self.sg_scene):
            if self.is_viewport_render:
                translator.update(None, rman_sg_camera)
                translator.update_transform(None, rman_sg_camera)
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
                    psys = None
                    if ob_inst.is_instance:
                        ob = ob_inst.instance_object
                        group_db_name =  object_utils.get_group_db_name(ob_inst)
                        psys = ob_inst.particle_system 
                    else:
                        ob = ob_inst.object
                        group_db_name =  object_utils.get_group_db_name(ob_inst) 
                    rman_type = object_utils._detect_primitive_(ob)
                    obj_db_name = object_utils.get_db_name(ob, rman_type=rman_type)
                    rman_sg_node = self.rman_objects.get(obj_db_name, None)

                    if rman_sg_node:
                        for m in object_utils._get_used_materials_(ob):
                            if m == mat:
                                if group_db_name in rman_sg_node.instances:
                                    rman_sg_node.instances[group_db_name].sg_node.SetMaterial(rman_sg_material.sg_node)

            else:
                translator.update(mat, rman_sg_material)   

    def _object_transform_updated(self, obj):
        ob = obj.id         
        rman_type = object_utils._detect_primitive_(ob)
        obj_key = object_utils.get_db_name(ob, rman_type=rman_type) 
        rman_group_translator = self.rman_translators['GROUP']  
        rman_sg_node = self.rman_objects.get(obj_key, None)
        rm = ob.renderman

        with self.rman.SGManager.ScopedEdit(self.sg_scene):                
            if rman_type == 'LIGHTFILTER':
                group_db_name = object_utils.get_group_db_name(ob)
                rman_sg_group = self.rman_objects.get(group_db_name, None)                
                rman_group_translator.update_transform(ob, rman_sg_group)

            elif obj.id.is_instancer:
                for ob_inst in self.depsgraph.object_instances:           
                    if ob_inst.is_instance and ob_inst.parent == ob:     
                        group_db_name = object_utils.get_group_db_name(ob_inst)
                        rman_sg_group = self.rman_objects.get(group_db_name, None)
                        if rman_sg_group:
                            rman_group_translator.update_transform(ob_inst, rman_sg_group)
                        else:
                            self._export_instance(ob_inst)
            else:
                if rman_type == "META":
                    self.rman_translators['META'].update(ob, rman_sg_node)
                elif rman_type == "CAMERA" and not self.is_viewport_render:                    
                    self.rman_translators['CAMERA'].update_transform(ob, rman_sg_node) 
                else:                       
                    for k,rman_sg_group in rman_sg_node.instances.items():     
                        for ob_inst in self.depsgraph.object_instances: 
                            group_db_name = object_utils.get_group_db_name(ob_inst)
                            if group_db_name == k:
                                rman_group_translator.update_transform(ob_inst, rman_sg_group)
                                break

    def _instancer_updated(self, ob):
        existing_instances = []
        parent_sg_node = None
        rman_group_translator = self.rman_translators['GROUP']
        rman_type = object_utils._detect_primitive_(ob)
        obj_key = object_utils.get_db_name(ob, rman_type=rman_type) 
        instancer_sg_node = self.rman_objects[obj_key]        
        if ob.is_instancer:
            for ob_inst in self.depsgraph.object_instances:                                
                if not ob_inst.is_instance and ob_inst.parent != ob:
                    continue

                group_db_name = object_utils.get_group_db_name(ob_inst)
                rman_sg_group = instancer_sg_node.instances.get(group_db_name, None)
                if not rman_sg_group:
                    self._export_instance(ob_inst)
                else:
                    rman_group_translator.update_transform(ob_inst, rman_sg_group) 
                
                existing_instances.append(group_db_name)
                
            for k in [key for key in instancer_sg_node.instances.keys() if key not in existing_instances]:
                rman_sg_group = instancer_sg_node.instances.pop(k, None)
                if rman_sg_group:
                    self.get_root_sg_node().RemoveChild(rman_sg_group.sg_node)
                    self.rman_objects.pop(k, None)
                    if rman_sg_group.rman_sg_node_instance:
                        rman_sg_group.rman_sg_node_instance.instances.pop(k, None)
        else:
            for k in [key for key in instancer_sg_node.instances.keys()]:
                v = instancer_sg_node.instances[k]
                self.get_root_sg_node().RemoveChild(v.sg_node)
                if v.rman_sg_node_instance:
                    v.rman_sg_node_instance.instances.pop(k, None)
            instancer_sg_node.instances.clear()

    def _obj_geometry_updated(self, obj):
        ob = obj.id
        rman_type = object_utils._detect_primitive_(ob)
        obj_key = object_utils.get_db_name(ob, rman_type=rman_type) 
        rman_sg_node = self.rman_objects[obj_key]
            
        with self.rman.SGManager.ScopedEdit(self.sg_scene):
            if obj.id.is_instancer or (rman_sg_node.is_instancer and not obj.id.is_instancer):
                rman_sg_node.is_instancer = obj.id.is_instancer
                self._instancer_updated(obj.id)

            if rman_type == 'LIGHTFILTER':
                self.rman_translators['LIGHTFILTER'].update(ob, rman_sg_node)
                for light_ob in [x for x in self.bl_scene.objects if object_utils._detect_primitive_(x) == 'LIGHT']:
                    light_key = object_utils.get_db_name(light_ob, rman_type='LIGHT')
                    rman_sg_light = self.rman_objects[light_key]
                    if rman_sg_light:
                        self.rman_translators['LIGHT'].update_light_filters(light_ob, rman_sg_light)

            elif rman_type == 'LIGHT':
                self.rman_translators['LIGHT'].update(ob, rman_sg_node)
                                                    
                if not self.scene_solo_light:
                    # only set if a solo light hasn't been set
                    rman_sg_node.sg_node.SetHidden(ob.data.renderman.mute)
            elif rman_type == 'CAMERA':
                rman_camera_translator = self.rman_translators['CAMERA']
                if not self.is_viewport_render:
                    rman_camera_translator.update(ob, rman_sg_node)
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

                if rman_type in ['MESH', 'POINTS']:
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
                        elif psys.settings.type == 'EMITTER':
                            psys_db_name = object_utils.get_db_name(ob, psys=psys)
                            rman_sg_particles_node = self.rman_particles.get(psys_db_name, None)
                            if psys.settings.render_type != 'OBJECT':
                                if rman_sg_particles_node:
                                    psys_translator.update(ob, psys, rman_sg_particles_node)
                                else:
                                    rman_sg_particles_node = psys_translator.export(ob, psys, psys_db_name)
                                    rman_sg_node.sg_node.AddChild(rman_sg_particles_node.sg_node)  
                                    self.rman_particles[psys_db_name] = rman_sg_particles_node 
                            elif psys.settings.render_type == 'OBJECT':
                                if rman_sg_particles_node:
                                    psys_translator.update(ob, psys, rman_sg_particles_node)          
                                else:
                                    rman_sg_particles_node = psys_translator.export(ob, psys, psys_db_name)
                                    self.sg_scene.Root().AddChild(rman_sg_particles_node.sg_node)                                     
                                    self.rman_particles[psys_db_name] = rman_sg_particles_node     

                                inst_ob = psys.settings.instance_object 
                                rman_group_translator = self.rman_translators['GROUP']
                                psys_translator.update(ob, psys, rman_sg_particles_node)

                                # For object instances, we need to loop through the depsgraph instances
                                for ob_inst in self.depsgraph.object_instances:                                
                                    if ob_inst.is_instance and ob_inst.instance_object == inst_ob and ob_inst.particle_system == psys:   
                                        db_name = object_utils.get_db_name(inst_ob, rman_type=rman_type)          
                                        if db_name == '':
                                            continue

                                        rman_sg_node = self.rman_objects.get(db_name, None)           
                                        if not rman_sg_node:
                                            continue
                                        group_db_name = object_utils.get_group_db_name(ob_inst)

                                        rman_sg_group = rman_group_translator.export(ob, group_db_name)
                                        rman_sg_group.sg_node.AddChild(rman_sg_node.sg_node)
                                        rman_group_translator.update_transform(ob_inst, rman_sg_group)

                                        psys_translator.add_object_instance(rman_sg_particles_node, rman_sg_group.sg_node) 
            
                                        # object attrs             
                                        psys_translator.export_object_attributes(ob, rman_sg_group.sg_node) 

                                        self.rman_objects[group_db_name] = rman_sg_group
                                        rman_sg_node.instances[group_db_name] = rman_sg_group
                                        self.attach_particle_material(psys, ob, inst_ob, rman_sg_group.sg_node)             

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
                with self.rman.SGManager.ScopedEdit(self.sg_scene): 
                    self.export_integrator()
                    self.export_samplefilters()
                    self.export_displayfilters()
                    self.export_viewport_stats()

            elif isinstance(obj.id, bpy.types.Camera):
                #cam = obj.object
                continue

            elif isinstance(obj.id, bpy.types.Material):
                rfb_log().debug("Material updated: %s" % obj.id.name)
                self._material_updated(obj)

            elif isinstance(obj.id, bpy.types.Object):

                rman_type = object_utils._detect_primitive_(ob)
                obj_key = object_utils.get_db_name(ob, rman_type=rman_type)                                

                if obj_key == "":
                    continue

                if obj_key not in self.rman_objects:
                    rfb_log().debug("New object added: %s" % obj.id.name)
                    if ob.type == 'CAMERA' and not self.is_viewport_render:
                        new_cams.append(obj.id)
                    else:
                        new_objs.append(obj.id)
                    continue

                if obj.is_updated_geometry:
                    rfb_log().debug("Object updated: %s" % obj.id.name)
                    self._obj_geometry_updated(obj)                    
                                          
                if obj.is_updated_transform:
                    rfb_log().debug("Transform updated: %s" % obj.id.name)
                    self._object_transform_updated(obj)

        # there are new objects
        if new_objs:
            with self.rman.SGManager.ScopedEdit(self.sg_scene): 
                rfb_log().debug("Adding new objects:")
                self.export_data_blocks(new_objs)
                for new_obj in new_objs:
                    for ob_inst in self.depsgraph.object_instances:
                        if ob_inst and ob_inst.instance_object == new_obj:
                            self._export_instance(ob_inst)
                        elif ob_inst.object == new_obj:
                            self._export_instance(ob_inst)

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
                    # there may be a collection instance still referencing the geo
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
        if context:
            self.bl_scene = context.scene
        with self.rman.SGManager.ScopedEdit(self.sg_scene):
            self.export_integrator() 
            self.export_viewport_stats()

    def update_viewport_integrator(self, context, integrator):
        self.bl_scene = context.scene
        with self.rman.SGManager.ScopedEdit(self.sg_scene):
            integrator_sg = self.rman.SGManager.RixSGShader("Integrator", integrator, "integrator")       
            self.sg_scene.SetIntegrator(integrator_sg)     
            self.export_viewport_stats(integrator=integrator)        

    def update_hider_options(self, context):
        self.bl_scene = context.scene
        with self.rman.SGManager.ScopedEdit(self.sg_scene):
            self.export_hider()
            self.export_viewport_stats()
 
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

    def update_solo_light(self, context):
        # solo light has changed
        self.bl_scene = context.scene
        self.scene_solo_light = self.bl_scene.renderman.solo_light
                    
        with self.rman.SGManager.ScopedEdit(self.sg_scene):
            
            for light_ob in [x for x in self.bl_scene.objects if object_utils._detect_primitive_(x) == 'LIGHT']:
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
            for light_ob in [x for x in self.bl_scene.objects if object_utils._detect_primitive_(x) == 'LIGHT']:
                db_name = object_utils.get_db_name(light_ob, rman_type='LIGHT')
                rman_sg_node = self.rman_objects.get(db_name, None)
                if not rman_sg_node:
                    continue
                rman_sg_node.sg_node.SetHidden(light_ob.data.renderman.mute)
