from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty,  CollectionProperty, PointerProperty
from ..rman_utils import string_utils
from ..rfb_logger import rfb_log
from ..rman_utils import shadergraph_utils

import bpy

def return_empty_list(label=''):
    items = []
    items.append(('0', label, '', '', 0))
    return items  

class COLLECTION_OT_add_remove(bpy.types.Operator):
    bl_label = "Add or Remove Paths"
    bl_idname = "collection.add_remove"

    action: EnumProperty(
        name="Action",
        description="Either add or remove properties",
        items=[('ADD', 'Add', ''),
               ('REMOVE', 'Remove', '')],
        default='ADD')
    context: StringProperty(
        name="Context",
        description="Name of context member to find renderman pointer in",
        default="")
    collection: StringProperty(
        name="Collection",
        description="The collection to manipulate",
        default="")
    collection_index: StringProperty(
        name="Index Property",
        description="The property used as a collection index",
        default="")
    defaultname: StringProperty(
        name="Default Name",
        description="Default name to give this collection item",
        default="")

    def invoke(self, context, event):
        scene = context.scene
        id = string_utils.getattr_recursive(context, self.properties.context)
        rm = id.renderman if hasattr(id, 'renderman') else id

        prop_coll = self.properties.collection
        coll_idx = self.properties.collection_index

        collection = getattr(rm, prop_coll)
        index = getattr(rm, coll_idx)

        if self.properties.action == 'ADD':
            dflt_name = self.properties.defaultname
            for coll in collection:
                if coll.name == dflt_name:
                    dflt_name = '%s_NEW' % dflt_name            
            collection.add()
            index += 1
            setattr(rm, coll_idx, index)
            collection[-1].name = dflt_name

        elif self.properties.action == 'REMOVE':
            collection.remove(index)
            setattr(rm, coll_idx, index - 1)

        return {'FINISHED'}

class COLLECTION_OT_meshlight_lightfilter_add_remove(bpy.types.Operator):
    bl_label = "Add Light Filter to Mesh Light"
    bl_idname = "renderman.add_meshlight_lightfilter"

    action: EnumProperty(
        name="Action",
        description="Either add or remove properties",
        items=[('ADD', 'Add', ''),
               ('REMOVE', 'Remove', '')],
        default='ADD')
    context: StringProperty(
        name="Context",
        description="Name of context member to find renderman pointer in",
        default="")
    collection: StringProperty(
        name="Collection",
        description="The collection to manipulate",
        default="")
    collection_index: StringProperty(
        name="Index Property",
        description="The property used as a collection index",
        default="")
    defaultname: StringProperty(
        name="Default Name",
        description="Default name to give this collection item",
        default="")    

    def invoke(self, context, event):
        scene = context.scene
        mat = context.material
        rm = mat.renderman_light

        prop_coll = self.properties.collection
        coll_idx = self.properties.collection_index

        collection = getattr(rm, prop_coll)
        index = getattr(rm, coll_idx)

        if self.properties.action == 'ADD':
            dflt_name = self.properties.defaultname
            for coll in collection:
                if coll.name == dflt_name:
                    dflt_name = '%s_NEW' % dflt_name
            collection.add()
            index += 1
            setattr(rm, coll_idx, index)
            collection[-1].name = dflt_name

        elif self.properties.action == 'REMOVE':
            collection.remove(index)
            setattr(rm, coll_idx, index - 1)

        return {'FINISHED'}               


