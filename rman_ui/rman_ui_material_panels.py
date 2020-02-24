from .rman_ui_base import ShaderPanel,ShaderNodePanel
from ..rman_utils.shadergraph_utils import is_renderman_nodetree
from ..rman_utils.draw_utils import _draw_props, panel_node_draw,draw_nodes_properties_ui
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
            # if mat.node_tree:
            #    layout.prop_search(
            #        mat, "node_tree", bpy.data, "node_groups")

        layout.separator()
        split = layout.split()

        col = split.column(align=True)
        col.label(text="Viewport Color:")
        col.prop(mat, "diffuse_color", text="")
        #col.prop(mat, "alpha")

        #col.separator()
        #col.label("Viewport Alpha:")
        #col.prop(mat.game_settings, "alpha_blend", text="")

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
                # draw_nodes_properties_ui(
                #    self.layout, context, nt, input_name=self.shader_type)
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

        # self._draw_shader_menu_params(layout, context, rm)


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
            # BBM addition begin

        # BBM addition end
        # self._draw_shader_menu_params(layout, context, rm)

class DATA_PT_renderman_light(ShaderPanel, Panel):
    bl_context = "data"
    bl_label = "Light"
    shader_type = 'light'

    def draw(self, context):
        layout = self.layout

        light = context.light
        ipr_running = False 
        if not light.renderman.use_renderman_node:
            layout.prop(light, "type", expand=True)
            layout.operator('shading.add_renderman_nodetree').idtype = 'light'
            #layout.operator('shading.convert_cycles_stuff')
            return
        else:
            if ipr_running:
                layout.label(
                    text="Note: Some items cannot be edited while IPR running.")
            row = layout.row()
            row.enabled = not ipr_running
            row.prop(light.renderman, "renderman_type", expand=True)
            if light.renderman.renderman_type == 'FILTER':
                row = layout.row()
                row.enabled = not ipr_running
                row.prop(light.renderman, "filter_type", expand=True)
            if light.renderman.renderman_type == "AREA":
                row = layout.row()
                row.enabled = not ipr_running
                row.prop(light.renderman, "area_shape", expand=True)
                row = layout.row()
                '''
                if light.renderman.area_shape == "rect":
                    row.prop(light, 'size', text="Size X")
                    row.prop(light, 'size_y')
                else:
                    row.prop(light, 'size', text="Diameter")
                '''


                    
            # layout.prop(light.renderman, "shadingrate")

        # layout.prop_search(light.renderman, "nodetree", bpy.data, "node_groups")
        row = layout.row()
        row.enabled = not ipr_running
        row.prop(light.renderman, 'illuminates_by_default')


class DATA_PT_renderman_node_shader_light(ShaderNodePanel, Panel):
    bl_label = "Light Shader"
    bl_context = 'data'

    def draw(self, context):
        layout = self.layout
        light = context.light

        light_node = light.renderman.get_light_node()
        if light_node:
            if light.renderman.renderman_type != 'FILTER':
                layout.prop(light.renderman, 'light_primary_visibility')
            _draw_props(light_node, light_node.prop_names, layout)



classes = [
    MATERIAL_PT_renderman_preview,
    MATERIAL_PT_renderman_shader_surface,
    MATERIAL_PT_renderman_shader_light,
    MATERIAL_PT_renderman_shader_displacement,
    DATA_PT_renderman_light,
    DATA_PT_renderman_node_shader_light

]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)        