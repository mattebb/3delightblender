from bpy.props import (StringProperty, BoolProperty, EnumProperty, IntProperty)

from ..rman_ui.rman_ui_base import CollectionPanel   
from ..rfb_utils.draw_utils import _draw_ui_from_rman_config, draw_node_properties_recursive
from ..rfb_utils import scene_utils
from ..rfb_utils import shadergraph_utils
from ..rfb_utils import string_utils
from ..rfb_utils import object_utils
from ..rfb_utils.envconfig_utils import envconfig
from .. import rfb_icons
from ..rman_operators.rman_operators_collections import return_empty_list   
from ..rman_constants import RFB_MAX_USER_TOKENS, RMAN_STYLIZED_FILTERS, RFB_ADDON_PATH  
from ..rman_config import __RFB_CONFIG_DICT__ as rfb_config
import bpy
import bpy_extras
import os
import re

class RENDERMAN_UL_LightLink_Light_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        rm = context.scene.renderman
        op = layout.operator("renderman.remove_light_link", text='', icon='REMOVE') 
        op.group_index = index
        light = item.light_ob
        light_shader = shadergraph_utils.get_light_node(light)      
        icon = rfb_icons.get_light_icon(light_shader.bl_label)        
        label = light.name
        layout.label(text=label, icon_value=icon.icon_id)     

class RENDERMAN_UL_LightLink_Object_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        rm = context.scene.renderman
        custom_icon = 'OBJECT_DATAMODE'
        layout.context_pointer_set("selected_obj", item.ob_pointer)
        op = layout.operator('renderman.remove_light_link_object', text='', icon='REMOVE')    
        label = item.ob_pointer.name
        layout.label(text=label, icon=custom_icon)

class RENDERMAN_UL_Object_Group_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        custom_icon = 'OBJECT_DATAMODE'
        layout.context_pointer_set("selected_obj", item.ob_pointer)
        op = layout.operator('renderman.remove_from_group', text='', icon='REMOVE')     
        label = item.ob_pointer.name
        layout.label(text=label, icon=custom_icon)  

class RENDERMAN_UL_LightMixer_Group_Members_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        rm = context.scene.renderman
        light = item.light_ob
        layout.context_pointer_set("selected_light", light)        
        op = layout.operator('renderman.remove_light_from_light_mixer_group', text='', icon='REMOVE')
   
        light_shader = shadergraph_utils.get_light_node(light)
        if not light_shader:
            layout.label(text=light.name)
            layout.label(text='NO LIGHT SHADER')
            return 

        icon = rfb_icons.get_light_icon(light_shader.bl_label)
        op.group_index = rm.light_mixer_groups_index
        layout.label(text=light.name, icon_value=icon.icon_id)

        light_rm = shadergraph_utils.get_rman_light_properties_group(light)
        if light_shader.bl_label == 'PxrEnvDayLight':
            layout.prop(light_shader, 'skyTint', text='')
        else:
            layout.prop(light_shader, 'enableTemperature', text='Temp')
            if light_shader.enableTemperature:
                layout.prop(light_shader, 'temperature', text='', slider=True)
            else:
                layout.prop(light_shader, 'lightColor', text='')
        layout.prop(light_shader, 'intensity', slider=True)
        layout.prop(light_shader, 'exposure', slider=True)        
        solo_icon = 'LIGHT'        
        if light.renderman.solo:
            solo_icon = 'OUTLINER_OB_LIGHT'
        layout.prop(light.renderman, 'solo', text='', icon=solo_icon, icon_only=True, emboss=False )
        mute_icon = 'HIDE_OFF'
        if light.renderman.mute:
            mute_icon = 'HIDE_ON'
        layout.prop(light.renderman, 'mute', text='', icon=mute_icon, icon_only=True, emboss=False)

class RENDER_OT_Renderman_Open_Workspace(CollectionPanel, bpy.types.Operator):

    bl_idname = "scene.rman_open_workspace"
    bl_label = "RenderMan Workspace"

    def execute(self, context):
        self.set_tokens(context)
        return{'FINISHED'}         

    def cancel(self, context):
        self.set_tokens(context)

    def set_tokens(self, context):
        string_utils.update_blender_tokens_cb(context.scene)

    def draw_item(self, layout, context, item):
        layout.prop(item, 'name')
        layout.prop(item, 'value')

    def add_callback(self, context):
        rm = context.scene.renderman
        if len(rm.user_tokens) < RFB_MAX_USER_TOKENS:
            return True
        return False

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        if context.scene.render.engine != "PRMAN_RENDER":
            return

        layout = self.layout
        rd = context.scene.render
        rm = context.scene.renderman
        is_rman_interactive_running = rm.is_rman_interactive_running

        split = layout.split(factor=0.33)
        col = layout.column()
        col.enabled = not is_rman_interactive_running

        _draw_ui_from_rman_config('rman_properties_scene', 'RENDER_PT_renderman_workspace', context, layout, rm) 

        layout.label(text='Scene Tokens')
        col = layout.column()
        row = col.row()
        row.prop(rm, 'version_token')
        row = col.row()
        row.prop(rm, 'take_token')

        self._draw_collection(context, layout, rm, "User Tokens",
                              "collection.add_remove",
                              "scene.renderman",
                              "user_tokens", "user_tokens_index", 
                              default_name='name_%d' % len(rm.user_tokens),
                              enable_add_func=self.add_callback)        

    def invoke(self, context, event):

        wm = context.window_manager
        width = rfb_config['editor_preferences']['workspace_editor']['width']
        return wm.invoke_props_dialog(self, width=width)                      

class PRMAN_OT_Renderman_Open_Light_Mixer_Editor(CollectionPanel, bpy.types.Operator):

    bl_idname = "scene.rman_open_light_mixer_editor"
    bl_label = "RenderMan Light Mixer Editor"

    def updated_light_selected_name(self, context):
        light_ob = context.scene.objects.get(self.selected_light_name, None)
        if not light_ob:
            return
                
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        light_ob.select_set(True)
        context.view_layer.objects.active = light_ob   

    def light_list_items(self, context):
        pattern = re.compile(self.light_search_filter)   
        scene = context.scene
        rm = scene.renderman

        if self.do_light_filter and self.light_search_filter == '':
            return return_empty_list(label='No Lights Found')

        group_index = rm.light_mixer_groups_index
        lights_in_group = []
        object_groups = rm.light_mixer_groups
        object_group = object_groups[group_index]
        lights_in_group = [member.light_ob.name for member in object_group.members]        

        items = []
        for light in scene_utils.get_all_lights(context.scene, include_light_filters=False):
            if light.name not in lights_in_group:
                if self.do_light_filter and not re.match(pattern, light.name):
                    continue
                items.append((light.name, light.name, ''))
        if not items:
            return return_empty_list(label='No Lights Found') 
        elif self.do_light_filter:
            items.insert(0, ('0', 'Results (%d)' % len(items), '', '', 0))
        else:
            items.insert(0, ('0', 'Select Light', '', '', 0))                  
        return items

    def update_do_light_filter(self, context):
        self.selected_light_name = '0'

    selected_light_name: EnumProperty(name="Light", items=light_list_items, update=updated_light_selected_name)
    light_search_filter: StringProperty(name="Light Filter Search", default="")
    do_light_filter: BoolProperty(name="Filter", 
                                description="Search and add multiple lights",
                                default=False,
                                update=update_do_light_filter)    

    def execute(self, context):
        return{'FINISHED'}         

    def invoke(self, context, event):

        wm = context.window_manager
        width = rfb_config['editor_preferences']['lightmixer_editor']['width']
        return wm.invoke_props_dialog(self, width=width)         

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
            row.prop(self, 'selected_light_name', text='')
            col = row.column()            
            if self.selected_light_name == '0' or self.selected_light_name == '':
                col.enabled = False
                op = col.operator("renderman.add_light_to_light_mixer_group", text='', icon='ADD')
                op.open_editor = False
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_light', bpy.data.objects[self.selected_light_name])
                op = col.operator("renderman.add_light_to_light_mixer_group", text='', icon='ADD')
                op.do_scene_selected = False
                op.open_editor = False
        else:
            row.prop(self, 'light_search_filter', text='', icon='VIEWZOOM')
            row = box.row()
            split = row.split(factor=0.25)
            row = split.row()
            row.prop(self, 'selected_light_name', text='')
            col = row.column()
            if self.selected_light_name == '0' or self.selected_light_name == '':
                col.enabled = False
                op = col.operator("renderman.add_light_to_light_mixer_group", text='', icon='ADD')
                op.open_editor = False
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_light', bpy.data.objects[self.selected_light_name])
                op = col.operator("renderman.add_light_to_light_mixer_group", text='', icon='ADD')
                op.do_scene_selected = False
                op.open_editor = False
        row = layout.row()
        split = row.split(factor=0.25)
        op = split.operator('renderman.convert_mixer_group_to_light_group', text='Convert to Light Group')
        op.group_index = rm.light_mixer_groups_index

        layout.template_list("RENDERMAN_UL_LightMixer_Group_Members_List", "Renderman_light_mixer_list",
                            light_group, "members", light_group, 'members_index', rows=6)

class PRMAN_PT_Renderman_Open_Light_Linking(bpy.types.Operator):

    bl_idname = "scene.rman_open_light_linking"
    bl_label = "RenderMan Light Linking Editor"

    def updated_light_selected_name(self, context):
        light_ob = context.scene.objects.get(self.selected_light_name, None)
        if not light_ob:
            return
                
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        light_ob.select_set(True)
        context.view_layer.objects.active = light_ob       

    def light_list_items(self, context):
        pattern = re.compile(self.light_search_filter)        
        scene = context.scene
        rm = scene.renderman
        if self.do_light_filter and self.light_search_filter == '':
            return return_empty_list(label='No Lights Found')
        
        lights_in_group = []
        for lg in rm.light_links:
            lights_in_group.append(lg.light_ob.name)

        items = []
        light_items = list()
        lightfilter_items = list()

        for light in scene_utils.get_all_lights(context.scene, include_light_filters=True):
            light_props = shadergraph_utils.get_rman_light_properties_group(light)            
            is_light = (light_props.renderman_light_role == 'RMAN_LIGHT')            
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
            return return_empty_list(label='No Lights Found') 
        elif self.do_light_filter:
            items.insert(0, ('0', 'Results (%d)' % len(items), '', '', 0))
        else:
            items.insert(0, ('0', 'Select Light', '', '', 0))                  
        return items    

    def update_do_light_filter(self, context):
        self.selected_light_name = '0'

    def updated_object_selected_name(self, context):
        ob = context.scene.objects.get(self.selected_obj_name, None)
        if not ob:
            return
                
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob             

    def obj_list_items(self, context):
        pattern = re.compile(self.object_search_filter)
        scene = context.scene
        rm = scene.renderman

        if self.do_object_filter and self.object_search_filter == '':
            return return_empty_list(label='No Objects Found')        

        group = rm.light_links[rm.light_links_index]

        objs_in_group = []
        for member in group.members:
            objs_in_group.append(member.ob_pointer.name)

        items = []
        for ob in [ob for ob in context.scene.objects if ob.type not in ['LIGHT', 'CAMERA']]:   
            if shadergraph_utils.is_mesh_light(ob):
                continue
            ob_name = ob.name   
            if ob_name not in objs_in_group:
                if self.do_object_filter and not re.match(pattern, ob_name):
                    continue  
                items.append((ob_name, ob_name, ''))
        if not items:
            return return_empty_list(label='No Objects Found')               
        elif self.do_object_filter:
            items.insert(0, ('0', 'Results (%d)' % len(items), '', '', 0))
        else:
            items.insert(0, ('0', 'Select Object', '', '', 0))
        return items       

    def update_do_object_filter(self, context):
        self.selected_obj_name = '0'

    light_search_filter: StringProperty(name="Light Filter Search", default="")
    do_light_filter: BoolProperty(name="Filter", 
                                description="Search and add multiple lights",
                                default=False, update=update_do_light_filter)
    selected_light_name: EnumProperty(name="", items=light_list_items, update=updated_light_selected_name)
    do_object_filter: BoolProperty(name="Object Filter", 
                                description="Search and add multiple objects",
                                default=False,
                                update=update_do_object_filter)    

    object_search_filter: StringProperty(name="Object Filter Search", default="")        

    selected_obj_name: EnumProperty(name="", items=obj_list_items, update=updated_object_selected_name)                   

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
            row.prop(self, 'selected_light_name', text='')
            col = row.column()            
            if self.selected_light_name == '0' or self.selected_light_name == '':
                col.enabled = False                
                op = col.operator("renderman.add_light_link", text='', icon='ADD')
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_light', bpy.data.objects[self.selected_light_name])
                op = col.operator("renderman.add_light_link", text='', icon='ADD')
        else:
            row.prop(self, 'light_search_filter', text='', icon='VIEWZOOM')  
            row = layout.row()             
            flow = row.column_flow(columns=3)
            row = flow.row()

            row.prop(self, 'selected_light_name', text='')
            col = row.column()
            if self.selected_light_name == '0' or self.selected_light_name == '':
                col.enabled= False
                op = col.operator("renderman.add_light_link", text='', icon='ADD')
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_light', bpy.data.objects[self.selected_light_name])
                op = col.operator("renderman.add_light_link", text='', icon='ADD')

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
            light_props = shadergraph_utils.get_rman_light_properties_group(light_link_item.light_ob)
            is_rman_light = (light_props.renderman_light_role == 'RMAN_LIGHT')
            row.prop(self, 'do_object_filter', text='', icon='FILTER', icon_only=True)
            if not self.do_object_filter:
                row.prop(self, 'selected_obj_name', text='')
                col = row.column()
                if self.selected_obj_name == '0' or self.selected_obj_name == '':
                    col.enabled = False
                    op = col.operator("renderman.add_light_link_object", text='', icon='ADD')                    
                else:
                    col.context_pointer_set('op_ptr', self) 
                    col.context_pointer_set('selected_obj', scene.objects[self.selected_obj_name])
                    op = col.operator("renderman.add_light_link_object", text='', icon='ADD')
                    op.do_scene_selected = False

                flow.template_list("RENDERMAN_UL_LightLink_Object_List", "Renderman_light_link_list",
                                light_link_item, "members", light_link_item, 'members_index', rows=5)            
            else:
                row.prop(self, 'object_search_filter', text='', icon='VIEWZOOM')
                row = flow.row()  
                row.prop(self, 'selected_obj_name')
                col = row.column()                
                if self.selected_obj_name == '0' or self.selected_obj_name == '':
                    col.enabled = False                    
                    op = col.operator("renderman.add_light_link_object", text='', icon='ADD')                
                else:
                    col.context_pointer_set('op_ptr', self) 
                    col.context_pointer_set('selected_obj', scene.objects[self.selected_obj_name])
                    op = col.operator("renderman.add_light_link_object", text='', icon='ADD')     
                    op.do_scene_selected = False           

                flow.template_list("RENDERMAN_UL_LightLink_Object_List", "Renderman_light_link_list",
                                light_link_item, "members", light_link_item, 'members_index', rows=4)                                          
      
            col = flow.column()
            if is_rman_light and len(light_link_item.members) > 0:
                col.prop(light_link_item, 'illuminate', text='')          

    def invoke(self, context, event):

        wm = context.window_manager
        width = rfb_config['editor_preferences']['lightlink_editor']['width']
        return wm.invoke_props_dialog(self, width=width)

class PRMAN_OT_Renderman_Open_Groups_Editor(CollectionPanel, bpy.types.Operator):

    bl_idname = "scene.rman_open_groups_editor"
    bl_label = "RenderMan Trace Sets Editor"

    def updated_object_selected_name(self, context):
        ob = context.scene.objects.get(self.selected_obj_name, None)
        if not ob:
            return
                
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob       

    def obj_list_items(self, context):
        pattern = re.compile(self.object_search_filter)        
        scene = context.scene
        rm = scene.renderman

        if self.do_object_filter and self.object_search_filter == '':
            return return_empty_list(label='No Objects Found')        

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
            return return_empty_list(label='No Objects Found')               
        elif self.do_object_filter:
            items.insert(0, ('0', 'Results (%d)' % len(items), '', '', 0))
        else:
            items.insert(0, ('0', 'Select Object', '', '', 0))
        return items  

    def update_do_object_filter(self, context):
        self.selected_obj_name = '0'            

    do_object_filter: BoolProperty(name="Object Filter", 
                                description="Search and add multiple objects",
                                default=False,
                                update=update_do_object_filter)    
    object_search_filter: StringProperty(name="Object Filter Search", default="")       
    selected_obj_name: EnumProperty(name="", items=obj_list_items, update=updated_object_selected_name)       

    def execute(self, context):
        return{'FINISHED'}         

    def draw(self, context):
        layout = self.layout
        scene = context.scene   
        rm = scene.renderman
        layout.separator()
        self._draw_collection(context, layout, rm, "Trace Sets",
                            "renderman.add_remove_object_groups",
                            "scene.renderman",
                            "object_groups", "object_groups_index",
                            default_name='traceSet_%d' % len(rm.object_groups))          

    def draw_objects_item(self, layout, context, item):
        row = layout.row()
        scene = context.scene
        rm = scene.renderman
        group = rm.object_groups[rm.object_groups_index]

        row = layout.row()
        row.separator()   

        row.prop(self, 'do_object_filter', text='', icon='FILTER', icon_only=True)
        if not self.do_object_filter:
            row.prop(self, 'selected_obj_name', text='')
            col = row.column()
            if self.selected_obj_name == '0' or self.selected_obj_name == '':
                col.enabled = False
                op = col.operator("renderman.add_to_group", text='', icon='ADD')
                op.open_editor = False
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_obj', scene.objects[self.selected_obj_name])
                op = col.operator("renderman.add_to_group", text='', icon='ADD')
                op.group_index = rm.object_groups_index    
                op.do_scene_selected = False
                op.open_editor = False
        else:
            row.prop(self, 'object_search_filter', text='', icon='VIEWZOOM')
            row = layout.row()  
            row.prop(self, 'selected_obj_name')
            col = row.column()
            if self.selected_obj_name == '0' or self.selected_obj_name == '':
                col.enabled = False
                op = col.operator("renderman.add_to_group", text='', icon='ADD')
                op.open_editor = False
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_obj', scene.objects[self.selected_obj_name])                
                op = col.operator("renderman.add_to_group", text='', icon='ADD')
                op.group_index = rm.object_groups_index
                op.do_scene_selected = False
                op.open_editor = False

        row = layout.row()
        
        row.template_list('RENDERMAN_UL_Object_Group_List', "",
                        group, "members", group, 'members_index', rows=6)        

    def draw_item(self, layout, context, item):
        self.draw_objects_item(layout, context, item)

    def invoke(self, context, event):

        wm = context.window_manager
        width = rfb_config['editor_preferences']['tracesets_editor']['width']
        return wm.invoke_props_dialog(self, width=width)  

