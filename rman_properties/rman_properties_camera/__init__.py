import bpy
from bpy.props import PointerProperty, BoolProperty, \
    EnumProperty, FloatProperty, StringProperty
from ... import rman_bl_nodes
from ... import rman_config
from ...rman_config import RmanBasePropertyGroup

class RendermanCameraSettings(RmanBasePropertyGroup, bpy.types.PropertyGroup):
    bl_label = "RenderMan Camera Settings"
    bl_idname = 'RendermanCameraSettings'

    rman_config_name: StringProperty(name='rman_config_name',
                                    default='rman_properties_camera')    

    def get_projection_name(self):
        return self.projection_type.replace('_settings', '')

    def get_projection_node(self):
        return getattr(self, self.projection_type + '_settings')

    def projection_items(self, context):
        items = []
        items.append(('none', 'None', 'None'))
        for n in rman_bl_nodes.__RMAN_PROJECTION_NODES__ :
            items.append((n.name, n.name, ''))
        return items

    projection_type: EnumProperty(
        items=projection_items, name='Projection Plugin')

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
    for cls in classes:
        bpy.utils.unregister_class(cls)     