from ..rman_render import RmanRender
from ..rman_utils import filepath_utils
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

class PRMAN_OT_RendermanBakeSelectedBrickmap(bpy.types.Operator):
    bl_idname = "renderman.bake_selected_brickmap"
    bl_label = "Bake to Brickmap"
    bl_description = "Bake to Brickmap"

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
        rman_render = RmanRender.get_rman_render()
        if not rman_render.rman_interactive_running:
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
            bpy.ops.render.render()
            scene.renderman.hider_type = 'RAYTRACE'
            scene.renderman.rman_bake_mode = org_bake_mode
        else:
            self.report({"ERROR"}, "Viewport rendering is on.")        
        return {'FINISHED'}        

    def invoke(self, context, event=None):
        ob = context.object
        self.properties.filename = '%s.{F4}.ptc' % ob.name
        context.window_manager.fileselect_add(self)
        return{'RUNNING_MODAL'}         

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
        view = context.space_data
        rman_render = RmanRender.get_rman_render()
        if view and view.shading.type != 'RENDERED':        
            view.shading.type = 'RENDERED'

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
    PRMAN_OT_RendermanBakeSelectedBrickmap,
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