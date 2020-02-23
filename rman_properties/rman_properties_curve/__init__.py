import bpy
from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    IntProperty, CollectionProperty
from ..rman_properties_misc import RendermanMeshPrimVar     


class RendermanCurveGeometrySettings(bpy.types.PropertyGroup):
    export_default_uv: BoolProperty(
        name="Export Default UVs",
        description="Export the active UV set as the default 'st' primitive variable",
        default=True)
    export_default_vcol: BoolProperty(
        name="Export Default Vertex Color",
        description="Export the active Vertex Color set as the default 'Cs' primitive variable",
        default=True)
    export_smooth_normals: BoolProperty(
        name="Export Smooth Normals",
        description="Export smooth per-vertex normals for PointsPolygons Geometry",
        default=True)

    prim_vars: CollectionProperty(
        type=RendermanMeshPrimVar, name="Primitive Variables")
    prim_vars_index: IntProperty(min=-1, default=-1)

classes = [         
    RendermanCurveGeometrySettings
]           

def register():

    for cls in classes:
        bpy.utils.register_class(cls)  

    bpy.types.Curve.renderman = PointerProperty(
        type=RendermanCurveGeometrySettings,
        name="Renderman Curve Geometry Settings")

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)