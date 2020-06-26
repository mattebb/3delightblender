import bpy
from bpy.props import EnumProperty, StringProperty, IntProperty, FloatProperty
from ..rman_render import RmanRender
from .. import rman_bl_nodes
from ..icons.icons import load_icons
from bpy.types import Menu

__HIDDEN_INTEGRATORS__ = ['PxrValidateBxdf', 'PxrDebugShadingContext']

class PRMAN_MT_Viewport_Integrator_Menu(Menu):
    bl_label = "Viewport Integrator Menu"
    bl_idname = "PRMAN_MT_Viewport_Integrator_Menu"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None    

    def draw(self, context):
        layout = self.layout
        for node in rman_bl_nodes.__RMAN_INTEGRATOR_NODES__:
            if node.name not in __HIDDEN_INTEGRATORS__:
                op = layout.operator('renderman_viewport.change_integrator', text=node.name)
                op.viewport_integrator = node.name  


class PRMAN_MT_Viewport_Refinement_Menu(Menu):
    bl_label = "Viewport Refinement Menu"
    bl_idname = "PRMAN_MT_Viewport_Refinement_Menu"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None    

    def draw(self, context):
        layout = self.layout
        for i in range(0, 7):
            op = layout.operator('renderman_viewport.change_refinement', text='%d' % i)
            op.viewport_hider_decidither = i 

class PRMAN_MT_Viewport_Res_Mult_Menu(Menu):
    bl_label = "Viewport Res Mult Menu"
    bl_idname = "PRMAN_MT_Viewport_Res_Mult_Menu"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None 

    def get_items(self):
        items=[
            (1.0, "100%"),
            (0.5, "50%"),
            (0.33, "33%"),
            (0.25, "25%"),
            (0.125, "12.5%")
        ]        
        return items

    def draw(self, context):
        layout = self.layout
        for val, nm in self.get_items():
            op = layout.operator('renderman_viewport.change_resolution_mult', text=nm)
            op.viewport_res_mult = val


class PRMAN_OT_Viewport_Integrators(bpy.types.Operator):
    bl_idname = "renderman_viewport.change_integrator"
    bl_label = "Select Integrator"
    bl_description = "Quickly change integrators during viewport renders. Does not change the scene integrator."
    bl_options = {"REGISTER", "UNDO"}    

    viewport_integrator: StringProperty(name="Viewport Integrator",
                                      description="Viewport integrator"
                                    )    

    def execute(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:
            rman_render.rman_scene_sync.update_viewport_integrator(context, self.viewport_integrator)

        return {"FINISHED"}    

class PRMAN_OT_Viewport_Refinement(bpy.types.Operator):
    bl_idname = "renderman_viewport.change_refinement"
    bl_label = "Refinement"
    bl_description = "This value determines how much refinement (in a dither pattern) will be applied to the image during interactive rendering. 0 means full refinement up to a value of 6 which is the least refinement per iteration."
    bl_options = {"REGISTER", "UNDO"}    

    viewport_hider_decidither: IntProperty(name="Interactive Refinement",
                                      description="",
                                      default=0
                                    )

    def execute(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:
            rm = context.scene.renderman
            rm.hider_decidither = int(self.viewport_hider_decidither)
            rman_render.rman_scene_sync.update_hider_options(context) 

        return {"FINISHED"}        

class PRMAN_OT_Viewport_Resolution_Mult(bpy.types.Operator):
    bl_idname = "renderman_viewport.change_resolution_mult"
    bl_label = "Res Mult"
    bl_description = "Lower the resolution of the viewport. This can help speed up renders."
    bl_options = {"REGISTER", "UNDO"}    

    viewport_res_mult: FloatProperty(name="Resolution Multiplier",
                                      description="",
                                      default=1.0
                                    )

    def execute(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:
            rman_render.rman_scene.viewport_render_res_mult = float(self.viewport_res_mult)
            rman_render.rman_scene_sync.update_viewport_res_mult(context) 

        return {"FINISHED"}                                                       

def draw_rman_viewport_props(self, context):
    layout = self.layout
    scene = context.scene

    if context.engine == "PRMAN_RENDER":
        view = context.space_data
        rman_render = RmanRender.get_rman_render()
        if view.shading.type == 'RENDERED':
            icons = load_icons()

            # integrators menu
            rman_icon = icons.get('rman_vp_viz.png')
            layout.menu('PRMAN_MT_Viewport_Integrator_Menu', text='', icon_value=rman_icon.icon_id)
            # decidither
            layout.menu('PRMAN_MT_Viewport_Refinement_Menu', text='', icon='IMPORT')
            # resolution mult
            rman_icon = icons.get('rman_vp_resolution.png')
            layout.menu('PRMAN_MT_Viewport_Res_Mult_Menu', text='', icon_value=rman_icon.icon_id)
            
        else:
            # stop rendering if we're not in viewport rendering
            if rman_render.rman_interactive_running:
                rman_render.stop_render()

classes = [
    PRMAN_MT_Viewport_Integrator_Menu,
    PRMAN_MT_Viewport_Refinement_Menu,
    PRMAN_MT_Viewport_Res_Mult_Menu,
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