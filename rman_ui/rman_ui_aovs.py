import bpy
import os
from bpy.props import StringProperty, IntProperty, CollectionProperty, EnumProperty, BoolProperty
from bpy.types import PropertyGroup, UIList, Operator, Panel, Menu
from ..rfb_logger import rfb_log
from .rman_ui_base import _RManPanelHeader
from .rman_ui_base import CollectionPanel
from .rman_ui_base import PRManButtonsPanel
from ..rfb_utils.draw_utils import get_open_close_icon, draw_props
from ..rfb_utils import string_utils
from ..rfb_utils import scene_utils
from ..rfb_utils.envconfig_utils import envconfig
from ..rfb_utils.draw_utils import _draw_ui_from_rman_config
from .. import rman_config
from ..rman_render import RmanRender

class COLLECTION_OT_rman_dspy_add_remove(bpy.types.Operator):
    bl_label = "Add or Remove RenderMan Displays"
    bl_idname = "renderman.dspy_add_remove"
    bl_description = "Add or remove RenderMan AOVs"

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

        # otherwise just add an empty one
        if self.properties.action == 'ADD':
            collection.add()

            index += 1
            setattr(rm, coll_idx, index)
            collection[-1].name = '%s_%d' % (self.properties.defaultname, len(collection))

        elif self.properties.action == 'REMOVE':
            if index == 0 or len(collection) == 1:
                rfb_log().error("Cannot delete the beauty display.")
                return {'FINISHED'}
            else:
                collection.remove(index)
                setattr(rm, coll_idx, index - 1)

        return {'FINISHED'}

class PRMAN_OT_Renderman_layer_channel_set_light_group(Operator):
    """Set Light Group for Display Channel"""

    bl_idname = "renderman.dspychan_set_light_group"
    bl_label = "Set Light Group"

    def light_groups_list(self, context):
        items = []
        lgt_grps = scene_utils.get_light_groups_in_scene(context.scene)
        items.append(('__CLEAR__', '__CLEAR__', ''))
        for nm in lgt_grps.keys():
            items.append((nm, nm, ''))
        return items

    light_groups: EnumProperty(name="Light Groups",
                        description="Select the light group you want to add",
                        items=light_groups_list)

    def execute(self, context):
        rm_rl = scene_utils.get_renderman_layer(context)

        if rm_rl:
            aov = rm_rl.custom_aovs[rm_rl.custom_aov_index]
            chan_ptr = aov.dspy_channels[aov.dspy_channels_index]
            chan = rm_rl.dspy_channels[chan_ptr.dspy_chan_idx]
            
            chan_light_group = self.properties.light_groups
            if chan_light_group == '__CLEAR__':
                chan_light_group = ''
            if chan_light_group != '':
                chan_name = '%s_%s' % (chan.name, chan_light_group)
            else:
                # find original name
                for nm,settings in rman_config.__RMAN_DISPLAY_CHANNELS__.items():
                    if chan.channel_source == settings['channelSource'] and chan.channel_type == settings['channelType']:
                        chan_name = nm
                        break
            for idx, c in enumerate(rm_rl.dspy_channels):
                # this channel with the same light group already exists
                # use that instead
                if chan_name == c.name and chan_light_group == c.light_group:
                    chan_ptr.dspy_chan_idx = idx
                    return

            chan.light_group = chan_light_group
            chan.name = chan_name

        return{'FINISHED'}        

class PRMAN_OT_Renderman_layer_add_channel(Operator):
    """Add a new channel"""

    bl_idname = "renderman.dspy_add_channel"
    bl_label = "Add Channel"

    channel_selector: StringProperty(name="Select Channel",
                        description="Select the channel you want to add",
                        default='')    

    def execute(self, context):
        rm_rl = scene_utils.get_renderman_layer(context)

        if rm_rl:
            selected_chan = self.properties.channel_selector
            aov = rm_rl.custom_aovs[rm_rl.custom_aov_index] 

            chan = None
            chan_idx = -1
            for idx, c in enumerate(rm_rl.dspy_channels):
                if c.name == selected_chan:
                    chan = c
                    chan_idx = idx
                    break
            if not chan:
                chan = rm_rl.dspy_channels.add()
                chan_idx = len(rm_rl.dspy_channels)-1
                chan.name = selected_chan    
                chan.channel_name = selected_chan
                if selected_chan == 'Custom':
                    chan.is_custom = True

                settings = rman_config.__RMAN_DISPLAY_CHANNELS__.get(selected_chan, None)
                if settings:
                    chan.channel_source = settings['channelSource']
                    chan.channel_type = settings['channelType']

            chan_ptr = aov.dspy_channels.add()  
            aov.dspy_channels_index = len(aov.dspy_channels)-1   
            chan_ptr.dspy_chan_idx = chan_idx

        return{'FINISHED'}       

class PRMAN_OT_Renderman_layer_delete_channel(Operator):
    """Delete a channel"""

    bl_idname = "renderman.dspychan_delete_channel"
    bl_label = "Delete Channel"

    def execute(self, context):
        rm_rl = scene_utils.get_renderman_layer(context)
        if rm_rl:
            aov = rm_rl.custom_aovs[rm_rl.custom_aov_index]
            idx = aov.dspy_channels_index
            chan = aov.dspy_channels.remove(aov.dspy_channels_index)  

        return{'FINISHED'}         

class PRMAN_UL_Renderman_aov_list(UIList):
    """RenderMan AOV UIList."""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="")        

class PRMAN_UL_Renderman_channel_list(UIList):
    """RenderMan Channel UIList."""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            rm_rl = scene_utils.get_renderman_layer(context)
            if item.dspy_chan_idx > -1:
                chan = rm_rl.dspy_channels[item.dspy_chan_idx]
                layout.label(text=chan.name)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="")                 

class RENDER_PT_layer_custom_aovs(CollectionPanel, Panel):
    bl_label = "Passes"
    bl_context = "view_layer"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine in {'PRMAN_RENDER'}

    def draw_item(self, layout, context, item):
        scene = context.scene
        rm = scene.renderman

        col = layout.column()
        col.label(text='Display Options (%s)' % item.name)
        row = col.row()
        rm_rl = scene_utils.get_renderman_layer(context)
        if rm_rl and rm_rl.custom_aov_index == 0:
            # don't allow renaming beauty display
            row.enabled = False
        row.prop(item, "name")
        
        row = col.row()
        row.prop(item, "displaydriver")
        displaydriver_settings = getattr(item, "%s_settings" % item.displaydriver)

        icon = get_open_close_icon(item.show_displaydriver_settings)
        text = item.displaydriver + " Settings:"

        row = col.row()
        row.prop(item, "show_displaydriver_settings", icon=icon, text=text,
                         emboss=False)
        if item.show_displaydriver_settings:
            draw_props(displaydriver_settings, displaydriver_settings.prop_names, col)   

        row = col.row()
        row.prop(item, 'camera')

        if rm.rman_bake_mode != 'pattern':
            row = col.row()
            row.prop(item, 'aov_bake')        

        # denoise options
        row = col.row()
        row.prop(item, 'denoise')
        row = col.row()
        row.enabled = item.denoise
        row.prop(item, 'denoise_mode')

        row = col.row()
        row.label(text='')
        row = col.row()
        row.label(text="Channels")
        row = col.row()
        if rm_rl and rm_rl.custom_aov_index == 0 and not envconfig().getenv('RFB_DUMP_RIB'):
            row.enabled = False
        row.menu('PRMAN_MT_renderman_create_dspychan_menu', text='Add Channel')
        row.operator("renderman.dspychan_delete_channel", text="Delete Channel")
        row = col.row()
        row.template_list("PRMAN_UL_Renderman_channel_list", "PRMAN", item, "dspy_channels", item,
                          "dspy_channels_index", rows=1)

        if rm_rl and rm_rl.custom_aov_index == 0:
            return

        if item.dspy_channels_index < 0:
            return

        if len(item.dspy_channels) < 1:
            return

        if item.dspy_channels_index >= len(item.dspy_channels):
            return

        channel_ptr = item.dspy_channels[item.dspy_channels_index]
        if channel_ptr.dspy_chan_idx < 0:
            return 
        channel = rm_rl.dspy_channels[channel_ptr.dspy_chan_idx]

        col = layout.column()
        if not channel.is_custom:
            col.enabled = False
        col.prop(channel, "name")      
        col.prop(channel, 'channel_type')
        col.prop(channel, "channel_source")      

        col = layout.column()
        icon = get_open_close_icon(channel.show_advanced)

        row = col.row()
        row.prop(channel, "show_advanced", icon=icon, text="Advanced",
                 emboss=False)
        if channel.show_advanced:
            col.label(text="Exposure Settings")
            col.prop(channel, "exposure_gain")
            col.prop(channel, "exposure_gamma")

            col = layout.column()
            col.label(text="Remap Settings")
            row = col.row(align=True)
            row.prop(channel, "remap_a", text="A")
            row.prop(channel, "remap_b", text="B")
            row.prop(channel, "remap_c", text="C")
            layout.separator()
            if rm.hider_pixelFilterMode != 'importance':
                row = col.row()
                row.prop(channel, "chan_pixelfilter")
                row = col.row()
                if channel.chan_pixelfilter != 'default':
                    row.prop(channel, "chan_pixelfilter_x", text="Size X")
                    row.prop(channel, "chan_pixelfilter_y", text="Size Y")
                layout.separator()
            row = col.row()
            row.prop(channel, "stats_type")
            layout.separator()
            row = col.row()
            row.prop(channel, "shadowthreshold")            
            layout.separator()
            split = col.split(factor=0.95)
            split.prop(channel, "light_group")
            split.operator_menu_enum('renderman.dspychan_set_light_group', 'light_groups', text='', icon='DISCLOSURE_TRI_DOWN')
            
            # FIXME: don't show for now
            # col.prop(channel, "object_group")

    def draw(self, context):
        layout = self.layout
        scene = context.scene      
        active_layer = context.view_layer
        rm_rl = active_layer.renderman

        if not rm_rl.use_renderman:
            layout.operator('renderman.dspy_convert_renderman_displays')
            layout.prop(scene.render.image_settings, "file_format")
            split = layout.split()
            col = split.column()
            rl = context.view_layer
            col.prop(rl, "use_pass_z")
            col.prop(rl, "use_pass_normal")
            col.prop(rl, "use_pass_vector")
            col.prop(rl, "use_pass_uv")
            col.prop(rl, "use_pass_object_index")

            col = split.column()
            col.label(text="Diffuse:")
            row = col.row(align=True)
            row.prop(rl, "use_pass_diffuse_direct", text="Direct", toggle=True)
            row.prop(rl, "use_pass_diffuse_indirect",
                     text="Indirect", toggle=True)
            row.prop(rl, "use_pass_diffuse_color", text="Albedo", toggle=True)
            col.label(text="Specular:")
            row = col.row(align=True)
            row.prop(rl, "use_pass_glossy_direct", text="Direct", toggle=True)
            row.prop(rl, "use_pass_glossy_indirect",
                     text="Indirect", toggle=True)

            col.prop(rl, "use_pass_subsurface_indirect", text="Subsurface")
            col.prop(rl, "use_pass_emit", text="Emission")

            col.prop(rl, "use_pass_ambient_occlusion")
        else:  
            if scene.renderman.is_rman_interactive_running:
                layout.operator("renderman.dspy_displays_reload")            
            layout.operator_menu_enum(
                "renderman.dspy_rman_add_dspy_template", 'dspy_template', text="Add Display Template")  
            layout.context_pointer_set("pass_list", rm_rl)
            self._draw_collection(context, layout, rm_rl, "AOVs",
                                  "renderman.dspy_add_remove", "pass_list",
                                  "custom_aovs", "custom_aov_index", default_name='dspy',
                                  ui_list_class='PRMAN_UL_Renderman_aov_list')

