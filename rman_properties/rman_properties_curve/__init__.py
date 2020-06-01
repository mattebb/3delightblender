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

    del bpy.types.Curve.renderman

    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass