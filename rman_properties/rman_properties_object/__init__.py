from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, \
    CollectionProperty

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

    del bpy.types.Object.renderman

    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass