from .. import rfb_icons
from ..rfb_utils.prefs_utils import get_pref
import bpy

# ------- Subclassed Panel Types -------
class _RManPanelHeader():
    COMPAT_ENGINES = {'PRMAN_RENDER'}

    @classmethod
    def poll(cls, context):
        return context.engine in cls.COMPAT_ENGINES

    def draw_header(self, context):
        if get_pref('draw_panel_icon', True):
            rfb_icon = rfb_icons.get_icon("rman_blender")
            self.layout.label(text="", icon_value=rfb_icon.icon_id)
        else:
            pass

class RENDERMAN_UL_Basic_UIList(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.prop(item, 'name', text='', emboss=False, icon_value=icon)    

class CollectionPanel(_RManPanelHeader):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'

    def _draw_collection(self, context, layout, ptr, name, operator,
                         opcontext, prop_coll, collection_index, default_name='', ui_list_class="RENDERMAN_UL_Basic_UIList", enable_add_func=None, enable_remove_func=None):
        layout.label(text=name)
        row = layout.row()
        row.template_list(ui_list_class, "PRMAN", ptr, prop_coll, ptr,
                          collection_index, rows=1)
        col = row.column(align=True)

        row = col.row()
        if enable_add_func:
            row.enabled = enable_add_func(context)
        if operator != '':
            op = row.operator(operator, icon="ADD", text="")
            op.context = opcontext
            op.collection = prop_coll
            op.collection_index = collection_index
            op.defaultname = default_name
            op.action = 'ADD'

            row = col.row()
            if enable_remove_func:
                row.enabled = enable_remove_func(context)
            op = row.operator(operator, icon="REMOVE", text="")
            op.context = opcontext
            op.collection = prop_coll
            op.collection_index = collection_index
            op.action = 'REMOVE'

        if hasattr(ptr, prop_coll) and len(getattr(ptr, prop_coll)) > 0 and \
                getattr(ptr, collection_index) >= 0:
            idx = getattr(ptr, collection_index)
            coll = getattr(ptr, prop_coll)
            if idx >= len(coll):
                return
            item = coll[idx]
            self.draw_item(layout, context, item)

class PRManButtonsPanel(_RManPanelHeader):
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"

class ShaderNodePanel(_RManPanelHeader):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_label = 'Node Panel'

    bl_context = ""

    @classmethod
    def poll(cls, context):
        if not _RManPanelHeader.poll(context):
            return False
        if cls.bl_context == 'material':
            if context.material and context.material.node_tree != '':
                return True
        if cls.bl_context == 'data':
            if not context.light:
                return False
            if context.light.renderman.use_renderman_node:
                return True
        return False


class ShaderPanel(_RManPanelHeader):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'

    shader_type = 'surface'
    param_exclude = {}

    @classmethod
    def poll(cls, context):
        is_rman = _RManPanelHeader.poll(context)
        if cls.bl_context == 'data' and cls.shader_type == 'light':
            return (hasattr(context, "light") and context.light is not None and is_rman)
        elif cls.bl_context == 'world':
            return (hasattr(context, "world") and context.world is not None and is_rman)
        elif cls.bl_context == 'material':
            return (hasattr(context, "material") and context.material is not None and is_rman)

classes = [
    RENDERMAN_UL_Basic_UIList
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