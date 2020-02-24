from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, \
    CollectionProperty

from ...rman_utils import filepath_utils
from ...rman_utils import property_utils
from ...rfb_logger import rfb_log
from ... import rman_render
from ... import rman_bl_nodes
from ...rman_bl_nodes import rman_bl_nodes_props    
from ..rman_properties_misc import RendermanGroup, LightLinking
from ..rman_properties_renderlayers import RendermanRenderLayerSettings
from ... import rman_config
from ...rman_config import RmanBasePropertyGroup

import bpy
import os
import sys

class RendermanSceneSettings(RmanBasePropertyGroup, bpy.types.PropertyGroup):

    rman_config_name: StringProperty(name='rman_config_name',
                                    default='rman_properties_scene')
    
    display_filters: CollectionProperty(
                        type=rman_bl_nodes_props.RendermanDisplayFilterSettings, 
                        name='Display Filters')
    display_filters_index: IntProperty(min=-1, default=-1)

    sample_filters: CollectionProperty(
                        type=rman_bl_nodes_props.RendermanSampleFilterSettings, 
                        name='Sample Filters')
    sample_filters_index: IntProperty(min=-1, default=-1)

    light_groups: CollectionProperty(type=RendermanGroup,
                                      name='Light Groups')
    light_groups_index: IntProperty(min=-1, default=-1)

    ll: CollectionProperty(type=LightLinking,
                            name='Light Links')

    # we need these in case object/light selector changes
    def reset_ll_light_index(self, context):
        self.ll_light_index = -1

    def reset_ll_object_index(self, context):
        self.ll_object_index = -1

    ll_light_index: IntProperty(min=-1, default=-1)
    ll_object_index: IntProperty(min=-1, default=-1)
    ll_light_type: EnumProperty(
        name="Select by",
        description="Select by",
        items=[('light', 'Lights', ''),
               ('group', 'Light Groups', '')],
        default='group', update=reset_ll_light_index)

    ll_object_type: EnumProperty(
        name="Select by",
        description="Select by",
        items=[('object', 'Objects', ''),
               ('group', 'Object Groups', '')],
        default='group', update=reset_ll_object_index)

    render_layers: CollectionProperty(type=RendermanRenderLayerSettings,
                                       name='Custom AOVs')


    def update_scene_solo_light(self, context):
        rr = rman_render.RmanRender.get_rman_render()        
        if rr.rman_interactive_running:
            if self.solo_light:
                rr.rman_scene.update_solo_light(context)
            else:
                rr.rman_scene.update_un_solo_light(context)

    solo_light: BoolProperty(name="Solo Light", update=update_scene_solo_light, default=False)

    render_selected_objects_only: BoolProperty(
        name="Only Render Selected",
        description="Render only the selected object(s)",
        default=False)

    external_animation: BoolProperty(
        name="Render Animation",
        description="Spool Animation",
        default=False)

    def update_integrator(self, context):
        rr = rman_render.RmanRender.get_rman_render()
        if rr.rman_interactive_running:
            rr.rman_scene.update_integrator(context)

    def integrator_items(self, context):
        items = []
        # Make PxrPathTracer be the first item, so
        # it's the default
        items.append(('PxrPathTracer', 'PxrPathTracer', ''))
        for n in rman_bl_nodes.__RMAN_INTEGRATOR_NODES__:
            if n.name != 'PxrPathTracer':
                items.append((n.name, n.name, ''))
        return items

    integrator: EnumProperty(
        name="Integrator",
        description="Integrator for rendering",
        items=integrator_items,
        update=update_integrator)

    show_integrator_settings: BoolProperty(
        name="Integration Settings",
        description="Show Integrator Settings",
        default=False
    )

    # Trace Sets (grouping membership)
    object_groups: CollectionProperty(
        type=RendermanGroup, name="Trace Sets")
    object_groups_index: IntProperty(min=-1, default=-1)

classes = [         
    RendermanSceneSettings
]           

def register():

    for cls in classes:
        cls._add_properties(cls, 'rman_properties_scene')
        bpy.utils.register_class(cls)  

    bpy.types.Scene.renderman = PointerProperty(
        type=RendermanSceneSettings, name="Renderman Scene Settings")    

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)