class RENDER_PT_layer_options(PRManButtonsPanel, Panel):
    bl_label = "Layer"
    bl_context = "render_layer"

    def draw(self, context):
        layout = self.layout

        scene = context.scene
        rd = scene.render
        rl = rd.layers.active

        split = layout.split()

        col = split.column()
        col.prop(scene, "layers", text="Scene")

        rm = scene.renderman
        rm_rl = scene_utils.get_renderman_layer(context)
        if rm_rl is None:
            return
        else:
            split = layout.split()
            col = split.column()


class PRMAN_OT_add_renderman_aovs(bpy.types.Operator):
    bl_idname = 'renderman.dspy_convert_renderman_displays'
    bl_label = "Switch to RenderMan Displays"
    bl_description = "Convert curent view layer to use RenderMan Display system"

    def execute(self, context):
        active_layer = context.view_layer
        # add the already existing passes
        rm_rl = active_layer.renderman
        rm_rl.use_renderman = True

        blender_aovs = [
            ('rgba', active_layer.use_pass_combined, ''),
            ('z_depth', active_layer.use_pass_z, 'z'),
            ('Nn', active_layer.use_pass_normal, "Normal"),
            ("dPdtime", active_layer.use_pass_vector, "Vectors"),
            ("u", active_layer.use_pass_uv, "u"),
            ("v", active_layer.use_pass_uv, "v"),
            ("id", active_layer.use_pass_object_index, "id"),
            ("blender_shadows", active_layer.use_pass_shadow, "Shadows"),
            ("blender_diffuse", active_layer.use_pass_diffuse_direct, "Diffuse"),
            ("blender_indirectdiffuse", active_layer.use_pass_diffuse_indirect, "IndirectDiffuse"),
            ("blender_albedo", active_layer.use_pass_diffuse_color, "Albedo"),
            ("blender_specular", active_layer.use_pass_glossy_direct, "Specular"),
            ("blender_indirectspecular", active_layer.use_pass_glossy_indirect, "IndirectSpecular"),
            ("blender_subsurface", active_layer.use_pass_subsurface_indirect,"Subsurface"),
            ("blender_emission", active_layer.use_pass_emit, "Emission")
        ]     

        for source, attr, name in blender_aovs:
            if attr:
                if source == "rgba":
                    aov_setting = rm_rl.custom_aovs.add()
                    aov_setting.name = 'beauty'
                    channel = rm_rl.dspy_channels.add()
                    channel.name = 'Ci'
                    channel.channel_name = 'Ci'
                    channel.channel_source = 'Ci'
                    channel.channel_type = 'color'     
                    chan_ptr = aov_setting.dspy_channels.add()                                   
                    chan_ptr.name = 'Ci'
                    chan_ptr.dspy_chan_idx = 0

                    channel = rm_rl.dspy_channels.add()
                    channel.name = 'a'
                    channel.channel_name = 'a'
                    channel.channel_source = 'a'
                    channel.channel_type = 'float'     
                    chan_ptr = aov_setting.dspy_channels.add()                                   
                    chan_ptr.name = 'a'
                    chan_ptr.dspy_chan_idx = 1                   

                else:                
                    aov_setting = rm_rl.custom_aovs.add()
                    aov_setting.name = name
                    settings = rman_config.__RMAN_DISPLAY_CHANNELS__[source]
                    channel = rm_rl.dspy_channels.add()
                    channel.name = name
                    channel.channel_name = name
                    channel.channel_source = settings['channelSource']
                    channel.channel_type = settings['channelType']
                    chan_ptr = aov_setting.dspy_channels.add()                                   
                    chan_ptr.name = name
                    chan_ptr.dspy_chan_idx = len(rm_rl.dspy_channels)-1

        return {'FINISHED'}

