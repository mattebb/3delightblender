from . import shadergraph_utils
from ..rman_constants import NODE_LAYOUT_SPLIT
from .. import rman_config
from ..icons.icons import load_icons
import bpy

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
                ui_prop = '%s_uio' % ndp.page
                # check if we've already drawn page with arrow
                if ndp.page not in row_dict:

                    ui_open = getattr(parent, ui_prop)
                    icon = 'DISCLOSURE_TRI_DOWN' if ui_open \
                        else 'DISCLOSURE_TRI_RIGHT'

                    row = layout.row(align=True)
                    row.prop(parent, ui_prop, icon=icon, text='',
                        icon_only=True, emboss=False)
                    row.label(text=ndp.page + ':')
                    
                    row = layout.row(align=True)
                    col = row.column()

                    row_dict[ndp.page] = col
                    if not ui_open:
                        continue
                    curr_col = col

                # now, check if this property should be drawn
                elif getattr(parent, ui_prop):
                    curr_col = row_dict[ndp.page]
                else:
                    continue
            else:
                curr_col = row_dict['default']

            if hasattr(ndp, 'conditionalVisOps'):
                # check if the conditionalVisOp to see if we're disabled
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
                _draw_props(node, prop, layout)

        elif prop_meta['renderman_type'] == 'array':
            ui_prop = prop_name + "_uio"
            ui_open = getattr(node, ui_prop)
            icon = 'DISCLOSURE_TRI_DOWN' if ui_open \
                else 'DISCLOSURE_TRI_RIGHT'

            split = layout.split(factor=NODE_LAYOUT_SPLIT)
            row = split.row()
            for i in range(level):
                row.label(text='', icon='BLANK1')

            row.prop(node, ui_prop, icon=icon, text='',
                        icon_only=True, emboss=False)
            sub_prop_names = list(prop)
            arraylen_nm = '%s_arraylen' % prop_name
            arraylen = getattr(node, arraylen_nm) 
            row.label(text=prop_name + ' [%d]:' % arraylen)

            if ui_open:
                row = layout.row(align=True)
                col = row.column()
                row = col.row()                        
                row.prop(node, arraylen_nm, text='Size')
                for i in range(0, arraylen):
                    row = col.row()
                    row.label(text='%s[%d]' % (prop_name, i))
                    row.prop(node, '%s[%d]' % (prop_name, i), text='')
            continue
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
                row.prop(node, prop_name)   


def panel_node_draw(layout, context, id_data, output_type, input_name):
    ntree = id_data.node_tree

    node = shadergraph_utils.find_node(id_data, output_type)
    if not node:
        layout.label(text="No output node")
    else:
        input =  shadergraph_utils.find_node_input(node, input_name)
        #layout.template_node_view(ntree, node, input)
        draw_nodes_properties_ui(layout, context, ntree)

    return True

def draw_nodes_properties_ui(layout, context, nt, input_name='Bxdf',
                             output_node_type="output"):
    output_node = next((n for n in nt.nodes
                        if hasattr(n, 'renderman_node_type') and n.renderman_node_type == output_node_type), None)
    if output_node is None:
        return

    socket = output_node.inputs[input_name]
    node = shadergraph_utils.socket_node_input(nt, socket)

    layout.context_pointer_set("nodetree", nt)
    layout.context_pointer_set("node", output_node)
    layout.context_pointer_set("socket", socket)

    if input_name not in ['Light', 'LightFilter']:
        split = layout.split(factor=0.35)
        split.label(text=socket.name + ':')

        if socket.is_linked:
            split.operator_menu_enum("node.add_%s" % input_name.lower(),
                                    "node_type", text=node.bl_label)
        else:
            split.operator_menu_enum("node.add_%s" % input_name.lower(),
                                    "node_type", text='None')

    if node is not None:
        draw_node_properties_recursive(layout, context, nt, node)


def draw_node_properties_recursive(layout, context, nt, node, level=0):

    icons = load_icons()

    def indented_label(layout, label, level):
        for i in range(level):
            layout.label(text='', icon='BLANK1')
        if label:
            layout.label(text=label)

    layout.context_pointer_set("node", node)
    layout.context_pointer_set("nodetree", nt)

    def draw_props(prop_names, layout, level):
        for prop_name in prop_names:
            is_pxrramp = node.plugin_name == 'PxrRamp'
            if prop_name == "codetypeswitch":
                row = layout.row()
                if node.codetypeswitch == 'INT':
                    row.prop_search(node, "internalSearch",
                                    bpy.data, "texts", text="")
                elif node.codetypeswitch == 'EXT':
                    row.prop(node, "shadercode")
            elif prop_name == "internalSearch" or prop_name == "shadercode" or prop_name == "expression":
                pass
            else:
                prop_meta = node.prop_meta[prop_name]
                prop = getattr(node, prop_name)

                if 'widget' in prop_meta:
                    if prop_meta['widget'] == 'null' or \
                        'hidden' in prop_meta and prop_meta['hidden']:
                        continue
                    elif prop_meta['widget'] == 'colorramp':
                        if is_pxrramp:
                            dummy_nt = bpy.data.node_groups[node.node_group]
                            if dummy_nt:
                                layout.template_color_ramp(
                                    dummy_nt.nodes["ColorRamp"], 'color_ramp')  
                                continue  
                        else:
                            rm = bpy.context.light.renderman
                            node_tree = bpy.context.light.node_tree
                            ramp_node = node_tree.nodes[rm.color_ramp_node]
                            layout.template_color_ramp(ramp_node, 'color_ramp')     
                            continue

                    elif prop_meta['widget'] == 'floatramp':
                        rm = bpy.context.light.renderman
                        node_tree = bpy.context.light.node_tree
                        float_node = node_tree.nodes[rm.float_ramp_node]
                        layout.template_curve_mapping(float_node, 'mapping')                  
                        continue

                # else check if the socket with this name is connected
                socket = node.inputs[prop_name] if prop_name in node.inputs \
                    else None
                layout.context_pointer_set("socket", socket)

                if socket and socket.is_linked:
                    input_node = shadergraph_utils.socket_node_input(nt, socket)
                    icon = 'DISCLOSURE_TRI_DOWN' if socket.ui_open \
                        else 'DISCLOSURE_TRI_RIGHT'

                    split = layout.split(factor=NODE_LAYOUT_SPLIT)
                    row = split.row()
                    indented_label(row, None, level)
                    row.prop(socket, "ui_open", icon=icon, text='',
                             icon_only=True, emboss=False)
                    label = prop_meta.get('label', prop_name)
                    rman_icon = icons.get('out_%s.png' % input_node.bl_label, None )
                    if not rman_icon:
                        rman_icon = icons.get('out_unknown.png')                  
                    row.label(text=label + ':', icon_value=rman_icon.icon_id)
                    if ('type' in prop_meta and prop_meta['type'] == 'vstruct') or prop_name == 'inputMaterial':
                        split.operator_menu_enum("node.add_layer", "node_type",
                                                 text=input_node.bl_label, icon="LAYER_USED")
                    elif prop_meta['renderman_type'] == 'bxdf':
                        split.operator_menu_enum("node.add_bxdf", "node_type",
                                                 text=input_node.bl_label, icon="LAYER_USED")                                                 
                    elif prop_meta['renderman_type'] == 'struct':
                        split.operator_menu_enum("node.add_manifold", "node_type",
                                                 text=input_node.bl_label, icon="LAYER_USED")
                    elif prop_meta['renderman_type'] == 'normal':
                        split.operator_menu_enum("node.add_bump", "node_type",
                                                 text=input_node.bl_label, icon="LAYER_USED")
                    else:
                        split.operator_menu_enum("node.add_pattern", "node_type",
                                                 text=input_node.bl_label, icon="LAYER_USED") 
                    if socket.ui_open:
                        draw_node_properties_recursive(layout, context, nt,
                                                       input_node, level=level + 1)

                else:                    
                    row = layout.row(align=True)
                    if prop_meta['renderman_type'] == 'page':
                        if is_pxrramp:
                            # don't' show the old color ramp
                            if prop_name == 'Color Ramp (Manual)':
                                continue
                        ui_prop = prop_name + "_uio"
                        ui_open = getattr(node, ui_prop)
                        icon = 'DISCLOSURE_TRI_DOWN' if ui_open \
                            else 'DISCLOSURE_TRI_RIGHT'

                        split = layout.split(factor=NODE_LAYOUT_SPLIT)
                        row = split.row()
                        for i in range(level):
                            row.label(text='', icon='BLANK1')

                        row.prop(node, ui_prop, icon=icon, text='',
                                 icon_only=True, emboss=False)
                        sub_prop_names = list(prop)
                        if node.bl_idname in {"PxrSurfaceBxdfNode", "PxrLayerPatternOSLNode"}:
                            for pn in sub_prop_names:
                                if pn.startswith('enable'):
                                    row.prop(node, pn, text='')
                                    sub_prop_names.remove(pn)
                                    break

                        row.label(text=prop_name.split('.')[-1] + ':')

                        if ui_open:
                            draw_props(sub_prop_names, layout, level + 1)
                    elif prop_meta['renderman_type'] == 'array':
                        ui_prop = prop_name + "_uio"
                        ui_open = getattr(node, ui_prop)
                        icon = 'DISCLOSURE_TRI_DOWN' if ui_open \
                            else 'DISCLOSURE_TRI_RIGHT'

                        split = layout.split(factor=NODE_LAYOUT_SPLIT)
                        row = split.row()
                        for i in range(level):
                            row.label(text='', icon='BLANK1')

                        row.prop(node, ui_prop, icon=icon, text='',
                                 icon_only=True, emboss=False)
                        sub_prop_names = list(prop)
                        arraylen = getattr(node, '%s_arraylen' % prop_name)
                        prop_label = prop_meta.get('label', prop_name)
                        row.label(text=prop_label + ' [%d]:' % arraylen)

                        if ui_open:
                            row = layout.row(align=True)
                            col = row.column()
                            row = col.row()
                            indented_label(row, None, level)                     
                            row.prop(node, '%s_arraylen' % prop_name, text='Size')
                            for i in range(0, arraylen):
                                row = col.row()
                                array_elem_nm = '%s[%d]' % (prop_name, i)
                                indented_label(row, None, level)
                                row.label(text='%s[%d]' % (prop_label, i))
                                row.prop(node, array_elem_nm, text='')
                                if array_elem_nm in node.inputs:
                                    if prop_meta['renderman_array_type'] == 'bxdf':
                                        row.operator_menu_enum("node.add_bxdf", "node_type",
                                                            text='', icon="LAYER_USED")                                                       
                                    elif prop_meta['renderman_array_type'] == 'struct':
                                        row.operator_menu_enum("node.add_manifold", "node_type",
                                                            text='', icon="LAYER_USED")
                                    elif prop_meta['renderman_array_type'] == 'normal':
                                        row.operator_menu_enum("node.add_bump", "node_type",
                                                            text='', icon="LAYER_USED")
                                    else:
                                        row.operator_menu_enum("node.add_pattern", "node_type",
                                                            text='', icon="LAYER_USED")
                        continue
                    else:
                        if is_pxrramp and prop_name == 'useNewRamp':
                            # don't show useNewRamp param
                            continue                        
                        indented_label(row, None, level)
                        # indented_label(row, socket.name+':')
                        
                        # don't draw prop for struct type
                        if "Subset" in prop_name and prop_meta['type'] == 'string':
                            row.prop_search(node, prop_name, bpy.data.scenes[0].renderman,
                                            "object_groups")
                        else:
                            if prop_meta['renderman_type'] not in ['struct', 'bxdf']:
                                row.prop(node, prop_name, slider=True)
                            else:
                                row.label(text=prop_meta['label'])
                        if prop_name in node.inputs:
                            if ('type' in prop_meta and prop_meta['type'] == 'vstruct') or prop_name == 'inputMaterial':
                                row.operator_menu_enum("node.add_layer", "node_type",
                                                       text='', icon="LAYER_USED")
                            elif prop_meta['renderman_type'] == 'bxdf':
                                row.operator_menu_enum("node.add_bxdf", "node_type",
                                                       text='', icon="LAYER_USED")                                                       
                            elif prop_meta['renderman_type'] == 'struct':
                                row.operator_menu_enum("node.add_manifold", "node_type",
                                                       text='', icon="LAYER_USED")
                            elif prop_meta['renderman_type'] == 'normal':
                                row.operator_menu_enum("node.add_bump", "node_type",
                                                       text='', icon="LAYER_USED")
                            else:
                                row.operator_menu_enum("node.add_pattern", "node_type",
                                                       text='', icon="LAYER_USED")

    # if this is a cycles node do something different
    if not hasattr(node, 'plugin_name') or node.bl_idname == 'PxrOSLPatternNode':
        node.draw_buttons(context, layout)
        for input in node.inputs:
            if input.is_linked:
                input_node = shadergraph_utils.socket_node_input(nt, input)
                icon = 'DISCLOSURE_TRI_DOWN' if input.show_expanded \
                    else 'DISCLOSURE_TRI_RIGHT'

                split = layout.split(factor=NODE_LAYOUT_SPLIT)
                row = split.row()
                indented_label(row, None, level)
                row.prop(input, "show_expanded", icon=icon, text='',
                         icon_only=True, emboss=False)
                row.label(text=input.name + ':')
                split.operator_menu_enum("node.add_pattern", "node_type",
                                         text=input_node.bl_label, icon="LAYER_USED")

                if input.show_expanded:
                    draw_node_properties_recursive(layout, context, nt,
                                                   input_node, level=level + 1)

            else:
                row = layout.row(align=True)
                indented_label(row, None, level)
                # indented_label(row, socket.name+':')
                # don't draw prop for struct type
                if input.hide_value:
                    row.label(text=input.name)
                else:
                    row.prop(input, 'default_value',
                             slider=True, text=input.name)
                row.operator_menu_enum("node.add_pattern", "node_type",
                                       text='', icon="LAYER_USED")
    else:
        draw_props(node.prop_names, layout, level)
    layout.separator()
