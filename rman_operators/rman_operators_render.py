from ..rman_render import RmanRender
import bpy
import os
import time

class PRMAN_OT_RendermanBake(bpy.types.Operator):
    bl_idname = "renderman.bake"
    bl_label = "Baking"
    bl_description = "Bake pattern nodes and/or illumination to 2D and 3D formats."
            
    def execute(self, context):

        scene = context.scene
        rman_render = RmanRender.get_rman_render()
        if not rman_render.rman_interactive_running:
            scene.renderman.hider_type = 'BAKE'
            bpy.ops.render.render()
            scene.renderman.hider_type = 'RAYTRACE'
        else:
            self.report({"ERROR"}, "Viewport rendering is on.")        
        return {'FINISHED'}

class PRMAN_OT_ExternalRendermanBake(bpy.types.Operator):
    bl_idname = "renderman.external_bake"
    bl_label = "External Baking"
    bl_description = "Spool an external bake render."
            
    def execute(self, context):

        scene = context.scene
        rman_render = RmanRender.get_rman_render()
        if not rman_render.rman_interactive_running:
            scene.renderman.hider_type = 'BAKE'
            scene.renderman.enable_external_rendering = True
            bpy.ops.render.render()
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

    def external_blender_batch(self, context):
        rm = context.scene.renderman
        if rm.queuing_system != 'none':
            from .. import rman_spool
            depsgraph = context.evaluated_depsgraph_get()
            spooler = rman_spool.RmanSpool(None, None, depsgraph)
            
            # create a temporary .blend file
            bl_scene_file = bpy.data.filepath
            pid = os.getpid()
            timestamp = int(time.time())
            _id = 'pid%s_%d' % (str(pid), timestamp)
            bl_filepath = os.path.dirname(bl_scene_file)
            bl_filename = os.path.splitext(os.path.basename(bl_scene_file))[0]
            bl_stash_scene_file = os.path.join(bl_filepath, '_%s%s_.blend' % (bl_filename, _id))
            bpy.ops.wm.save_as_mainfile(filepath=bl_stash_scene_file, copy=True)

            spooler.blender_batch_render(bl_stash_scene_file)
        else:
            self.report({'ERROR'}, 'Queuing system set to none')       

    def external_rib_render(self, context):
        scene = context.scene
        rman_render = RmanRender.get_rman_render()
        if not rman_render.rman_interactive_running:        
            scene.renderman.enable_external_rendering = True        
            bpy.ops.render.render()
            scene.renderman.enable_external_rendering = False
        else:
            self.report({"ERROR"}, "Viewport rendering is on.")           

    def execute(self, context):
        scene = context.scene
        rman_render = RmanRender.get_rman_render()
        if not rman_render.rman_interactive_running: 
            if scene.renderman.spool_style == 'rib':
                self.external_rib_render(context)       
            else:
                self.external_blender_batch(context)
        else:
            self.report({"ERROR"}, "Viewport rendering is on.")              
        return {'FINISHED'}        

class PRMAN_OT_StartInteractive(bpy.types.Operator):

    ''''''
    bl_idname = "lighting.start_interactive"
    bl_label = "Start Interactive Rendering"
    bl_description = "Start Interactive Rendering"

    def invoke(self, context, event=None):
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            if space.shading.type != 'RENDERED':    
                                space.shading.type = 'RENDERED'

        return {'FINISHED'}

class PRMAN_OT_StoptInteractive(bpy.types.Operator):

    ''''''
    bl_idname = "lighting.stop_interactive"
    bl_label = "Stop Interactive Rendering"
    bl_description = "Stop Interactive Rendering"

    def invoke(self, context, event=None):
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            if space.shading.type == 'RENDERED':    
                                space.shading.type = 'SOLID'

        return {'FINISHED'}

classes = [
    PRMAN_OT_RendermanBake,
    PRMAN_OT_ExternalRendermanBake,
    PRMAN_OT_ExternalRender,
    PRMAN_OT_StartInteractive,
    PRMAN_OT_StoptInteractive 
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