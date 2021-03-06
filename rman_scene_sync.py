# utils
from .rfb_utils import object_utils
from .rfb_utils import transform_utils
from .rfb_utils import texture_utils
from .rfb_utils import scene_utils
from .rfb_utils import shadergraph_utils

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

        self.update_instances = set() # set of objects we need to update their instances
        self.update_particle_systems = set() # set of objects that need their particle systems updated

    @property
    def sg_scene(self):
        return self.__sg_scene

    @sg_scene.setter
    def sg_scene(self, sg_scene):
        self.__sg_scene = sg_scene          

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
                    translator.update_viewport_cam(ob, rman_sg_camera, force_update=True)
                translator.update_transform(None, rman_sg_camera)
            else:
                translator.update_transform(camera, rman_sg_camera)  

    def _scene_updated(self):
        if self.rman_scene.bl_frame_current != self.rman_scene.bl_scene.frame_current:
            # frame changed, update any materials and objects that 
            # are marked as frame sensitive
            self.rman_scene.bl_frame_current = self.rman_scene.bl_scene.frame_current
            material_translator = self.rman_scene.rman_translators["MATERIAL"]

            with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):  
                for mat in bpy.data.materials:   
                    db_name = object_utils.get_db_name(mat)  
                    rman_sg_material = self.rman_scene.rman_materials.get(mat.original, None)
                    if rman_sg_material and rman_sg_material.is_frame_sensitive:
                        material_translator.update(mat, rman_sg_material)

                for o in bpy.data.objects:
                    rman_type = object_utils._detect_primitive_(o)
                    rman_sg_node = self.rman_scene.rman_objects.get(o.original, None)
                    if not rman_sg_node:
                        continue
                    translator = self.rman_scene.rman_translators.get(rman_type, None)
                    if translator and rman_sg_node.is_frame_sensitive:
                        translator.update(o, rman_sg_node)

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

    def _material_updated(self, obj, updated_obs):
        mat = obj.id
        rman_sg_material = self.rman_scene.rman_materials.get(mat.original, None)
        translator = self.rman_scene.rman_translators["MATERIAL"]              
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):   
            mat = obj.id              
            if not rman_sg_material:
                rfb_log().debug("New material: %s" % mat.name)
                db_name = object_utils.get_db_name(mat)
                rman_sg_material = translator.export(mat, db_name)
                self.rman_scene.rman_materials[mat.original] = rman_sg_material
                for ob in updated_obs:
                    rman_sg_node = self.rman_scene.rman_objects[ob]
                    for k,rman_sg_group in rman_sg_node.instances.items():
                        rman_sg_group.sg_node.SetMaterial(rman_sg_material.sg_node) 
                
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
                    ob = ob.original
                    rman_camera_translator = self.rman_scene.rman_translators['CAMERA']
                    if not self.rman_scene.is_viewport_render:
                        rman_camera_translator.update(ob, rman_sg_node)  
                    else:
                        rman_camera_translator.update_viewport_cam(ob, rman_sg_node, force_update=True)       

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
                translator.export_object_primvars(ob, rman_sg_node)
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
        ## FIXME: this function is waaayyy too big and is doing too much stuff

        new_objs = set() # set of new objects
        new_cams = set() # set of new cameras
        self.update_instances = set()
        self.update_particle_systems = set()

        do_delete = False # whether or not we need to do an object deletion
        do_add = False # whether or not we need to add an object
        num_instances_changed = False # if the number of instances has changed since the last update
        particle_system_updated = False # if a particle system has updated
        org_num_instances = self.rman_scene.num_object_instances # the number of instances previously
        
        self.rman_scene.depsgraph = depsgraph
        self.rman_scene.bl_scene = depsgraph.scene
        self.rman_scene.context = context        

        # Running set of transform objects. We need this in case a new material
        # is added and attached to objects. For some reason, Blender tells us objects
        # have been updated before we are told a material has been updated
        update_transform_obs = set() 
        
        # Particle system was updated        
        if depsgraph.id_type_updated('PARTICLE'):
            particle_system_updated = True

        # Check the number of instances. If we differ, an object may have been
        # added or deleted
        if self.rman_scene.num_object_instances != len(depsgraph.object_instances):
            num_instances_changed = True
            if self.rman_scene.num_object_instances > len(depsgraph.object_instances):
                do_delete = True
            else:
                do_add = True
            self.rman_scene.num_object_instances = len(depsgraph.object_instances)
            
        def _check_empty(ob, rman_sg_node=None):
            # check the objects in the collection
            # if they need updating
            if ob.is_instancer:
                rfb_log().debug("Check empty instancer: %s" % obj.id.name)
                collection = ob.instance_collection
                if collection:
                    if num_instances_changed:
                        for col_obj in collection.all_objects:
                            if col_obj.original not in self.rman_scene.rman_objects:
                                new_objs.add(col_obj.original)
                            self.update_instances.add(col_obj.original) 
                            self.update_particle_systems.add(col_obj.original)           
                    else:
                        collection_objs = collection.all_objects.keys()
                        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
                            rman_group_translator = self.rman_scene.rman_translators['GROUP']
                            for ob_inst in self.rman_scene.depsgraph.object_instances: 
                                if ob_inst.is_instance:
                                    id = ob_inst.instance_object
                                else:
                                    id = ob_inst.object

                                if id.original.name not in collection_objs:
                                    continue

                                rman_sg_node = self.rman_scene.rman_objects.get(id.original, None)
                                group_db_name = object_utils.get_group_db_name(ob_inst) 
                                rman_sg_group = rman_sg_node.instances.get(group_db_name, None)
                                if rman_sg_group:
                                    rman_group_translator.update_transform(ob_inst, rman_sg_group)  
                                self.update_particle_systems.add(id.original)       
            else:
                translator = self.rman_scene.rman_translators['EMPTY']
                with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
                    translator.export_transform(ob, rman_sg_node.sg_node)
                    if ob.renderman.export_as_coordsys:
                        self.rman_scene.get_root_sg_node().AddCoordinateSystem(rman_sg_node.sg_node)
                    else:
                        self.rman_scene.get_root_sg_node().RemoveCoordinateSystem(rman_sg_node.sg_node)                                                


        rfb_log().debug("------Start update scene--------")
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
                self._material_updated(obj, update_transform_obs)    
              
            elif isinstance(obj.id, bpy.types.Object):

                rman_type = object_utils._detect_primitive_(ob)
                # grab the object from bpy.data, because the depsgraph doesn't seem
                # to get the updated viewport hidden value                
                ob_data = bpy.data.objects.get(ob.name, ob)
                rman_sg_node = self.rman_scene.rman_objects.get(obj.id.original, None)
                is_hidden = ob_data.hide_get()
                if do_add and not rman_sg_node:
                    rman_type = object_utils._detect_primitive_(ob_data)
                    if ob_data.hide_get():
                        # don't add if this hidden in the viewport
                        continue                    
                    if ob.type == 'CAMERA': 
                        new_cams.add(obj.id.original)
                    else:
                        if rman_type == 'EMPTY' and ob.is_instancer:
                            _check_empty(ob)
                        else:
                            if rman_type == 'LIGHT':
                                # double check if this light is an rman light
                                # for now, we don't support adding Blender lights in IPR
                                #
                                # we can also get to this point when adding new rman lights because
                                # blender will tell us a new light has been added before we've had to chance
                                # to modify its properties to be an rman light, so we don't want to
                                # add this light just yet.
                                if not shadergraph_utils.is_rman_light(ob):
                                    self.rman_scene.num_object_instances = org_num_instances
                                    rfb_log().debug("------End update scene----------")
                                    return
                            elif rman_type == 'EMPTY':
                                # same issue can also happen with empty
                                # we have not been able to tag our types before Blender
                                # tells us an empty has been added
                                self.rman_scene.num_object_instances = org_num_instances
                                rfb_log().debug("------End update scene----------")
                                return
                            rfb_log().debug("New object added: %s" % obj.id.name)                                    
                            new_objs.add(obj.id.original)
                            self.update_instances.add(obj.id.original)
                    continue      

                if rman_sg_node and rman_sg_node.sg_node:
                    # double check hidden value
                    if rman_sg_node.is_hidden != is_hidden:
                        do_delete = False
                        rman_sg_node.is_hidden = is_hidden
                        if shadergraph_utils.is_rman_light(ob_data, include_light_filters=False):
                            with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene): 
                                rman_sg_node.sg_node.GetHidden() != int(is_hidden)
                                self._update_light_visibility(rman_sg_node, ob_data)
                        else:
                            if rman_type == 'EMPTY' and ob.is_instancer:
                                _check_empty(ob)
                            else:         
                                self.update_instances.add(obj.id.original)        
                                self.update_particle_systems.add(obj.id.original)   
                else:
                    continue        

                if obj.is_updated_transform:
                    rfb_log().debug("Transform updated: %s" % obj.id.name)
                    if ob.type in ['CAMERA']:
                        # we deal with main camera transforms in view_draw
                        rman_sg_camera = self.rman_scene.rman_cameras[ob.original]
                        if rman_sg_camera == self.rman_scene.main_camera:
                            continue
                        translator = self.rman_scene.rman_translators['CAMERA']
                        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
                            translator._update_render_cam_transform(ob, rman_sg_camera)                        
                        continue
                    
                    if rman_type == 'LIGHTFILTER':
                        self._light_filter_transform_updated(obj)
                    elif rman_type == 'GPENCIL':
                        # FIXME: we shouldn't handle this specifically, but we seem to be
                        # hitting a prman crash when removing and adding instances of
                        # grease pencil curves
                        self._gpencil_transform_updated(obj)
                    elif rman_type == 'EMPTY':
                        _check_empty(ob, rman_sg_node)
                    elif num_instances_changed:
                        self.update_instances.add(obj.id.original)                  
                    else:
                        update_transform_obs.add(obj.id.original)
                        # this is a simple transform
                        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
                            rman_group_translator = self.rman_scene.rman_translators['GROUP']
                            for ob_inst in self.rman_scene.depsgraph.object_instances: 
                                if ob_inst.is_instance:
                                    id = ob_inst.instance_object
                                else:
                                    id = ob_inst.object

                                if id.original != ob.original:
                                    continue
                                group_db_name = object_utils.get_group_db_name(ob_inst) 
                                rman_sg_group = rman_sg_node.instances.get(group_db_name, None)
                                if rman_sg_group:
                                    rman_group_translator.update_transform(ob_inst, rman_sg_group)

                elif obj.is_updated_geometry:
                    if is_hidden:
                        # don't update if this is hidden
                        continue
                    if num_instances_changed:
                        self.update_particle_systems.add(obj.id.original)                   
                    elif not particle_system_updated:
                        rfb_log().debug("Object updated: %s" % obj.id.name)
                        self._obj_geometry_updated(obj)   
                    elif obj.id.type not in ['CAMERA']:    
                        rfb_log().debug("Object's Particle Systems updated: %s" % obj.id.name)    
                        self.update_particle_systems.add(obj.id.original)                            

            elif isinstance(obj.id, bpy.types.Collection):
                if not do_delete:
                    continue
                
                rfb_log().debug("Collection updated")
                # mark all objects in a collection
                # as needing their instances updated
                # the collection could have been updated with new objects
                # FIXME: like grease pencil above we seem to crash when removing and adding instances 
                # of curves, we need to figure out what's going on
                for o in obj.id.all_objects:
                    if o.type in ('ARMATURE', 'CURVE', 'CAMERA'):
                        continue
                    self.update_instances.add(o.original)

        # call txmake all in case of new textures
        texture_utils.get_txmanager().txmake_all(blocking=False)                      

        # loop over any objects that were marked their particle systems needing updated
        # if the particle system is an instancer, we mark the instanced object as needing
        # its instances updated
        for ob in self.update_particle_systems:
            rman_type = object_utils._detect_primitive_(ob)
            rman_sg_node = self.rman_scene.rman_objects.get(ob, None)
            if rman_type not in ['MESH', 'POINTS']:
                continue
            ob_eval = ob.evaluated_get(self.rman_scene.depsgraph)
            rfb_log().debug("Find particle systems for: %s" % ob.name)

            with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
                
                if not rman_sg_node.rman_sg_particle_group_node:
                    db_name = rman_sg_node.db_name
                    particles_group_db = ''
                    rman_sg_node.rman_sg_particle_group_node = self.rman_scene.rman_translators['GROUP'].export(None, particles_group_db) 
                    rman_sg_node.sg_node.AddChild(rman_sg_node.rman_sg_particle_group_node.sg_node) 

                rman_sg_node.rman_sg_particle_group_node.sg_node.RemoveAllChildren()
                psys_translator = self.rman_scene.rman_translators['PARTICLES']
                if len(ob_eval.particle_systems) < 1:
                    continue

                for psys in ob_eval.particle_systems:
                    if psys.settings.render_type == 'OBJECT':
                        # this particle system is a instancer, add the instanced object
                        # to the self.update_instances list
                        inst_ob = psys.settings.instance_object 
                        if inst_ob:
                            self.update_instances.add(inst_ob.original)      
                        continue

                    ob_psys = self.rman_scene.rman_particles.get(ob_eval.original, dict())
                    rman_sg_particles = ob_psys.get(psys.settings.original, None)
                    if not rman_sg_particles:
                        psys_db_name = '%s' % psys.name
                        rman_sg_particles = psys_translator.export(ob, psys, psys_db_name)
                        if not rman_sg_particles:
                            continue
                    psys_translator.update(ob, psys, rman_sg_particles)
                    ob_psys[psys.settings.original] = rman_sg_particles
                    self.rman_scene.rman_particles[ob.original] = ob_psys          
                    rman_sg_node.rman_sg_particle_group_node.sg_node.AddChild(rman_sg_particles.sg_node)                 
                    
        # add new objs:
        if new_objs:
            with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene): 
                rfb_log().debug("Adding new objects:")
                self.rman_scene.export_data_blocks(new_objs)

                self.rman_scene.scene_any_lights = self.rman_scene._scene_has_lights()
                if self.rman_scene.scene_any_lights:
                    self.rman_scene.default_light.SetHidden(1)    

        # update instances
        if self.update_instances:
            with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
                # delete all instances for each object in the
                # self.update_instances list
                #
                # even if it's a simple a transform, we still have to delete all
                # the instances as this could be part of a particle system, or
                # the object is instanced at the vertices/faces of another object
                #
                # in these cases, Blender only seems to tell us that the object has
                # transformed; it does not tell us whether instances of the object
                # has been removed

                rfb_log().debug("Deleting instances")
                for ob in self.update_instances:
                    #rfb_log().debug("Deleting instances of: %s" % ob.name)
                    rman_sg_node = self.rman_scene.rman_objects.get(ob, None) 
                    if rman_sg_node:
                        for k,rman_sg_group in rman_sg_node.instances.items():
                            if ob.parent and object_utils._detect_primitive_(ob.parent) == 'EMPTY':
                                rman_empty_node = self.rman_scene.rman_objects.get(ob.parent.original)
                                rman_empty_node.sg_node.RemoveChild(rman_sg_group.sg_node)
                            else:
                                self.rman_scene.get_root_sg_node().RemoveChild(rman_sg_group.sg_node)                            
                        rman_sg_node.instances.clear()         

                rfb_log().debug("Re-emit instances")
                for ob_inst in self.rman_scene.depsgraph.object_instances: 
                    if ob_inst.is_instance:
                        ob = ob_inst.instance_object
                    else:
                        ob = ob_inst.object

                    if ob.original not in self.update_instances:
                        continue

                    self.rman_scene._export_instance(ob_inst)                              

        # delete any objects, if necessary    
        if do_delete:
            self.delete_objects()
 
        rfb_log().debug("------End update scene----------")

    def delete_objects(self):
        rfb_log().debug("Deleting objects")
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            keys = [k for k in self.rman_scene.rman_objects.keys()]
            for obj in keys:
                try:
                    ob = self.rman_scene.bl_scene.objects.get(obj.name_full, None)
                    if ob:
                        continue
                except Exception as e:
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
                    del self.rman_scene.rman_objects[obj]

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

    def update_cropwindow(self, cropwindow=None):
        if not self.rman_render.rman_interactive_running:
            return
        if cropwindow:
            with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene): 
                options = self.rman_scene.sg_scene.GetOptions()
                options.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_CropWindow, cropwindow, 4)  
                self.rman_scene.sg_scene.SetOptions(options)           

    def update_integrator(self, context):
        if not self.rman_render.rman_interactive_running:
            return        
        if context:
            self.rman_scene.bl_scene = context.scene
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            self.rman_scene.export_integrator() 
            self.rman_scene.export_viewport_stats()

    def update_viewport_integrator(self, context, integrator):
        if not self.rman_render.rman_interactive_running:
            return        
        self.rman_scene.bl_scene = context.scene
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            integrator_sg = self.rman_scene.rman.SGManager.RixSGShader("Integrator", integrator, "integrator")       
            self.rman_scene.sg_scene.SetIntegrator(integrator_sg)     
            self.rman_scene.export_viewport_stats(integrator=integrator)  

    def update_viewport_res_mult(self, context):
        if not self.rman_render.rman_interactive_running:
            return        
        if not self.rman_scene.is_viewport_render:
            return         
        if context:
            self.rman_scene.context = context
            self.rman_scene.bl_scene = context.scene    
            self.rman_scene.viewport_render_res_mult = float(context.scene.renderman.viewport_render_res_mult)
        rman_sg_camera = self.rman_scene.main_camera
        translator = self.rman_scene.rman_translators['CAMERA']
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            translator.update_viewport_resolution(rman_sg_camera)
            translator.update_transform(None, rman_sg_camera)
            self.rman_scene.export_viewport_stats()                  

    def update_global_options(self, context):
        if not self.rman_render.rman_interactive_running:
            return        
        self.rman_scene.bl_scene = context.scene
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            self.rman_scene.export_global_options()            
            self.rman_scene.export_hider()
            self.rman_scene.export_viewport_stats()

    def update_root_node_func(self, context):
        if not self.rman_render.rman_interactive_running:
            return        
        self.rman_scene.bl_scene = context.scene
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            self.rman_scene.export_root_sg_node()         
 
    def update_material(self, mat):
        if not self.rman_render.rman_interactive_running:
            return        
        rman_sg_material = self.rman_scene.rman_materials.get(mat.original, None)
        if not rman_sg_material:
            return
        translator = self.rman_scene.rman_translators["MATERIAL"]     
        has_meshlight = rman_sg_material.has_meshlight   
        rfb_log().debug("Manual material update called for: %s." % mat.name)
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):                  
            translator.update(mat, rman_sg_material)

        if has_meshlight != rman_sg_material.has_meshlight:
            # we're dealing with a mesh light
            rfb_log().debug("Manually calling mesh_light_update")
            self.rman_scene.depsgraph = bpy.context.evaluated_depsgraph_get()
            self._mesh_light_update(mat)    

    def update_light(self, ob):
        if not self.rman_render.rman_interactive_running:
            return        
        rman_sg_light = self.rman_scene.rman_objects.get(ob.original, None)
        if not rman_sg_light:
            return
        translator = self.rman_scene.rman_translators["LIGHT"]        
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            translator.update(ob, rman_sg_light)         

    def update_light_filter(self, ob):
        if not self.rman_render.rman_interactive_running:
            return        
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
        if not self.rman_render.rman_interactive_running:
            return        
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
        if not self.rman_render.rman_interactive_running:
            return        
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
        if not self.rman_render.rman_interactive_running:
            return        
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            self.rman_scene.export_samplefilters(sel_chan_name=chan_name)

    def update_displays(self, context):
        if not self.rman_render.rman_interactive_running:
            return        
        self.rman_scene.bl_scene = context.scene    
        self.rman_scene._find_renderman_layer()
        with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene):
            self.rman_scene.export_displays()         

    def texture_updated(self, nodeID):
        if not self.rman_render.rman_interactive_running:
            return        
        if nodeID == '':
            return
        tokens = nodeID.split('|')
        if len(tokens) < 3:
            return
        node_name,param,ob_name = tokens

        node, ob = scene_utils.find_node_by_name(node_name, ob_name)
        if node == None or ob == None:
            return

        ob_type = type(ob)

        if ob_type == bpy.types.Material:
            self.update_material(ob)
            return
        elif ob_type == bpy.types.World:
            ob.update_tag()   
        else:
            # light, lightfilters, and cameras
            ob.update_tag(refresh={'DATA'})