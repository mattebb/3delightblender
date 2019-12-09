from . import rman_ui_txmanager
from . import rman_ui_aovs
from . import rman_ui_viewport

def register():
    rman_ui_txmanager.register()
    rman_ui_aovs.register()
    rman_ui_viewport.register()

def unregister():
    rman_ui_txmanager.unregister()
    rman_ui_aovs.unregister()
    rman_ui_viewport.unregister()