class COLLECTION_OT_object_groups_add_remove(bpy.types.Operator):
    bl_label = "Add or Remove Object Groups"
    bl_idname = "renderman.add_remove_object_groups"

    action: EnumProperty(
        name="Action",
        description="Either add or remove properties",
        items=[('ADD', 'Add', ''),
               ('REMOVE', 'Remove', '')],
        default='ADD')
    context: StringProperty(
        name="Context",
        description="Name of context member to find renderman pointer in",
        default="")
    collection: StringProperty(
        name="Collection",
        description="The collection to manipulate",
        default="")
    collection_index: StringProperty(
        name="Index Property",
        description="The property used as a collection index",
        default="")
    defaultname: StringProperty(
        name="Default Name",
        description="Default name to give this collection item",
        default="")

    def invoke(self, context, event):
        scene = context.scene
        id = string_utils.getattr_recursive(context, self.properties.context)
        rm = id.renderman if hasattr(id, 'renderman') else id

        prop_coll = self.properties.collection
        coll_idx = self.properties.collection_index

        collection = getattr(rm, prop_coll)
        index = getattr(rm, coll_idx)

        if self.properties.action == 'ADD':
            dflt_name = self.properties.defaultname
            for coll in collection:
                if coll.name == dflt_name:
                    dflt_name = '%s_NEW' % dflt_name
            collection.add()
            index += 1
            setattr(rm, coll_idx, index)
            collection[-1].name = dflt_name

        elif self.properties.action == 'REMOVE':
            group = collection[index]            
            # get a list of all objects in this group
            ob_list = [member.ob_pointer for member in group.members]
            collection.remove(index)
            setattr(rm, coll_idx, index - 1)

            # now tell each object to update
            for ob in ob_list:
                ob.update_tag(refresh={'OBJECT'})

        return {'FINISHED'}               

class PRMAN_OT_add_multilayer_list(bpy.types.Operator):
    bl_idname = 'renderman.add_multilayer_list'
    bl_label = 'Add multilayer list'

    def execute(self, context):
        scene = context.scene
        scene.renderman.multilayer_lists.add()
        active_layer = context.view_layer
        scene.renderman.multilayer_lists[-1].render_layer = active_layer.name
        return {'FINISHED'}

class PRMAN_OT_convert_mixer_group_to_light_group(bpy.types.Operator):
    bl_idname = 'renderman.convert_mixer_group_to_light_group'
    bl_label = 'Convert to Light Mixer Group' 
    bl_description = 'Convert the currently selected light mixer group to a light group. If the lights in this mixer group were already in a light group, this will override.'

    group_index: IntProperty(name="group_index", default=-1)

    def execute(self, context):
        if self.properties.group_index < 0:
            return {'FINISHED'}

        scene = context.scene
        mixer_group_index = self.properties.group_index

        mixer_groups = scene.renderman.light_mixer_groups
        mixer_group = mixer_groups[mixer_group_index]

        for member in mixer_group.members:
            light_ob = member.light_ob
            light_shader = shadergraph_utils.get_light_node(light_ob, include_light_filters=False)
            light_shader.lightGroup = mixer_group.name
            light_ob.update_tag(refresh={'DATA'})

        return {'FINISHED'}       


class PRMAN_OT_add_light_to_light_mixer_group(bpy.types.Operator):
    bl_idname = 'renderman.add_light_to_light_mixer_group'
    bl_label = 'Add Selected Light to Light Mixer Group' 

    group_index: IntProperty(default=0)
    do_scene_selected: BoolProperty(name="do_scene_selected", default=False)  
    open_editor: BoolProperty(default=False)  

    def add_selected(self, context):
        scene = context.scene
        group_index = scene.renderman.light_mixer_groups_index
        object_groups = scene.renderman.light_mixer_groups
        object_group = object_groups[group_index]        
        ob = getattr(context, "selected_light", None)
        if not ob:
            return {'FINISHED'}

        do_add = True

        for member in object_group.members:
            if ob == member.light_ob:
                do_add = False
                break                

        if do_add:
            ob_in_group = object_group.members.add()
            ob_in_group.name = ob.name
            ob_in_group.light_ob = ob       

            op = getattr(context, 'op_ptr')
            if op:
                op.selected_light_name = '0'              
            
    def add_scene_selected(self, context):
        scene = context.scene
        group_index = self.group_index
        if not hasattr(context, 'selected_objects'):
            return {'FINISHED'}        
        
        object_groups = scene.renderman.light_mixer_groups
        object_group = object_groups[group_index]
        for ob in context.selected_objects:
            if not shadergraph_utils.is_rman_light(ob):
                continue
            do_add = True
            for member in object_group.members:
                if ob == member.light_ob:
                    do_add = False
                    break                

            if do_add:
                ob_in_group = object_group.members.add()
                ob_in_group.name = ob.name
                ob_in_group.light_ob = ob          

    def execute(self, context):
        if self.properties.do_scene_selected:
            self.add_scene_selected(context)
        else:
            self.add_selected(context)

        if self.properties.open_editor:
            bpy.ops.scene.rman_open_light_mixer_editor('INVOKE_DEFAULT')
        return {'FINISHED'}   

