from . import rman_ui_txmanager
from . import rman_ui_aovs
from . import rman_ui_viewport
from . import rman_ui_light_handlers

def register():
    rman_ui_txmanager.register()
    rman_ui_aovs.register()
    rman_ui_viewport.register()
    rman_ui_light_handlers.register()

def unregister():
    rman_ui_txmanager.unregister()
    rman_ui_aovs.unregister()
    rman_ui_viewport.unregister()
    rman_ui_light_handlers.unregister()
