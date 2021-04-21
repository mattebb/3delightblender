from . import shadergraph_utils
from ..rman_constants import NODE_LAYOUT_SPLIT
from .. import rman_config
from .. import rfb_icons
import bpy
import re

def draw_indented_label(layout, label, level):
    for i in range(level):
        layout.label(text='', icon='BLANK1')
    if label:
        layout.label(text=label)

def get_open_close_icon(is_open=True):
    icon = 'DISCLOSURE_TRI_DOWN' if is_open \
        else 'DISCLOSURE_TRI_RIGHT'
    return icon

def draw_sticky_toggle(layout, node, prop_name, output_node=None):
    if not output_node:
        return
    if output_node.solo_node_name != '':
        return
    if not output_node.is_sticky_selected():
        return
    sticky_prop = '%s_sticky' % prop_name
    if hasattr(node, sticky_prop):    
        sticky_icon = 'HIDE_ON'
        if getattr(node, sticky_prop):
            sticky_icon = 'HIDE_OFF'                
        layout.prop(node, sticky_prop, text='', icon=sticky_icon, icon_only=True, emboss=False)    

def _draw_ui_from_rman_config(config_name, panel, context, layout, parent):
    row_dict = dict()
    row = layout.row(align=True)
    col = row.column(align=True)
    row_dict['default'] = col
    rmcfg = rman_config.__RMAN_CONFIG__.get(config_name, None)
    is_rman_interactive_running = context.scene.renderman.is_rman_interactive_running
    is_rman_running = context.scene.renderman.is_rman_running

    curr_col = col
    for param_name, ndp in rmcfg.params.items():

        if ndp.panel == panel:
            if not hasattr(parent, ndp.name):
                continue
            
            has_page = False
            page_prop = ''
            page_open = False
            page_name = ''
            editable = getattr(ndp, 'editable', False)
            is_enabled = True
            if hasattr(ndp, 'page') and ndp.page != '':       
                page_prop = ndp.page + "_uio"
                page_open = getattr(parent, page_prop, False)        
                page_name = ndp.page       
                has_page = True

            if has_page:
                # check if we've already drawn page with arrow
                if page_name not in row_dict:

                    row = layout.row(align=True)
                    icon = get_open_close_icon(page_open)
                    row.context_pointer_set("node", parent)               
                    op = row.operator('node.rman_open_close_page', text='', icon=icon, emboss=False) 
                    op.prop_name = page_prop
           
                    row.label(text=page_name)
                    
                    row = layout.row(align=True)
                    col = row.column()

                    row_dict[page_name] = col
                    curr_col = col
                else:
                    curr_col = row_dict[page_name]
            else:
                curr_col = row_dict['default']

            conditionalVisOps = getattr(ndp, 'conditionalVisOps', None)
            if conditionalVisOps:
                # check if the conditionalVisOp to see if we're disabled
                expr = conditionalVisOps.get('expr', None)
                node = parent              
                if expr and not eval(expr):
                    # conditionalLockOps disable the prop rather
                    # than hide them
                    if not hasattr(ndp, 'conditionalLockOps'):
                        continue
                    else:
                        is_enabled = False

            label = ndp.label if hasattr(ndp, 'label') else ndp.name
            row = curr_col.row()
            widget = getattr(ndp, 'widget', '')
            options = getattr(ndp, 'options', None)
            if ndp.is_array():
                if has_page:           
                    if not page_open:
                        continue      
                    row.label(text='', icon='BLANK1')          
                ui_prop = param_name + "_uio"
                ui_open = getattr(parent, ui_prop)
                icon = get_open_close_icon(ui_open)
                row.context_pointer_set("node", parent)               
                op = row.operator('node.rman_open_close_page', text='', icon=icon, emboss=False)  
                op.prop_name = ui_prop

                prop = getattr(parent, param_name)      
                prop_meta = node.prop_meta[param_name]                      
                sub_prop_names = list(prop)
                arraylen_nm = '%s_arraylen' % param_name
                arraylen = getattr(parent, arraylen_nm)
                prop_label = prop_meta.get('label', param_name)
                row.label(text=prop_label + ' [%d]:' % arraylen)
                if ui_open:
                    row2 = curr_col.row()
                    col = row2.column()
                    row3 = col.row()      
                    row3.label(text='', icon='BLANK1')                  
                    row3.prop(parent, arraylen_nm, text='Size')
                    for i in range(0, arraylen):
                        row4 = col.row()
                        row4.label(text='', icon='BLANK1')
                        row4.label(text='%s[%d]' % (prop_label, i))
                        row4.prop(parent, '%s[%d]' % (param_name, i), text='')                

                
            elif widget == 'propSearch' and options:
                # use a prop_search layout
                prop_search_parent = options.get('prop_parent')
                prop_search_name = options.get('prop_name')
                if has_page:
                    row.label(text='', icon='BLANK1')
                eval(f'row.prop_search(parent, ndp.name, {prop_search_parent}, "{prop_search_name}", text=label)')               
            else:    
                if has_page:           
                    if not page_open:
                        continue
                    row.label(text='', icon='BLANK1')
                row.prop(parent, ndp.name, text=label)         

            if is_rman_interactive_running:
                row.enabled = editable
            elif is_rman_running:
                row.enabled = False
            else:
                row.enabled = is_enabled

def draw_prop(node, prop_name, layout, level=0, nt=None, context=None, sticky=False):
    if prop_name == "codetypeswitch":
        row = layout.row()
        if node.codetypeswitch == 'INT':
            row.prop_search(node, "internalSearch",
                            bpy.data, "texts", text="")
        elif node.codetypeswitch == 'EXT':
            row.prop(node, "shadercode")
    elif prop_name == "internalSearch" or prop_name == "shadercode" or prop_name == "expression":
        return
    else:
        prop_meta = node.prop_meta[prop_name]
        prop = getattr(node, prop_name, None)
        if prop is None:
            return

        read_only = prop_meta.get('readOnly', False)
        widget = prop_meta.get('widget', 'default')
        prop_hidden = getattr(node, '%s_hidden' % prop_name, False)
        prop_disabled = getattr(node, '%s_disabled' % prop_name, False)

        if widget == 'null' or prop_hidden:
            return
        elif widget == 'colorramp':
            node_group = bpy.data.node_groups[node.rman_fake_node_group]
            ramp_name =  prop
            ramp_node = node_group.nodes[ramp_name]
            layout.template_color_ramp(
                    ramp_node, 'color_ramp')  
            return       
        elif widget == 'floatramp':
            node_group = bpy.data.node_groups[node.rman_fake_node_group]
            ramp_name =  prop
            ramp_node = node_group.nodes[ramp_name]
            layout.template_curve_mapping(
                    ramp_node, 'mapping')  
            return                      

        # double check the conditionalVisOps
        # this might be our first time drawing, i.e.: scene was just opened.
        conditionalVisOps = prop_meta.get('conditionalVisOps', None)
        if conditionalVisOps:
            cond_expr = conditionalVisOps.get('expr', None)
            if cond_expr:
                try:
                    hidden = not eval(cond_expr)
                    if prop_meta.get('conditionalLockOps', None):
                        setattr(node, '%s_disabled' % prop_name, hidden)
                        prop_disabled = hidden
                        if hasattr(node, 'inputs') and prop_name in node.inputs:
                            node.inputs[prop_name].hide = hidden                        
                    else:
                        setattr(node, '%s_hidden' % prop_name, hidden)
                        if hasattr(node, 'inputs') and prop_name in node.inputs:
                            node.inputs[prop_name].hide = hidden
                        if hidden:
                            return
                except:                        
                    pass

        # else check if the socket with this name is connected
        inputs = getattr(node, 'inputs', dict())
        socket =  inputs.get(prop_name, None)
        layout.context_pointer_set("socket", socket)

        if socket and socket.is_linked:
            input_node = shadergraph_utils.socket_node_input(nt, socket)
            icon = get_open_close_icon(socket.ui_open)

            split = layout.split()
            row = split.row()
            draw_indented_label(row, None, level)
            row.context_pointer_set("socket", socket)               
            row.operator('node.rman_open_close_link', text='', icon=icon, emboss=False)
            label = prop_meta.get('label', prop_name)
            
            rman_icon = rfb_icons.get_icon('out_%s' % input_node.bl_label)               
            row.label(text=label + ' (%s):' % input_node.name)
            if sticky:
                return

            row.context_pointer_set("socket", socket)
            row.context_pointer_set("node", node)
            row.context_pointer_set("nodetree", nt)
            row.menu('NODE_MT_renderman_connection_menu', text='', icon_value=rman_icon.icon_id)
                                    
            if socket.ui_open:
                draw_node_properties_recursive(layout, context, nt,
                                                input_node, level=level + 1)

        else:                    
            row = layout.row(align=True)
            row.enabled = not prop_disabled
            if prop_meta['renderman_type'] == 'page':
                ui_prop = prop_name + "_uio"
                ui_open = getattr(node, ui_prop)
                icon = get_open_close_icon(ui_open)

                split = layout.split(factor=NODE_LAYOUT_SPLIT)
                row = split.row()
                row.enabled = not prop_disabled
                draw_indented_label(row, None, level)

                row.context_pointer_set("node", node)               
                op = row.operator('node.rman_open_close_page', text='', icon=icon, emboss=False)            
                op.prop_name = ui_prop

                sub_prop_names = list(prop)
                if node.bl_idname in {"PxrSurfaceBxdfNode", "PxrLayerPatternOSLNode"}:
                    for pn in sub_prop_names:
                        if pn.startswith('enable'):
                            row.prop(node, pn, text='')
                            sub_prop_names.remove(pn)
                            break

                row.label(text=prop_name.split('.')[-1] + ':')

                if ui_open:
                    draw_props(node, sub_prop_names, layout, level=level + 1, nt=nt, context=context)
            elif prop_meta['renderman_type'] == 'array':
                ui_prop = prop_name + "_uio"
                ui_open = getattr(node, ui_prop)
                icon = get_open_close_icon(ui_open)

                split = layout.split(factor=NODE_LAYOUT_SPLIT)
                row = split.row()
                row.enabled = not prop_disabled
                draw_indented_label(row, None, level)

                row.context_pointer_set("node", node)               
                op = row.operator('node.rman_open_close_page', text='', icon=icon, emboss=False)            
                op.prop_name = ui_prop

                sub_prop_names = list(prop)
                arraylen = getattr(node, '%s_arraylen' % prop_name)
                prop_label = prop_meta.get('label', prop_name)
                row.label(text=prop_label + ' [%d]:' % arraylen)

                if ui_open:
                    level += 1
                    row = layout.row(align=True)
                    col = row.column()
                    row = col.row()
                    draw_indented_label(row, None, level)                     
                    row.prop(node, '%s_arraylen' % prop_name, text='Size')
                    for i in range(0, arraylen):
                        row = layout.row(align=True)
                        col = row.column()                           
                        row = col.row()
                        array_elem_nm = '%s[%d]' % (prop_name, i)
                        draw_indented_label(row, None, level)
                        if draw_connection_menu and array_elem_nm in node.inputs:
                            op_text = ''
                            socket = node.inputs[array_elem_nm]
                            row.context_pointer_set("socket", socket)
                            row.context_pointer_set("node", node)
                            row.context_pointer_set("nodetree", nt)

                            if socket.is_linked:
                                input_node = shadergraph_utils.socket_node_input(nt, socket)
                                rman_icon = rfb_icons.get_icon('out_%s' % input_node.bl_label)
                                row.label(text='%s[%d] (%s):' % (prop_label, i, input_node.name))    
                                row.menu('NODE_MT_renderman_connection_menu', text='', icon_value=rman_icon.icon_id)
                                draw_node_properties_recursive(layout, context, nt, input_node, level=level + 1)
                            else:
                                row.label(text='%s[%d]: ' % (prop_label, i))
                                rman_icon = rfb_icons.get_icon('rman_connection_menu')
                                row.menu('NODE_MT_renderman_connection_menu', text='', icon_value=rman_icon.icon_id)
                return
            else:                      
                draw_indented_label(row, None, level)
                
                if widget == 'propsearch':
                    # use a prop_search layout
                    options = prop_meta['options']
                    prop_search_parent = options.get('prop_parent')
                    prop_search_name = options.get('prop_name')
                    eval(f'row.prop_search(node, prop_name, {prop_search_parent}, "{prop_search_name}")') 
                elif prop_meta['renderman_type'] in ['struct', 'bxdf', 'vstruct']:
                    row.label(text=prop_meta['label'])
                elif read_only:
                    # param is read_only i.e.: it is expected that this param has a connection
                    row.label(text=prop_meta['label'])
                    row2 = row.row()
                    row2.prop(node, prop_name, text="", slider=True)
                    row2.enabled=False                           
                else:
                    row.prop(node, prop_name, slider=True)

                if prop_name in inputs:
                    row.context_pointer_set("socket", socket)
                    row.context_pointer_set("node", node)
                    row.context_pointer_set("nodetree", nt)
                    rman_icon = rfb_icons.get_icon('rman_connection_menu')
                    row.menu('NODE_MT_renderman_connection_menu', text='', icon_value=rman_icon.icon_id)

            if widget in ['fileinput','assetidinput']:                            
                prop_val = getattr(node, prop_name)
                if prop_val != '':
                    row = layout.row(align=True)
                    row.enabled = not prop_disabled
                    draw_indented_label(row, None, level)
                    row.prop(node, '%s_colorspace' % prop_name, text='Color Space')
                    rman_icon = rfb_icons.get_icon('rman_txmanager')        
                    from . import texture_utils
                    from . import scene_utils
                    id = scene_utils.find_node_owner(node)
                    nodeID = texture_utils.generate_node_id(node, prop_name, ob=id)
                    op = row.operator('rman_txmgr_list.open_txmanager', text='', icon_value=rman_icon.icon_id)  
                    op.nodeID = nodeID                             

