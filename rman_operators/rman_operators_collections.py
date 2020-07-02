from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty,  CollectionProperty, PointerProperty
from ..rman_utils import string_utils
from ..rfb_logger import rfb_log

import bpy

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
    # BBM addition begin
    is_shader_param: BoolProperty(name='Is shader parameter', default=False)
    shader_type: StringProperty(
        name="shader type",
        default='surface')
    # BBM addition end

    def invoke(self, context, event):
        scene = context.scene
        # BBM modification
        if not self.properties.is_shader_param:
            id = string_utils.getattr_recursive(context, self.properties.context)
            rm = id.renderman if hasattr(id, 'renderman') else id
        else:
            if context.active_object.name in bpy.data.lights.keys():
                rm = bpy.data.lights[context.active_object.name].renderman
            else:
                rm = context.active_object.active_material.renderman
            id = getattr(rm, '%s_shaders' % self.properties.shader_type)
            rm = getattr(id, self.properties.context)

        prop_coll = self.properties.collection
        coll_idx = self.properties.collection_index

        collection = getattr(rm, prop_coll)
        index = getattr(rm, coll_idx)

        # otherwise just add an empty one
        if self.properties.action == 'ADD':
            collection.add()

            index += 1
            setattr(rm, coll_idx, index)
            collection[-1].name = self.properties.defaultname
            # BBM addition begin
            # if coshader array, add the selected coshader
            if self.is_shader_param:
                coshader_name = getattr(rm, 'bl_hidden_%s_menu' % prop_coll)
                collection[-1].name = coshader_name
            # BBM addition end
        elif self.properties.action == 'REMOVE':
            if prop_coll == 'light_groups' and collection[index].name == 'All':
                return {'FINISHED'}
            elif prop_coll == 'object_groups' and collection[index].name == 'collector':
                return {'FINISHED'}
            elif prop_coll == 'aov_channels' and not collection[index].custom:
                return {'FINISHED'}
            else:
                collection.remove(index)
                setattr(rm, coll_idx, index - 1)

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

class PRMAN_OT_add_light_to_group(bpy.types.Operator):
    bl_idname = 'renderman.add_light_to_group'
    bl_label = 'Add Selected to Object Group'

    def light_list_items(self, context):
        scene = context.scene
        rm = scene.renderman
        lights_in_group = []
        for lg in rm.light_groups:
            lights_in_group.extend([member.light_ob.name for member in lg.members])

        items = []
        for light in [light.name for light in context.scene.objects if light.type == 'LIGHT']:
            if light not in lights_in_group:
                items.append((light, light, ''))
        return items    

    selected_light_name: EnumProperty(name="Light", items=light_list_items)

    def execute(self, context):
        scene = context.scene
        group_index = scene.renderman.light_groups_index
        selected_light_name = self.properties.selected_light_name

        object_groups = scene.renderman.light_groups
        object_group = object_groups[group_index]
        members = [member.light_ob for member in object_group.members]
        ob = scene.objects.get(selected_light_name, None)
        if not ob:
            return {'FINISHED'}

        if ob not in members:
            do_add = True

            # check if light is already in another group
            # can only be in one
            for lg in scene.renderman.light_groups:
                lg_members = [member.light_ob for member in lg.members]
                if ob.data in lg_members:
                    do_add = False
                    self.report({'WARNING'}, "Light %s cannot be added to light group %s, already a member of %s" % (
                        ob.name, scene.renderman.light_groups[group_index].name, lg.name))

            if do_add:
                ob_in_group = object_group.members.add()
                ob_in_group.name = ob.name
                ob_in_group.light_ob = ob.data
                light_shader = ob.data.renderman.get_light_node()
                if light_shader:
                    light_shader.lightGroup = object_group.name
        return {'FINISHED'}   

class PRMAN_OT_remove_light_from_group(bpy.types.Operator):
    bl_idname = 'renderman.remove_light_from_group'
    bl_label = 'Remove Selected from Object Group'

    group_index: IntProperty(default=0)
    selected_light_name: StringProperty(default='object')

    def execute(self, context):
        scene = context.scene
        group_index = self.properties.group_index
        selected_light_name = self.properties.selected_light_name

        object_group = scene.renderman.light_groups
        object_group = object_group[group_index].members
        members = [member.light_ob for member in object_group]
        ob = scene.objects.get(selected_light_name, None)
        if not ob:
            return {'FINISHED'}

        for i, member in enumerate(object_group):
            if member.light_ob == ob.data:
                object_group.remove(i)
                break

        return {'FINISHED'}            


class PRMAN_OT_add_to_group(bpy.types.Operator):
    bl_idname = 'renderman.add_to_group'
    bl_label = 'Add Selected to Object Group'

    group_index: IntProperty(default=0)
    item_type: StringProperty(default='object')

    def execute(self, context):
        scene = context.scene
        group_index = self.properties.group_index
        item_type = self.properties.item_type

        object_group = scene.renderman.object_groups if item_type == 'object' \
            else scene.renderman.light_groups
        object_group = object_group[group_index].members
        if hasattr(context, 'selected_objects'):

            members = object_group.keys()

            for ob in context.selected_objects:
                if ob.name not in members:
                    if item_type != 'light' or ob.type == 'LIGHT':
                        do_add = True
                        if item_type == 'light' and ob.type == 'LIGHT':
                            # check if light is already in another group
                            # can only be in one
                            for lg in scene.renderman.light_groups:
                                if ob.name in lg.members.keys():
                                    do_add = False
                                    self.report({'WARNING'}, "Light %s cannot be added to light group %s, already a member of %s" % (
                                        ob.name, scene.renderman.light_groups[group_index].name, lg.name))

                        if do_add:
                            ob_in_group = object_group.add()
                            ob_in_group.name = ob.name

        return {'FINISHED'}


class PRMAN_OT_remove_from_group(bpy.types.Operator):
    bl_idname = 'renderman.remove_from_group'
    bl_label = 'Remove Selected from Object Group'

    group_index: IntProperty(default=0)
    item_type: StringProperty(default='object')

    def execute(self, context):
        scene = context.scene
        group_index = self.properties.group_index
        item_type = self.properties.item_type

        object_group = scene.renderman.object_groups if item_type == 'object' \
            else scene.renderman.light_groups
        object_group = object_group[group_index].members
        if hasattr(context, 'selected_objects'):
            for ob in context.selected_objects:
                if ob.name in object_group.keys():
                    index = object_group.keys().index(ob.name)
                    object_group.remove(index)

        return {'FINISHED'}


class PRMAN_OT_remove_add_rem_light_link(bpy.types.Operator):
    bl_idname = 'renderman.add_rem_light_link'
    bl_label = 'Add/Remove Selected from Object Group'

    add_remove: StringProperty(default='add')
    ll_name: StringProperty(default='')

    def execute(self, context):
        scene = context.scene

        add_remove = self.properties.add_remove
        ll_name = self.properties.ll_name

        if add_remove == 'add':
            ll = scene.renderman.ll.add()
            ll.name = ll_name
        else:
            ll_index = scene.renderman.ll.keys().index(ll_name)
            if engine.is_ipr_running():
                engine.ipr.remove_light_link(
                    context, scene.renderman.ll[ll_index])
            scene.renderman.ll.remove(ll_index)

        return {'FINISHED'}

classes = [
    COLLECTION_OT_add_remove,
    PRMAN_OT_add_to_group,
    PRMAN_OT_add_light_to_group,
    PRMAN_OT_remove_light_from_group,
    PRMAN_OT_remove_from_group,
    PRMAN_OT_remove_add_rem_light_link,
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