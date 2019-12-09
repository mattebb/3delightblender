import bpy
from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty, BoolVectorProperty
from ..rman_render import RmanRender

# FIXME
# find a better way to get a list of the integrators
from ..properties import integrator_names

class RendermanViewportProperties(bpy.types.PropertyGroup):

    def update_viewport_integrator(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:
            rman_render.rman_scene.update_viewport_integrator(context)

    def update_hider_decidither(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:
            rm = context.scene.renderman
            rm.hider_decidither = int(self.viewport_hider_decidither)
            rman_render.rman_scene.update_hider_options(context)           

    viewport_integrator: EnumProperty(name="Viewport Integrator",
                                      description="",
                                      items=integrator_names, update=update_viewport_integrator,
                                      default='PxrPathTracer')

    viewport_hider_decidither: EnumProperty(name="Interactive Refinement",
                                      description="",
                                      items=[
                                          ("0", "0", ""),
                                          ("1", "1", ""),
                                          ("2", "2", ""),
                                          ("3", "3", ""),
                                          ("4", "4", ""),
                                          ("5", "5", ""),
                                          ("6", "6", ""),
                                      ],
                                      default="0",
                                      update=update_hider_decidither
                                    )

def draw_rman_viewport_props(self, context):
    layout = self.layout
    scene = context.scene

    if context.engine == "PRMAN_RENDER":
        view = context.space_data
        rman_render = RmanRender.get_rman_render()
        rm_viewport = scene.renderman_viewport
        if view.shading.type == 'RENDERED':
            # integrators menu
            layout.prop(rm_viewport, 'viewport_integrator', text='')
            layout.prop(rm_viewport, 'viewport_hider_decidither', text='')
            
        else:
            # stop rendering if we're not in viewport rendering
            if rman_render.rman_interactive_running:
                rman_render.stop_render()

classes = [
    RendermanViewportProperties
]

def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.VIEW3D_HT_header.append(draw_rman_viewport_props)
    bpy.types.Scene.renderman_viewport = PointerProperty(
        type=RendermanViewportProperties, name="Renderman Viewport Properties"
    )

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls) 

    bpy.types.VIEW3D_HT_header.remove(draw_rman_viewport_props)        