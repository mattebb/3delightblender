from bpy.props import (PointerProperty, StringProperty, BoolProperty,
                       EnumProperty, IntProperty, FloatProperty, FloatVectorProperty,
                       CollectionProperty)

from .rman_ui_base import CollectionPanel   
from .rman_ui_base import PRManButtonsPanel 
from ..rman_utils.draw_utils import _draw_props
from ..rman_utils.draw_utils import _draw_ui_from_rman_config  
from ..rman_utils import scene_utils
from ..rman_render import RmanRender       
from ..icons.icons import load_icons          
from bpy.types import Panel
import bpy

class RENDERMAN_UL_LIGHT_list(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        rm = context.scene.renderman
        icon = 'NONE'
        ll_prefix = "lg_%s>%s" % (rm.ll_light_type, item.name)
        label = item.name
        for ll in rm.ll.keys():
            if ll_prefix in ll:
                icon = 'TRIA_RIGHT'
                break

        layout.alignment = 'CENTER'
        layout.label(text=label, icon=icon)


class RENDERMAN_UL_OBJECT_list(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        rm = context.scene.renderman
        icon = 'NONE'
        light_type = rm.ll_light_type
        lg = bpy.data.lights if light_type == "light" else rm.light_groups
        ll_prefix = "lg_%s>%s>obj_%s>%s" % (
            light_type, lg[rm.ll_light_index].name, rm.ll_object_type, item.name)

        label = item.name
        if ll_prefix in rm.ll.keys():
            ll = rm.ll[ll_prefix]
            if ll.illuminate == 'DEFAULT':
                icon = 'TRIA_RIGHT'
            elif ll.illuminate == 'ON':
                icon = 'DISCLOSURE_TRI_RIGHT'
            else:
                icon = 'DISCLOSURE_TRI_DOWN'

        layout.alignment = 'CENTER'
        layout.label(text=label, icon=icon)

class RENDERMAN_GROUP_UL_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        # We could write some code to decide which icon to use here...
        custom_icon = 'OBJECT_DATAMODE'
        # Make sure your code supports all 3 layout types
        layout.alignment = 'CENTER'
        layout.label(text=item.name, icon=custom_icon)

class RENDER_PT_Renderman_Workspace(PRManButtonsPanel, Panel):
    bl_label = "Workspace"
    bl_context = "scene"

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        if context.scene.render.engine != "PRMAN_RENDER":
            return

        layout = self.layout
        layout.operator('scene.rman_open_workspace', text='Open Workspace')

class RENDER_OT_Renderman_Open_Workspace(bpy.types.Operator):

    bl_idname = "scene.rman_open_workspace"
    bl_label = "RenderMan Workspace"

    def execute(self, context):
        return{'FINISHED'}         

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        if context.scene.render.engine != "PRMAN_RENDER":
            return

        layout = self.layout
        rd = context.scene.render
        rm = context.scene.renderman
        rman_render = RmanRender.get_rman_render()
        is_rman_interactive_running = rman_render.rman_interactive_running

        split = layout.split(factor=0.33)
        col = layout.column()
        col.enabled = not is_rman_interactive_running

        _draw_ui_from_rman_config('rman_properties_scene', 'RENDER_PT_renderman_workspace', context, layout, rm) 

    def invoke(self, context, event):

        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=600)                      


class PRMAN_PT_Renderman_Light_Panel(PRManButtonsPanel, Panel):
    bl_label = "RenderMan Light Groups"
    bl_context = "scene"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW' 

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        rm = scene.renderman

        row = layout.row()
        row.operator('scene.rman_open_light_panel', text='Open Light Panel')        

class PRMAN_OT_Renderman_Open_Light_Panel(CollectionPanel, bpy.types.Operator):

    bl_idname = "scene.rman_open_light_panel"
    bl_label = "RenderMan Light Panel"

    def add_button_enabled(self, context):
        scene = context.scene
        rm = scene.renderman
        lights_in_group = []
        for lg in rm.light_groups:
            lights_in_group.extend([member.light_ob.name for member in lg.members])

        items = []
        for light in [light.name for light in context.scene.objects if light.type == 'LIGHT']:
            if light not in lights_in_group:
                items.append(light)
        if not items:
            return False
        return True       

    def remove_button_enabled(self, context):
        scene = context.scene
        rm = scene.renderman
        return len(rm.light_groups) > 1 and rm.light_groups_index != 0

    def execute(self, context):
        return{'FINISHED'}         

    def invoke(self, context, event):

        scene = context.scene
        rm = scene.renderman
        rm.light_groups.clear()
        if 'All' not in rm.light_groups.keys():
            default_group = rm.light_groups.add()
            default_group.name = 'All'      

        lgt_grps = scene_utils.get_light_groups_in_scene(context.scene)
        for nm, lights in lgt_grps.items():
            grp = rm.light_groups.add()
            grp.name = nm  
            for light in lights:
                member = grp.members.add()
                member.name = light.name
                member.light_ob = light

        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=800)         

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        rm = scene.renderman
        self._draw_collection(context, layout, rm, "Light Groups",
                              "collection.add_remove",
                              "scene.renderman",
                              "light_groups", "light_groups_index", 
                              default_name='lightGroup_%d' % len(rm.light_groups), 
                              enable_add_func=self.add_button_enabled,
                              enable_remove_func=self.remove_button_enabled)    

    def draw_item(self, layout, context, item):
        scene = context.scene
        rm = scene.renderman
        light_group = rm.light_groups[rm.light_groups_index]

        lights = [member.light_ob for member in light_group.members]
        row = layout.row(align=True)

        split = row.split(factor=0.35)
        split.prop(item, 'name')
        split.enabled = light_group.name != 'All'
        row.separator()        
        if light_group.name == 'All':
            lights = [
                light.data for light in context.scene.objects if light.type == 'LIGHT']
        else:            
            box = layout.box()
            row = box.row()
            split = row.split(factor=0.25)
            split.operator_menu_enum("renderman.add_light_to_group", 'selected_light_name', text="Add Light")
            split.label(text='')

        if len(lights) > 0:
            box = layout.box()
            row = box.row()

            columns = box.column_flow(columns=11)
            columns.label(text='Name')
            columns.label(text='Solo')
            columns.label(text='Mute')
            columns.label(text='Intensity')
            columns.label(text='Exposure')
            columns.label(text='Color')
            columns.label(text='Enable Temp')
            columns.label(text='Temp')
            if light_group.name != 'All':
                columns.label(text='Remove')

            for light in lights:
                if light.name not in scene.objects:
                    continue
                light_rm = light.renderman
                if light_rm.renderman_light_role == 'RMAN_LIGHTFILTER':
                    continue
                row = box.row()
                columns = box.column_flow(columns=11)
                columns.label(text=light.name)
                columns.prop(light_rm, 'solo', text='')
                columns.prop(light_rm, 'mute', text='')
                light_shader = light.renderman.get_light_node()
                if light_shader:

                    columns.prop(light_shader, 'intensity', text='')
                    columns.prop(light_shader, 'exposure', text='')
                    if light_shader.bl_label == 'PxrEnvDayLight':
                        columns.prop(light_shader, 'skyTint', text='')
                        columns.label(text='')
                    else:
                        columns.prop(light_shader, 'lightColor', text='')
                        columns.prop(light_shader, 'enableTemperature', text='')
                        columns.prop(light_shader, 'temperature', text='')
                else:
                    columns.label(text='')
                    columns.prop(light, 'energy', text='')
                    columns.prop(light, 'color', text='')
                    columns.label(text='')
                    columns.label(text='')
                if light_group.name != 'All':
                    op = columns.operator('renderman.remove_light_from_group', text='', icon='CANCEL')
                    op.group_index = rm.light_groups_index
                    op.selected_light_name = light.name   

class PRMAN_PT_Renderman_Light_Linking_Panel(PRManButtonsPanel, Panel):
    bl_label = "RenderMan Light Linking"
    bl_context = "scene"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'  

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.operator('scene.rman_open_light_linking', text='Open Light Linking')

class PRMAN_PT_Renderman_Open_Light_Linking(CollectionPanel, bpy.types.Operator):

    bl_idname = "scene.rman_open_light_linking"
    bl_label = "RenderMan Light Linking"

    def execute(self, context):
        return{'FINISHED'}         

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        rm = scene.renderman
        row = layout.row()

        flow = row.column_flow(columns=3)
        # first colomn select Light
        flow.prop(rm, 'll_light_type')
        flow.prop(rm, 'll_object_type')
        flow.label(text='')

        # second row the selectors
        row = layout.row()
        flow = row.column_flow(columns=3)
        if rm.ll_light_type == 'light':
            flow.template_list("RENDERMAN_UL_LIGHT_list", "Renderman_light_link_list",
                               bpy.data, "lights", rm, 'll_light_index')
        else:
            flow.template_list("RENDERMAN_UL_LIGHT_list", "Renderman_light_link_list",
                               rm, "light_groups", rm, 'll_light_index')

        if rm.ll_object_type == 'object':
            flow.template_list("RENDERMAN_UL_OBJECT_list", "Renderman_light_link_list",
                               bpy.data, "objects", rm, 'll_object_index')
        else:
            flow.template_list("RENDERMAN_UL_OBJECT_list", "Renderman_light_link_list",
                               rm, "object_groups", rm, 'll_object_index')

        if rm.ll_light_index == -1 or rm.ll_object_index == -1:
            flow.label(text="Select light and object")
        else:
            from_name = bpy.data.lights[rm.ll_light_index] if rm.ll_light_type == 'light' \
                else rm.light_groups[rm.ll_light_index]
            to_name = bpy.data.objects[rm.ll_object_index] if rm.ll_object_type == 'object' \
                else rm.object_groups[rm.ll_object_index]
            ll_name = "lg_%s>%s>obj_%s>%s" % (rm.ll_light_type, from_name.name,
                                              rm.ll_object_type, to_name.name)

            col = flow.column()
            if ll_name in rm.ll:
                col.prop(rm.ll[ll_name], 'illuminate')
                rem = col.operator(
                    'renderman.add_rem_light_link', text='Remove Light Link')
                rem.ll_name = ll_name
                rem.add_remove = "remove"
            else:
                add = col.operator(
                    'renderman.add_rem_light_link', text='Add Light Link')
                add.ll_name = ll_name
                add.add_remove = 'add'

    def invoke(self, context, event):

        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=700)                   

class PRMAN_PT_Renderman_Object_Panel(PRManButtonsPanel, Panel):
    bl_label = "RenderMan Object Groups"
    bl_context = "scene"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        layout.operator('scene.rman_open_object_groups', text='Object Groups')

class PRMAN_OT_Renderman_Open_Object_Groups(CollectionPanel, bpy.types.Operator):

    bl_idname = "scene.rman_open_object_groups"
    bl_label = "RenderMan Object Groups"

    def execute(self, context):
        return{'FINISHED'}         

    def draw(self, context):
        layout = self.layout
        scene = context.scene   
        rm = scene.renderman
        self._draw_collection(context, layout, rm, "",
                              "collection.add_remove",
                              "scene.renderman",
                              "object_groups", "object_groups_index",
                              default_name='objectGroup_%d' % len(rm.object_groups))

    def draw_item(self, layout, context, item):
        row = layout.row()
        scene = context.scene
        rm = scene.renderman
        group = rm.object_groups[rm.object_groups_index]

        row = layout.row()
        row.operator('renderman.add_to_group',
                     text='Add Selected to Group').group_index = rm.object_groups_index
        row.operator('renderman.remove_from_group',
                     text='Remove Selected from Group').group_index = rm.object_groups_index

        row = layout.row()
        row.template_list("RENDERMAN_GROUP_UL_List", "Renderman_group_list",
                          group, "members", group, 'members_index',
                          item_dyntip_propname='name',
                          type='GRID', columns=3)  

    def invoke(self, context, event):

        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=700)                                                                   

classes = [
    RENDER_PT_Renderman_Workspace,
    RENDER_OT_Renderman_Open_Workspace,
    PRMAN_PT_Renderman_Light_Panel,
    PRMAN_OT_Renderman_Open_Light_Panel,
    PRMAN_PT_Renderman_Light_Linking_Panel,
    PRMAN_PT_Renderman_Open_Light_Linking,
    PRMAN_PT_Renderman_Object_Panel,
    PRMAN_OT_Renderman_Open_Object_Groups,
    RENDERMAN_GROUP_UL_List,
    RENDERMAN_UL_LIGHT_list,
    RENDERMAN_UL_OBJECT_list

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