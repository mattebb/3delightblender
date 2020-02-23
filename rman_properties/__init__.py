from . import rman_properties_scene
from . import rman_properties_misc
from . import rman_properties_object
from . import rman_properties_mesh
from . import rman_properties_material
from . import rman_properties_curve
from . import rman_properties_world

def register():
    rman_properties_scene.register()
    rman_properties_misc.register()
    rman_properties_object.register()
    rman_properties_mesh.register()
    rman_properties_material.register()
    rman_properties_curve.register()
    rman_properties_world.register()

def unregister():
    rman_properties_scene.unregister()
    rman_properties_misc.unregister()
    rman_properties_object.unregister()
    rman_properties_mesh.unregister()
    rman_properties_material.unregister()
    rman_properties_curve.unregister()
    rman_properties_world.unregister()