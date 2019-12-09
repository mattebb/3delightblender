from ..icons.icons import load_icons
from ..rman_utils import prefs_utils

# ------- Subclassed Panel Types -------
class _RManPanelHeader():
    COMPAT_ENGINES = {'PRMAN_RENDER'}

    @classmethod
    def poll(cls, context):
        return context.engine in cls.COMPAT_ENGINES

    def draw_header(self, context):
        if prefs_utils.get_addon_prefs().draw_panel_icon:
            icons = load_icons()
            rfb_icon = icons.get("rfb_panel")
            self.layout.label(text="", icon_value=rfb_icon.icon_id)
        else:
            pass

class CollectionPanel(_RManPanelHeader):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'

    def _draw_collection(self, context, layout, ptr, name, operator,
                         opcontext, prop_coll, collection_index, default_name='', ui_list_class="UI_UL_list"):
        layout.label(text=name)
        row = layout.row()
        row.template_list(ui_list_class, "PRMAN", ptr, prop_coll, ptr,
                          collection_index, rows=1)
        col = row.column(align=True)

        op = col.operator(operator, icon="ADD", text="")
        op.context = opcontext
        op.collection = prop_coll
        op.collection_index = collection_index
        op.defaultname = default_name
        op.action = 'ADD'

        op = col.operator(operator, icon="REMOVE", text="")
        op.context = opcontext
        op.collection = prop_coll
        op.collection_index = collection_index
        op.action = 'REMOVE'

        if hasattr(ptr, prop_coll) and len(getattr(ptr, prop_coll)) > 0 and \
                getattr(ptr, collection_index) >= 0:
            item = getattr(ptr, prop_coll)[getattr(ptr, collection_index)]
            self.draw_item(layout, context, item)