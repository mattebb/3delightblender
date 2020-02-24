from .rman_ui_base import ShaderPanel
from bpy.types import Panel
import bpy

class DATA_PT_renderman_world(ShaderPanel, Panel):
    bl_context = "world"
    bl_label = "World"
    shader_type = 'world'

    def draw(self, context):
        layout = self.layout
        world = context.scene.world

        """
        DISABLE FOR NOW

        if not world.renderman.use_renderman_node:
            #FIXME layout.prop(world, "horizon_color")
            layout.prop(world, 'color')
            layout.operator('shading.add_renderman_nodetree').idtype = 'world'
            return
        else:
            layout.prop(world.renderman, "renderman_type", expand=True)
            if world.renderman.renderman_type == 'NONE':
                return
            layout.prop(world.renderman, 'light_primary_visibility')
            light_node = world.renderman.get_light_node()
            if light_node:
                draw_props(light_node, light_node.prop_names, layout)
        """

classes = [
    DATA_PT_renderman_world
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls) 