from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty, PointerProperty

from ...rman_utils import filepath_utils
from ...rman_utils import property_utils
from ...rfb_logger import rfb_log
from ...rman_config import RmanBasePropertyGroup

import bpy

class RendermanMaterialSettings(RmanBasePropertyGroup, bpy.types.PropertyGroup):
    rman_config_name: StringProperty(name='rman_config_name',
                                    default='rman_properties_material') 

classes = [         
    RendermanMaterialSettings
]           

def register():

    for cls in classes:
        cls._add_properties(cls, 'rman_properties_material')
        bpy.utils.register_class(cls)  

    bpy.types.Material.renderman = PointerProperty(
        type=RendermanMaterialSettings, name="Renderman Material Settings")

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)