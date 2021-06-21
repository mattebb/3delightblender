from .rman_ui_base import _RManPanelHeader
from .rman_ui_base import CollectionPanel
from .rman_ui_base import PRManButtonsPanel
from ..rfb_utils.draw_utils import _draw_ui_from_rman_config
from ..rman_constants import NODE_LAYOUT_SPLIT
from ..rfb_utils import object_utils
from bpy.types import Panel
import bpy

class MESH_PT_renderman_mesh_attrs(CollectionPanel, Panel):
    bl_context = "data"
    bl_label = "Mesh Attributes"

    @classmethod
    def poll(cls, context):
        if not context.mesh:
            return False
        return CollectionPanel.poll(context)

    def draw(self, context):
        layout = self.layout
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False        
        mesh = context.mesh
        rm = mesh.renderman

        _draw_ui_from_rman_config('rman_properties_mesh', 'MESH_PT_renderman_mesh_attrs', context, layout, rm)             

class MESH_PT_renderman_prim_vars(CollectionPanel, Panel):
    bl_context = "data"
    bl_label = "Primitive Variables"

    def draw_item(self, layout, context, item):
        ob = context.object
        if context.mesh:
            geo = context.mesh
        layout.prop(item, "name")

        row = layout.row()
        row.prop(item, "data_source", text="Source")
        if item.data_source == 'VERTEX_COLOR':
            row.prop_search(item, "data_name", geo, "vertex_colors", text="")
        elif item.data_source == 'UV_TEXTURE':
            row.prop_search(item, "data_name", geo, "uv_textures", text="")
        elif item.data_source == 'VERTEX_GROUP':
            row.prop_search(item, "data_name", ob, "vertex_groups", text="")

    @classmethod
    def poll(cls, context):
        if not context.mesh:
            return False
        return CollectionPanel.poll(context)

    def draw(self, context):
        layout = self.layout
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False           
        mesh = context.mesh
        rm = mesh.renderman

        self._draw_collection(context, layout, rm, "Primitive Variables:",
                              "collection.add_remove", "mesh", "prim_vars",
                              "prim_vars_index")

        _draw_ui_from_rman_config('rman_properties_mesh', 'MESH_PT_renderman_prim_vars', context, layout, rm)


        if len(rm.reference_pose) > 0:
            layout.operator('mesh.freeze_reference_pose', text='Re-Freeze Reference Pose')
        else:
            layout.operator('mesh.freeze_reference_pose', text='Freeze Reference Pose')

classes = [
    MESH_PT_renderman_mesh_attrs,
    MESH_PT_renderman_prim_vars  
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