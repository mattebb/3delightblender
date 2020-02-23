from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty, BoolVectorProperty

from ...rman_utils import filepath_utils
from ...rman_utils import property_utils
from ...rfb_logger import rfb_log
from ... import rman_render
from ... import rman_bl_nodes
from ...rman_bl_nodes import rman_bl_nodes_props    
from ...properties import RendermanGroup,RendermanRenderLayerSettings,LightLinking
from ... import rman_config
from ...rman_config import RmanBasePropertyGroup
from ..rman_properties_misc import RendermanOpenVDBChannel, RendermanAnimSequenceSettings 

import bpy

class RendermanObjectSettings(RmanBasePropertyGroup, bpy.types.PropertyGroup):

    rman_config_name: StringProperty(name='rman_config_name',
                                    default='rman_properties_object')

    openvdb_channels: CollectionProperty(
        type=RendermanOpenVDBChannel, name="OpenVDB Channels")
    openvdb_channel_index: IntProperty(min=-1, default=-1)

    archive_anim_settings: PointerProperty(
        type=RendermanAnimSequenceSettings,
        name="Animation Sequence Settings")    

    export_archive: BoolProperty(
        name="Export as Archive",
        description="At render export time, store this object as a RIB archive",
        default=False)
    export_archive_path: StringProperty(
        name="Archive Export Path",
        description="Path to automatically save this object as a RIB archive",
        subtype='FILE_PATH',
        default="")

classes = [         
    RendermanObjectSettings
]           

def register():

    for cls in classes:
        cls._add_properties(cls, 'rman_properties_object')
        bpy.utils.register_class(cls)  

    bpy.types.Object.renderman = PointerProperty(
        type=RendermanObjectSettings, name="Renderman Object Settings")

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)