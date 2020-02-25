from ..rman_render import RmanRender
from ..icons.icons import load_icons
from ..rman_utils.shadergraph_utils import is_renderman_nodetree
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
            rman_render_icon = icons.get("render")            
            row.operator("render.render", text="Render",
                        icon_value=rman_render_icon.icon_id)

            # IPR
            #rman_rerender_controls = icons.get("start_ipr")
            #row.operator('lighting.start_interactive', text="Start IPR",
            #                icon_value=rman_rerender_controls.icon_id)      

            # Batch Render

            #rman_batch = icons.get("batch_render")
            #row.operator("renderman.external_render",
            #             text="External Render", icon_value=rman_batch.icon_id)

        else:
            row = layout.row(align=True)
            rman_rerender_controls = icons.get("stop_ipr")
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

        if hasattr(context.space_data, 'id') and \
                type(context.space_data.id) == bpy.types.Material and \
                not is_renderman_nodetree(context.space_data.id):
            row.operator(
                'shading.add_renderman_nodetree', text="Convert to RenderMan").idtype = "node_editor"

        row.operator('nodes.new_bxdf')


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
            rman_render_icon = icons.get("render")            
            row.operator("render.render", text="Render",
                        icon_value=rman_render_icon.icon_id)    

        else:
            row = layout.row(align=True)
            rman_rerender_controls = icons.get("stop_ipr")
            row.operator('lighting.stop_interactive', text="Stop IPR",
                            icon_value=rman_rerender_controls.icon_id)  

classes = [
    PRMAN_HT_DrawRenderHeaderInfo,
    PRMAN_HT_DrawRenderHeaderNode,
    PRMAN_HT_DrawRenderHeaderImage,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)                            