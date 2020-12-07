from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, \
    CollectionProperty

from ...rfb_utils import filepath_utils
from ...rfb_utils import property_utils
from ...rfb_logger import rfb_log
from ... import rman_render
from ... import rman_bl_nodes
from ...rman_bl_nodes import rman_bl_nodes_props    
from ..rman_properties_misc import RendermanLightGroup, RendermanGroup, LightLinking, RendermanUserTokenGroup
from ..rman_properties_renderlayers import RendermanRenderLayerSettings
from ... import rman_config
from ...rman_config import RmanBasePropertyGroup

import bpy
import os
import sys

class RendermanSceneSettings(RmanBasePropertyGroup, bpy.types.PropertyGroup):

    rman_config_name: StringProperty(name='rman_config_name',
                                    default='rman_properties_scene')
    
    light_groups: CollectionProperty(type=RendermanLightGroup,
                                      name='Light Groups')
    light_groups_index: IntProperty(min=-1, default=-1)

    light_mixer_groups: CollectionProperty(type=RendermanLightGroup,
                                      name='Light Mixer Groups')
    light_mixer_groups_index: IntProperty(min=-1, default=-1)    

    light_links: CollectionProperty(type=LightLinking,
                            name='Light Links')

    def update_light_link_index(self, context):
        scene = context.scene
        rm = scene.renderman
        light_links = rm.light_links[rm.light_links_index]
        light_ob = light_links.light_ob
                
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        light_ob.select_set(True)
        context.view_layer.objects.active = light_ob    

    light_links_index: IntProperty(min=-1, default=-1, update=update_light_link_index)

    def update_scene_solo_light(self, context):
        rr = rman_render.RmanRender.get_rman_render()        
        if self.solo_light:
            rr.rman_scene_sync.update_solo_light(context)
        else:
            rr.rman_scene_sync.update_un_solo_light(context)

    solo_light: BoolProperty(name="Solo Light", update=update_scene_solo_light, default=False)

    render_selected_objects_only: BoolProperty(
        name="Only Render Selected",
        description="Render only the selected object(s)",
        default=False)

    external_animation: BoolProperty(
        name="Render Animation",
        description="Spool Animation",
        default=False)

    # Trace Sets (grouping membership)
    object_groups: CollectionProperty(
        type=RendermanGroup, name="Trace Sets")
    object_groups_index: IntProperty(min=-1, default=-1)

    # Tokens
    version_token: IntProperty(name="version", default=1, min=1)
    take_token: IntProperty(name="take", default=1, min=1)
    user_tokens: CollectionProperty(type=RendermanUserTokenGroup, name="User Tokens")
    user_tokens_index: IntProperty(min=-1, max=10, default=-1)

    # txmanager
    txmanagerData: StringProperty(name="txmanagerData", default="")

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

    del bpy.types.Scene.renderman

    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass
