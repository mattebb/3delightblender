from .rman_ui_base import _RManPanelHeader
from .rman_ui_base import CollectionPanel
from .rman_ui_base import PRManButtonsPanel
from ..rman_utils.draw_utils import _draw_ui_from_rman_config
from ..rman_utils.draw_utils import _draw_props
from ..rman_constants import NODE_LAYOUT_SPLIT
from ..rman_render import RmanRender
from .. icons import icons
from bpy.types import Panel
import bpy

class RENDER_PT_renderman_render(PRManButtonsPanel, Panel):
    bl_label = "Render"

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        if context.scene.render.engine != "PRMAN_RENDER":
            return

        layout = self.layout
        rd = context.scene.render
        rm = context.scene.renderman
        rman_render = RmanRender.get_rman_render()
        is_rman_interactive_running = rman_render.rman_interactive_running

        if not is_rman_interactive_running:

            # Render
            row = layout.row(align=True)
            rman_render_icon = icons.get_icon("rman_render") 
            row.operator("render.render", text="Render",
                        icon_value=rman_render_icon.icon_id)

            # Batch Render
            rman_batch = icons.get_icon("rman_batch")
            row.operator("render.render", text="Render Animation",
                        icon_value=rman_batch.icon_id).animation = True

        else:
            row = layout.row(align=True)
            rman_rerender_controls = icons.get_icon("rman_ipr_cancel")
            row.operator('lighting.stop_interactive', text="Stop IPR",
                            icon_value=rman_rerender_controls.icon_id)                                          


        split = layout.split(factor=0.33)
        col = layout.column()
        col.enabled = not is_rman_interactive_running

        _draw_ui_from_rman_config('rman_properties_scene', 'RENDER_PT_renderman_render', context, layout, rm)  

class RENDER_PT_renderman_spooling(PRManButtonsPanel, Panel):
    bl_label = "External Rendering"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout
        scene = context.scene
        rm = scene.renderman

        rman_render = RmanRender.get_rman_render()
        is_rman_interactive_running = rman_render.rman_interactive_running
        layout.enabled = not is_rman_interactive_running        

        # button
        col = layout.column()
        row = col.row(align=True)
        rman_batch = icons.get_icon("rman_batch")
        row.operator("renderman.external_render",
                     text="External Render", icon_value=rman_batch.icon_id)
        rman_bake = icons.get_icon("rman_bake")                     
        row.operator("renderman.external_bake",
                     text="External Bake Render", icon_value=rman_bake.icon_id)

        # do animation
        col.prop(rm, 'external_animation')
        col = layout.column(align=True)
        col.enabled = rm.external_animation
        col.prop(scene, "frame_start", text="Start")
        col.prop(scene, "frame_end", text="End")

class RENDER_PT_renderman_spooling_export_options(PRManButtonsPanel, Panel):
    bl_label = "Spool Options"
    bl_parent_id = 'RENDER_PT_renderman_spooling'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout
        scene = context.scene
        rm = scene.renderman

        rman_render = RmanRender.get_rman_render()
        is_rman_interactive_running = rman_render.rman_interactive_running
        layout.enabled = not is_rman_interactive_running           

        col = layout.column()
        _draw_ui_from_rman_config('rman_properties_scene', 'RENDER_PT_renderman_spooling_export_options', context, layout, rm)        

class RENDER_PT_renderman_sampling(PRManButtonsPanel, Panel):
    bl_label = "Sampling"

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout
        scene = context.scene
        rm = scene.renderman

        col = layout.column()
        row = col.row(align=True)

        '''
        row.menu("PRMAN_MT_presets", text=bpy.types.WM_MT_operator_presets.bl_label)
        row.operator("render.renderman_preset_add", text="", icon='ADD')
        row.operator("render.renderman_preset_add", text="",icon='REMOVE').remove_active = True
        '''

        _draw_ui_from_rman_config('rman_properties_scene', 'RENDER_PT_renderman_sampling', context, layout, rm)

class RENDER_PT_renderman_sampling_ipr(PRManButtonsPanel, Panel):
    bl_label = "IPR Sampling"
    bl_parent_id = 'RENDER_PT_renderman_sampling'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout
        scene = context.scene
        rm = scene.renderman

        col = layout.column()
        row = col.row(align=True)

        _draw_ui_from_rman_config('rman_properties_scene', 'RENDER_PT_renderman_sampling_ipr', context, layout, rm)  

class RENDER_PT_renderman_motion_blur(PRManButtonsPanel, Panel):
    bl_label = "Motion Blur"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        rm = context.scene.renderman
        layout = self.layout
        _draw_ui_from_rman_config('rman_properties_scene', 'RENDER_PT_renderman_motion_blur', context, layout, rm)   

class RENDER_PT_renderman_baking(PRManButtonsPanel, Panel):
    bl_label = "Baking"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False        
        layout = self.layout
        rman_render = RmanRender.get_rman_render()
        is_rman_interactive_running = rman_render.rman_interactive_running
        layout.enabled = not is_rman_interactive_running  
        scene = context.scene
        rm = scene.renderman         
        row = layout.row()
        rman_batch = icons.get_icon("rman_bake")
        row.operator("renderman.bake",
                     text="Bake", icon_value=rman_batch.icon_id)  

        _draw_ui_from_rman_config('rman_properties_scene', 'RENDER_PT_renderman_baking', context, layout, rm)      

class RENDER_PT_renderman_advanced_settings(PRManButtonsPanel, Panel):
    bl_label = "Advanced"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout
        scene = context.scene
        rm = scene.renderman

        _draw_ui_from_rman_config('rman_properties_scene', 'RENDER_PT_renderman_advanced_settings', context, layout, rm)      

class RENDER_PT_renderman_custom_options(PRManButtonsPanel, Panel):
    bl_label = "Custom Options"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout
        scene = context.scene
        rm = scene.renderman

        _draw_ui_from_rman_config('rman_properties_scene', 'RENDER_PT_renderman_custom_options', context, layout, rm)

classes = [
    RENDER_PT_renderman_render,
    RENDER_PT_renderman_spooling,
    RENDER_PT_renderman_spooling_export_options,    
    RENDER_PT_renderman_baking,
    RENDER_PT_renderman_sampling,
    RENDER_PT_renderman_sampling_ipr,
    RENDER_PT_renderman_motion_blur,    
    RENDER_PT_renderman_advanced_settings,
    RENDER_PT_renderman_custom_options
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