class PRMAN_OT_Renderman_Open_Stylized_Help(bpy.types.Operator):
    bl_idname = "renderman.rman_stylized_help"
    bl_label = "Stylized Help" 
    bl_description = "Get help on how to use RenderMan Stylzied Looks"

    def execute(self, context):
        return{'FINISHED'}     

    def draw(self, context):
        layout = self.layout       
        box = layout.box()
        box.scale_y = 0.4
        rman_icon = rfb_icons.get_icon('out_PxrStylizedControl')
        box.label(text="RenderMan Stylized Looks HOWTO", icon_value = rman_icon.icon_id)
        rman_icon = rfb_icons.get_icon('help_stylized_1')
        box.template_icon(rman_icon.icon_id, scale=10.0)
        box.label(text="")
        box.label(text="To start using RenderMan Stylized Looks, click the Enable Stylized Looks.")
        box.label(text="")
        box.label(text="Stylized looks requires BOTH a stylized pattern node") 
        box.label(text="be connected in an object's shading material network")
        box.label(text="and one of the stylized display filters be present in the scene.")
        box.label(text="")
        box.label(text="In the RenderMan Stylized Editor, the Patterns tab allows you to")
        box.label(text="search for an object in the scene and attach a PxrStylizedControl pattern.")
        box.label(text="You can use the drop down list or do a filter search to select the object you want to stylized.")
        box.label(text="If no material is present, a PxrSurface material will automatically be created for you.")
        box.label(text="The stylized pattern allows for per-object control.")
        box.label(text="")
        box.label(text="The Filters tab allows you to add one of the stylized display filters.")
        box.label(text="The filters can be turned on and off, individually.")
        box.label(text="As mentioned in earlier, both the patterns and the filters need to be present.")
        box.label(text="So you need to add at least one filter for the stylized looks to work.")       

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=500)  

class PRMAN_OT_Renderman_Open_Stylized_Editor(bpy.types.Operator):

    bl_idname = "scene.rman_open_stylized_editor"
    bl_label = "RenderMan Stylized Editor"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine in {'PRMAN_RENDER'} 

    def updated_object_selected_name(self, context):
        ob = context.scene.objects.get(self.selected_obj_name, None)
        if not ob:
            return
                
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob       

    def obj_list_items(self, context):
        pattern = re.compile(self.object_search_filter)        
        scene = context.scene
        rm = scene.renderman

        if self.do_object_filter and self.object_search_filter == '':
            return return_empty_list(label='No Objects Found')        

        items = []
        for ob in context.scene.objects:
            if ob.type in ['LIGHT', 'CAMERA']:
                continue

            mat = object_utils.get_active_material(ob)
            if not mat:
                items.append((ob.name, ob.name, ''))
                continue

            if not shadergraph_utils.is_renderman_nodetree(mat):
                items.append((ob.name, ob.name, ''))
                continue

            if self.do_object_filter and not re.match(pattern, ob.name):
                continue
            if not shadergraph_utils.has_stylized_pattern_node(ob):
                items.append((ob.name, ob.name, ''))
        if not items:
            return return_empty_list(label='No Objects Found')               
        elif self.do_object_filter:
            items.insert(0, ('0', 'Results (%d)' % len(items), '', '', 0))
        else:
            items.insert(0, ('0', 'Select Object', '', '', 0))
        return items  

    def update_do_object_filter(self, context):
        self.selected_obj_name = '0'            

    do_object_filter: BoolProperty(name="Object Filter", 
                                description="Search and add multiple objects",
                                default=False,
                                update=update_do_object_filter)    
    object_search_filter: StringProperty(name="Object Filter Search", default="")       
    selected_obj_name: EnumProperty(name="", items=obj_list_items, update=updated_object_selected_name)    

    def current_filters(self, context):
        items = []
        scene = context.scene   
        world = scene.world
        nt = world.node_tree

        nodes = shadergraph_utils.find_all_stylized_filters(world)

        for node in nodes:
            items.append((node.name, node.name, ""))

        if len(items) < 1:
            items.append(('0', '', '', '', 0))

        return items  

    stylized_filter: EnumProperty(
        name="",
        items=current_filters
    )    

    stylized_tabs: EnumProperty(
        name="",
        items=[
            ('patterns', 'Patterns', 'Add or eidt stylized patterns attached to objects in the scene'),
            ('filters', 'Filters', 'Add or edit stylized display filters in the scene'),
        ]
    )

    def get_stylized_objects(self, context):
        items = []
        scene = context.scene 
        for ob in scene.objects:
            node = shadergraph_utils.has_stylized_pattern_node(ob)
            if node:
                items.append((ob.name, ob.name, ''))

        if len(items) < 1:
            items.append(('0', '', '', '', 0))                

        return items      

    stylized_objects: EnumProperty(
        name="",
        items=get_stylized_objects
    )

    def update_render_stylized(self, context):
        scene = context.scene
        rm = scene.renderman
        rm.render_rman_stylized = self.enabled_render_stylized
        if rm.render_rman_stylized:
            bpy.ops.renderman.dspy_displays_reload('EXEC_DEFAULT')
        world = scene.world
        world.update_tag()            

    enabled_render_stylized: BoolProperty(
        name="Enable Stylized Looks",
        update=update_render_stylized
    )
         
    def execute(self, context):
        return{'FINISHED'}   


    def draw_patterns_tab(self, context): 
        scene = context.scene   
        rm = scene.renderman
        selected_objects = context.selected_objects        

        layout = self.layout           

        row = layout.row()
        row.separator()   

        row.prop(self, 'do_object_filter', text='', icon='FILTER', icon_only=True)
        if not self.do_object_filter:
            row.prop(self, 'selected_obj_name', text='')
            col = row.column()

            if self.selected_obj_name == '0' or self.selected_obj_name == '':
                pass
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_obj', scene.objects[self.selected_obj_name])  
                col.operator_menu_enum('node.rman_attach_stylized_pattern', 'stylized_pattern')                

        else:
            row.prop(self, 'object_search_filter', text='', icon='VIEWZOOM')
            row = layout.row()  
            row.prop(self, 'selected_obj_name')
            col = row.column()

            if self.selected_obj_name == '0' or self.selected_obj_name == '':
                pass
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_obj', scene.objects[self.selected_obj_name])             
                col.operator_menu_enum('node.rman_attach_stylized_pattern', 'stylized_pattern')            

        if self.properties.stylized_objects != '0':                

            layout.separator()
            row = layout.row(align=True)
            col = row.column()
            col.label(text='Stylized Objects')           

            row = layout.row(align=True)
            col = row.column()
            col.prop(self, 'stylized_objects')

            ob = scene.objects.get(self.properties.stylized_objects, None)
            node = shadergraph_utils.has_stylized_pattern_node(ob)
            mat = object_utils.get_active_material(ob)
            col.separator()
            col.label(text=node.name)
            col.separator()
            draw_node_properties_recursive(layout, context, mat.node_tree, node, level=1)

    def draw_filters_tab(self, context):
        scene = context.scene   
        world = scene.world
        nt = world.node_tree             
        layout = self.layout            
        
        row = layout.row(align=True)
        col = row.column()
        col.context_pointer_set('op_ptr', self) 
        col.operator_menu_enum('node.rman_add_stylized_filter', 'filter_name')            

        layout.separator()  
        output = shadergraph_utils.find_node(world, 'RendermanDisplayfiltersOutputNode')
        if not output:
            row = layout.row()
            row.label(text="No Stylized Filters")
            return 

        layout.separator()
        row = layout.row()
        row.label(text="Scene Filters")            
        row = layout.row()

        layout.prop(self, 'stylized_filter')
        selected_stylized_node = None
        if self.properties.stylized_filter != '':
            nodes = shadergraph_utils.find_all_stylized_filters(world)
            for node in nodes:
                if node.name == self.properties.stylized_filter:
                    selected_stylized_node = node
                    break
        
        if selected_stylized_node:
            rman_icon = rfb_icons.get_displayfilter_icon(node.bl_label) 
            layout.prop(selected_stylized_node, "is_active")
            if selected_stylized_node.is_active:
                draw_node_properties_recursive(layout, context, nt, selected_stylized_node, level=1)             

    def draw(self, context):

        layout = self.layout  
        scene = context.scene 
        rm = scene.renderman         
        split = layout.split()
        row = split.row()
        col = row.column()
        col.prop(self, 'enabled_render_stylized', text='Enable Stylized Looks')
        col = row.column()
        icon = rfb_icons.get_icon('rman_help')
        col.operator("renderman.rman_stylized_help", text="", icon_value=icon.icon_id)
        if not rm.render_rman_stylized:
            return

        row = layout.row(align=True)
        row.prop_tabs_enum(self, 'stylized_tabs', icon_only=False)

        if self.properties.stylized_tabs == "patterns":
            self.draw_patterns_tab(context)
        else:
            self.draw_filters_tab(context)
        
        
    def invoke(self, context, event):
        scene = context.scene
        rm = scene.renderman
        self.properties.enabled_render_stylized = rm.render_rman_stylized
        wm = context.window_manager
        width = rfb_config['editor_preferences']['stylizedlooks_editor']['width']
        return wm.invoke_props_dialog(self, width=width)

classes = [
    RENDER_OT_Renderman_Open_Workspace,
    PRMAN_OT_Renderman_Open_Light_Mixer_Editor,    
    PRMAN_PT_Renderman_Open_Light_Linking,
    PRMAN_OT_Renderman_Open_Groups_Editor,
    RENDERMAN_UL_Object_Group_List,
    RENDERMAN_UL_LightLink_Light_List,
    RENDERMAN_UL_LightLink_Object_List,
    RENDERMAN_UL_LightMixer_Group_Members_List,
    PRMAN_OT_Renderman_Open_Stylized_Help,
    PRMAN_OT_Renderman_Open_Stylized_Editor
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