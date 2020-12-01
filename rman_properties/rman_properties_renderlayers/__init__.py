import bpy

from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty, BoolVectorProperty, PointerProperty
    
from ... import rman_bl_nodes
from ... import rman_config
from ...rfb_utils import scene_utils
from ...rman_config import RmanBasePropertyGroup

class RendermanDspyChannel(RmanBasePropertyGroup, bpy.types.PropertyGroup):
    rman_config_name: StringProperty(name='rman_config_name',
                                    default='rman_properties_dspychan') 

    def update_name(self, context):
        self.channel_name = self.name

    name: StringProperty(name='Channel Name', update=update_name)
    channel_name: StringProperty()

    channel_source: StringProperty(name="Channel Source",
            description="Source definition for the channel",
            default="lpe:C[<.D><.S>][DS]*[<L.>O]"
            )

    channel_type: EnumProperty(name="Channel Type",
            description="Channel type",
            items=[
                ("color", "color", ""),
                ("float", "float", ""),
                ("vector", "vector", ""),
                ("normal", "normal", ""),
                ("point", "point", ""),
                ("int", "int", "")],
            default="color"
            )            

    is_custom: BoolProperty(name="Custom", default=False)

    custom_lpe_string: StringProperty(
        name="lpe String",
        description="This is where you enter the custom lpe string")

    def object_groups(self, context):
        items = []
        items.append((" ", " ", ""))
        rm = context.scene.renderman
        for i, ogrp in enumerate(rm.object_groups):
            if i == 0:
                continue
            items.append((ogrp.name, ogrp.name, ""))
        return items        

    object_group: EnumProperty(name='Object Group', items=object_groups)       
    light_group: StringProperty(name='Light Group', default='')

class RendermanDspyChannelPointer(bpy.types.PropertyGroup):
    dspy_chan_idx: IntProperty(default=-1, name="Display Channel Index")

class RendermanAOV(RmanBasePropertyGroup, bpy.types.PropertyGroup):

    name: StringProperty(name='Display Name')
    rman_config_name: StringProperty(name='rman_config_name',
                                    default='rman_properties_aov') 


    def displaydriver_items(self, context):
        items = []   
        # default to OpenEXR    
        items.append(('openexr', 'openexr', '')) 
        for n in rman_bl_nodes.__RMAN_DISPLAY_NODES__:
            dspy = n.name.split('d_')[1]
            if dspy == 'openexr':
                continue
            items.append((dspy, dspy, ''))
        return items

    displaydriver: EnumProperty(
        name="Display Driver",
        description="Display driver for rendering",
        items=displaydriver_items)

    dspy_channels_index: IntProperty(min=-1, default=-1)   
    dspy_channels: CollectionProperty(type=RendermanDspyChannelPointer, name="Display Channels") 

class RendermanRenderLayerSettings(bpy.types.PropertyGroup):

    use_renderman: BoolProperty(name="use_renderman", default=False)
    custom_aovs: CollectionProperty(type=RendermanAOV,
                                     name='Custom AOVs')
    custom_aov_index: IntProperty(min=-1, default=-1)
    dspy_channels: CollectionProperty(type=RendermanDspyChannel,
                                     name='Display Channels')                                          


classes = [
    RendermanRenderLayerSettings          
]

props_classes = [
    (RendermanDspyChannel, 'rman_properties_dspychan'),    
    (RendermanDspyChannelPointer, ''),
    (RendermanAOV, 'rman_properties_aov')
]

def register():

    for cls,cfg_name in props_classes:
        if cfg_name:
            cls._add_properties(cls, cfg_name)
        bpy.utils.register_class(cls)    

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.ViewLayer.renderman = PointerProperty(
        type=RendermanRenderLayerSettings, name="Renderman RenderLayer Settings")           

def unregister():

    del bpy.types.ViewLayer.renderman

    for cls,cfg_name in props_classes:        
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass 

    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass
