from .rman_ui_base import ShaderPanel
from ..rman_utils.shadergraph_utils import is_renderman_nodetree
from ..rman_utils.draw_utils import _draw_props
from ..rman_utils.draw_utils import _draw_ui_from_rman_config
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

        # Projection plugin
        layout.prop(cam.renderman, "projection_type")
        if cam.renderman.projection_type != 'none':
            projection_node = cam.renderman.get_projection_node()
            _draw_props(projection_node, projection_node.prop_names, layout)


classes = [
    DATA_PT_renderman_camera
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
