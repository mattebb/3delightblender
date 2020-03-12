from . import rman_operators_printer
from . import rman_operators_view3d

def register():
    rman_operators_printer.register()
    rman_operators_view3d.register()

def unregister():
    rman_operators_printer.unregister()
    rman_operators_view3d.unregister()