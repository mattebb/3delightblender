# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 - 2017 Pixar
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#
# ##### END MIT LICENSE BLOCK #####

import bpy
import math
import blf
from bpy.types import Panel
from .nodes import is_renderman_nodetree, panel_node_draw
from .rman_constants import NODE_LAYOUT_SPLIT


# global dictionaries
from bl_ui.properties_particle import ParticleButtonsPanel

# helper functions for parameters
from .nodes import draw_nodes_properties_ui, draw_node_properties_recursive

from .rman_ui.rman_ui_base import _RManPanelHeader
from .rman_ui.rman_ui_base import CollectionPanel
from .rman_ui.rman_ui_base import PRManButtonsPanel
from .rman_render import RmanRender
from .rman_utils import object_utils

def get_panels():
    exclude_panels = {
        'DATA_PT_area',
        'DATA_PT_camera_dof',
        'DATA_PT_falloff_curve',
        'DATA_PT_light',
        'DATA_PT_preview',
        'DATA_PT_shadow',
        # 'DATA_PT_spot',
        'DATA_PT_sunsky',
        # 'MATERIAL_PT_context_material',
        'MATERIAL_PT_diffuse',
        'MATERIAL_PT_flare',
        'MATERIAL_PT_halo',
        'MATERIAL_PT_mirror',
        'MATERIAL_PT_options',
        'MATERIAL_PT_pipeline',
        'MATERIAL_PT_preview',
        'MATERIAL_PT_shading',
        'MATERIAL_PT_shadow',
        'MATERIAL_PT_specular',
        'MATERIAL_PT_sss',
        'MATERIAL_PT_strand',
        'MATERIAL_PT_transp',
        'MATERIAL_PT_volume_density',
        'MATERIAL_PT_volume_integration',
        'MATERIAL_PT_volume_lighting',
        'MATERIAL_PT_volume_options',
        'MATERIAL_PT_volume_shading',
        'MATERIAL_PT_volume_transp',
        'RENDERLAYER_PT_layer_options',
        'RENDERLAYER_PT_layer_passes',
        'RENDERLAYER_PT_views',
        'RENDER_PT_antialiasing',
        'RENDER_PT_bake',
        #'RENDER_PT_motion_blur',
        'RENDER_PT_performance',
        'RENDER_PT_freestyle',
        # 'RENDER_PT_post_processing',
        'RENDER_PT_shading',
        'RENDER_PT_render',
        'RENDER_PT_stamp',
        'RENDER_PT_simplify',
        'RENDER_PT_color_management',
        'TEXTURE_PT_context_texture',
        'WORLD_PT_ambient_occlusion',
        'WORLD_PT_environment_lighting',
        'WORLD_PT_gather',
        'WORLD_PT_indirect_lighting',
        'WORLD_PT_mist',
        'WORLD_PT_preview',
        'WORLD_PT_world',
        'NODE_DATA_PT_light',
        'NODE_DATA_PT_spot',
    }

    panels = []
    for t in bpy.types.Panel.__subclasses__():
        if hasattr(t, 'COMPAT_ENGINES') and 'BLENDER_RENDER' in t.COMPAT_ENGINES:
            if t.__name__ not in exclude_panels:
                panels.append(t)

    return panels


# icons
import os
from . icons.icons import load_icons
from . util import get_addon_prefs


from bpy.props import (PointerProperty, StringProperty, BoolProperty,
                       EnumProperty, IntProperty, FloatProperty, FloatVectorProperty,
                       CollectionProperty)

# ------- UI panel definitions -------
narrowui = 180

class DATA_PT_renderman_display_filters(CollectionPanel, Panel):
    bl_label = "Display Filters"
    bl_context = 'scene'

    def draw_item(self, layout, context, item):
        layout.prop(item, 'filter_type')
        layout.separator()
        filter_node = item.get_filter_node()
        draw_props(filter_node, filter_node.prop_names, layout)

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        rm = scene.renderman

        self._draw_collection(context, layout, rm, "Display Filters:",
                              "collection.add_remove", "scene", "display_filters",
                              "display_filters_index")


class DATA_PT_renderman_Sample_filters(CollectionPanel, Panel):
    bl_label = "Sample Filters"
    bl_context = 'scene'

    def draw_item(self, layout, context, item):
        layout.prop(item, 'filter_type')
        layout.separator()
        filter_node = item.get_filter_node()
        draw_props(filter_node, filter_node.prop_names, layout)

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        rm = scene.renderman

        self._draw_collection(context, layout, rm, "Sample Filters:",
                              "collection.add_remove", "scene", "sample_filters",
                              "sample_filters_index")


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
            and context.light.renderman.renderman_type != 'FILTER'

    def draw(self, context):
        layout = self.layout
        light = context.light

        self._draw_collection(context, layout, light.renderman, "",
                              "collection.add_remove", "light", "light_filters",
                              "light_filters_index")

class PARTICLE_PT_renderman_particle(ParticleButtonsPanel, Panel, _RManPanelHeader):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "particle"
    bl_label = "Render"

    def draw(self, context):
        layout = self.layout

        # XXX todo: handle strands properly

        psys = context.particle_system
        rm = psys.settings.renderman
        rman_render = RmanRender.get_rman_render()
        is_rman_interactive_running = rman_render.rman_interactive_running        

        col = layout.column()

        #col.enabled = not is_rman_interactive_running
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

        '''
        if psys.settings.type == 'EMITTER':
            col.row().prop(rm, "particle_type", expand=True)
            if rm.particle_type == 'OBJECT':
                col.prop_search(rm, "particle_instance_object", bpy.data,
                                "objects", text="")
                col.prop(rm, 'use_object_material')
            elif rm.particle_type == 'GROUP':
                col.prop_search(rm, "particle_instance_object", bpy.data,
                                "groups", text="")

            if rm.particle_type == 'OBJECT' and rm.use_object_material:
                pass
            else:
                col.prop(psys.settings, "material_slot")
            col.row().prop(rm, "constant_width", text="Override Width")
            col.row().prop(rm, "width")

        else:
            col.prop(psys.settings, "material_slot")
        '''

        # XXX: if rm.type in ('sphere', 'disc', 'patch'):
        # implement patchaspectratio and patchrotation

        split = layout.split()
        col = split.column()

        if psys.settings.type == 'HAIR':
            #row = col.row()
            #row.prop(psys.settings.cycles, "root_width", text='Root Width')
            #row.prop(psys.settings.cycles, "tip_width", text='Tip Width')
            #row = col.row()
            #row.prop(psys.settings.cycles, "radius_scale", text='Width Multiplier')

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

# headers to draw the interactive start/stop buttons


class PRMAN_HT_DrawRenderHeaderInfo(bpy.types.Header):
    bl_space_type = "INFO"

    def draw(self, context):
        if context.scene.render.engine != "PRMAN_RENDER":
            return
        layout = self.layout
        icons = load_icons()
        rman_render = RmanRender.get_rman_render()
        is_rman_interactive_running = rman_render.rman_interactive_running

        
        if not is_rman_interactive_running:

            # Render
            row = layout.row(align=True)
            rman_render_icon = icons.get("render")            
            row.operator("render.render", text="Render",
                        icon_value=rman_render_icon.icon_id)

            # IPR
            #rman_rerender_controls = icons.get("start_ipr")
            #row.operator('lighting.start_interactive', text="Start IPR",
            #                icon_value=rman_rerender_controls.icon_id)      

            # Batch Render
            rman_batch = icons.get("batch_render")
            row.operator("renderman.external_render",
                         text="External Render", icon_value=rman_batch.icon_id)

        else:
            row = layout.row(align=True)
            rman_rerender_controls = icons.get("stop_ipr")
            row.operator('lighting.stop_interactive', text="Stop IPR",
                            icon_value=rman_rerender_controls.icon_id)      

class PRMAN_HT_DrawRenderHeaderNode(bpy.types.Header):
    bl_space_type = "NODE_EDITOR"

    def draw(self, context):
        if context.scene.render.engine != "PRMAN_RENDER":
            return
        layout = self.layout

        row = layout.row(align=True)

        if hasattr(context.space_data, 'id') and \
                type(context.space_data.id) == bpy.types.Material and \
                not is_renderman_nodetree(context.space_data.id):
            row.operator(
                'shading.add_renderman_nodetree', text="Convert to RenderMan").idtype = "node_editor"

        row.operator('nodes.new_bxdf')


class PRMAN_HT_DrawRenderHeaderImage(bpy.types.Header):
    bl_space_type = "IMAGE_EDITOR"

    def draw(self, context):
        if context.scene.render.engine != "PRMAN_RENDER":
            return
        layout = self.layout
        icons = load_icons()

        rman_render = RmanRender.get_rman_render()
        is_rman_interactive_running = rman_render.rman_interactive_running

        if not is_rman_interactive_running:

            # Render
            row = layout.row(align=True)
            rman_render_icon = icons.get("render")            
            row.operator("render.render", text="Render",
                        icon_value=rman_render_icon.icon_id)

            # IPR
            #rman_rerender_controls = icons.get("start_ipr")
            #row.operator('lighting.start_interactive', text="Start IPR",
            #                icon_value=rman_rerender_controls.icon_id)      

        else:
            row = layout.row(align=True)
            rman_rerender_controls = icons.get("stop_ipr")
            row.operator('lighting.stop_interactive', text="Stop IPR",
                            icon_value=rman_rerender_controls.icon_id)                      


def PRMan_menu_func(self, context):
    if context.scene.render.engine != "PRMAN_RENDER":
        return
    self.layout.separator()

    rman_render = RmanRender.get_rman_render()
    is_rman_interactive_running = rman_render.rman_interactive_running

    if not is_rman_interactive_running:
        self.layout.operator('lighting.start_interactive',
                            text="RenderMan Start Interactive Rendering")
    else:
        self.layout.operator('lighting.stop_interactive',
                            text="RenderMan Stop Interactive Rendering")                                           

#################
#       Tab     #
#################
class PRMAN_PT_Renderman_Light_Panel(CollectionPanel, Panel):
    # bl_idname = "renderman_light_panel"
    bl_label = "RenderMan Light Groups"
    bl_context = "scene"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'  # bl_category = "Renderman"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        rm = scene.renderman
        # if len(rm.light_groups) == 0:
        #    light_group = rm.object_groups.add()
        #    light_group.name = 'All'
        self._draw_collection(context, layout, rm, "",
                              "collection.add_remove",
                              "scene.renderman",
                              "light_groups", "light_groups_index", default_name=str(len(rm.light_groups)))

    def draw_item(self, layout, context, item):
        scene = context.scene
        rm = scene.renderman
        light_group = rm.light_groups[rm.light_groups_index]
        # row.template_list("RENDERMAN_GROUP_UL_List", "Renderman_light_group_list",
        #                    light_group, "members", light_group, 'members_index',
        #                    rows=9, maxrows=100, type='GRID', columns=9)

        row = layout.row()
        add = row.operator('renderman.add_to_group', text='Add Selected to Group')
        add.item_type = 'light'
        add.group_index = rm.light_groups_index

        # row = layout.row()
        remove = row.operator('renderman.remove_from_group',
                              text='Remove Selected from Group')
        remove.item_type = 'light'
        remove.group_index = rm.light_groups_index

        light_names = [member.name for member in light_group.members]
        if light_group.name == 'All':
            light_names = [
                light.name for light in context.scene.objects if light.type == 'LIGHT']

        if len(light_names) > 0:
            box = layout.box()
            row = box.row()
            columns = box.column_flow(columns=8)
            columns.label(text='Name')
            columns.label(text='Solo')
            columns.label(text='Mute')
            columns.label(text='Intensity')
            columns.label(text='Exposure')
            columns.label(text='Color')
            columns.label(text='Temperature')

            for light_name in light_names:
                if light_name not in scene.objects:
                    continue
                light = scene.objects[light_name].data
                light_rm = light.renderman
                if light_rm.renderman_type == 'FILTER':
                    continue
                row = box.row()
                columns = box.column_flow(columns=8)
                columns.label(text=light_name)
                columns.prop(light_rm, 'solo', text='')
                columns.prop(light_rm, 'mute', text='')
                light_shader = light.renderman.get_light_node()
                if light_shader:

                    columns.prop(light_shader, 'intensity', text='')
                    columns.prop(light_shader, 'exposure', text='')
                    if light_shader.bl_label == 'PxrEnvDayLight':
                        # columns.label('sun tint')
                        columns.prop(light_shader, 'skyTint', text='')
                        columns.label(text='')
                    else:
                        columns.prop(light_shader, 'lightColor', text='')
                        row = columns.row()
                        row.prop(light_shader, 'enableTemperature', text='')
                        row.prop(light_shader, 'temperature', text='')
                else:
                    columns.label(text='')
                    columns.label(text='')
                    columns.prop(light, 'energy', text='')
                    columns.prop(light, 'color', text='')
                    columns.label(text='')


class RENDERMAN_UL_LIGHT_list(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        rm = context.scene.renderman
        icon = 'NONE'
        ll_prefix = "lg_%s>%s" % (rm.ll_light_type, item.name)
        label = item.name
        for ll in rm.ll.keys():
            if ll_prefix in ll:
                icon = 'TRIA_RIGHT'
                break

        layout.alignment = 'CENTER'
        layout.label(text=label, icon=icon)


class RENDERMAN_UL_OBJECT_list(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        rm = context.scene.renderman
        icon = 'NONE'
        light_type = rm.ll_light_type
        lg = bpy.data.lights if light_type == "light" else rm.light_groups
        ll_prefix = "lg_%s>%s>obj_%s>%s" % (
            light_type, lg[rm.ll_light_index].name, rm.ll_object_type, item.name)

        label = item.name
        if ll_prefix in rm.ll.keys():
            ll = rm.ll[ll_prefix]
            if ll.illuminate == 'DEFAULT':
                icon = 'TRIA_RIGHT'
            elif ll.illuminate == 'ON':
                icon = 'DISCLOSURE_TRI_RIGHT'
            else:
                icon = 'DISCLOSURE_TRI_DOWN'

        layout.alignment = 'CENTER'
        layout.label(text=label, icon=icon)


class PRMAN_PT_Renderman_Light_Link_Panel(CollectionPanel, Panel):
    # bl_idname = "renderman_light_panel"
    bl_label = "RenderMan Light Linking"
    bl_context = "scene"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'  # bl_category = "Renderman"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        rm = scene.renderman
        row = layout.row()

        flow = row.column_flow(columns=3)
        # first colomn select Light
        flow.prop(rm, 'll_light_type')
        flow.prop(rm, 'll_object_type')
        flow.label(text='')

        # second row the selectors
        row = layout.row()
        flow = row.column_flow(columns=3)
        if rm.ll_light_type == 'light':
            flow.template_list("RENDERMAN_UL_LIGHT_list", "Renderman_light_link_list",
                               bpy.data, "lights", rm, 'll_light_index')
        else:
            flow.template_list("RENDERMAN_UL_LIGHT_list", "Renderman_light_link_list",
                               rm, "light_groups", rm, 'll_light_index')

        if rm.ll_object_type == 'object':
            flow.template_list("RENDERMAN_UL_OBJECT_list", "Renderman_light_link_list",
                               bpy.data, "objects", rm, 'll_object_index')
        else:
            flow.template_list("RENDERMAN_UL_OBJECT_list", "Renderman_light_link_list",
                               rm, "object_groups", rm, 'll_object_index')

        if rm.ll_light_index == -1 or rm.ll_object_index == -1:
            flow.label(text="Select light and object")
        else:
            from_name = bpy.data.lights[rm.ll_light_index] if rm.ll_light_type == 'light' \
                else rm.light_groups[rm.ll_light_index]
            to_name = bpy.data.objects[rm.ll_object_index] if rm.ll_object_type == 'object' \
                else rm.object_groups[rm.ll_object_index]
            ll_name = "lg_%s>%s>obj_%s>%s" % (rm.ll_light_type, from_name.name,
                                              rm.ll_object_type, to_name.name)

            col = flow.column()
            if ll_name in rm.ll:
                col.prop(rm.ll[ll_name], 'illuminate')
                rem = col.operator(
                    'renderman.add_rem_light_link', text='Remove Light Link')
                rem.ll_name = ll_name
                rem.add_remove = "remove"
            else:
                add = col.operator(
                    'renderman.add_rem_light_link', text='Add Light Link')
                add.ll_name = ll_name
                add.add_remove = 'add'


class RENDERMAN_GROUP_UL_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        # We could write some code to decide which icon to use here...
        custom_icon = 'OBJECT_DATAMODE'
        # Make sure your code supports all 3 layout types
        layout.alignment = 'CENTER'
        layout.label(text=item.name, icon=custom_icon)


class PRMAN_PT_Renderman_Object_Panel(CollectionPanel, Panel):
    #bl_idname = "renderman_object_groups_panel"
    bl_label = "RenderMan Object Groups"
    bl_context = "scene"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'  # bl_category = "Renderman"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        rm = scene.renderman
        # if len(rm.object_groups) == 0:
        #    collector_group = rm.object_groups.add()
        #    collector_group.name = 'collector'

        self._draw_collection(context, layout, rm, "",
                              "collection.add_remove",
                              "scene.renderman",
                              "object_groups", "object_groups_index",
                              default_name=str(len(rm.object_groups)))

    def draw_item(self, layout, context, item):
        row = layout.row()
        scene = context.scene
        rm = scene.renderman
        group = rm.object_groups[rm.object_groups_index]

        row = layout.row()
        row.operator('renderman.add_to_group',
                     text='Add Selected to Group').group_index = rm.object_groups_index
        row.operator('renderman.remove_from_group',
                     text='Remove Selected from Group').group_index = rm.object_groups_index

        row = layout.row()
        row.template_list("RENDERMAN_GROUP_UL_List", "Renderman_group_list",
                          group, "members", group, 'members_index',
                          item_dyntip_propname='name',
                          type='GRID', columns=3)


class PRMAN_PT_Renderman_UI_Panel(bpy.types.Panel, _RManPanelHeader):
    #bl_idname = "renderman_ui_panel"
    bl_label = "RenderMan"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Renderman"

    def draw(self, context):
        icons = load_icons()
        layout = self.layout
        scene = context.scene
        rm = scene.renderman

        # save Scene
        # layout.operator("wm.save_mainfile", text="Save Scene", icon='FILE_TICK')

        # layout.separator()

        if context.scene.render.engine != "PRMAN_RENDER":
            return

        # Render
        rman_render = RmanRender.get_rman_render()
        is_rman_interactive_running = rman_render.rman_interactive_running        

        if not is_rman_interactive_running:

            row = layout.row(align=True)
            rman_render_icon = icons.get("render")
            row.operator("render.render", text="Render",
                        icon_value=rman_render_icon.icon_id)

            row.prop(context.scene, "rm_render", text="",
                    icon='DISCLOSURE_TRI_DOWN' if context.scene.rm_render else 'DISCLOSURE_TRI_RIGHT')

            if context.scene.rm_render:
                scene = context.scene
                rd = scene.render

                box = layout.box()
                row = box.row(align=True)

                # Display Driver
                row.prop(rm, "render_into")

                # presets
                row = box.row(align=True)
                row.label(text="Sampling Preset:")
                row.menu("PRMAN_MT_presets", text=bpy.types.WM_MT_operator_presets.bl_label)
                row.operator("render.renderman_preset_add", text="", icon='ADD')
                row.operator("render.renderman_preset_add", text="",
                            icon='REMOVE').remove_active = True

                # denoise, holdouts and selected row
                row = box.row(align=True)
                #row.prop(rm, "do_denoise", text="Denoise")
                row.prop(rm, "do_holdout_matte", text="Render Holdouts")
                
                #row.prop(rm, "render_selected_objects_only",
                #         text="Render Selected")


                # animation
                row = box.row(align=True)
                rman_batch = icons.get("batch_render")
                row.operator("render.render", text="Render Animation",
                            icon_value=rman_batch.icon_id).animation = True

                # row = box.row(align=True)
                # rman_batch = icons.get("batch_render")
                # row.operator("render.render",text="Batch Render",icon_value=rman_batch.icon_id).animation=True

                # #Resolution
                # row = box.row(align=True)
                # sub = row.column(align=True)
                # sub.label(text="Resolution:")
                # sub.prop(rd, "resolution_x", text="X")
                # sub.prop(rd, "resolution_y", text="Y")
                # sub.prop(rd, "resolution_percentage", text="")

                # # layout.prop(rm, "display_driver")
                # #Sampling
                # row = box.row(align=True)
                # row.label(text="Sampling:")
                # row = box.row(align=True)
                # col = row.column()
                # col.prop(rm, "pixel_variance")
                # row = col.row(align=True)
                # row.prop(rm, "min_samples", text="Min Samples")
                # row.prop(rm, "max_samples", text="Max Samples")
                # row = col.row(align=True)
                # row.prop(rm, "max_specular_depth", text="Specular Depth")
                # row.prop(rm, "max_diffuse_depth", text="Diffuse Depth")

            # IPR

            # Start IPR
            
            #row = layout.row(align=True)
            #rman_rerender_controls = icons.get("start_ipr")
            #row.operator('lighting.start_interactive', text="Start IPR",
            #                icon_value=rman_rerender_controls.icon_id)

            #row.prop(context.scene, "rm_ipr", text="",
            #            icon='DISCLOSURE_TRI_DOWN' if context.scene.rm_ipr else 'DISCLOSURE_TRI_RIGHT')
            

            if context.scene.rm_ipr:

                scene = context.scene
                rm = scene.renderman

                # STart IT
                rman_it = icons.get("start_it")
                layout.operator("rman.start_it", text="Start IT",
                                icon_value=rman_it.icon_id)

                # Interactive and Preview Sampling
                box = layout.box()
                row = box.row(align=True)

                col = row.column()
                col.prop(rm, "preview_pixel_variance")
                row = col.row(align=True)
                row.prop(rm, "preview_min_samples", text="Min Samples")
                row.prop(rm, "preview_max_samples", text="Max Samples")
                row = col.row(align=True)
                row.prop(rm, "preview_max_specular_depth",
                            text="Specular Depth")
                row.prop(rm, "preview_max_diffuse_depth", text="Diffuse Depth")
                row = col.row(align=True)

            row = layout.row(align=True)
            rman_batch = icons.get("batch_render")

            row.operator("renderman.external_render",
                        text="External Render", icon_value=rman_batch.icon_id)

            row.prop(context.scene, "rm_render_external", text="",
                    icon='DISCLOSURE_TRI_DOWN' if context.scene.rm_render_external else 'DISCLOSURE_TRI_RIGHT')
            if context.scene.rm_render_external:
                scene = context.scene
                rd = scene.render

                box = layout.box()
                row = box.row(align=True)

                # Display Driver
                # row.prop(rm, "display_driver", text='Render into')

                # animation
                row = box.row(align=True)
                row.prop(rm, "external_animation")

                row = box.row(align=True)
                row.enabled = rm.external_animation
                row.prop(scene, "frame_start", text="Start")
                row.prop(scene, "frame_end", text="End")

                # presets
                row = box.row(align=True)
                row.label(text="Sampling Preset:")
                row.menu("PRMAN_MT_presets")

                #row = box.row(align=True)
                #row.prop(rm, "render_selected_objects_only",
                #        text="Render Selected")

                # spool render
                row = box.row(align=True)
                col = row.column()
                col.prop(rm, "queuing_system", text='')            

        else:
            row = layout.row(align=True)
            rman_rerender_controls = icons.get("stop_ipr")
            row.operator('lighting.stop_interactive', text="Stop IPR",
                            icon_value=rman_rerender_controls.icon_id)            

        layout.separator()

        # Create Camera
        row = layout.row(align=True)
        row.operator("object.add_prm_camera",
                     text="Add Camera", icon='CAMERA_DATA')

        row.prop(context.scene, "prm_cam", text="",
                 icon='DISCLOSURE_TRI_DOWN' if context.scene.prm_cam else 'DISCLOSURE_TRI_RIGHT')

        if context.scene.prm_cam:
            ob = bpy.context.object
            box = layout.box()
            row = box.row(align=True)
            row.menu("PRMAN_MT_Camera_List_Menu",
                     text="Camera List", icon='CAMERA_DATA')

            if ob.type == 'CAMERA':

                row = box.row(align=True)
                row.prop(ob, "name", text="", icon='LIGHT_HEMI')
                row.prop(ob, "hide_viewport", text="")
                row.prop(ob, "hide_render",
                         icon='RESTRICT_RENDER_OFF', text="")
                row.operator("object.delete_cameras",
                             text="", icon='PANEL_CLOSE')

                row = box.row(align=True)
                row.scale_x = 2
                row.operator("view3d.object_as_camera", text="", icon='CURSOR')

                row.scale_x = 2
                row.operator("view3d.view_camera", text="", icon='VISIBLE_IPO_ON')

                if context.space_data.lock_camera == False:
                    row.scale_x = 2
                    row.operator("wm.context_toggle", text="",
                                 icon='UNLOCKED').data_path = "space_data.lock_camera"
                elif context.space_data.lock_camera == True:
                    row.scale_x = 2
                    row.operator("wm.context_toggle", text="",
                                 icon='LOCKED').data_path = "space_data.lock_camera"

                row.scale_x = 2
                row.operator("view3d.camera_to_view",
                             text="", icon='VIEW3D')

                row = box.row(align=True)
                row.label(text="Depth Of Field :")

                row = box.row(align=True)
                row.prop(context.object.data.dof, "focus_object", text="")
                #row.prop(context.object.data.cycles, "aperture_type", text="")

                row = box.row(align=True)
                row.prop(context.object.data.dof, "focus_distance", text="Distance")

            else:
                row = layout.row(align=True)
                row.label(text="No Camera Selected")

        layout.separator()

        # Create Env Light
        row = layout.row(align=True)
        rman_RMSEnvLight = icons.get("envlight")
        row.operator("object.mr_add_hemi", text="Add EnvLight",
                     icon_value=rman_RMSEnvLight.icon_id)

        lights = [obj for obj in bpy.context.scene.objects if obj.type == "LIGHT"]

        light_hemi = False
        light_area = False
        light_point = False
        light_spot = False
        light_sun = False

        if len(lights):
            for light in lights:
                if light.data.type == 'HEMI':
                    light_hemi = True

                if light.data.type == 'AREA':
                    light_area = True

                if light.data.type == 'POINT':
                    light_point = True

                if light.data.type == 'SPOT':
                    light_spot = True

                if light.data.type == 'SUN':
                    light_sun = True

        if light_hemi:

            row.prop(context.scene, "rm_env", text="",
                     icon='DISCLOSURE_TRI_DOWN' if context.scene.rm_env else 'DISCLOSURE_TRI_RIGHT')

            if context.scene.rm_env:
                ob = bpy.context.object
                box = layout.box()
                row = box.row(align=True)
                row.menu("PRMAN_MT_Hemi_List_Menu",
                         text="EnvLight List", icon='LIGHT_HEMI')

                if ob.type == 'LIGHT' and ob.data.type == 'HEMI':

                    row = box.row(align=True)
                    row.prop(ob, "name", text="", icon='LIGHT_HEMI')
                    row.prop(ob, "hide_viewport", text="")
                    row.prop(ob, "hide_render",
                             icon='RESTRICT_RENDER_OFF', text="")
                    row.operator("object.delete_lights",
                                 text="", icon='PANEL_CLOSE')
                    row = box.row(align=True)
                    row.prop(ob, "rotation_euler", index=2, text="Rotation")

                else:
                    row = layout.row(align=True)
                    row.label(text="No EnvLight Selected")

        # Create Area Light

        row = layout.row(align=True)
        rman_RMSAreaLight = icons.get("arealight")
        row.operator("object.mr_add_area", text="Add AreaLight",
                     icon_value=rman_RMSAreaLight.icon_id)

        lights = [obj for obj in bpy.context.scene.objects if obj.type == "LIGHT"]

        light_hemi = False
        light_area = False
        light_point = False
        light_spot = False
        light_sun = False

        if len(lights):
            for light in lights:
                if light.data.type == 'HEMI':
                    light_hemi = True

                if light.data.type == 'AREA':
                    light_area = True

                if light.data.type == 'POINT':
                    light_point = True

                if light.data.type == 'SPOT':
                    light_spot = True

                if light.data.type == 'SUN':
                    light_sun = True

        if light_area:

            row.prop(context.scene, "rm_area", text="",
                     icon='DISCLOSURE_TRI_DOWN' if context.scene.rm_area else 'DISCLOSURE_TRI_RIGHT')

            if context.scene.rm_area:
                ob = bpy.context.object
                box = layout.box()
                row = box.row(align=True)
                row.menu("PRMAN_MT_Area_List_Menu",
                         text="AreaLight List", icon='LIGHT_AREA')

                if ob.type == 'LIGHT' and ob.data.type == 'AREA':

                    row = box.row(align=True)
                    row.prop(ob, "name", text="", icon='LIGHT_AREA')
                    row.prop(ob, "hide_viewport", text="")
                    row.prop(ob, "hide_render",
                             icon='RESTRICT_RENDER_OFF', text="")
                    row.operator("object.delete_lights",
                                 text="", icon='PANEL_CLOSE')

                else:
                    row = layout.row(align=True)
                    row.label(text="No AreaLight Selected")

        # Daylight

        row = layout.row(align=True)
        rman_PxrStdEnvDayLight = icons.get("daylight")
        row.operator("object.mr_add_sky", text="Add Daylight",
                     icon_value=rman_PxrStdEnvDayLight.icon_id)

        lights = [obj for obj in bpy.context.scene.objects if obj.type == "LIGHT"]

        light_hemi = False
        light_area = False
        light_point = False
        light_spot = False
        light_sun = False

        if len(lights):
            for light in lights:
                if light.data.type == 'SUN':
                    light_sun = True

                if light.data.type == 'HEMI':
                    light_hemi = True

                if light.data.type == 'AREA':
                    light_area = True

                if light.data.type == 'POINT':
                    light_point = True

                if light.data.type == 'SPOT':
                    light_spot = True

        if light_sun:

            row.prop(context.scene, "rm_daylight", text="",
                     icon='DISCLOSURE_TRI_DOWN' if context.scene.rm_daylight else 'DISCLOSURE_TRI_RIGHT')

            if context.scene.rm_daylight:
                ob = bpy.context.object
                box = layout.box()
                row = box.row(align=True)
                row.menu("PRMAN_MT_DayLight_List_Menu",
                         text="DayLight List", icon='LIGHT_SUN')

                if ob.type == 'LIGHT' and ob.data.type == 'SUN':

                    row = box.row(align=True)
                    row.prop(ob, "name", text="", icon='LIGHT_SUN')
                    row.prop(ob, "hide_viewport", text="")
                    row.prop(ob, "hide_render",
                             icon='RESTRICT_RENDER_OFF', text="")
                    row.operator("object.delete_lights",
                                 text="", icon='PANEL_CLOSE')

                else:
                    row = layout.row(align=True)
                    row.label(text="No DayLight Selected")

        # Dynamic Binding Editor

        # Create Holdout

        # Open Linking Panel
        # row = layout.row(align=True)
        # row.operator("renderman.lighting_panel")

        selected_objects = []
        if context.selected_objects:
            for obj in context.selected_objects:
                if obj.type not in ['CAMERA', 'LIGHT', 'SPEAKER']:
                    selected_objects.append(obj)

        if selected_objects:
            layout.separator()
            layout.label(text="Seleced Objects:")
            box = layout.box()

            # Create PxrLM Material
            render_PxrDisney = icons.get("pxrdisney")
            box.operator_menu_enum(
                "object.add_bxdf", 'bxdf_name', text="Add New Material", icon='MATERIAL')

            # Make Selected Geo Emissive∂
            rman_RMSGeoAreaLight = icons.get("geoarealight")
            box.operator("object.addgeoarealight", text="Make Emissive",
                         icon_value=rman_RMSGeoAreaLight.icon_id)

            # Add Subdiv Sheme
            rman_subdiv = icons.get("add_subdiv_sheme")
            box.operator("object.add_subdiv_sheme",
                         text="Make Subdiv", icon_value=rman_subdiv.icon_id)

            # Add/Create RIB Box /
            # Create Archive node
            rman_archive = icons.get("archive_RIB")
            box.operator("export.export_rib_archive",
                         icon_value=rman_archive.icon_id)
        # Create Geo LightBlocker

        # Update Archive !! Not needed with current system.

        # Open Last RIB
        #rman_open_last_rib = icons.get("open_last_rib")
        #layout.prop(rm, "path_rib_output",icon_value=rman_open_last_rib.icon_id)

        # Inspect RIB Selection

        # Shared Geometry Attribute

        # Add/Atach Coordsys

        # Open Tmake Window  ?? Run Tmake on everything.

        # Create OpenVDB Visualizer
        layout.separator()
        # RenderMan Doc
        rman_help = icons.get("help")
        layout.operator("wm.url_open", text="RenderMan Docs",
                        icon_value=rman_help.icon_id).url = "https://github.com/prman-pixar/RenderManForBlender/wiki/Documentation-Home"
        rman_info = icons.get("info")
        layout.operator("wm.url_open", text="About RenderMan",
                        icon_value=rman_info.icon_id).url = "https://renderman.pixar.com/store/intro"

        # Reload the addon
        # rman_reload = icons.get("reload_plugin")
        # layout.operator("renderman.restartaddon", icon_value=rman_reload.icon_id)

        # Enable the menu item to display the examples menu in the RenderMan
        # Panel.
        layout.separator()
        layout.menu("PRMAN_MT_examples", icon_value=rman_help.icon_id)

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

classes = [
    #DATA_PT_renderman_camera,
    #DATA_PT_renderman_light,
    #DATA_PT_renderman_node_shader_light,
    DATA_PT_renderman_display_filters,
    DATA_PT_renderman_Sample_filters,
    DATA_PT_renderman_node_filters_light,

    PARTICLE_PT_renderman_particle,
    PARTICLE_PT_renderman_prim_vars,
    PRMAN_HT_DrawRenderHeaderInfo,
    PRMAN_HT_DrawRenderHeaderNode,
    PRMAN_HT_DrawRenderHeaderImage,
    PRMAN_PT_Renderman_Light_Panel,
    PRMAN_PT_Renderman_Light_Link_Panel,
    PRMAN_PT_Renderman_Object_Panel,
    PRMAN_PT_Renderman_UI_Panel,
    PRMAN_PT_context_material,
    ]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.utils.register_class(RENDERMAN_GROUP_UL_List)
    bpy.utils.register_class(RENDERMAN_UL_LIGHT_list)
    bpy.utils.register_class(RENDERMAN_UL_OBJECT_list)
    # bpy.utils.register_class(RENDERMAN_OUTPUT_list)
    # bpy.utils.register_class(RENDERMAN_CHANNEL_list)
    #bpy.types.TOPBAR_MT_render.append(PRMan_menu_func)

    for panel in get_panels():
        panel.COMPAT_ENGINES.add('PRMAN_RENDER')


def unregister():
    bpy.utils.unregister_class(RENDERMAN_GROUP_UL_List)
    bpy.utils.unregister_class(RENDERMAN_UL_LIGHT_list)
    bpy.utils.unregister_class(RENDERMAN_UL_OBJECT_list)
    # bpy.utils.register_class(RENDERMAN_OUTPUT_list)
    # bpy.utils.register_class(RENDERMAN_CHANNEL_list)
    #bpy.types.TOPBAR_MT_render.remove(PRMan_menu_func)

    for panel in get_panels():
        panel.COMPAT_ENGINES.remove('PRMAN_RENDER')

    for cls in classes:
        bpy.utils.unregister_class(cls)
