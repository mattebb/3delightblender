from .rman_ui_base import ShaderPanel
from ..rfb_utils.shadergraph_utils import is_renderman_nodetree
from ..rfb_utils.draw_utils import draw_node_properties_recursive
from ..rfb_utils.draw_utils import _draw_ui_from_rman_config
from ..rfb_utils import shadergraph_utils
from .. import rfb_icons
import bpy
from bpy.types import Panel

class DATA_PT_renderman_camera(ShaderPanel, Panel):
    bl_context = "data"
    bl_label = "RenderMan Camera"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        if not context.camera:
            return False
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        cam = context.camera
        scene = context.scene
        rm = cam.renderman

        _draw_ui_from_rman_config('rman_properties_camera', 'DATA_PT_renderman_camera', context, layout, rm) 
            

class DATA_PT_renderman_projection(ShaderPanel, Panel):
    bl_context = "data"
    bl_label = "RenderMan Projection"
    bl_parent_id = 'DATA_PT_renderman_camera'

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        if not context.camera:
            return False
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        cam = context.camera
        scene = context.scene
        rm = cam.renderman

        layout.separator()
        if not rm.rman_nodetree:
            layout.operator('node.rman_add_projection_nodetree', text='Add Projection Plugin')
        else:
            nt = rm.rman_nodetree
            output = shadergraph_utils.find_node_from_nodetree(nt, 'RendermanProjectionsOutputNode')
            socket = output.inputs[0]
            

            split = layout.split(factor=0.35)
            split.label(text=socket.name + ':')

            split.context_pointer_set("socket", socket)
            split.context_pointer_set("node", output)
            split.context_pointer_set("nodetree", nt)            
            if socket.is_linked:
                node = socket.links[0].from_node
                rman_icon = rman_icon = rfb_icons.get_samplefilter_icon(node.bl_label)
                split.menu('NODE_MT_renderman_connection_menu', text='%s (%s)' % (node.name, node.bl_label), icon_value=rman_icon.icon_id)
                layout.prop(rm, "rman_use_cam_fov")
                draw_node_properties_recursive(layout, context, nt, node)
            else:
                split.menu('NODE_MT_renderman_connection_menu', text='None', icon='NODE_MATERIAL')  
        

classes = [
    DATA_PT_renderman_camera,
    DATA_PT_renderman_projection
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
