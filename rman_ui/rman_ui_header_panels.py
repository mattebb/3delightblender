from ..rman_render import RmanRender
from ..icons.icons import load_icons
from ..rman_utils.shadergraph_utils import is_renderman_nodetree, find_selected_pattern_node
import bpy

class PRMAN_HT_DrawRenderHeaderInfo(bpy.types.Header):
    '''Adds a render button or stop IPR button to the Info
    UI panel
    '''

    bl_space_type = "INFO"

    def draw(self, context):
        if context.scene.render.engine != "PRMAN_RENDER":
            return
        layout = self.layout
        icons = load_icons()
        rman_render = RmanRender.get_rman_render()
        is_rman_interactive_running = rman_render.rman_interactive_running

        
        if not is_rman_interactive_running:

            # Render
            row = layout.row(align=True)
            rman_render_icon = icons.get("rman_render.png")            
            row.operator("render.render", text="Render",
                        icon_value=rman_render_icon.icon_id)
        else:
            row = layout.row(align=True)
            rman_rerender_controls = icons.get("rman_ipr_cancel.png")
            row.operator('lighting.stop_interactive', text="Stop IPR",
                            icon_value=rman_rerender_controls.icon_id)      


class PRMAN_HT_DrawRenderHeaderNode(bpy.types.Header):
    '''
    Adds a New RenderMan Material button or Convert to RenderMan button to 
    the node editor UI.
    '''

    bl_space_type = "NODE_EDITOR"

    def draw(self, context):
        if context.scene.render.engine != "PRMAN_RENDER":
            return
        layout = self.layout

        row = layout.row(align=True)

        if not hasattr(context.space_data, 'id'):
            return

        if type(context.space_data.id) == bpy.types.Material:
            rman_output_node = is_renderman_nodetree(context.space_data.id)
            icons = load_icons()

            if not rman_output_node:           
                rman_icon = icons.get('rman_graph.png') 
                row.operator(
                    'shading.add_renderman_nodetree', text="", icon_value=rman_icon.icon_id).idtype = "node_editor"
                row.operator('nodes.new_bxdf', text='', icon='MATERIAL')
            else:
                nt = context.space_data.id.node_tree
                selected_node = find_selected_pattern_node(nt)
                if selected_node:
                    row.context_pointer_set("nodetree", nt)  
                    row.context_pointer_set("node", rman_output_node)  
                    
                    if rman_output_node.solo_node_name != '':
                        rman_icon = icons.get('rman_solo_on.png')
                        op = row.operator('node.rman_set_node_solo', text='', icon_value=rman_icon.icon_id)
                        op.refresh_solo = False
                        op.solo_node_name = selected_node.name

                        op = row.operator('node.rman_set_node_solo', text='', icon='FILE_REFRESH')
                        op.refresh_solo = True  
                    else:      
                        rman_icon = icons.get('rman_solo_off.png')
                        op = row.operator('node.rman_set_node_solo', text='', icon_value=rman_icon.icon_id)
                        op.refresh_solo = False
                        op.solo_node_name = selected_node.name                                

        elif type(context.space_data.id) == bpy.types.World:
            if not context.space_data.id.renderman.use_renderman_node:
                row.operator(
                    'shading.add_renderman_nodetree', text="Add RenderMan Nodes").idtype = "world"                

class PRMAN_HT_DrawRenderHeaderImage(bpy.types.Header):
    '''Adds a render button or stop IPR button to the image editor
    UI
    '''

    bl_space_type = "IMAGE_EDITOR"

    def draw(self, context):
        if context.scene.render.engine != "PRMAN_RENDER":
            return
        layout = self.layout
        icons = load_icons()

        rman_render = RmanRender.get_rman_render()
        is_rman_interactive_running = rman_render.rman_interactive_running

        if not is_rman_interactive_running:

            # Render
            row = layout.row(align=True)
            rman_render_icon = icons.get("rman_render.png")       
            row.operator("render.render", text="Render",
                        icon_value=rman_render_icon.icon_id)    

        else:
            row = layout.row(align=True)
            rman_rerender_controls = icons.get("rman_ipr_cancel.png")
            row.operator('lighting.stop_interactive', text="Stop IPR",
                            icon_value=rman_rerender_controls.icon_id)  

classes = [
    #PRMAN_HT_DrawRenderHeaderInfo,
    PRMAN_HT_DrawRenderHeaderNode,
    #PRMAN_HT_DrawRenderHeaderImage,
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