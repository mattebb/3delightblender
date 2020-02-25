import bpy

from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty, BoolVectorProperty
    
from ... import rman_bl_nodes
from ... import rman_config
from ...rman_config import RmanBasePropertyGroup

class RendermanDspyChannel(RmanBasePropertyGroup, bpy.types.PropertyGroup):
    rman_config_name: StringProperty(name='rman_config_name',
                                    default='rman_properties_dspychan') 

    def channel_list(self, context):
        items = []
        items.append(("SELECT", "", "", "", 1))
        pages = dict()
        i = 2
        for nm,settings in rman_config.__RMAN_DISPLAY_CHANNELS__.items():
            page_nm = settings['group']
            lst = None
            if page_nm not in pages:
                pages[page_nm] = []
            lst = pages[page_nm]
            item = ( ('%s %s' % (settings['channelType'], settings['channelSource']), nm, settings['description'], "", i ) )
            i += 1
            lst.append(item)

        for page_nm,page_items in pages.items():
            items.append( ("", page_nm, page_nm, "", 0 ) )
            for page_item in page_items:
                items.append(page_item)
        
        return items

    def update_type(self, context):
        types = self.channel_list(context)
        if self.channel_selector == "SELECT":
            return
        for item in types:
            if self.channel_selector == item[0]:
                self.channel_def = item[0]
                self.name = item[1]
                self.channel_name = item[1]
                self.channel_selector = "SELECT"
                break

    name: StringProperty(name='Channel Name')
    channel_name: StringProperty()

    channel_def: StringProperty(name="Channel Definition",
            description="This contains both the type and the source for the channel"
            )

    channel_selector: EnumProperty(name="Select Channel",
                            description="",
                            items=channel_list, update=update_type)

    custom_lpe_string: StringProperty(
        name="lpe String",
        description="This is where you enter the custom lpe string")

    def light_groups(self, context):
        items = []
        items.append((" ", " ", ""))
        rm = context.scene.renderman
        for i, lgrp in enumerate(rm.light_groups):
            if i == 0:
                continue
            items.append((lgrp.name, lgrp.name, ""))
        return items

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
    light_group: EnumProperty(name='Light Group', items=light_groups)

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

    dspy_channels: CollectionProperty(type=RendermanDspyChannel,
                                     name='Display Channels')
    dspy_channels_index: IntProperty(min=-1, default=-1)    

class RendermanRenderLayerSettings(bpy.types.PropertyGroup):

    render_layer: StringProperty()
    custom_aovs: CollectionProperty(type=RendermanAOV,
                                     name='Custom AOVs')
    custom_aov_index: IntProperty(min=-1, default=-1)

classes = [
    RendermanRenderLayerSettings          
]

props_classes = [
    (RendermanDspyChannel, 'rman_properties_dspychan'),
    (RendermanAOV, 'rman_properties_aov')
]

def register():

    for cls,cfg_name in props_classes:
        cls._add_properties(cls, cfg_name)
        bpy.utils.register_class(cls)    

    for cls in classes:
        bpy.utils.register_class(cls)

        

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
