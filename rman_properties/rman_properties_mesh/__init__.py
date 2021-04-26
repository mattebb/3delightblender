from bpy.props import PointerProperty, IntProperty, CollectionProperty

from ...rfb_logger import rfb_log 
from ...rman_config import RmanBasePropertyGroup
from ..rman_properties_misc import RendermanMeshPrimVar, RendermanMeshReferencePose 

import bpy

class RendermanMeshGeometrySettings(RmanBasePropertyGroup, bpy.types.PropertyGroup):
    prim_vars: CollectionProperty(
        type=RendermanMeshPrimVar, name="Primitive Variables")
    prim_vars_index: IntProperty(min=-1, default=-1)

    reference_pose: CollectionProperty(
        type=RendermanMeshReferencePose, name=""
    )

classes = [         
    RendermanMeshGeometrySettings
]           

def register():

    for cls in classes:
        cls._add_properties(cls, 'rman_properties_mesh')
        bpy.utils.register_class(cls)  

    bpy.types.Mesh.renderman = PointerProperty(
        type=RendermanMeshGeometrySettings,
        name="Renderman Mesh Geometry Settings")

def unregister():

    del bpy.types.Mesh.renderman

    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass