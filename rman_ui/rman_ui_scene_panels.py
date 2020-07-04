from bpy.props import (PointerProperty, StringProperty, BoolProperty,
                       EnumProperty, IntProperty, FloatProperty, FloatVectorProperty,
                       CollectionProperty)

from .rman_ui_base import CollectionPanel   
from .rman_ui_base import PRManButtonsPanel 
from ..rman_utils.draw_utils import _draw_props
from ..rman_utils.draw_utils import _draw_ui_from_rman_config  
from ..rman_utils import scene_utils
from ..rman_render import RmanRender       
from ..icons.icons import get_light_icon 
from ..rman_operators.rman_operators_collections import return_empty_list     
from bpy.types import Panel
import bpy
import re

class RENDERMAN_UL_LightLink_Light_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        rm = context.scene.renderman
        label = item.name
        op = layout.operator("renderman.remove_light_link", text='', icon='REMOVE') 
        op.group_index = index
        light = item.light_ob
        light_shader = light.renderman.get_light_node()        
        icon = get_light_icon(light_shader.bl_label)        
        layout.label(text=label, icon_value=icon.icon_id) 

class RENDERMAN_UL_LightLink_Object_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        rm = context.scene.renderman
        custom_icon = 'OBJECT_DATAMODE'
        label = item.name
        op = layout.operator('renderman.remove_light_link_object', text='', icon='REMOVE')
        op.selected_obj_name = item.name        
        layout.label(text=label, icon=custom_icon)

class RENDERMAN_UL_Object_Group_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        custom_icon = 'OBJECT_DATAMODE'
        op = layout.operator('renderman.remove_from_group', text='', icon='REMOVE')
        op.selected_obj_name = item.name        
        layout.label(text=item.name, icon=custom_icon)

class RENDERMAN_UL_LightMixer_Group_Members_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        rm = context.scene.renderman
        light = item.light_ob
        light_shader = light.renderman.get_light_node()        
        icon = get_light_icon(light_shader.bl_label)

        op = layout.operator('renderman.remove_light_from_group', text='', icon='REMOVE')
        op.group_index = rm.light_mixer_groups_index
        op.selected_light_name = light.name  
        layout.label(text=light.name, icon_value=icon.icon_id)

        light_rm = light.renderman
        if light_shader.bl_label == 'PxrEnvDayLight':
            layout.prop(light_shader, 'skyTint', text='')
        else:
            layout.prop(light_shader, 'enableTemperature', text='Temp')
            if light_shader.enableTemperature:
                layout.prop(light_shader, 'temperature', text='', slider=True)
            else:
                layout.prop(light_shader, 'lightColor', text='')
        layout.prop(light_shader, 'exposure', slider=True)                
        if light_rm.solo:
            layout.prop(light_rm, 'solo', text='', icon='OUTLINER_OB_LIGHT', icon_only=True )
        else:
                layout.prop(light_rm, 'solo', text='', icon='LIGHT', icon_only=True )
        layout.prop(light_rm, 'mute', text='', icon='CANCEL', icon_only=True)

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


class PRMAN_PT_Renderman_Light_Mixer_Panel(PRManButtonsPanel, Panel):
    bl_label = "RenderMan Light Mixer"
    bl_context = "scene"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW' 

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        rm = scene.renderman

        row = layout.row()
        row.operator('scene.rman_open_light_mixer_editor', text='Open Light Mixer Editor')   

class PRMAN_OT_Renderman_Open_Light_Mixer_Editor(CollectionPanel, bpy.types.Operator):

    bl_idname = "scene.rman_open_light_mixer_editor"
    bl_label = "RenderMan Light Mixer Editor"

    def light_list_items(self, context):
        pattern = re.compile(self.light_search_filter)   
        scene = context.scene
        rm = scene.renderman
        group_index = rm.light_mixer_groups_index
        lights_in_group = []
        object_groups = rm.light_mixer_groups
        object_group = object_groups[group_index]
        lights_in_group = [member.light_ob.name for member in object_group.members]        

        items = []
        for light in [light for light in context.scene.objects if light.type == 'LIGHT']:
            is_light = (light.data.renderman.renderman_light_role == 'RMAN_LIGHT') 
            if not is_light:
                continue            
            if light.name not in lights_in_group:
                if self.do_light_filter and not re.match(pattern, light.name):
                    continue
                items.append((light.name, light.name, ''))
        if not items:
            return return_empty_list() 
        return items    

    selected_light_name: EnumProperty(name="Light", items=light_list_items)
    light_search_filter: StringProperty(name="Light Filter Search", default="")
    do_light_filter: BoolProperty(name="Filter", 
                                description="Search and add multiple lights",
                                default=False)    

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
                member.light_ob = light.data

        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=600)         

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        rm = scene.renderman
        self._draw_collection(context, layout, rm, "Light Mixer Groups",
                              "collection.add_remove",
                              "scene.renderman",
                              "light_mixer_groups", "light_mixer_groups_index", 
                              default_name='mixerGroup_%d' % len(rm.light_mixer_groups))

    def draw_item(self, layout, context, item):
        scene = context.scene
        rm = scene.renderman
        light_group = rm.light_mixer_groups[rm.light_mixer_groups_index]

        lights = [member.light_ob for member in light_group.members]
        row = layout.row(align=True)
        row.separator()        

        box = layout.box()
        row = box.row()
        split = row.split(factor=0.25)
        row = split.row()
        row.prop(self, 'do_light_filter', text='', icon='FILTER', icon_only=True)
        if not self.do_light_filter:
            if self.selected_light_name != '0':
                row.prop(self, 'selected_light_name', text='')
                op = row.operator("renderman.add_light_to_group", text='', icon='ADD')
                op.selected_light_name = self.selected_light_name
            else:
                row.label(text='No Lights to Add')
        else:
            row.prop(self, 'light_search_filter', text='', icon='VIEWZOOM')
            row = box.row()
            split = row.split(factor=0.25)
            row = split.row()
            if self.light_search_filter != '' and self.selected_light_name != '0':
                row.prop(self, 'selected_light_name', text='')
                op = row.operator("renderman.add_light_to_group", text='', icon='ADD')
                op.selected_light_name = self.selected_light_name
            else:
                row.label(text='No Results')

        layout.template_list("RENDERMAN_UL_LightMixer_Group_Members_List", "Renderman_light_mixer_list",
                            light_group, "members", light_group, 'members_index', rows=6)

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

