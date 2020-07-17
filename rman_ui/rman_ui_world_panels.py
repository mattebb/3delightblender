from .rman_ui_base import ShaderPanel
from bpy.props import (PointerProperty, StringProperty, BoolProperty,
                       EnumProperty, IntProperty, FloatProperty, FloatVectorProperty,
                       CollectionProperty)

from .rman_ui_base import CollectionPanel   
from .rman_ui_base import PRManButtonsPanel 
from ..rman_utils.draw_utils import draw_node_properties_recursive, draw_nodes_properties_ui
from ..rman_utils.shadergraph_utils import find_node
from .. import rfb_icons
from bpy.types import Panel
import bpy

class DATA_PT_renderman_world(ShaderPanel, Panel):
    bl_context = "world"
    bl_label = "World"
    shader_type = 'world'

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        world = context.scene.world
        return rd.engine == 'PRMAN_RENDER' and not world.renderman.use_renderman_node    

    def draw(self, context):
        layout = self.layout
        world = context.scene.world

        if not world.renderman.use_renderman_node:
            layout.prop(world, 'color')
            rman_icon = rfb_icons.get_icon('rman_graph')
            layout.operator('material.rman_add_rman_nodetree', icon_value=rman_icon.icon_id).idtype = 'world'
        
class DATA_PT_renderman_world_integrators(ShaderPanel, Panel):
    bl_label = "Integrator"
    bl_context = 'world'

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        world = context.scene.world
        return rd.engine == 'PRMAN_RENDER' and world.renderman.use_renderman_node

    def draw(self, context):
        layout = self.layout
        world = context.scene.world
        rm = world.renderman
        nt = world.node_tree

        draw_nodes_properties_ui(layout, context, nt, input_name='Integrator', output_node_type='integrators_output')

class DATA_PT_renderman_world_display_filters(ShaderPanel, Panel):
    bl_label = "Display Filters"
    bl_context = 'world'

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        world = context.scene.world
        return rd.engine == 'PRMAN_RENDER' and world.renderman.use_renderman_node

    def draw(self, context):
        layout = self.layout
        world = context.scene.world
        rm = world.renderman
        nt = world.node_tree

        output = find_node(world, 'RendermanDisplayfiltersOutputNode')
        if not output:
            return
      
        row = layout.row(align=True)
        col = row.column()
        col.operator('node.rman_add_displayfilter_node_socket', text='Add')
        col = row.column()
        col.enabled = len(output.inputs) > 1
        col.operator('node.rman_remove_displayfilter_node_socket', text='Remove')
        for socket in output.inputs:
            layout.label(text=socket.name)
            layout.context_pointer_set("node", output)
            layout.context_pointer_set("nodetree", nt)
            layout.context_pointer_set("socket", socket)      
            if socket.is_linked:
                link = socket.links[0]
                node = link.from_node                 
                rman_icon = rfb_icons.get_displayfilter_icon(node.bl_label)
                layout.menu('NODE_MT_renderman_connection_menu', text=node.bl_label, icon_value=rman_icon.icon_id)
                draw_node_properties_recursive(layout, context, nt, node, level=1)                    
            else:
                layout.menu('NODE_MT_renderman_connection_menu', text='None', icon='NODE_MATERIAL')         

class DATA_PT_renderman_world_sample_filters(ShaderPanel, Panel):
    bl_label = "Sample Filters"
    bl_context = 'world'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        world = context.scene.world
        return rd.engine == 'PRMAN_RENDER' and world.renderman.use_renderman_node

    def draw(self, context):
        layout = self.layout
        world = context.scene.world
        rm = world.renderman
        nt = world.node_tree

        output = find_node(world, 'RendermanSamplefiltersOutputNode')
        if not output:
            return   

        row = layout.row(align=True)
        col = row.column()
        col.operator('node.rman_add_samplefilter_node_socket', text='Add')
        col = row.column()
        col.enabled = len(output.inputs) > 1
        col.operator('node.rman_remove_samplefilter_node_socket', text='Remove')
        for socket in (output.inputs):
            layout.label(text=socket.name)

            layout.context_pointer_set("socket", socket)
            layout.context_pointer_set("node", output)
            layout.context_pointer_set("nodetree", nt)            
            if socket.is_linked:
                link = socket.links[0]
                node = link.from_node                 
                rman_icon = rfb_icons.get_samplefilter_icon(node.bl_label)
                layout.menu('NODE_MT_renderman_connection_menu', text=node.bl_label, icon_value=rman_icon.icon_id)
                draw_node_properties_recursive(layout, context, nt, node, level=1)                    
            else:
                layout.menu('NODE_MT_renderman_connection_menu', text='None', icon='NODE_MATERIAL')   
    
classes = [
    DATA_PT_renderman_world,
    DATA_PT_renderman_world_integrators,
    DATA_PT_renderman_world_display_filters,
    DATA_PT_renderman_world_sample_filters
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