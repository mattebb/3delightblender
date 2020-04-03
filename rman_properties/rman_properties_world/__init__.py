import bpy
from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    IntProperty, CollectionProperty, EnumProperty, FloatProperty
from ..rman_properties_misc import RendermanMeshPrimVar     


class RendermanWorldSettings(bpy.types.PropertyGroup):

    use_renderman_node: BoolProperty(
        name="Use RenderMans World Node",
        description="Will enable RenderMan World Nodes, opening more options",
        default=False)

classes = [         
    RendermanWorldSettings
]           

def register():

    for cls in classes:
        bpy.utils.register_class(cls)  

    bpy.types.World.renderman = PointerProperty(
        type=RendermanWorldSettings, name="Renderman World Settings")

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)