import bpy
from bpy.props import EnumProperty
from ..rman_render import RmanRender
from .. import rman_bl_nodes

__HIDDEN_INTEGRATORS__ = ['PxrValidateBxdf', 'PxrDebugShadingContext']

class PRMAN_OT_Viewport_Integrators(bpy.types.Operator):
    bl_idname = "renderman_viewport.change_integrator"
    bl_label = "Select Integrator"
    bl_description = "Quickly change integrators during viewport renders. Does not change the scene integrator."
    bl_options = {"REGISTER", "UNDO"}    

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
                                      description="Viewport integrator",
                                      items=viewport_integrator_items
                                    )    

    def execute(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:
            rman_render.rman_scene.update_viewport_integrator(context, self.viewport_integrator)

        return {"FINISHED"}    

class PRMAN_OT_Viewport_Refinement(bpy.types.Operator):
    bl_idname = "renderman_viewport.change_refinement"
    bl_label = "Refinement"
    bl_description = "This value determines how much refinement (in a dither pattern) will be applied to the image during interactive rendering. 0 means full refinement up to a value of 6 which is the least refinement per iteration."
    bl_options = {"REGISTER", "UNDO"}    

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
                                      default="0"
                                    )

    def execute(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:
            rm = context.scene.renderman
            rm.hider_decidither = int(self.viewport_hider_decidither)
            rman_render.rman_scene.update_hider_options(context) 

        return {"FINISHED"}        

class PRMAN_OT_Viewport_Resolution_Mult(bpy.types.Operator):
    bl_idname = "renderman_viewport.change_resolution_mult"
    bl_label = "Res Mult"
    bl_description = "Lower the resolution of the viewport. This can help speed up renders."
    bl_options = {"REGISTER", "UNDO"}    

    viewport_res_mult: EnumProperty(name="Resolution Multiplier",
                                      description="",
                                      items=[
                                          ("1.0", "100%", ""),
                                          ("0.5", "50%", ""),
                                          ("0.33", "33%", ""),
                                          ("0.25", "25%", ""),
                                          ("0.125", "12.5%", "")
                                      ],
                                      default="1.0"
                                    )

    def execute(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:
            rm = context.scene.renderman
            rm.viewport_render_res_mult = float(self.viewport_res_mult)
            rman_render.rman_scene.update_viewport_res_mult(context) 

        return {"FINISHED"}                                                       

def draw_rman_viewport_props(self, context):
    layout = self.layout
    scene = context.scene

    if context.engine == "PRMAN_RENDER":
        view = context.space_data
        rman_render = RmanRender.get_rman_render()
        if view.shading.type == 'RENDERED':
            # integrators menu
            layout.operator_menu_enum('renderman_viewport.change_integrator', 'viewport_integrator', text='Select Integrator')
            # decidither
            layout.operator_menu_enum('renderman_viewport.change_refinement', 'viewport_hider_decidither', text='Refinement')
            # resolution mult
            layout.operator_menu_enum('renderman_viewport.change_resolution_mult', 'viewport_res_mult', text='Res Mult')
            
        else:
            # stop rendering if we're not in viewport rendering
            if rman_render.rman_interactive_running:
                rman_render.stop_render()

classes = [
    PRMAN_OT_Viewport_Integrators,
    PRMAN_OT_Viewport_Refinement,
    PRMAN_OT_Viewport_Resolution_Mult
]

def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.VIEW3D_HT_header.append(draw_rman_viewport_props)

def unregister():

    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass

    bpy.types.VIEW3D_HT_header.remove(draw_rman_viewport_props)        