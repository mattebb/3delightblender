from .rman_ui_base import _RManPanelHeader,ShaderPanel,ShaderNodePanel, CollectionPanel 
from ..rman_utils.shadergraph_utils import is_renderman_nodetree
from ..rman_utils.draw_utils import _draw_props, panel_node_draw,draw_nodes_properties_ui
from ..icons.icons import load_icons
import bpy
from bpy.types import Panel

class MATERIAL_PT_renderman_preview(Panel, ShaderPanel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_options = {'DEFAULT_CLOSED'}
    bl_context = "material"
    bl_label = "Preview"

    def draw(self, context):
        layout = self.layout
        mat = context.material
        row = layout.row()

        if mat:
            row.template_preview(context.material, show_buttons=1)

        layout.separator()
        split = layout.split()

        col = split.column(align=True)
        col.label(text="Viewport Color:")
        col.prop(mat, "diffuse_color", text="")

        col = split.column(align=True)
        col.label(text="Viewport Specular:")
        col.prop(mat, "specular_color", text="")
        #FIXME col.prop(mat, "specular_hardness", text="Hardness")

class MATERIAL_PT_renderman_shader_surface(ShaderPanel, Panel):
    bl_context = "material"
    bl_label = "Bxdf"
    shader_type = 'Bxdf'

    def draw(self, context):
        mat = context.material
        layout = self.layout
        if context.material.renderman and context.material.node_tree:
            nt = context.material.node_tree

            if is_renderman_nodetree(mat):
                panel_node_draw(layout, context, mat,
                                'RendermanOutputNode', 'Bxdf')
            else:
                if not panel_node_draw(layout, context, mat, 'ShaderNodeOutputMaterial', 'Surface'):
                    layout.prop(mat, "diffuse_color")
            layout.separator()

        else:
            # if no nodetree we use pxrdisney
            mat = context.material
            rm = mat.renderman

            row = layout.row()
            row.prop(mat, "diffuse_color")

            layout.separator()
        if mat and not is_renderman_nodetree(mat):
            rm = mat.renderman
            row = layout.row()
            row.prop(rm, "copy_color_params")
            layout.operator(
                'shading.add_renderman_nodetree').idtype = "material"
            if not mat.grease_pencil:
                layout.operator('shading.convert_cycles_stuff')


class MATERIAL_PT_renderman_shader_light(ShaderPanel, Panel):
    bl_context = "material"
    bl_label = "Light Emission"
    shader_type = 'Light'

    def draw(self, context):
        if context.material.node_tree:
            nt = context.material.node_tree
            draw_nodes_properties_ui(
                self.layout, context, nt, input_name=self.shader_type)


class MATERIAL_PT_renderman_shader_displacement(ShaderPanel, Panel):
    bl_context = "material"
    bl_label = "Displacement"
    shader_type = 'Displacement'

    def draw(self, context):
        if context.material.node_tree:
            nt = context.material.node_tree
            draw_nodes_properties_ui(
                self.layout, context, nt, input_name=self.shader_type)

class DATA_PT_renderman_light(ShaderPanel, Panel):
    bl_context = "data"
    bl_label = "Light"
    shader_type = 'light'

    def draw(self, context):
        layout = self.layout

        light = context.light
        if not light.renderman.use_renderman_node:
            layout.prop(light, "type", expand=True)
            layout.operator('shading.add_renderman_nodetree').idtype = 'light'
            return
        else:       
            row = layout.row()
            row.prop(light.renderman, "renderman_lock_light_type")                          
            if not light.renderman.renderman_lock_light_type:
                row = layout.row()
                row.prop(light.renderman, "renderman_light_role", expand=True)
                if light.renderman.renderman_light_role == 'RMAN_LIGHTFILTER':
                    row = layout.row()
                    row.prop(light.renderman, "renderman_light_filter_shader")

                elif light.renderman.renderman_light_role == 'RMAN_LIGHT':
                    row = layout.row()
                    row.prop(light.renderman, 'renderman_light_shader')                
            else:
                row = layout.row()
                col = row.column()
                icons = load_icons()
                rman_light_icon = icons.get("arealight")
                if light.renderman.renderman_light_role == 'RMAN_LIGHTFILTER':
                    col.label(text="%s" % light.renderman.renderman_light_filter_shader, icon_value=rman_light_icon.icon_id)
                else:
                    col.label(text="%s" % light.renderman.renderman_light_shader, icon_value=rman_light_icon.icon_id)


class PRMAN_PT_context_material(_RManPanelHeader, Panel):
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_label = ""
    bl_context = "material"
    bl_options = {'HIDE_HEADER'}
    COMPAT_ENGINES = {'PRMAN_RENDER'}

    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.type == 'GPENCIL':
            return False
        else:
            return (context.material or context.object) and _RManPanelHeader.poll(context)

    def draw(self, context):
        layout = self.layout

        mat = context.material
        ob = context.object
        slot = context.material_slot
        space = context.space_data

        if ob:
            is_sortable = len(ob.material_slots) > 1
            rows = 1
            if (is_sortable):
                rows = 4

            row = layout.row()

            row.template_list("MATERIAL_UL_matslots", "", ob, "material_slots", ob, "active_material_index", rows=rows)

            col = row.column(align=True)
            col.operator("object.material_slot_add", icon='ADD', text="")
            col.operator("object.material_slot_remove", icon='REMOVE', text="")

            col.menu("MATERIAL_MT_context_menu", icon='DOWNARROW_HLT', text="")

            if is_sortable:
                col.separator()

                col.operator("object.material_slot_move", icon='TRIA_UP', text="").direction = 'UP'
                col.operator("object.material_slot_move", icon='TRIA_DOWN', text="").direction = 'DOWN'

            if ob.mode == 'EDIT':
                row = layout.row(align=True)
                row.operator("object.material_slot_assign", text="Assign")
                row.operator("object.material_slot_select", text="Select")
                row.operator("object.material_slot_deselect", text="Deselect")

        split = layout.split(factor=0.65)

        if ob:
            split.template_ID(ob, "active_material", new="material.new")
            row = split.row()

            if slot:
                row.prop(slot, "link", text="")
            else:
                row.label()
        elif mat:
            split.template_ID(space, "pin_id")
            split.separator()


class DATA_PT_renderman_node_shader_light(ShaderNodePanel, Panel):
    bl_label = "Light Shader"
    bl_context = 'data'

    def draw(self, context):
        layout = self.layout
        light = context.light

        light_node = light.renderman.get_light_node()
        if light_node:
            if light.renderman.renderman_light_role != 'RMAN_LIGHTFILTER':
                layout.prop(light.renderman, 'light_primary_visibility')
            _draw_props(light_node, light_node.prop_names, layout)

class DATA_PT_renderman_node_filters_light(CollectionPanel, Panel):
    bl_label = "Light Filters"
    bl_context = 'data'

    def draw_item(self, layout, context, item):
        layout.prop(item, 'filter_name')

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER' and hasattr(context, "light") \
            and context.light is not None and hasattr(context.light, 'renderman') \
            and context.light.renderman.renderman_light_role != 'RMAN_LIGHTFILTER'

    def draw(self, context):
        layout = self.layout
        light = context.light

        self._draw_collection(context, layout, light.renderman, "",
                              "collection.add_remove", "light", "light_filters",
                              "light_filters_index")

classes = [
    MATERIAL_PT_renderman_preview,
    MATERIAL_PT_renderman_shader_surface,
    MATERIAL_PT_renderman_shader_light,
    MATERIAL_PT_renderman_shader_displacement,
    DATA_PT_renderman_light,
    DATA_PT_renderman_node_shader_light,
    DATA_PT_renderman_node_filters_light,
    PRMAN_PT_context_material
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)        