class PRMAN_OT_RenderMan_Add_Dspy_Template(bpy.types.Operator):
    bl_idname = "renderman.dspy_rman_add_dspy_template"
    bl_label = "Add Display Template"
    bl_description = "Add a display from a display template"
    bl_options = {"REGISTER", "UNDO"}

    def dspy_template_items(self, context):
        items = []
        for nm, props in rman_config.__RMAN_DISPLAY_TEMPLATES__.items():
            hidden = props.get('hidden', 0)
            if not hidden:
                items.append((nm, nm, ''))
        return items        

    dspy_template: EnumProperty(items=dspy_template_items, name="Add Display Template")

    def execute(self, context):     
        # add the already existing passes
        scene = context.scene
        rm = scene.renderman
        rm_rl = scene_utils.get_renderman_layer(context)
        if not rm_rl.use_renderman:
            bpy.ops.renderman.dspy_convert_renderman_displays('EXEC_DEFAULT')

        rman_dspy_channels = rman_config.__RMAN_DISPLAY_CHANNELS__
        tmplt = rman_config.__RMAN_DISPLAY_TEMPLATES__[self.dspy_template]

        aov_setting = rm_rl.custom_aovs.add()
        dspy_name = tmplt.get('displayName', self.dspy_template)
        aov_setting.name = dspy_name

        for chan in tmplt['channels']:
            channel = None
            for c in rm_rl.dspy_channels:
                if c.name == chan:
                    channel = c
                    break
            if not channel:
                channel = rm_rl.dspy_channels.add()
                settings = rman_dspy_channels[chan]
                channel.name = chan
                channel.channel_name = chan
                channel.channel_source = settings['channelSource']
                channel.channel_type = settings['channelType']
                stats_type = settings.get('statistics', 'none')
                channel.stats_type = stats_type                

            chan_ptr = aov_setting.dspy_channels.add()                                   
            chan_ptr.name = chan
            chan_ptr.dspy_chan_idx = len(rm_rl.dspy_channels)-1            
     
        return {"FINISHED"}        

class PRMAN_OT_Renderman_Displays_Reload(Operator):
    """AOVs Reaload"""

    bl_idname = "renderman.dspy_displays_reload"
    bl_label = "Displays Reload"
    bl_description = "Tell RenderMan to re-read the displays during IPR"

    def execute(self, context):     
        rman_render = RmanRender.get_rman_render()   
        rman_render.rman_scene_sync.update_displays(context) 

        return {"FINISHED"}   


class PRMAN_MT_renderman_create_dspychan_menu(Menu):
    bl_label = ""
    bl_idname = "PRMAN_MT_renderman_create_dspychan_menu"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None    

    def draw(self, context):
        layout = self.layout

        op = layout.operator("renderman.dspy_add_channel", text='Custom')
        op.channel_selector = 'Custom'
        layout.menu('PRMAN_MT_renderman_create_dspychan_submenu_existing')

        groups = list()
        for nm,settings in rman_config.__RMAN_DISPLAY_CHANNELS__.items():
            group = settings['group']
            if group not in groups:
                groups.append(group)               

        for grp in groups:
            nm_cleanup = grp.replace(' ', '_')
            layout.menu('PRMAN_MT_renderman_create_dspychan_submenu_%s' % nm_cleanup)
     

class PRMAN_MT_renderman_create_dspychan_submenu_existing(Menu):
    bl_label = "Existing"
    bl_idname = "PRMAN_MT_renderman_create_dspychan_submenu_existing"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None    

    def draw(self, context):
        layout = self.layout

        rm_rl = scene_utils.get_renderman_layer(context)
        existing = list()
        for dspy_chan in rm_rl.dspy_channels:
            existing.append(dspy_chan.channel_name)

        for nm in existing:
            op = layout.operator("renderman.dspy_add_channel", text='%s' % nm)
            op.channel_selector = nm                             

classes = [
    COLLECTION_OT_rman_dspy_add_remove,
    PRMAN_OT_Renderman_layer_channel_set_light_group,
    PRMAN_OT_Renderman_layer_add_channel,
    PRMAN_OT_Renderman_layer_delete_channel,
    PRMAN_OT_RenderMan_Add_Dspy_Template,
    PRMAN_UL_Renderman_aov_list,
    PRMAN_UL_Renderman_channel_list,
    RENDER_PT_layer_custom_aovs,
    RENDER_PT_layer_options,
    PRMAN_OT_add_renderman_aovs,
    PRMAN_OT_Renderman_Displays_Reload,
    PRMAN_MT_renderman_create_dspychan_menu,
    PRMAN_MT_renderman_create_dspychan_submenu_existing    
]
    
def register_renderman_dspychan_submenus():
    global classes

    def draw(self, context):
        layout = self.layout  

        rm_rl = scene_utils.get_renderman_layer(context)
 
        aov = rm_rl.custom_aovs[rm_rl.custom_aov_index] 
        aov_channels = list()
        for chan_ptr in aov.dspy_channels:
            if chan_ptr.dspy_chan_idx < 0:
                continue
            chan = rm_rl.dspy_channels[chan_ptr.dspy_chan_idx]
            aov_channels.append(chan.name)

        existing = list()
        for dspy_chan in rm_rl.dspy_channels:
            if dspy_chan.channel_name not in aov_channels:
                existing.append(dspy_chan.channel_name)

        for nm,settings in rman_config.__RMAN_DISPLAY_CHANNELS__.items():
            if nm in existing or nm in aov_channels:
                continue
            group = settings['group'] 
            if group != self.bl_label:
                continue        
            op = layout.operator("renderman.dspy_add_channel", text='%s' % nm)
            op.channel_selector = nm    
                 
    groups = list()
    for nm,settings in rman_config.__RMAN_DISPLAY_CHANNELS__.items():
        group = settings['group']
        if group not in groups:
            groups.append(group)               

    for grp in groups:
        nm_cleanup = grp.replace(' ', '_')
        typename = 'PRMAN_MT_renderman_create_dspychan_submenu_%s' % nm_cleanup
        ntype = type(typename, (Menu,), {})
        ntype.bl_label = grp
        ntype.bl_idname = typename
        if "__annotations__" not in ntype.__dict__:
            setattr(ntype, "__annotations__", {})        
        ntype.draw = draw
        classes.append(ntype)    

def register():

    register_renderman_dspychan_submenus()

    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():

    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass  