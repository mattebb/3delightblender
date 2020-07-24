import bpy
from bpy.props import StringProperty, IntProperty, CollectionProperty, EnumProperty, BoolProperty
from bpy.types import PropertyGroup, UIList, Operator, Panel
from ..rfb_logger import rfb_log
from .rman_ui_base import _RManPanelHeader
from .rman_ui_base import CollectionPanel
from .rman_ui_base import PRManButtonsPanel
from ..rman_utils.draw_utils import _draw_props
from ..rman_utils import string_utils
from ..rman_utils import scene_utils
from ..rman_utils.draw_utils import _draw_ui_from_rman_config
from .. import rman_config

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
        items.append(('', '__CLEAR__', ''))
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
            chan = aov.dspy_channels[aov.dspy_channels_index]
            chan.light_group = self.properties.light_groups

        return{'FINISHED'}        

class PRMAN_OT_Renderman_layer_add_channel(Operator):
    """Add a new channel"""

    bl_idname = "renderman.dspy_add_channel"
    bl_label = "Add Channel"

    def channel_list(self, context):
        items = []
        pages = dict()
        i = 1
        for nm,settings in rman_config.__RMAN_DISPLAY_CHANNELS__.items():
            page_nm = settings['group']
            lst = None
            if page_nm not in pages:
                pages[page_nm] = []
            lst = pages[page_nm]
            item = ( nm, nm, settings['description'], "", i )
            i += 1
            lst.append(item)

        for page_nm,page_items in pages.items():
            items.append( ("", page_nm, page_nm, "", 0 ) )
            for page_item in page_items:
                items.append(page_item)
        
        return items

    channel_selector: EnumProperty(name="Select Channel",
                        description="Select the channel you want to add",
                        items=channel_list)

    def execute(self, context):
        rm_rl = scene_utils.get_renderman_layer(context)

        if rm_rl:
            aov = rm_rl.custom_aovs[rm_rl.custom_aov_index]
            chan = aov.dspy_channels.add()

            selected_chan = self.properties.channel_selector
            settings = rman_config.__RMAN_DISPLAY_CHANNELS__[selected_chan]
            chan.name = selected_chan
            chan.channel_name = selected_chan
            chan.channel_source = settings['channelSource']
            chan.channel_type = settings['channelType']

        return{'FINISHED'}       

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'channel_selector')

    def invoke(self, context, event):

        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)             

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
            layout.label(text=item.name)

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

        icon = 'DISCLOSURE_TRI_DOWN' if item.show_displaydriver_settings \
            else 'DISCLOSURE_TRI_RIGHT'
        text = item.displaydriver + " Settings:"

        row = col.row()
        row.prop(item, "show_displaydriver_settings", icon=icon, text=text,
                         emboss=False)
        if item.show_displaydriver_settings:
            _draw_props(displaydriver_settings, displaydriver_settings.prop_names, col)   

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
        if rm_rl and rm_rl.custom_aov_index == 0:
            row.enabled = False
        row.operator("renderman.dspy_add_channel", text="Add Channel")
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

        channel = item.dspy_channels[item.dspy_channels_index]

        col = layout.column()
        col.prop(channel, "name")      
        col.prop(channel, 'channel_type')
        col.prop(channel, "channel_source")      

        col = layout.column()
        icon = 'DISCLOSURE_TRI_DOWN' if channel.show_advanced \
            else 'DISCLOSURE_TRI_RIGHT'

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
            split = col.split(factor=0.95)
            split.prop(channel, "light_group")
            split.operator_menu_enum('renderman.dspychan_set_light_group', 'light_groups', text='', icon='DISCLOSURE_TRI_DOWN')
            
            # FIXME: don't show for now
            # col.prop(channel, "object_group")

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        rm = scene.renderman
        rm_rl = None
        active_layer = context.view_layer
        for l in rm.render_layers:
            if l.render_layer == active_layer.name:
                rm_rl = l
                break
        if rm_rl is None:
            layout.operator('renderman.dspy_convert_renderman_displays')
            layout.prop(scene.render.image_settings, "file_format")
            split = layout.split()
            col = split.column()
            rl = active_layer
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
        rm_rl = None
        active_layer = context.view_layer
        for l in rm.render_layers:
            if l.render_layer == active_layer.name:
                rm_rl = l
                break
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
        scene = context.scene
        scene.renderman.render_layers.add()
        active_layer = context.view_layer
        # this sucks.  but can't find any other way to refer to render layer
        scene.renderman.render_layers[-1].render_layer = active_layer.name

        # add the already existing passes
        scene = context.scene
        rm = scene.renderman
        rm_rl = scene.renderman.render_layers[-1]
        active_layer = context.view_layer

        rl = active_layer

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
                    channel = aov_setting.dspy_channels.add()
                    channel.name = 'Ci'
                    channel.channel_name = 'Ci'
                    channel.channel_source = 'Ci'
                    channel.channel_type = 'color'
                    channel = aov_setting.dspy_channels.add()
                    channel.name = 'a'
                    channel.channel_name = 'a'
                    channel.channel_source = 'a'
                    channel.channel_type = 'float'   

                else:
                    aov_setting = rm_rl.custom_aovs.add()
                    aov_setting.name = name

                    settings = rman_config.__RMAN_DISPLAY_CHANNELS__[source]

                    channel = aov_setting.dspy_channels.add()
                    channel.name = name
                    channel.channel_name = name  
                    channel.channel_source = settings['channelSource']
                    channel.channel_type = settings['channelType']                  

        return {'FINISHED'}

class PRMAN_OT_RenderMan_Add_Dspy_Template(bpy.types.Operator):
    bl_idname = "renderman.dspy_rman_add_dspy_template"
    bl_label = "Add Display Template"
    bl_description = "Add a display from a display template"
    bl_options = {"REGISTER", "UNDO"}

    def dspy_template_items(self, context):
        items = []
        for nm, props in rman_config.__RMAN_DISPLAY_TEMPLATES__.items():
            items.append((nm, nm, ''))
        return items        

    dspy_template: EnumProperty(items=dspy_template_items, name="Add Display Template")

    def execute(self, context):     
        # add the already existing passes
        scene = context.scene
        rm = scene.renderman
        rm_rl = scene.renderman.render_layers[-1]

        rman_dspy_channels = rman_config.__RMAN_DISPLAY_CHANNELS__
        tmplt = rman_config.__RMAN_DISPLAY_TEMPLATES__[self.dspy_template]

        aov_setting = rm_rl.custom_aovs.add()
        aov_setting.name = self.dspy_template

        for chan in tmplt['channels']:
            channel = aov_setting.dspy_channels.add()
            settings = rman_dspy_channels[chan]
            channel.name = chan
            channel.channel_name = chan
            channel.channel_source = settings['channelSource']
            channel.channel_type = settings['channelType']
            stats_type = settings.get('statistics', 'none')
            channel.stats_type = stats_type
     
        return {"FINISHED"}        


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
    PRMAN_OT_add_renderman_aovs
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