from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty, BoolVectorProperty

from ...rman_utils import filepath_utils
from ...rman_utils import property_utils
from ...rfb_logger import rfb_log 
from ...properties import RendermanGroup,RendermanRenderLayerSettings,LightLinking
from ... import rman_config

import bpy

class RendermanMeshPrimVar(bpy.types.PropertyGroup):
    name: StringProperty(
        name="Variable Name",
        description="Name of the exported renderman primitive variable")
    data_name: StringProperty(
        name="Data Name",
        description="Name of the Blender data to export as the primitive variable")
    data_source: EnumProperty(
        name="Data Source",
        description="Blender data type to export as the primitive variable",
        items=[('VERTEX_GROUP', 'Vertex Group', ''),
               ('VERTEX_COLOR', 'Vertex Color', ''),
               ('UV_TEXTURE', 'UV Texture', '')
               ]
    )

class RendermanOpenVDBChannel(bpy.types.PropertyGroup):
    name: StringProperty(name="Channel Name")
    type: EnumProperty(name="Channel Type",
                        items=[
                            ('float', 'Float', ''),
                            ('vector', 'Vector', ''),
                            ('color', 'Color', ''),
                        ])

class RendermanAnimSequenceSettings(bpy.types.PropertyGroup):
    animated_sequence: BoolProperty(
        name="Animated Sequence",
        description="Interpret this archive as an animated sequence (converts #### in file path to frame number)",
        default=False)
    sequence_in: IntProperty(
        name="Sequence In Point",
        description="The first numbered file to use",
        default=1)
    sequence_out: IntProperty(
        name="Sequence Out Point",
        description="The last numbered file to use",
        default=24)
    blender_start: IntProperty(
        name="Blender Start Frame",
        description="The frame in Blender to begin playing back the sequence",
        default=1)

classes = [      
    RendermanMeshPrimVar,   
    RendermanOpenVDBChannel,
    RendermanAnimSequenceSettings
]

def register():

    for cls in classes:
        bpy.utils.register_class(cls)  

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)                        