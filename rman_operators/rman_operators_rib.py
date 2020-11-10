import bpy
import os
import webbrowser
import sys
from ..rfb_logger import rfb_log
from ..rfb_utils.prefs_utils import get_pref
from ..rfb_utils import prefs_utils
from ..rfb_utils import string_utils
from ..rfb_utils import filepath_utils
from ..rman_render import RmanRender
from bpy.props import StringProperty, BoolProperty


def _view_rib(rib_output):
    
    rman_editor = get_pref('rman_editor', '')

    if rman_editor:
        rman_editor = filepath_utils.get_real_path(rman_editor)
        command = rman_editor + " " + rib_output
        try:
            os.system(command)
            return
        except Exception:
            rfb_log().error("File or text editor not available. (Check and make sure text editor is in system path.)")        


    if sys.platform == ("win32"):
        try:
            os.startfile(rib_output)
            return
        except:
            pass
    else:
        if sys.platform == ("darwin"):
            opener = 'open -t'
        else:
            opener = os.getenv('EDITOR', 'xdg-open')
            opener = os.getenv('VIEW', opener)
        try:
            command = opener + " " + rib_output
            os.system(command)
        except Exception as e:
            rfb_log().error("Open RIB file command failed: %s" % command)
            pass
        
    # last resort, try webbrowser
    try:
        webbrowser.open(rib_output)
    except Exception as e:
        rfb_log().error("Open RIB file with web browser failed: %s" % str(e))

class PRMAN_OT_Renderman_open_scene_RIB(bpy.types.Operator):
    bl_idname = 'renderman.open_scene_rib'
    bl_label = "View RIB."
    bl_description = "Generate RIB for the current frame and open in a text editor"

    def invoke(self, context, event=None):
        scene = context.scene
        rman_render = RmanRender.get_rman_render()
        if not rman_render.rman_interactive_running:   
            rm = scene.renderman     
            rm.enable_external_rendering = True
            anim_prev_val = rm.external_animation
            spool_prev_val = rm.queuing_system
            format_prev_val = rm.rib_format
            rm.external_animation = False
            rm.queuing_system = 'none'
            rm.rib_format = 'ASCII'
            bpy.ops.render.render()
            rm.enable_external_rendering = False
            rm.external_animation = anim_prev_val
            rm.queuing_system = spool_prev_val
            rm.rib_format = format_prev_val

            rib_output = string_utils.expand_string(rm.path_rib_output, 
                                                    frame=scene.frame_current, 
                                                    asFilePath=True)   

            _view_rib(rib_output)
        else:
            self.report({"ERROR"}, "Viewport rendering is on.")   

        return {'FINISHED'}

class PRMAN_OT_Open_Selected_RIB(bpy.types.Operator):
    bl_idname = "renderman.open_selected_rib"
    bl_label = "View Selected RIB"
    bl_description = "Open RIB for selected object"

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def invoke(self, context, event=None):
        ob = context.active_object
        if ob:
            temp_dir = prefs_utils.get_bl_temp_dir()
            rib_output = os.path.join(temp_dir, 'selected.rib')
            rman_render = RmanRender.get_rman_render()
            if not rman_render.rman_interactive_running:
                rman_render.start_export_rib_selected(context, rib_output, export_materials=True, export_all_frames=False)
                _view_rib(rib_output)
            else:
                self.report({"ERROR"}, "Viewport rendering is on.")

        else:
            rfb_log().error("Nothing selected for RIB export.")

        return {'FINISHED'}         

class PRMAN_OT_ExportRIBObject(bpy.types.Operator):
    bl_idname = "export.rman_export_rib_archive"
    bl_label = "Export Object as RIB Archive"
    bl_description = "Export single object as a RIB archive for use in other blend files or for other uses"

    export_mat: BoolProperty(
        name="Export Material",
        description="Do you want to export the material?",
        default=True)

    export_all_frames: BoolProperty(
        name="Export All Frames",
        description="Export entire animation time frame",
        default=False)

    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH")

    filename: bpy.props.StringProperty(
        subtype="FILE_NAME",
        default="")

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def execute(self, context):
        ob = context.active_object
        if ob:
            export_path = self.filepath
            export_range = self.export_all_frames
            export_mats = self.export_mat
            rman_render = RmanRender.get_rman_render()
            if not rman_render.rman_interactive_running:
                rman_render.start_export_rib_selected(context, export_path, export_materials=export_mats, export_all_frames=export_range)
            else:
                self.report({"ERROR"}, "Viewport rendering is on.")

        else:
            rfb_log().error("Nothing selected for RIB export.")

        return {'FINISHED'}

    def invoke(self, context, event=None):

        context.window_manager.fileselect_add(self)
        return{'RUNNING_MODAL'}        

classes = [
    PRMAN_OT_Renderman_open_scene_RIB,
    PRMAN_OT_Open_Selected_RIB,
    PRMAN_OT_ExportRIBObject
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
