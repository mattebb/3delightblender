from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty, PointerProperty

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

    del bpy.types.Material.renderman

    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass