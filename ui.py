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

def PRMan_menu_func(self, context):
    if context.scene.render.engine != "PRMAN_RENDER":
        return
    self.layout.separator()

    rman_render = RmanRender.get_rman_render()
    is_rman_interactive_running = rman_render.rman_interactive_running

    if not is_rman_interactive_running:
        self.layout.operator('renderman.start_ipr',
                            text="RenderMan Start Interactive Rendering")
    else:
        self.layout.operator('renderman.stop_ipr',
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


classes = [

    ]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    for panel in get_panels():
        panel.COMPAT_ENGINES.add('PRMAN_RENDER')


def unregister():

    for panel in get_panels():
        panel.COMPAT_ENGINES.remove('PRMAN_RENDER')

    for cls in classes:
        bpy.utils.unregister_class(cls)
