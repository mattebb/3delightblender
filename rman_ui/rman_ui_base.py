from ..icons.icons import load_icons
from ..rman_utils import prefs_utils
from .. import rman_config
from ..rman_constants import NODE_LAYOUT_SPLIT

def _draw_ui_from_rman_config(config_name, panel, context, layout, parent):
    row_dict = dict()
    row = layout.row(align=True)
    col = row.column(align=True)
    row_dict['default'] = col
    rmcfg = rman_config.__RMAN_CONFIG__.get(config_name, None)

    curr_col = col
    for param_name, ndp in rmcfg.params.items():

        if ndp.panel == panel:
            if not hasattr(parent, ndp.name):
                continue

            if hasattr(ndp, 'page') and ndp.page != '':
                if ndp.page not in row_dict:
                    row = layout.row(align=True)
                    row.label(text=ndp.page)
                    row = layout.row(align=True)
                    col = row.column(align=True)
                    row_dict[ndp.page] = col
                curr_col = row_dict[ndp.page]
            else:
                curr_col = row_dict['default']

            if hasattr(ndp, 'conditionalVisOps'):
                expr = ndp.conditionalVisOps['expr']
                node = parent
                if not eval(expr):
                    continue

            label = ndp.label if hasattr(ndp, 'label') else ndp.name
            row = curr_col.row()
            row.prop(parent, ndp.name, text=label)    

def _draw_props(node, prop_names, layout):
    for prop_name in prop_names:
        prop_meta = node.prop_meta[prop_name]
        prop = getattr(node, prop_name)
        row = layout.row()

        if prop_meta['renderman_type'] == 'page':
            ui_prop = prop_name + "_uio"
            ui_open = getattr(node, ui_prop)
            icon = 'DISCLOSURE_TRI_DOWN' if ui_open \
                else 'DISCLOSURE_TRI_RIGHT'

            split = layout.split(factor=NODE_LAYOUT_SPLIT)
            row = split.row()
            row.prop(node, ui_prop, icon=icon, text='',
                     icon_only=True, emboss=False)
            row.label(text=prop_name.split('.')[-1] + ':')

            if ui_open:
                draw_props(node, prop, layout)

        else:
            if 'widget' in prop_meta and prop_meta['widget'] == 'null' or \
                    'hidden' in prop_meta and prop_meta['hidden'] or prop_name == 'combineMode':
                continue

            row.label(text='', icon='BLANK1')
            # indented_label(row, socket.name+':')
            if "Subset" in prop_name and prop_meta['type'] == 'string':
                row.prop_search(node, prop_name, bpy.data.scenes[0].renderman,
                                "object_groups")
            else:
                if 'widget' in prop_meta and prop_meta['widget'] == 'floatRamp':
                    rm = bpy.context.light.renderman
                    nt = bpy.context.light.node_tree
                    float_node = nt.nodes[rm.float_ramp_node]
                    layout.template_curve_mapping(float_node, 'mapping')
                elif 'widget' in prop_meta and prop_meta['widget'] == 'colorRamp':
                    rm = bpy.context.light.renderman
                    nt = bpy.context.light.node_tree
                    ramp_node = nt.nodes[rm.color_ramp_node]
                    layout.template_color_ramp(ramp_node, 'color_ramp')
                else:
                    row.prop(node, prop_name)                           

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

class PRManButtonsPanel(_RManPanelHeader):
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
