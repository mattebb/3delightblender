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

class Renderman_Dspys_COLLECTION_OT_add_remove(bpy.types.Operator):
    bl_label = "Add or Remove Paths"
    bl_idname = "rman_dspys_collection.add_remove"

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


class PRMAN_OT_Renderman_layer_add_channel(Operator):
    """Add a new channel"""

    bl_idname = "rman_dspy_channel_list.add_channel"
    bl_label = "Add Channel"

    def execute(self, context):
        rm_rl = scene_utils.get_renderman_layer(context)

        if rm_rl:
            aov = rm_rl.custom_aovs[rm_rl.custom_aov_index]
            chan = aov.dspy_channels.add()
            chan.channel_def = 'color Ci'
            chan.name = 'Ci'
            chan.channel_name = 'Ci'

        return{'FINISHED'}       

class PRMAN_OT_Renderman_layer_delete_channel(Operator):
    """Delete a channel"""

    bl_idname = "rman_dspy_channel_list.delete_channel"
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
        row.operator("rman_dspy_channel_list.add_channel", text="Add Channel")
        row.operator("rman_dspy_channel_list.delete_channel", text="Delete Channel")
        row = col.row()
        row.template_list("UI_UL_list", "PRMAN", item, "dspy_channels", item,
                          "dspy_channels_index", rows=1)

        if item.dspy_channels_index < 0:
            return

        if len(item.dspy_channels) < 1:
            return

        channel = item.dspy_channels[item.dspy_channels_index]

        col = layout.column()
        col.prop(channel, "channel_selector")
        if channel.channel_def == "color custom_lpe":
            col.prop(channel, "name")
            col.prop(channel, "custom_lpe_string")
        else:
            col.prop(channel, "name")            

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
            col.prop(channel, "light_group")
            
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
            layout.operator('renderman.add_renderman_aovs')
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
            layout.context_pointer_set("pass_list", rm_rl)
            self._draw_collection(context, layout, rm_rl, "AOVs",
                                  "rman_dspys_collection.add_remove", "pass_list",
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
    bl_idname = 'renderman.add_renderman_aovs'
    bl_label = "Switch to RenderMan Passes"

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

        aovs = [
            # (name, do?, declare type/name, source)
            ("color rgba", active_layer.use_pass_combined, "rgba"),
            ("float z", active_layer.use_pass_z, "z_depth"),
            ("normal Nn", active_layer.use_pass_normal, "Normal"),
            ("vector dPdtime", active_layer.use_pass_vector, "Vectors"),
            ("float u", active_layer.use_pass_uv, "u"),
            ("float v", active_layer.use_pass_uv, "v"),
            ("float id", active_layer.use_pass_object_index, "id"),
            ("color lpe:shadows;C[<.D><.S>]<L.>",
             active_layer.use_pass_shadow, "Shadows"),
            ("color lpe:C<.D><L.>",
             active_layer.use_pass_diffuse_direct, "Diffuse"),
            ("color lpe:(C<RD>[DS]+<L.>)|(C<RD>[DS]*O)",
             active_layer.use_pass_diffuse_indirect, "IndirectDiffuse"),
            ("color lpe:nothruput;noinfinitecheck;noclamp;unoccluded;overwrite;C(U2L)|O",
             active_layer.use_pass_diffuse_color, "Albedo"),
            ("color lpe:C<.S><L.>",
             active_layer.use_pass_glossy_direct, "Specular"),
            ("color lpe:(C<RS>[DS]+<L.>)|(C<RS>[DS]*O)",
             active_layer.use_pass_glossy_indirect, "IndirectSpecular"),
            ("color lpe:(C<TD>[DS]+<L.>)|(C<TD>[DS]*O)",
             active_layer.use_pass_subsurface_indirect, "Subsurface"),
            ("color lpe:emission", active_layer.use_pass_emit, "Emission"),
        ]

        for aov_type, attr, name in aovs:
            if attr:
                if name == "rgba":
                    aov_setting = rm_rl.custom_aovs.add()
                    aov_setting.name = 'beauty'
                    channel = aov_setting.dspy_channels.add()
                    channel.name = 'Ci'
                    channel.channel_name = 'Ci'
                    channel.channel_def = 'color Ci'
                    channel = aov_setting.dspy_channels.add()
                    channel.name = 'a'
                    channel.channel_name = 'a'
                    channel.channel_def = 'float a'    

                else:
                    aov_setting = rm_rl.custom_aovs.add()
                    aov_setting.name = name

                    channel = aov_setting.dspy_channels.add()
                    channel.name = name
                    channel.channel_def = aov_type
                    channel.channel_name = name                    

        return {'FINISHED'}


classes = [
    Renderman_Dspys_COLLECTION_OT_add_remove,
    PRMAN_OT_Renderman_layer_add_channel,
    PRMAN_OT_Renderman_layer_delete_channel,
    PRMAN_UL_Renderman_aov_list,
    RENDER_PT_layer_custom_aovs,
    RENDER_PT_layer_options,
    PRMAN_OT_add_renderman_aovs
]

def register():

    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)   