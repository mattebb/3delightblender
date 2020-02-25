from .rman_ui_base import _RManPanelHeader, CollectionPanel
from ..rman_render import RmanRender
from bl_ui.properties_particle import ParticleButtonsPanel
import bpy
from bpy.types import Panel

class PARTICLE_PT_renderman_particle(ParticleButtonsPanel, Panel, _RManPanelHeader):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "particle"
    bl_label = "Render"

    def draw(self, context):
        layout = self.layout

        psys = context.particle_system
        rm = psys.settings.renderman
        rman_render = RmanRender.get_rman_render()
        is_rman_interactive_running = rman_render.rman_interactive_running        

        col = layout.column()

        if psys.settings.type == 'EMITTER':
            if psys.settings.render_type != 'OBJECT':
                col.row().prop(rm, "constant_width", text="Override Width")
                col.row().prop(rm, "width")
        if psys.settings.render_type == 'OBJECT':
            col.prop(rm, 'use_object_material')
            if not rm.use_object_material:
                col.prop(psys.settings, "material_slot")
        else:
            col.prop(psys.settings, "material_slot")            


        split = layout.split()
        col = split.column()

        if psys.settings.type == 'HAIR':

            col.prop(rm, 'export_scalp_st')
            col.prop(rm, 'round_hair')


class PARTICLE_PT_renderman_prim_vars(CollectionPanel, Panel):
    bl_context = "particle"
    bl_label = "Primitive Variables"

    def draw_item(self, layout, context, item):
        ob = context.object
        layout.prop(item, "name")

        row = layout.row()
        row.prop(item, "data_source", text="Source")

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        if not context.particle_system:
            return False
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        psys = context.particle_system
        rm = psys.settings.renderman

        self._draw_collection(context, layout, rm, "Primitive Variables:",
                              "collection.add_remove",
                              "particle_system.settings",
                              "prim_vars", "prim_vars_index")

        layout.prop(rm, "export_default_size")

classes = [
    PARTICLE_PT_renderman_prim_vars,
    PARTICLE_PT_renderman_particle
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)        