from ..rfb_utils import filepath_utils
from ..rman_render import RmanRender
import bpy
import os
import time
import webbrowser

class PRMAN_OT_Renderman_Use_Renderman(bpy.types.Operator):
    bl_idname = "renderman.use_renderman"
    bl_label = "Use RenderMan"
    bl_description = "Switch render engine to RenderMan"
            
    def execute(self, context):
        rd = context.scene.render
        if rd.engine != 'PRMAN_RENDER':
            rd.engine = 'PRMAN_RENDER'

        return {'FINISHED'}

class PRMAN_OT_RendermanBake(bpy.types.Operator):
    bl_idname = "renderman.bake"
    bl_label = "Baking"
    bl_description = "Bake pattern nodes and/or illumination to 2D and 3D formats."
    bl_options = {'INTERNAL'}    
            
    def execute(self, context):

        scene = context.scene
        rm = scene.renderman
        if not rm.is_rman_interactive_running:
            scene.renderman.hider_type = 'BAKE'
            bpy.ops.render.render(layer=context.view_layer.name)
            scene.renderman.hider_type = 'RAYTRACE'
        else:
            self.report({"ERROR"}, "Viewport rendering is on.")        
        return {'FINISHED'}

class PRMAN_OT_RendermanBakeSelectedBrickmap(bpy.types.Operator):
    bl_idname = "renderman.bake_selected_brickmap"
    bl_label = "Bake to Brickmap"
    bl_description = "Bake to Brickmap"
    bl_options = {'INTERNAL'}    

    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH")

    filename: bpy.props.StringProperty(
        subtype="FILE_NAME",
        default="")

    filter_glob: bpy.props.StringProperty(
        default="*.ptc",
        options={'HIDDEN'},
        )        


    @classmethod
    def poll(cls, context):
        return context.object is not None
            
    def execute(self, context):

        scene = context.scene
        rm = scene.renderman
        if not rm.is_rman_interactive_running:
            ob = context.object
            fp = filepath_utils.get_real_path(self.properties.filepath)
            fp = os.path.splitext(fp)[0]

            org_bake_filename_attr = ob.renderman.bake_filename_attr
            org_bake_illum_mode = scene.renderman.rman_bake_illum_mode
            org_bake_mode = scene.renderman.rman_bake_mode
            org_bake_illum_filename = scene.renderman.rman_bake_illum_filename
            scene.renderman.hider_type = 'BAKE_BRICKMAP_SELECTED'
            scene.renderman.rman_bake_mode = 'integrator'
            ob.renderman.bake_filename_attr = fp
            bpy.ops.render.render(layer=context.view_layer.name)
            scene.renderman.hider_type = 'RAYTRACE'
            scene.renderman.rman_bake_mode = org_bake_mode
        else:
            self.report({"ERROR"}, "Viewport rendering is on.")        
        return {'FINISHED'}        

    def invoke(self, context, event=None):
        ob = context.object
        self.properties.filename = '%s.<F4>.ptc' % ob.name
        context.window_manager.fileselect_add(self)
        return{'RUNNING_MODAL'}         

class PRMAN_OT_ExternalRendermanBake(bpy.types.Operator):
    bl_idname = "renderman.external_bake"
    bl_label = "External Baking"
    bl_description = "Spool an external bake render."
    bl_options = {'INTERNAL'}    
            
    def execute(self, context):

        scene = context.scene
        rm = scene.renderman        
        if not rm.is_rman_interactive_running:
            scene.renderman.hider_type = 'BAKE'
            scene.renderman.enable_external_rendering = True
            bpy.ops.render.render(layer=context.view_layer.name)
            scene.renderman.hider_type = 'RAYTRACE'
            scene.renderman.enable_external_rendering = False
        else:
            self.report({"ERROR"}, "Viewport rendering is on.")        
        return {'FINISHED'}


class PRMAN_OT_ExternalRender(bpy.types.Operator):

    ''''''
    bl_idname = "renderman.external_render"
    bl_label = "External Render"
    bl_description = "Launch a spooled external render."
    bl_options = {'INTERNAL'}    

    def external_blender_batch(self, context):
        rm = context.scene.renderman
        if rm.queuing_system != 'none':
            from .. import rman_spool
            
            depsgraph = context.evaluated_depsgraph_get()

            # FIXME: we should move all of this into
            # rman_render.py
            rr = RmanRender.get_rman_render()
            rr.rman_scene.bl_scene = depsgraph.scene_eval
            rr.rman_scene.bl_view_layer = depsgraph.view_layer
            rr.rman_scene.bl_frame_current = rr.rman_scene.bl_scene.frame_current
            rr.rman_scene._find_renderman_layer()
            rr.rman_scene.external_render = True
            spooler = rman_spool.RmanSpool(rr, rr.rman_scene, depsgraph)
            
            # create a temporary .blend file

            bl_scene_file = bpy.data.filepath
            pid = os.getpid()
            timestamp = int(time.time())
            _id = 'pid%s_%d' % (str(pid), timestamp)
            bl_filepath = os.path.dirname(bl_scene_file)
            bl_filename = os.path.splitext(os.path.basename(bl_scene_file))[0]
            # set blend_token to the real filename
            rm.blend_token = bl_filename
            bl_stash_scene_file = os.path.join(bl_filepath, '_%s%s_.blend' % (bl_filename, _id))
            bpy.ops.wm.save_as_mainfile(filepath=bl_stash_scene_file, copy=True)
            spooler.blender_batch_render(bl_stash_scene_file)
            # now reset the token back
            rm.blend_token = ''

        else:
            self.report({'ERROR'}, 'Queuing system set to none')       

    def external_rib_render(self, context):
        scene = context.scene
        rm = scene.renderman
        if not rm.is_rman_interactive_running:
            scene.renderman.enable_external_rendering = True        
            bpy.ops.render.render(layer=context.view_layer.name)
            scene.renderman.enable_external_rendering = False
        else:
            self.report({"ERROR"}, "Viewport rendering is on.")           

    def execute(self, context):
        scene = context.scene
        rm = scene.renderman
        if not rm.is_rman_interactive_running:
            if scene.renderman.spool_style == 'rib':
                self.external_rib_render(context)       
            else:
                self.external_blender_batch(context)
        else:
            self.report({"ERROR"}, "Viewport rendering is on.")              
        return {'FINISHED'}        

class PRMAN_OT_StartInteractive(bpy.types.Operator):

    ''''''
    bl_idname = "renderman.start_ipr"
    bl_label = "Start Interactive Rendering"
    bl_description = "Start Interactive Rendering"
    bl_options = {'INTERNAL'}    

    def invoke(self, context, event=None):
        view = context.space_data
        if view and view.shading.type != 'RENDERED':        
            view.shading.type = 'RENDERED'

        return {'FINISHED'}

class PRMAN_OT_StopInteractive(bpy.types.Operator):

    ''''''
    bl_idname = "renderman.stop_ipr"
    bl_label = "Stop Interactive Rendering"
    bl_description = "Stop Interactive Rendering"
    bl_options = {'INTERNAL'}    

    def invoke(self, context, event=None):
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            if space.shading.type == 'RENDERED':    
                                space.shading.type = 'SOLID'

        rr = RmanRender.get_rman_render()
        rr.rman_running = False

        return {'FINISHED'}

class PRMAN_OT_StopRender(bpy.types.Operator):
    ''''''
    bl_idname = "renderman.stop_render"
    bl_label = "Stop Render"
    bl_description = "Stop the current render."
    bl_options = {'INTERNAL'}

    def invoke(self, context, event=None):
        rm = context.scene.renderman      
        if rm.is_rman_running:  
            rr = RmanRender.get_rman_render()   
            
            # FIXME: For some reason if we call
            # rr.stop_render() directly, we crash
            # blender. For now, just set rman_is_live_rendering
            # to False and wait
            rr.rman_is_live_rendering = False  
            while rr.rman_running:
                time.sleep(0.001)

        return {'FINISHED'}

class PRMAN_OT_AttachStatsRender(bpy.types.Operator):

    ''''''
    bl_idname = "renderman.attach_stats_render"
    bl_label = "Attach Stats Listener"
    bl_description = "Attach the stats listener to the renderer"
    bl_options = {'INTERNAL'}

    def invoke(self, context, event=None):

        rr = RmanRender.get_rman_render()
        rr.stats_mgr.attach()
        return {'FINISHED'}      

class PRMAN_OT_DisconnectStatsRender(bpy.types.Operator):

    ''''''
    bl_idname = "renderman.disconnect_stats_render"
    bl_label = "Disconnect Stats Listener"
    bl_description = "Disconnect the stats listener from the renderer. This shouldn't need to be done in most circumstances. Disconnecting can cause error-proned behavior."
    bl_options = {'INTERNAL'}

    def invoke(self, context, event=None):

        rr = RmanRender.get_rman_render()
        rr.stats_mgr.disconnect()
        return {'FINISHED'}                 

class PRMAN_OT_UpdateStatsConfig(bpy.types.Operator):

    ''''''
    bl_idname = "renderman.update_stats_config"
    bl_label = "Update Config"
    bl_description = "Update the current stats configuration"
    bl_options = {'INTERNAL'}

    def invoke(self, context, event=None):

        rr = RmanRender.get_rman_render()
        bpy.ops.wm.save_userpref()         
        rr.stats_mgr.update_session_config()
        return {'FINISHED'}            

class PRMAN_OT_Renderman_Launch_Webbrowser(bpy.types.Operator):

    ''''''
    bl_idname = "renderman.launch_webbrowser"
    bl_label = ""
    bl_description = ""
    bl_options = {'INTERNAL'}

    url: bpy.props.StringProperty(name="URL", default='')

    def invoke(self, context, event=None):
        try:
            webbrowser.open(self.url)
        except Exception as e:
            rfb_log().error("Failed to open URL: %s" % str(e))    
        return {'FINISHED'}        

classes = [
    PRMAN_OT_Renderman_Use_Renderman,
    PRMAN_OT_RendermanBake,
    PRMAN_OT_RendermanBakeSelectedBrickmap,
    PRMAN_OT_ExternalRendermanBake,
    PRMAN_OT_ExternalRender,
    PRMAN_OT_StartInteractive,
    PRMAN_OT_StopInteractive,
    PRMAN_OT_StopRender,
    PRMAN_OT_AttachStatsRender,
    PRMAN_OT_DisconnectStatsRender,
    PRMAN_OT_UpdateStatsConfig,
    PRMAN_OT_Renderman_Launch_Webbrowser
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