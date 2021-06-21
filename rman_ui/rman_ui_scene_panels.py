from .rman_ui_base import PRManButtonsPanel 
from bpy.types import Panel
import bpy

class PRMAN_PT_Renderman_Light_Mixer_Panel(PRManButtonsPanel, Panel):
    bl_label = "RenderMan Light Mixer"
    bl_context = "scene"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW' 

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        rm = scene.renderman

        row = layout.row()
        row.operator('scene.rman_open_light_mixer_editor', text='Open Light Mixer Editor')   

class PRMAN_PT_Renderman_Light_Linking_Panel(PRManButtonsPanel, Panel):
    bl_label = "RenderMan Light Linking"
    bl_context = "scene"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'  

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.operator('scene.rman_open_light_linking', text='Open Light Linking')            

class PRMAN_PT_Renderman_Groups_Panel(PRManButtonsPanel, Panel):
    bl_label = "RenderMan Trace Sets"
    bl_context = "scene"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        layout.operator('scene.rman_open_groups_editor', text='Trace Sets Editor')                                                   

classes = [
    PRMAN_PT_Renderman_Light_Mixer_Panel, 
    PRMAN_PT_Renderman_Light_Linking_Panel,
    PRMAN_PT_Renderman_Groups_Panel
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