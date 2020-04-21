import bpy
from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    IntProperty, CollectionProperty
from ...rman_config import RmanBasePropertyGroup    
from ..rman_properties_misc import RendermanMeshPrimVar     


class RendermanCurveGeometrySettings(RmanBasePropertyGroup, bpy.types.PropertyGroup):
    prim_vars: CollectionProperty(
        type=RendermanMeshPrimVar, name="Primitive Variables")
    prim_vars_index: IntProperty(min=-1, default=-1)

classes = [         
    RendermanCurveGeometrySettings
]           

def register():

    for cls in classes:
        cls._add_properties(cls, 'rman_properties_curve')
        bpy.utils.register_class(cls)  

    bpy.types.Curve.renderman = PointerProperty(
        type=RendermanCurveGeometrySettings,
        name="Renderman Curve Geometry Settings")

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)