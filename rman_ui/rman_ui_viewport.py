import bpy
from bpy.props import EnumProperty, PointerProperty
from ..rman_render import RmanRender
from .. import rman_bl_nodes

__HIDDEN_INTEGRATORS__ = ['PxrValidateBxdf', 'PxrDebugShadingContext']

class RendermanViewportProperties(bpy.types.PropertyGroup):

    def update_viewport_integrator(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:
            rman_render.rman_scene.update_viewport_integrator(context, self.viewport_integrator)

    def update_hider_decidither(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:
            rm = context.scene.renderman
            rm.hider_decidither = int(self.viewport_hider_decidither)
            rman_render.rman_scene.update_hider_options(context) 

    def viewport_integrator_items(self, context):
        items = []
        items.append(('Select Integrator', 'Select Integrator', '', '', 0))
        i = 1
        for node in rman_bl_nodes.__RMAN_INTEGRATOR_NODES__:
            if node.name not in __HIDDEN_INTEGRATORS__:
                items.append((node.name, node.name, '', '', i))
                i += 1
        return items

    viewport_integrator: EnumProperty(name="Viewport Integrator",
                                      description="Quickly change integrators during viewport renders. Does not change the scene integrator.",
                                      items=viewport_integrator_items,
                                      update=update_viewport_integrator
                                    )


    viewport_hider_decidither: EnumProperty(name="Interactive Refinement",
                                      description="This value determines how much refinement (in a dither pattern) will be applied to the image during interactive rendering. 0 means full refinement up to a value of 6 which is the least refinement per iteration.",
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
            # decidither
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
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass

    bpy.types.VIEW3D_HT_header.remove(draw_rman_viewport_props)        