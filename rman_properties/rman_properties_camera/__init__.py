import bpy
from bpy.props import PointerProperty, BoolProperty, \
    EnumProperty, FloatProperty, StringProperty
from ... import rman_config
from ...rman_config import RmanBasePropertyGroup

class RendermanCameraSettings(RmanBasePropertyGroup, bpy.types.PropertyGroup):
    bl_label = "RenderMan Camera Settings"
    bl_idname = 'RendermanCameraSettings'

    rman_config_name: StringProperty(name='rman_config_name',
                                    default='rman_properties_camera')    

    rman_nodetree: PointerProperty(
        name="NodeTree",
        type=bpy.types.ShaderNodeTree
    )

classes = [
    RendermanCameraSettings,
]

def register():
    for cls in classes:
        cls._add_properties(cls, 'rman_properties_camera')
        bpy.utils.register_class(cls)

    bpy.types.Camera.renderman = PointerProperty(
        type=RendermanCameraSettings, name="Renderman Camera Settings")  
   
def unregister():

    del bpy.types.Camera.renderman

    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass     