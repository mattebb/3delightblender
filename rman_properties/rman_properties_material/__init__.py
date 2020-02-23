from bpy.props import BoolProperty, EnumProperty, IntProperty, PointerProperty

from ...rman_utils import filepath_utils
from ...rman_utils import property_utils
from ...rfb_logger import rfb_log
from ...rman_config import RmanBasePropertyGroup

import bpy

class RendermanMaterialSettings(bpy.types.PropertyGroup):
    instance_num: IntProperty(name='Instance number for IPR', default=0)

    preview_render_type: EnumProperty(
        name="Preview Render Type",
        description="Object to display in material preview",
        items=[('SPHERE', 'Sphere', ''),
               ('CUBE', 'Cube', '')],
        default='SPHERE')

    copy_color_params: BoolProperty(
        name="Copy Color Parameters",
        description="""Copy Blender material color parameters when adding a new RenderMan node tree. Copies
                    diffuse_color, diffuse_intensity, and specular_color. Only used if we are unable
                    to convert a Cycles shading network.""",
        default=False)

classes = [         
    RendermanMaterialSettings
]           

def register():

    for cls in classes:
        bpy.utils.register_class(cls)  

    bpy.types.Material.renderman = PointerProperty(
        type=RendermanMaterialSettings, name="Renderman Material Settings")

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)