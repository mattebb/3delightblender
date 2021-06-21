from bpy.types import Operator
from bpy.props import StringProperty, IntProperty, CollectionProperty, EnumProperty, BoolProperty
import bpy

class PRMAN_OT_Renderman_printer(Operator):
    """An operator to simply print messages."""

    bl_idname = "renderman.printer"
    bl_label = "RenderMan Message"
    bl_options = {'INTERNAL'}

    message: StringProperty()
    
    level: EnumProperty(
        name="level",
        items=[
            ('INFO', 'INFO', ''),
            ('ERROR', 'ERROR', ''),
            ('DEBUG', 'DEBUG', ''),
            ('WARNING', 'WARNING', '')
        ]
    )

    @classmethod
    def poll(cls, context):
        if hasattr(context, 'window_manager'):
            return True
        return False


    def draw(self, context):
        layout = self.layout
        col = layout.column()
        rman_icon = 'ERROR'
        if self.level == 'INFO':
            rman_icon = 'INFO'

        col.label(text='%s' % self.message, icon=rman_icon)  

    def execute(self, context):  
        try:
            self.report({'%s' % self.level}, '%s' % self.message )
        except RuntimeError as e:
            pass

        return{'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)   

classes = [
   PRMAN_OT_Renderman_printer 
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