class PRMAN_PT_Renderman_Open_Light_Linking(bpy.types.Operator):

    bl_idname = "scene.rman_open_light_linking"
    bl_label = "RenderMan Light Linking Editor"

    def light_list_items(self, context):
        pattern = re.compile(self.light_search_filter)        
        scene = context.scene
        rm = scene.renderman
        lights_in_group = []
        for lg in rm.light_links:
            lights_in_group.append(lg.light_ob.name)

        items = []
        light_items = list()
        lightfilter_items = list()
        for light in [light for light in context.scene.objects if light.type == 'LIGHT']:
            is_light = (light.data.renderman.renderman_light_role == 'RMAN_LIGHT')            
            if light.name not in lights_in_group:
                if self.do_light_filter and not re.match(pattern, light.name):
                    continue    
                if is_light:
                    light_items.append((light.name, light.name, '',))
                else:
                    lightfilter_items.append((light.name, light.name, ''))        
        if light_items:            
            items.extend(light_items)
        if lightfilter_items:           
            items.extend(lightfilter_items)
        if not items:
            return return_empty_list()            
        return items    

    def obj_list_items(self, context):
        pattern = re.compile(self.object_search_filter)
        scene = context.scene
        rm = scene.renderman
        group = rm.light_links[rm.light_links_index]
        objs_in_group = []
        for member in group.members:
            objs_in_group.append(member.ob_pointer.name)

        items = []
        for ob_name in [ob.name for ob in context.scene.objects if ob.type not in ['LIGHT', 'CAMERA']]:            
            if ob_name not in objs_in_group:
                if self.do_object_filter and not re.match(pattern, ob_name):
                    continue  
                items.append((ob_name, ob_name, ''))
        if not items:
            return return_empty_list()               
        return items       

    light_search_filter: StringProperty(name="Light Filter Search", default="")
    do_light_filter: BoolProperty(name="Filter", 
                                description="Search and add multiple lights",
                                default=False)
    selected_light_name: EnumProperty(name="", items=light_list_items)

    do_object_filter: BoolProperty(name="Object Filter", 
                                description="Search and add multiple objects",
                                default=False)    

    object_search_filter: StringProperty(name="Object Filter Search", default="")        

    selected_obj_name: EnumProperty(name="", items=obj_list_items)                   

    def execute(self, context):
        return{'FINISHED'}         

    def draw(self, context):
        layout = self.layout        
        scene = context.scene
        rm = scene.renderman
        row = layout.row()

        flow = row.column_flow(columns=3)
        row = flow.row()
        row.prop(self, 'do_light_filter', text='', icon='FILTER', icon_only=True)
        if not self.do_light_filter:
            if self.selected_light_name != '0':
                row.prop(self, 'selected_light_name', text='')
                row.context_pointer_set('op_ptr', self) 
                op = row.operator("renderman.add_light_link", text='', icon='ADD')
                op.selected_light_name = self.selected_light_name
            else:
                row.label(text='No Lights to Add')
        else:
            row.prop(self, 'light_search_filter', text='', icon='VIEWZOOM')  
            row = layout.row()             
            flow = row.column_flow(columns=3)
            row = flow.row()
            if self.light_search_filter != '' and self.selected_light_name != '0':
                row.prop(self, 'selected_light_name', text='')
                row.context_pointer_set('op_ptr', self) 
                op = row.operator("renderman.add_light_link", text='', icon='ADD')
                op.selected_light_name = self.selected_light_name
            else:
                row.label(text='No Results')

        flow.label(text='')

        row = layout.row()
        flow = row.column_flow(columns=3)

        flow.label(text='Lights')
        flow.label(text='Objects')
        flow.label(text='Illumination')

        row = layout.row()
        flow = row.column_flow(columns=3)

        flow.template_list("RENDERMAN_UL_LightLink_Light_List", "Renderman_light_link_list",
                            scene.renderman, "light_links", rm, 'light_links_index', rows=6)

        if rm.light_links_index != -1:
            light_link_item = scene.renderman.light_links[rm.light_links_index]  
            row = flow.row()          
            row.prop(self, 'do_object_filter', text='', icon='FILTER', icon_only=True)
            if not self.do_object_filter:
                if self.selected_obj_name != '0':
                    row.prop(self, 'selected_obj_name', text='')
                    row.context_pointer_set('op_ptr', self) 
                    op = row.operator("renderman.add_light_link_object", text='', icon='ADD')
                    op.selected_obj_name = self.selected_obj_name
                else:
                    row.label(text='No Objects to Add')
                flow.template_list("RENDERMAN_UL_LightLink_Object_List", "Renderman_light_link_list",
                                light_link_item, "members", light_link_item, 'members_index', rows=5)            
            else:
                row.prop(self, 'object_search_filter', text='', icon='VIEWZOOM')
                row = flow.row()  
                if self.object_search_filter != '' and self.selected_obj_name != '0':
                    row.prop(self, 'selected_obj_name')
                    row.context_pointer_set('op_ptr', self) 
                    op = row.operator("renderman.add_light_link_object", text='', icon='ADD')
                    op.selected_obj_name = self.selected_obj_name     
                else:
                    row.label(text='No Reults')
                    row.label(text='')  

                flow.template_list("RENDERMAN_UL_LightLink_Object_List", "Renderman_light_link_list",
                                light_link_item, "members", light_link_item, 'members_index', rows=4)                                          
      
            col = flow.column()
            col.prop(light_link_item, 'illuminate', text='')          

    def invoke(self, context, event):

        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=900)                   

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
    bl_label = "RenderMan Object Groups Editor"

    def obj_list_items(self, context):
        pattern = re.compile(self.object_search_filter)        
        scene = context.scene
        rm = scene.renderman
        group = rm.object_groups[rm.object_groups_index]
        objs_in_group = []
        for member in group.members:
            objs_in_group.append(member.ob_pointer.name)

        items = []
        for ob_name in [ob.name for ob in context.scene.objects if ob.type not in ['LIGHT', 'CAMERA']]:
            if ob_name not in objs_in_group:
                if self.do_object_filter and not re.match(pattern, ob_name):
                    continue
                items.append((ob_name, ob_name, ''))
        if not items:
            return return_empty_list()                 
        return items       


    do_object_filter: BoolProperty(name="Object Filter", 
                                description="Search and add multiple objects",
                                default=False)    

    object_search_filter: StringProperty(name="Object Filter Search", default="")        

    selected_obj_name: EnumProperty(name="", items=obj_list_items)       

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
        row.separator()   

        row.prop(self, 'do_object_filter', text='', icon='FILTER', icon_only=True)
        if not self.do_object_filter:
            if self.selected_obj_name != '0':
                row.prop(self, 'selected_obj_name', text='')
                row.context_pointer_set('op_ptr', self) 
                op = row.operator("renderman.add_to_group", text='', icon='ADD')
                op.selected_obj_name = self.selected_obj_name
                op.group_index = rm.object_groups_index
            else:
                row.label(text='No Objects to Add')       
        else:
            row.prop(self, 'object_search_filter', text='', icon='VIEWZOOM')
            row = layout.row()  
            if self.object_search_filter != '' and self.selected_obj_name != '0':
                row.prop(self, 'selected_obj_name')
                row.context_pointer_set('op_ptr', self) 
                op = row.operator("renderman.add_to_group", text='', icon='ADD')
                op.selected_obj_name = self.selected_obj_name     
                op.group_index = rm.object_groups_index
            else:
                row.label(text='No Reults')
                row.label(text='') 


        row = layout.row()
        
        row.template_list('RENDERMAN_UL_Object_Group_List', "",
                        group, "members", group, 'members_index', rows=6)

    def invoke(self, context, event):

        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=500)                                                                   

classes = [
    RENDER_PT_Renderman_Workspace,
    RENDER_OT_Renderman_Open_Workspace,
    PRMAN_PT_Renderman_Light_Mixer_Panel,
    PRMAN_OT_Renderman_Open_Light_Mixer_Editor,    
    PRMAN_PT_Renderman_Light_Linking_Panel,
    PRMAN_PT_Renderman_Open_Light_Linking,
    PRMAN_PT_Renderman_Object_Panel,
    PRMAN_OT_Renderman_Open_Object_Groups,
    RENDERMAN_UL_Object_Group_List,
    RENDERMAN_UL_LightLink_Light_List,
    RENDERMAN_UL_LightLink_Object_List,
    RENDERMAN_UL_LightMixer_Group_Members_List

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