from .rman_ui_base import PRManButtonsPanel 
from bpy.types import Panel
import bpy

class RENDER_PT_renderman_workspace(PRManButtonsPanel, Panel):
    bl_label = "Workspace"
    bl_context = "output"

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        if context.scene.render.engine != "PRMAN_RENDER":
            return

        layout = self.layout
        layout.prop(context.scene.renderman, 'root_path_output')
        layout.operator('scene.rman_open_workspace', text='Open Workspace')

classes = [
    RENDER_PT_renderman_workspace
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():

    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass        