# utils
from .rman_utils import object_utils
from .rman_utils import transform_utils
from .rman_utils import texture_utils
from .rman_utils import scene_utils
from .rman_utils import shadergraph_utils

from .rfb_logger import rfb_log
from .rman_sg_nodes.rman_sg_lightfilter import RmanSgLightFilter

import bpy

class RmanSceneSync(object):
    '''
    The RmanSceneSync class handles keeping the RmanScene object in sync
    during IPR. 

    Attributes:
        rman_render (RmanRender) - pointer back to the current RmanRender object
        rman () - rman python module
        rman_scene (RmanScene) - pointer to the current RmanScene object
        sg_scene (RixSGSCene) - the RenderMan scene graph object

    '''

    def __init__(self, rman_render=None, rman_scene=None, sg_scene=None):
        self.rman_render = rman_render
        self.rman = rman_render.rman
        self.rman_scene = rman_scene
        self.sg_scene = sg_scene          

    def update_view(self, context, depsgraph):
        camera = depsgraph.scene.camera
        self.rman_scene.context = context
        self.rman_scene.depsgraph = depsgraph
        self.rman_scene.bl_scene = depsgraph.scene_eval
        rman_sg_camera = self.rman_scene.main_camera
        translator = self.rman_scene.rman_translators['CAMERA']
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            if self.rman_scene.is_viewport_render:
                ob = translator.update_viewport_resolution(rman_sg_camera)
                if ob:
                    translator.update_viewport_cam(ob, rman_sg_camera)
                translator.update_transform(None, rman_sg_camera)
            else:
                translator.update_transform(camera, rman_sg_camera)  

    def _scene_updated(self):
        if self.rman_scene.bl_frame_current != self.rman_scene.bl_scene.frame_current:
            # frame changed, update any materials and lights that 
            # are marked as frame sensitive
            self.rman_scene.bl_frame_current = self.rman_scene.bl_scene.frame_current
            material_translator = self.rman_scene.rman_translators["MATERIAL"]
            light_translator = self.rman_scene.rman_translators["LIGHT"]

            with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):  
                for mat in bpy.data.materials:   
                    db_name = object_utils.get_db_name(mat)  
                    rman_sg_material = self.rman_scene.rman_materials.get(mat.original, None)
                    if rman_sg_material and rman_sg_material.is_frame_sensitive:
                        material_translator.update(mat, rman_sg_material)

                for o in bpy.data.objects:
                    if o.type == 'LIGHT':                                
                        obj_key = object_utils.get_db_name(o, rman_type='LIGHT') 
                        rman_sg_node = self.rman_scene.rman_objects[o.original]
                        if rman_sg_node.is_frame_sensitive:
                            light_translator.update(o, rman_sg_node)   

    def _mesh_light_geo_update(self, target_ob):
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            for ob_inst in self.rman_scene.depsgraph.object_instances:
                if ob_inst.is_instance:
                    ob = ob_inst.instance_object
                    group_db_name =  object_utils.get_group_db_name(ob_inst)
                else:
                    ob = ob_inst.object
                    group_db_name =  object_utils.get_group_db_name(ob_inst)
                
                if ob != target_ob:
                    continue
                     
                rman_sg_node = self.rman_scene.rman_objects.get(ob.original, None)
                if rman_sg_node:
                    rman_sg_group = rman_sg_node.instances.get(group_db_name, None)
                    if rman_sg_group:
                        rman_sg_node.instances.pop(group_db_name)
                        self.rman_scene.sg_scene.DeleteDagNode(rman_sg_group.sg_node)
                        rman_type = object_utils._detect_primitive_(ob)
                        translator = self.rman_scene.rman_translators.get(rman_type, None)
                        if not translator:
                            return
                        translator.update(ob, rman_sg_node)                                
                        self.rman_scene._export_instance(ob_inst)  
                        break     

    def _mesh_light_update(self, mat):
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            for ob_inst in self.rman_scene.depsgraph.object_instances:
                psys = None
                if ob_inst.is_instance:
                    ob = ob_inst.instance_object
                    group_db_name =  object_utils.get_group_db_name(ob_inst)
                else:
                    ob = ob_inst.object
                    group_db_name =  object_utils.get_group_db_name(ob_inst)
                if not hasattr(ob.data, 'materials'):
                    continue   
                if ob.type in ('ARMATURE', 'CURVE', 'CAMERA'):
                    continue                         
                rman_sg_node = self.rman_scene.rman_objects.get(ob.original, None)
                if rman_sg_node:
                    found = False
                    for name, material in ob.data.materials.items():
                        if name == mat.name:
                            found = True

                    if found:
                        rman_sg_group = rman_sg_node.instances.get(group_db_name, None)
                        if rman_sg_group:
                            rman_sg_node.instances.pop(group_db_name)
                            self.rman_scene.sg_scene.DeleteDagNode(rman_sg_group.sg_node)                              
                            self.rman_scene._export_instance(ob_inst)                 

    def _material_updated(self, obj):
        mat = obj.id
        db_name = object_utils.get_db_name(mat)
        rman_sg_material = self.rman_scene.rman_materials.get(mat.original, None)
        translator = self.rman_scene.rman_translators["MATERIAL"]              
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):   
            mat = obj.id              
            if not rman_sg_material:
                rfb_log().debug("New material: %s" % mat.name)
                rman_sg_material = translator.export(mat, db_name)
                self.rman_scene.rman_materials[mat.original] = rman_sg_material
                
                # Not sure of a better method to do this.
                # There doesn't seem to be an API call to know what objects in the scene
                # have this specific material, so we loop thru all objs
                #
                # we're assuming all instances of the object have the same material
                # if they don't, we would have to loop over depsgraph.object_instances

                '''
                for ob in bpy.data.objects:
                    rman_sg_node = self.rman_scene.rman_objects.get(ob.original, None)
                    if rman_sg_node:
                        for m in object_utils._get_used_materials_(ob):
                            if m == mat:
                                for k,rman_sg_group in rman_sg_node.instannces.items():
                                    # we're dealing with a mesh light.
                                    if rman_sg_material.has_meshlight != rman_sg_group.is_meshlight:
                                        rman_sg_node.instances.pop(group_db_name)
                                        self.rman_scene.sg_scene.DeleteDagNode(rman_sg_group.sg_node)
                                        self.rman_scene._export_instance(ob_inst)
                                    else:
                                        rman_sg_group.sg_node.SetMaterial(rman_sg_material.sg_node)  
                '''
                
            else:
                rfb_log().debug("Material, call update")
                translator.update(mat, rman_sg_material)   

    def _light_filter_transform_updated(self, obj):
        ob = obj.id
        rman_sg_lightfilter = self.rman_scene.rman_objects.get(ob.original, None)
        if rman_sg_lightfilter:
            rman_group_translator = self.rman_scene.rman_translators['GROUP']  
            with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):              
                rman_group_translator.update_transform(ob, rman_sg_lightfilter)

    def _gpencil_transform_updated(self, obj):
        ob = obj.id
        rman_sg_gpencil = self.rman_scene.rman_objects.get(ob.original, None)
        if rman_sg_gpencil:
            with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):       
                rman_group_translator = self.rman_scene.rman_translators['GROUP']         
                for ob_inst in self.rman_scene.depsgraph.object_instances: 
                    group_db_name = object_utils.get_group_db_name(ob_inst)
                    rman_sg_group = rman_sg_gpencil.instances.get(group_db_name, None)
                    if rman_sg_group:
                        rman_group_translator.update_transform(ob, rman_sg_group)                

    def _obj_geometry_updated(self, obj):
        ob = obj.id
        rman_type = object_utils._detect_primitive_(ob)
        db_name = object_utils.get_db_name(ob, rman_type=rman_type) 
        rman_sg_node = self.rman_scene.rman_objects.get(ob.original, None)

        if rman_type in ['LIGHT', 'LIGHTFILTER', 'CAMERA']:
            with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
                if rman_type == 'LIGHTFILTER':
                    if not isinstance(rman_sg_node, RmanSgLightFilter):
                        # We have a type mismatch. We can get into this situation when
                        # a new light filter is added to the scene. Blender doesn't
                        # seem to give us a chance to set properties on an object before telling us
                        # a new object has been added. So, we delete this node and re-export it
                        # as a RmanSgLightFilter
                        for k,rman_sg_group in rman_sg_node.instances.items():
                            self.rman_scene.get_root_sg_node().RemoveChild(rman_sg_group.sg_node)
                        rman_sg_node.instances.clear() 
                        del rman_sg_node
                        self.rman_scene.rman_objects.pop(ob.original)
                        rman_sg_node = self.rman_scene.rman_translators['LIGHTFILTER'].export(ob, db_name)            

                    self.rman_scene.rman_translators['LIGHTFILTER'].update(ob, rman_sg_node)
                    for light_ob in rman_sg_node.lights_list:
                        if isinstance(light_ob, bpy.types.Material):
                            rman_sg_material = self.rman_scene.rman_materials.get(light_ob.original, None)
                            if rman_sg_material:
                                self.rman_scene.rman_translators['MATERIAL'].update_light_filters(light_ob, rman_sg_material)                      
                        else:
                            rman_sg_light = self.rman_scene.rman_objects.get(light_ob.original, None)
                            if rman_sg_light:
                                self.rman_scene.rman_translators['LIGHT'].update_light_filters(light_ob, rman_sg_light)                      

                elif rman_type == 'LIGHT':
                    self.rman_scene.rman_translators['LIGHT'].update(ob, rman_sg_node)
                                                        
                    if not self.rman_scene.scene_solo_light:
                        # only set if a solo light hasn't been set
                        rman_sg_node.sg_node.SetHidden(ob.data.renderman.mute)
                elif rman_type == 'CAMERA':
                    rman_camera_translator = self.rman_scene.rman_translators['CAMERA']
                    if not self.rman_scene.is_viewport_render:
                        rman_camera_translator.update(ob, rman_sg_node)         

        else:
            if rman_sg_node.rman_type != rman_type:
                # for now, we don't allow the rman_type to be changed
                rfb_log().error("Changing primitive type is currently not supported.")
                return
            with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):     
                translator = self.rman_scene.rman_translators.get(rman_type, None)
                if not translator:
                    return
                translator.update(ob, rman_sg_node)
                # material slots could have changed, so we need to double
                # check that too
                for k,v in rman_sg_node.instances.items():
                    self.rman_scene.attach_material(ob, v)

    def _update_light_visibility(self, rman_sg_node, ob):
        if not self.rman_scene.scene_solo_light:
            if not ob.hide_get():
                rman_sg_node.sg_node.SetHidden(ob.renderman.mute)
            else:
                rman_sg_node.sg_node.SetHidden(1)   

    def update_scene(self, context, depsgraph):
        new_objs = []
        new_cams = []
        self.rman_scene.depsgraph = depsgraph
        self.rman_scene.bl_scene = depsgraph.scene
        self.rman_scene.context = context
        do_delete = False
        update_instances = []
        updated_geo = []

        def _check_empty(ob):
            # check the objects in the collection
            # if they need updating

            collection = ob.instance_collection
            if collection:
                for col_obj in collection.all_objects:
                    if col_obj.original not in self.rman_scene.rman_objects:
                        new_objs.append(col_obj.original)
                    update_instances.append(col_obj.original)            

        for obj in depsgraph.updates:
            ob = obj.id

            if isinstance(obj.id, bpy.types.Scene):
                self._scene_updated()

            elif isinstance(obj.id, bpy.types.World):
                with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene): 
                    self.rman_scene.export_integrator()
                    self.rman_scene.export_samplefilters()
                    self.rman_scene.export_displayfilters()
                    self.rman_scene.export_viewport_stats()

            elif isinstance(obj.id, bpy.types.Camera):
                if self.rman_scene.is_viewport_render:
                    if self.rman_scene.bl_scene.camera.data != obj.id:
                        continue
                    rman_sg_camera = self.rman_scene.main_camera
                    translator = self.rman_scene.rman_translators['CAMERA']
                    with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
                        translator.update_viewport_cam(self.rman_scene.bl_scene.camera, rman_sg_camera)       

            elif isinstance(obj.id, bpy.types.Material):
                rfb_log().debug("Material updated: %s" % obj.id.name)
                self._material_updated(obj)

            elif isinstance(obj.id, bpy.types.Object):

                rman_type = object_utils._detect_primitive_(ob)

                if obj.id.original not in self.rman_scene.rman_objects:
                    rfb_log().debug("New object added: %s" % obj.id.name)
                    if ob.type == 'CAMERA' and not self.rman_scene.is_viewport_render:
                        new_cams.append(obj.id.original)
                    else:
                        if ob.type == 'EMPTY' and ob.is_instancer:
                            _check_empty(ob)
                        else:
                            new_objs.append(obj.id.original)
                            update_instances.append(obj.id.original)
                    continue              

                if obj.is_updated_geometry:
                    if shadergraph_utils.is_mesh_light(obj.id):
                        # FIXME: the renderer currently doesn't allow geometry edits of
                        # mesh lights. For now, we remove instances of this mesh light
                        # and re-add. This is the same workaround we do when we convert
                        # a regular geometry into a mesh light. Once there's a fix in the 
                        # renderer, we can remove this if block.
                        rfb_log().debug("Mesh light updated: %s" % obj.id.name)
                        self._mesh_light_geo_update(obj.id)
                    else:
                        rfb_log().debug("Object updated: %s" % obj.id.name)
                        self._obj_geometry_updated(obj)                    
                        updated_geo.append(obj.id.original)    
                                          
                if obj.is_updated_transform:
                    if ob.type in ['CAMERA']:
                        # we deal with camera transforms in view_draw
                        continue
                    rfb_log().debug("Transform updated: %s" % obj.id.name)
                    if rman_type == 'LIGHTFILTER':
                        self._light_filter_transform_updated(obj)
                    elif rman_type == 'GPENCIL':
                        # FIXME: we shouldn't handle this specifically, but we seem to be
                        # hitting a prman crash when removing and adding instances of
                        # grease pencil curves
                        self._gpencil_transform_updated(obj)
                    else:
                        if ob.type == 'EMPTY' and ob.is_instancer:
                            _check_empty(ob)
                        else:
                            update_instances.append(obj.id.original)

                rman_sg_node = self.rman_scene.rman_objects.get(obj.id.original, None)
                if rman_sg_node and rman_sg_node.sg_node:
                    # double check hidden value
                    # grab the object from bpy.data, because the depsgraph doesn't seem
                    # to get the updated value
                    ob_data = bpy.data.objects.get(ob.name, ob)
                    with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene): 
                        if shadergraph_utils.is_rman_light(ob_data, include_light_filters=False): #rman_type == 'LIGHT':
                            self._update_light_visibility(rman_sg_node, ob_data)
                        else:
                            rman_sg_node.sg_node.SetHidden(ob_data.hide_get())

            elif isinstance(obj.id, bpy.types.Collection):
                rfb_log().debug("Collection updated")
                if not new_objs:
                    do_delete = True
                
                # mark all objects in a collection that is part of a dupli_group
                # as needing their instances updated
                # the collection could have been updated with new objects
                # FIXME: like grease pencil above we seem to crash when removing and adding instances 
                # of curves, we need to figure out what's going on
                if obj.id.users_dupli_group:
                    for o in obj.id.all_objects:
                        update_instances.append(o.original)

        # call txmake all in case of new textures
        texture_utils.get_txmanager().txmake_all(blocking=False)                      

        # if object was marked as updated geometry, updated any attached particle systems
        # if the particle system is an instancer, we mark the instanced object as needing
        # its instances updated
        for ob in updated_geo:
            rman_type = object_utils._detect_primitive_(ob)
            rman_sg_node = self.rman_scene.rman_objects.get(ob, None)
            if rman_type not in ['MESH', 'POINTS']:
                continue
            with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
                ob_eval = ob.evaluated_get(self.rman_scene.depsgraph)

                if not rman_sg_node.rman_sg_particle_group_node:
                    db_name = rman_sg_node.db_name
                    particles_group_db = '%s_particles_group' % db_name
                    rman_sg_node.rman_sg_particle_group_node = self.rman_scene.rman_translators['GROUP'].export(None, particles_group_db) 
                    rman_sg_node.sg_node.AddChild(rman_sg_node.rman_sg_particle_group_node.sg_node) 

                rman_sg_node.rman_sg_particle_group_node.sg_node.RemoveAllChildren()

                for psys in ob_eval.particle_systems:
                    psys_translator = self.rman_scene.rman_translators[psys.settings.type]
                    if psys.settings.type == 'HAIR' and psys.settings.render_type == 'PATH':
                        hair_db_name = object_utils.get_db_name(ob_eval, psys=psys)                                        
                        rman_sg_hair_node = psys_translator.export(ob_eval, psys, hair_db_name)
                        psys_translator.update(ob_eval, psys, rman_sg_hair_node)
                        if rman_sg_hair_node.sg_node:
                            rman_sg_node.rman_sg_particle_group_node.sg_node.AddChild(rman_sg_hair_node.sg_node) 
                        self.rman_scene.rman_particles[psys.settings.original] = rman_sg_hair_node
                    elif psys.settings.type == 'EMITTER':                        
                        rman_sg_particles_node = self.rman_scene.rman_particles.get(psys.settings.original, None)
                        if psys.settings.render_type != 'OBJECT':
                            psys_db_name = object_utils.get_db_name(ob_eval, psys=psys)
                            rman_sg_particles_node = psys_translator.export(ob_eval, psys, psys_db_name)
                            if rman_sg_particles_node.sg_node:
                                rman_sg_node.rman_sg_particle_group_node.sg_node.AddChild(rman_sg_particles_node.sg_node)  
                            self.rman_scene.rman_particles[psys.settings.original] = rman_sg_particles_node 
                            psys_translator.update(ob_eval, psys, rman_sg_particles_node)
                        elif psys.settings.render_type == 'OBJECT':
                            if rman_sg_particles_node:
                                psys_translator.clear_children(ob_eval, psys, rman_sg_particles_node)
                            inst_ob = psys.settings.instance_object 
                            if inst_ob:
                                update_instances.append(inst_ob.original)

        # add new objs:
        if new_objs:
            with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene): 
                rfb_log().debug("Adding new objects:")
                self.rman_scene.export_data_blocks(new_objs)

                self.rman_scene.scene_any_lights = self.rman_scene._scene_has_lights()
                if self.rman_scene.scene_any_lights:
                    self.rman_scene.default_light.SetHidden(1)        

        # delete any objects, if necessary    
        if do_delete:
            rfb_log().debug("Deleting objects")
            with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
                keys = [k for k in self.rman_scene.rman_objects.keys()]
                for obj in keys:
                    try:
                        ob = self.rman_scene.bl_scene.objects.get(obj.name_full, None)
                        if ob:
                            continue
                    except:
                        pass
     
                    rman_sg_node = self.rman_scene.rman_objects.get(obj, None)
                    if rman_sg_node:                        
                        for k,v in rman_sg_node.instances.items():
                            if v.sg_node:
                                self.rman_scene.sg_scene.DeleteDagNode(v.sg_node)    
                        rman_sg_node.instances.clear()             

                        # For now, don't delete the geometry itself
                        # there may be a collection instance still referencing the geo

                        # self.rman_scene.sg_scene.DeleteDagNode(rman_sg_node.sg_node)                     
                        # del self.rman_scene.rman_objects[obj]

                        # We just deleted a light filter. We need to tell all lights
                        # associated with this light filter to update
                        if isinstance(rman_sg_node, RmanSgLightFilter):
                            for light_ob in rman_sg_node.lights_list:
                                light_key = object_utils.get_db_name(light_ob, rman_type='LIGHT')
                                rman_sg_light = self.rman_scene.rman_objects.get(light_ob.original, None)
                                if rman_sg_light:
                                    self.rman_scene.rman_translators['LIGHT'].update_light_filters(light_ob, rman_sg_light)                                
                        try:
                            self.rman_scene.processed_obs.remove(obj)
                        except ValueError:
                            rfb_log().debug("Obj not in self.rman_scene.processed_obs")
                            pass

                    if self.rman_scene.render_default_light:
                        self.rman_scene.scene_any_lights = self.rman_scene._scene_has_lights()     
                        if not self.rman_scene.scene_any_lights:
                            self.rman_scene.default_light.SetHidden(0)

        # update instances
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            # delete all instances for each object in the
            # update_instances list
            # even if it's a simple a transform, we still have to delete all
            # the instances as this could be coming from a particle system where
            # some instances aren't there any more
            for ob in update_instances:
                rfb_log().debug("Deleting instances of: %s" % ob.name)
                rman_sg_node = self.rman_scene.rman_objects.get(ob, None) 
                if rman_sg_node:
                    for k,rman_sg_group in rman_sg_node.instances.items():
                        self.rman_scene.get_root_sg_node().RemoveChild(rman_sg_group.sg_node)
                    rman_sg_node.instances.clear()         
            parent = None
            for ob_inst in self.rman_scene.depsgraph.object_instances: 
                if ob_inst.is_instance:
                    ob = ob_inst.instance_object
                    parent = ob_inst.parent
                else:
                    ob = ob_inst.object

                if ob.original not in update_instances:
                    continue

                rfb_log().debug("Re-emit instance: %s" % ob.name)
                self.rman_scene._export_instance(ob_inst)                            

    def update_cropwindow(self, cropwindow=None):
        if cropwindow:
            with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene): 
                options = self.rman_scene.sg_scene.GetOptions()
                options.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_CropWindow, cropwindow, 4)  
                self.rman_scene.sg_scene.SetOptions(options)           

    def update_integrator(self, context):
        if context:
            self.rman_scene.bl_scene = context.scene
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            self.rman_scene.export_integrator() 
            self.rman_scene.export_viewport_stats()

    def update_viewport_integrator(self, context, integrator):
        self.rman_scene.bl_scene = context.scene
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            integrator_sg = self.rman_scene.rman.SGManager.RixSGShader("Integrator", integrator, "integrator")       
            self.rman_scene.sg_scene.SetIntegrator(integrator_sg)     
            self.rman_scene.export_viewport_stats(integrator=integrator)  

    def update_viewport_res_mult(self, context):
        if not self.rman_scene.is_viewport_render:
            return         
        if context:
            self.rman_scene.context = context
            self.rman_scene.bl_scene = context.scene            
        rman_sg_camera = self.rman_scene.main_camera
        translator = self.rman_scene.rman_translators['CAMERA']
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            translator.update_viewport_resolution(rman_sg_camera)
            translator.update_transform(None, rman_sg_camera)
            self.rman_scene.export_viewport_stats()                  

    def update_hider_options(self, context):
        self.rman_scene.bl_scene = context.scene
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            self.rman_scene.export_hider()
            self.rman_scene.export_viewport_stats()
 
    def update_material(self, mat):
        rman_sg_material = self.rman_scene.rman_materials.get(mat.original, None)
        if not rman_sg_material:
            return
        translator = self.rman_scene.rman_translators["MATERIAL"]     
        has_meshlight = rman_sg_material.has_meshlight   
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):                  
            translator.update(mat, rman_sg_material)

        if has_meshlight != rman_sg_material.has_meshlight:
            # we're dealing with a mesh light
            self.rman_scene.depsgraph = bpy.context.evaluated_depsgraph_get()
            self._mesh_light_update(mat)    

    def update_light(self, ob):
        rman_sg_light = self.rman_scene.rman_objects.get(ob.original, None)
        if not rman_sg_light:
            return
        translator = self.rman_scene.rman_translators["LIGHT"]        
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            translator.update(ob, rman_sg_light)         

    def update_light_filter(self, ob):
        rman_sg_node = self.rman_scene.rman_objects.get(ob.original, None)
        if not rman_sg_node:
            return

        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            self.rman_scene.rman_translators['LIGHTFILTER'].update(ob, rman_sg_node)
            for light_ob in rman_sg_node.lights_list:
                light_key = object_utils.get_db_name(light_ob, rman_type='LIGHT')
                rman_sg_light = self.rman_scene.rman_objects.get(light_ob.original, None)
                if rman_sg_light:
                    self.rman_scene.rman_translators['LIGHT'].update_light_filters(light_ob, rman_sg_light)                    

    def update_solo_light(self, context):
        # solo light has changed
        self.rman_scene.bl_scene = context.scene
        self.rman_scene.scene_solo_light = self.rman_scene.bl_scene.renderman.solo_light
                    
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):            
            for light_ob in scene_utils.get_all_lights(self.rman_scene.bl_scene, include_light_filters=False):
                rman_sg_node = self.rman_scene.rman_objects.get(light_ob.original, None)
                if not rman_sg_node:
                    continue
                rm = light_ob.renderman
                if not rm:
                    continue

                if rm.solo:
                    rman_sg_node.sg_node.SetHidden(0)
                else:
                    rman_sg_node.sg_node.SetHidden(1)  

    def update_un_solo_light(self, context):
        # solo light has changed
        self.rman_scene.bl_scene = context.scene
        self.rman_scene.scene_solo_light = self.rman_scene.bl_scene.renderman.solo_light
                    
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):                                               
            for light_ob in scene_utils.get_all_lights(self.rman_scene.bl_scene, include_light_filters=False):
                rman_sg_node = self.rman_scene.rman_objects.get(light_ob.original, None)
                if not rman_sg_node:
                    continue
                rm = light_ob.renderman
                if not rm:
                    continue         
                rman_sg_node.sg_node.SetHidden(light_ob.hide_get())         

    def update_viewport_chan(self, context, chan_name):
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            self.rman_scene.export_samplefilters(sel_chan_name=chan_name)