def draw_props(node, prop_names, layout, level=0, nt=None, context=None):
    layout.context_pointer_set("node", node)
    if nt:
        layout.context_pointer_set("nodetree", nt)

    for prop_name in prop_names:
        draw_prop(node, prop_name, layout, level=level, nt=nt, context=context)

def panel_node_draw(layout, context, id_data, output_type, input_name):
    ntree = id_data.node_tree

    node = shadergraph_utils.find_node(id_data, output_type)
    if not node:
        layout.label(text="No output node")
    else:
        input =  shadergraph_utils.find_node_input(node, input_name)
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

        split.context_pointer_set("socket", socket)
        split.context_pointer_set("node", output_node)
        split.context_pointer_set("nodetree", nt)            
        if socket.is_linked:
            rman_icon = rfb_icons.get_icon('out_%s' % node.bl_label)            
            split.menu('NODE_MT_renderman_connection_menu', text='%s (%s)' % (node.name, node.bl_label), icon_value=rman_icon.icon_id)
        else:
            split.menu('NODE_MT_renderman_connection_menu', text='None', icon='NODE_MATERIAL')            

    if node is not None:
        draw_node_properties_recursive(layout, context, nt, node)

def show_node_sticky_params(layout, node, prop_names, context, nt, output_node, node_label_drawn=False):
    label_drawn = node_label_drawn
    for prop_name in prop_names:
        prop_meta = node.prop_meta[prop_name]
        renderman_type = prop_meta.get('renderman_type', '')
        if renderman_type == 'page':
            prop = getattr(node, prop_name)
            sub_prop_names = list(prop)
            label_drawn = show_node_sticky_params(layout, node, sub_prop_names, context, nt, output_node, label_drawn)
        else:
            sticky_prop = '%s_sticky' % prop_name
            if not getattr(node, sticky_prop, False):
                continue
            row = layout.row(align=True)
            if not label_drawn:
                row = layout.row(align=True)
                rman_icon = rfb_icons.get_icon('out_%s' % node.bl_label)
                row.label(text='%s (%s)' % (node.name, node.bl_label), icon_value=rman_icon.icon_id)
                label_drawn = True
                row = layout.row(align=True)
            inputs = getattr(node, 'inputs', dict())
            socket =  inputs.get(prop_name, None)
            
            draw_sticky_toggle(row, node, prop_name, output_node)                
            draw_prop(node, prop_name, row, level=1, nt=nt, context=context, sticky=True)

    return label_drawn

def show_node_match_params(layout, node, expr, match_on, prop_names, context, nt, node_label_drawn=False):
    pattern = re.compile(expr)
    if match_on in ['NODE_NAME', 'NODE_TYPE', 'NODE_LABEL']:
        haystack = node.name
        if match_on == 'NODE_TYPE':
            haystack = node.bl_label
        elif match_on == 'NODE_LABEL':
            haystack = node.label
        if not re.match(pattern, haystack):
            return node_label_drawn

    label_drawn = node_label_drawn
    for prop_name in prop_names:
        prop_meta = node.prop_meta[prop_name]
        prop_label = prop_meta.get('label', prop_name)
        renderman_type = prop_meta.get('renderman_type', '')
        if renderman_type == 'page':
            prop = getattr(node, prop_name)
            sub_prop_names = list(prop)
            label_drawn = show_node_match_params(layout, node, expr, match_on, sub_prop_names, context, nt, label_drawn)
        else:
            if match_on in ['PARAM_LABEL', 'PARAM_NAME']:
                haystack = prop_name
                if match_on == 'PARAM_LABEL':
                    haystack = prop_label
                if not re.match(pattern, haystack):
                    continue               

            row = layout.row(align=True)
            if not label_drawn:
                row = layout.row(align=True)
                rman_icon = rfb_icons.get_icon('out_%s' % node.bl_label)
                row.label(text='%s (%s)' % (node.name, node.bl_label), icon_value=rman_icon.icon_id)
                label_drawn = True
                row = layout.row(align=True)
            inputs = getattr(node, 'inputs', dict())
            socket =  inputs.get(prop_name, None)
            
            draw_prop(node, prop_name, row, level=1, nt=nt, context=context, sticky=True)
            
    return label_drawn

def draw_node_properties_recursive(layout, context, nt, node, level=0):

    # if this is a cycles node do something different
    if not hasattr(node, 'plugin_name') or node.bl_idname == 'PxrOSLPatternNode':
        node.draw_buttons(context, layout)
        for input in node.inputs:
            if input.is_linked:
                input_node = shadergraph_utils.socket_node_input(nt, input)
                icon = get_open_close_icon(input.show_expanded)

                split = layout.split(factor=NODE_LAYOUT_SPLIT)
                row = split.row()
                draw_indented_label(row, None, level)

                label = input.name                
                rman_icon = rfb_icons.get_icon('out_%s' % input_node.bl_label)
                row.prop(input, "show_expanded", icon=icon, text='',
                         icon_only=True, emboss=False)                                   
                row.label(text=label + ' (%s):' % input_node.name)
                row.context_pointer_set("socket", input)
                row.context_pointer_set("node", node)
                row.context_pointer_set("nodetree", nt)
                row.menu('NODE_MT_renderman_connection_menu', text='', icon_value=rman_icon.icon_id)           

                if input.show_expanded:
                    draw_node_properties_recursive(layout, context, nt,
                                                   input_node, level=level + 1)

            else:
                row = layout.row(align=True)              
                draw_indented_label(row, None, level)
                # indented_label(row, socket.name+':')
                # don't draw prop for struct type
                if input.hide_value:
                    row.label(text=input.name)
                else:
                    row.prop(input, 'default_value',
                             slider=True, text=input.name)

                row.context_pointer_set("socket", input)
                row.context_pointer_set("node", node)
                row.context_pointer_set("nodetree", nt)
                row.menu('NODE_MT_renderman_connection_menu', text='', icon='NODE_MATERIAL')

    else:
        draw_props(node, node.prop_names, layout, level, nt=nt, context=context)
    layout.separator()