class PRMAN_OT_remove_light_from_light_mixer_group(bpy.types.Operator):
    bl_idname = 'renderman.remove_light_from_light_mixer_group'
    bl_label = 'Remove Selected from Light Mixer Group'

    group_index: IntProperty(default=0)

    def execute(self, context):
        scene = context.scene
        group_index = self.properties.group_index

        object_group = scene.renderman.light_mixer_groups
        object_group = object_group[group_index].members
        members = [member.light_ob for member in object_group]
        ob = getattr(context, "selected_light", None)
        if not ob:
            return {'FINISHED'}   

        for i, member in enumerate(object_group):
            if member.light_ob == ob:
                object_group.remove(i)
                break

        return {'FINISHED'}            

class PRMAN_OT_add_to_group(bpy.types.Operator):
    bl_idname = 'renderman.add_to_group'
    bl_label = 'Add Selected to Object Group'

    group_index: IntProperty(default=-1)
    do_scene_selected: BoolProperty(name="do_scene_selected", default=False)
    open_editor: BoolProperty(default=False)

    def add_selected(self, context):
        scene = context.scene
        rm = scene.renderman
        group_index = rm.object_groups_index
        ob = getattr(context, "selected_obj", None)
        if not ob:
            return {'FINISHED'}       

        object_groups = scene.renderman.object_groups
        object_group = object_groups[group_index]
        do_add = True
        for member in object_group.members:            
            if ob == member.ob_pointer:
                do_add = False
                break
        if do_add:
            ob_in_group = object_group.members.add()
            ob_in_group.name = ob.name
            ob_in_group.ob_pointer = ob    
            op = getattr(context, 'op_ptr')
            if op:
                op.selected_obj_name = '0'             
            ob.update_tag(refresh={'OBJECT'})    

    def add_scene_selected(self, context):
        scene = context.scene
        rm = scene.renderman
        if not hasattr(context, 'selected_objects'):
            return {'FINISHED'}

        group_index = self.properties.group_index
        object_groups = scene.renderman.object_groups
        object_group = object_groups[group_index]
        for ob in context.selected_objects:
            do_add = True
            for member in object_group.members:            
                if ob == member.ob_pointer:
                    do_add = False
                    break
            if do_add:
                ob_in_group = object_group.members.add()
                ob_in_group.name = ob.name
                ob_in_group.ob_pointer = ob      
                ob.update_tag(refresh={'OBJECT'})          

    def execute(self, context):
        if self.properties.do_scene_selected:
            self.add_scene_selected(context)
        else:
            self.add_selected(context)

        if self.properties.open_editor:
            bpy.ops.scene.rman_open_groups_editor('INVOKE_DEFAULT')            
        
        return {'FINISHED'}

class PRMAN_OT_remove_from_group(bpy.types.Operator):
    bl_idname = 'renderman.remove_from_group'
    bl_label = 'Remove Selected from Object Group'

    def execute(self, context):
        scene = context.scene
        rm = scene.renderman        
        group_index = rm.object_groups_index
        ob = getattr(context, "selected_obj", None)
        if not ob:
            return {'FINISHED'}        

        object_groups = scene.renderman.object_groups
        object_group = object_groups[group_index]
        for i, member in enumerate(object_group.members):
            if member.ob_pointer == ob:
                object_group.members.remove(i)
                ob.update_tag(refresh={'OBJECT'})
                break

        return {'FINISHED'}

class PRMAN_OT_add_light_link_object(bpy.types.Operator):
    bl_idname = 'renderman.add_light_link_object'
    bl_label = 'Add Selected Object to Light Link'

    def obj_list_items(self, context):
        scene = context.scene
        rm = scene.renderman
        group = rm.light_links[rm.light_links_index]
        objs_in_group = []
        for member in group.members:
            objs_in_group.append(member.ob_pointer.name)

        items = []
        for ob_name in [ob.name for ob in context.scene.objects if ob.type not in ['LIGHT', 'CAMERA']]:
            if ob_name not in objs_in_group:
                items.append((ob_name, ob_name, ''))
        return items       

    group_index: IntProperty(default=-1)
    do_scene_selected: BoolProperty(name="do_scene_selected", default=False)    

    def execute(self, context):
        scene = context.scene
        rm = scene.renderman

        ll = None
        if self.group_index == -1:
            light_links_index = rm.light_links_index
            ll = scene.renderman.light_links[light_links_index]
        else:
            ll = scene.renderman.light_links.get[self.group_index]

        if not ll:
            return {'FINISHED'}              
    
        ob = getattr(context, "selected_obj", None)
        if not ob:
            return {'FINISHED'}                  

        do_add = True
        for member in ll.members:            
            if ob == member.ob_pointer:
                do_add = False
                break
        if do_add:
            ob_in_group = ll.members.add()
            ob_in_group.name = ob.name
            ob_in_group.ob_pointer = ob   
            light_props = shadergraph_utils.get_rman_light_properties_group(ll.light_ob)
            if light_props.renderman_light_role == 'RMAN_LIGHTFILTER':
                subset = ob.renderman.rman_lightfilter_subset.add()
                subset.name = ll.light_ob.name
                subset.light_ob = ll.light_ob              
            else:
                if ll.illuminate == 'OFF':
                    subset = ob.renderman.rman_lighting_excludesubset.add()
                    subset.name = ll.light_ob.name
                    subset.light_ob = ll.light_ob
            ob.update_tag(refresh={'OBJECT'})

            op = getattr(context, 'op_ptr')
            if op:
                op.selected_obj_name = '0'                    

        return {'FINISHED'}

class PRMAN_OT_remove_light_link_object(bpy.types.Operator):
    bl_idname = 'renderman.remove_light_link_object'
    bl_label = 'Remove Selected Object from Light Link'

    group_index: IntProperty(default=-1)

    def execute(self, context):
        scene = context.scene
        rm = scene.renderman

        ll = None
        if self.group_index == -1:
            light_links_index = rm.light_links_index
            ll = scene.renderman.light_links[light_links_index]
        else:
            ll = scene.renderman.light_links.get[self.group_index]

        if not ll:
            return {'FINISHED'}              
    
        ob = getattr(context, "selected_obj", None)
        if not ob:
            return {'FINISHED'}       

        for i, member in enumerate(ll.members):
            if member.ob_pointer == ob:
                ll.members.remove(i)
                ll.members_index -= 1
                grp = ob.renderman.rman_lighting_excludesubset
                light_props = shadergraph_utils.get_rman_light_properties_group(self.light_ob)
                if light_props.renderman_light_role == 'RMAN_LIGHTFILTER':
                    grp = ob.renderman.rman_lightfilter_subset
                for j, subset in enumerate(grp):
                    if subset.light_ob == ll.light_ob:
                        grp.remove(j)
                        ob.update_tag(refresh={'OBJECT'})
                        break
                break                            

        return {'FINISHED'}


class PRMAN_OT_add_light_link(bpy.types.Operator):
    bl_idname = 'renderman.add_light_link'
    bl_label = 'Add New Light Link'
  
    group_index: IntProperty(default=-1)
    do_scene_selected: BoolProperty(name="do_scene_selected", default=False)

    def add_selected(self, context):
        scene = context.scene
        rm = scene.renderman

        light_ob = getattr(context, 'selected_light', None)
        if not light_ob:
            return {'FINISHED'}      

        do_add = True
        for light_link in rm.light_links:
            if light_ob == light_link.light_ob:
                do_add = False
                break            

        if do_add:
            ll = scene.renderman.light_links.add()
            ll.name = light_ob.name
            ll.light_ob = light_ob     
            
            op = getattr(context, 'op_ptr')
            if op:
                op.selected_light_name = '0'

            light_ob.update_tag(refresh={'DATA'})
            
    def add_scene_selected(self, context):
        scene = context.scene
        rm = scene.renderman
        obs_list = []
        op = getattr(context, 'op_ptr')
        if op:
            for nm in op.light_search_results.split('|'):
                ob = scene.objects[nm]
                if ob:
                    obs_list.append(ob)
            op.light_search_results = ''
            op.light_search_filter = ''   
            op.do_light_filter = False            
        else:
            if not hasattr(context, 'selected_objects'):
                return {'FINISHED'}

            obs_list = context.selected_objects                
            
        group_index = self.properties.group_index
        object_groups = scene.renderman.object_groups
        object_group = object_groups[group_index]
        for light_ob in obs_list:
            do_add = True
            for light_link in rm.light_links:
                if light_ob == light_link.light_ob:
                    do_add = False
                    break            

            if do_add:
                ll = scene.renderman.light_links.add()
                ll.name = light_ob.name
                ll.light_ob = light_ob.data   
                light_ob.update_tag(refresh={'DATA'})  

    def execute(self, context):
        if self.properties.do_scene_selected:
            self.add_scene_selected(context)
        else:
            self.add_selected(context)               

        return {'FINISHED'}

class PRMAN_OT_remove_light_link(bpy.types.Operator):
    bl_idname = 'renderman.remove_light_link'
    bl_label = 'Remove Light Link'

    group_index: IntProperty(name="idx", default=-1)

    def execute(self, context):
        scene = context.scene
        rm = scene.renderman
        group_index = self.group_index
        if group_index == -1:
            group_index = rm.light_links_index
        if group_index != -1:
            light_link = rm.light_links[group_index]
            for i, member in enumerate(light_link.members):
                ob = member.ob_pointer
                grp = ob.renderman.rman_lighting_excludesubset
                light_props = shadergraph_utils.get_rman_light_properties_group(light_link.light_ob)
                if light_props.renderman_light_role == 'RMAN_LIGHTFILTER':
                    grp = ob.renderman.rman_lightfilter_subset
                for j, subset in enumerate(grp):
                    if subset.light_ob == light_link.light_ob:
                        grp.remove(j)
                        break
                ob.update_tag(refresh={'OBJECT'})   

            light_link.light_ob.update_tag(refresh={'DATA'})
            rm.light_links.remove(group_index)
            rm.light_links_index -= 1

        return {'FINISHED'}

classes = [
    COLLECTION_OT_add_remove,
    COLLECTION_OT_meshlight_lightfilter_add_remove,
    COLLECTION_OT_object_groups_add_remove,
    PRMAN_OT_convert_mixer_group_to_light_group,
    PRMAN_OT_add_to_group,
    PRMAN_OT_add_light_to_light_mixer_group,
    PRMAN_OT_remove_light_from_light_mixer_group,
    PRMAN_OT_remove_from_group,
    PRMAN_OT_add_light_link_object,
    PRMAN_OT_remove_light_link_object,
    PRMAN_OT_add_light_link,
    PRMAN_OT_remove_light_link
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass       