import bpy
from bpy.props import StringProperty, IntProperty, CollectionProperty, EnumProperty, BoolProperty
from bpy.types import PropertyGroup, UIList, Operator, Panel
from ..rfb_logger import rfb_log
from .rman_ui_base import _RManPanelHeader
from .rman_ui_base import CollectionPanel
from ..rman_utils import string_utils
from ..rman_utils import scene_utils

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
            chan.aov_name = 'color Ci'

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
        # ll = rm.light_linking
        # row = layout.row()
        # row.prop(item, "layers")

        col = layout.column()
        col.label(text='Display Options (%s)' % item.name)
        row = col.row()
        rm_rl = scene_utils.get_renderman_layer(context)
        if rm_rl and rm_rl.custom_aov_index == 0:
            # don't allow renaming beauty display
            row.enabled = False
        row.prop(item, "name")
        row = col.row()
        row.prop(item, "aov_display_driver")
        row = col.row()
        row.prop(item, 'camera')

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
        #row.prop(item, aov_name)
        row = col.row()
        row.template_list("UI_UL_list", "PRMAN", item, "dspy_channels", item,
                          "dspy_channels_index", rows=1)

        if item.dspy_channels_index < 0:
            return

        if len(item.dspy_channels) < 1:
            return

        channel = item.dspy_channels[item.dspy_channels_index]

        col = layout.column()
        col.prop(channel, "aov_name")
        if channel.aov_name == "color custom_lpe":
            col.prop(channel, "name")
            col.prop(channel, "custom_lpe_string")

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
            
            # Quantize settings
            """
            row = col.row()
            row.label(text="Quantize Settings:")
            row = col.row(align=True)
            row.prop(channel, "quantize_zero")
            row.prop(channel, "quantize_one")
            row.prop(channel, "quantize_min")
            row.prop(channel, "quantize_max")
            """

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
            split = layout.split()
            col = split.column()
            rl = active_layer
            #col.prop(rl, "use_metadata")
            #col.prop(rl, "use_pass_combined")
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


classes = [
    Renderman_Dspys_COLLECTION_OT_add_remove,
    PRMAN_OT_Renderman_layer_add_channel,
    PRMAN_OT_Renderman_layer_delete_channel,
    PRMAN_UL_Renderman_aov_list,
    RENDER_PT_layer_custom_aovs
]

def register():

    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)   