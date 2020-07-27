import bpy
from bpy.props import EnumProperty, StringProperty, IntProperty, FloatProperty
from ..rman_render import RmanRender
from .. import rman_bl_nodes
from .. import rfb_icons
from ..rman_utils.prefs_utils import get_pref
from ..rman_utils import display_utils
from bpy.types import Menu

import bpy
import gpu
from gpu_extras.batch import batch_for_shader

__HIDDEN_INTEGRATORS__ = ['PxrValidateBxdf', 'PxrDebugShadingContext']
__DRAW_CROP_HANDLER__ = None

class PRMAN_MT_Viewport_Integrator_Menu(Menu):
    bl_label = "Viewport Integrator Menu"
    bl_idname = "PRMAN_MT_Viewport_Integrator_Menu"

    @classmethod
    def poll(cls, context):
        return context.engine == "PRMAN_RENDER"

    def draw(self, context):
        layout = self.layout
        for node in rman_bl_nodes.__RMAN_INTEGRATOR_NODES__:
            if node.name not in __HIDDEN_INTEGRATORS__:
                layout.operator_context = 'EXEC_DEFAULT'
                op = layout.operator('renderman_viewport.change_integrator', text=node.name)
                op.viewport_integrator = node.name  


class PRMAN_MT_Viewport_Refinement_Menu(Menu):
    bl_label = "Viewport Refinement Menu"
    bl_idname = "PRMAN_MT_Viewport_Refinement_Menu"

    @classmethod
    def poll(cls, context):
        return context.engine == "PRMAN_RENDER"    

    def draw(self, context):
        layout = self.layout
        for i in range(0, 7):
            layout.operator_context = 'EXEC_DEFAULT'
            op = layout.operator('renderman_viewport.change_refinement', text='%d' % i)
            op.viewport_hider_decidither = i 

class PRMAN_MT_Viewport_Res_Mult_Menu(Menu):
    bl_label = "Viewport Res Mult Menu"
    bl_idname = "PRMAN_MT_Viewport_Res_Mult_Menu"

    @classmethod
    def poll(cls, context):
        return context.engine == "PRMAN_RENDER" 

    def get_items(self):
        items=[
            (1.0, "100%"),
            (0.5, "50%"),
            (0.33, "33%"),
            (0.25, "25%"),
            (0.125, "12.5%")
        ]        
        return items

    def draw(self, context):
        layout = self.layout
        for val, nm in self.get_items():
            layout.operator_context = 'EXEC_DEFAULT'
            op = layout.operator('renderman_viewport.change_resolution_mult', text=nm)
            op.viewport_res_mult = val

class PRMAN_MT_Viewport_Channel_Sel_Menu(Menu):
    bl_label = "Channel Selector Menu"
    bl_idname = "PRMAN_MT_Viewport_Channel_Sel_Menu"
    bl_options = {"INTERNAL"}       

    @classmethod
    def poll(cls, context):
        return context.engine == "PRMAN_RENDER" 

    def draw(self, context):
        layout = self.layout
        rman_render = RmanRender.get_rman_render()
        rman_render.rman_scene._find_renderman_layer()
        dspys_dict = display_utils.get_dspy_dict(rman_render.rman_scene)
        for chan_name, chan_params in dspys_dict['channels'].items():
            layout.operator_context = 'EXEC_DEFAULT'
            op = layout.operator('renderman_viewport.channel_selector', text=chan_name)
            op.channel_name = chan_name

class PRMAN_OT_Viewport_Integrators(bpy.types.Operator):
    bl_idname = "renderman_viewport.change_integrator"
    bl_label = "Select Integrator"
    bl_description = "Quickly change integrators during viewport renders. Does not change the scene integrator."
    bl_options = {"INTERNAL"}      

    viewport_integrator: StringProperty(name="Viewport Integrator",
                                      description="Viewport integrator"
                                    )    

    def execute(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:
            rman_render.rman_scene_sync.update_viewport_integrator(context, self.viewport_integrator)

        return {"FINISHED"}    

class PRMAN_OT_Viewport_Refinement(bpy.types.Operator):
    bl_idname = "renderman_viewport.change_refinement"
    bl_label = "Refinement"
    bl_description = "This value determines how much refinement (in a dither pattern) will be applied to the image during interactive rendering. 0 means full refinement up to a value of 6 which is the least refinement per iteration."
    bl_options = {"INTERNAL"}       

    viewport_hider_decidither: IntProperty(name="Interactive Refinement",
                                      description="",
                                      default=0
                                    )

    def execute(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:
            rm = context.scene.renderman
            rm.hider_decidither = int(self.viewport_hider_decidither)
            rman_render.rman_scene_sync.update_hider_options(context) 

        return {"FINISHED"}        

class PRMAN_OT_Viewport_Resolution_Mult(bpy.types.Operator):
    bl_idname = "renderman_viewport.change_resolution_mult"
    bl_label = "Res Mult"
    bl_description = "Lower the resolution of the viewport. This can help speed up renders."
    bl_options = {"INTERNAL"}       

    viewport_res_mult: FloatProperty(name="Resolution Multiplier",
                                      description="",
                                      default=1.0
                                    )

    def execute(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:
            rman_render.rman_scene.viewport_render_res_mult = float(self.viewport_res_mult)
            rman_render.rman_scene_sync.update_viewport_res_mult(context) 

        return {"FINISHED"}       

class PRMAN_OT_Viewport_Channel_Selector(bpy.types.Operator):
    bl_idname = "renderman_viewport.channel_selector"
    bl_label = "Channel"
    bl_description = "Select a different channel to view"
    bl_options = {"INTERNAL"}      

    channel_name: StringProperty(name="Channel",
                                      description="",
                                      default="Ci"
                                    )

    def execute(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:
            rman_render.rman_scene_sync.update_viewport_chan(context, self.properties.channel_name) 

        return {"FINISHED"}                                                            

class PRMAN_OT_Viewport_Snapshot(bpy.types.Operator):
    bl_idname = "renderman_viewport.snapshot"
    bl_label = "Snapshot"
    bl_description = "Save a snapshot of the current viewport render. Image is saved into the Image Editor."
    bl_options = {"INTERNAL"} 

    def execute(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:
            scene = context.scene
            rman_render.save_viewport_snapshot(frame=scene.frame_current)        

        return {"FINISHED"}  


class DrawCropWindowHelper(object):
    def __init__(self):
        self.crop_windowing = False
        self.reset()   
        self.__draw_handler = None
        self.__draw_handler = bpy.types.SpaceView3D.draw_handler_add(self.draw, (), 'WINDOW', 'POST_PIXEL')    

    def __del__(self):
        bpy.types.SpaceView3D.draw_handler_remove(self.__draw_handler, 'WINDOW')

    def reset(self):
        self.start_pos_x = -1
        self.start_pos_y = -1
        self.end_pos_x = -1
        self.end_pos_y = -1  
        self.__crop_windowing = False    

    @property
    def crop_windowing(self):
        return self.__crop_windowing

    @crop_windowing.setter
    def crop_windowing(self, crop_windowing):
        self.__crop_windowing = crop_windowing            

    @property
    def start_pos_x(self):
        return self.__start_pos_x

    @start_pos_x.setter
    def start_pos_x(self, start_pos_x):
        self.__start_pos_x = start_pos_x       

    @property
    def start_pos_y(self):
        return self.__start_pos_y

    @start_pos_y.setter
    def start_pos_y(self, start_pos_y):
        self.__start_pos_y = start_pos_y  

    @property
    def end_pos_x(self):
        return self.__end_pos_x

    @end_pos_x.setter
    def end_pos_x(self, end_pos_x):
        self.__end_pos_x = end_pos_x                                         

    @property
    def end_pos_y(self):
        return self.__end_pos_y

    @end_pos_y.setter
    def end_pos_y(self, end_pos_y):
        self.__end_pos_y = end_pos_y                                 

    def draw(self):

        if self.start_pos_x == -1 and self.start_pos_y == -1 and self.end_pos_x == -1 and self.end_pos_y == -1:
            return

        self.crop_windowing = True
        c1 = (self.start_pos_x, self.start_pos_y)
        c2 = (self.end_pos_x, self.start_pos_y)
        c3 = (self.end_pos_x, self.end_pos_y)
        c4 = (self.start_pos_x, self.end_pos_y)

        vertices = (c1,c2,c3,c4)
        indices = ((0, 1), (1, 2), (2,3), (3, 0))

        shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'LINES', {"pos": vertices}, indices=indices)

        shader.bind()
        shader.uniform_float("color", get_pref('rman_viewport_crop_color', default=(0.0, 0.498, 1.0, 1.0)))
        batch.draw(shader)     

    def is_inside_cropwindow(self, x, y):
        '''
        Check if point is inside the crop window
        '''
        
        if self.start_pos_x == -1 and self.start_pos_y == -1 and self.end_pos_x == -1 and self.end_pos_y == -1:
            return False

        inside_x = False
        inside_y = False
        if self.start_pos_x < self.end_pos_x:
            if x > self.start_pos_x and x < self.end_pos_x:
                inside_x = True
        else:
            if x > self.end_pos_x and x < self.start_pos_x:
                inside_x = True

        if self.start_pos_y < self.end_pos_y:
            if y > self.start_pos_y and y < self.end_pos_y:
                inside_y = True
        else:
            if y > self.end_pos_y and y < self.start_pos_y:
                inside_y = True

        return (inside_x and inside_y)

def get_crop_helper():
    global __DRAW_CROP_HANDLER__
    return __DRAW_CROP_HANDLER__

class PRMAN_OT_Viewport_CropWindow_Reset(bpy.types.Operator):
    bl_idname = "renderman_viewport.cropwindow_reset"
    bl_label = "Reset CropWindow"
    bl_description = "Reset Cropwindow"
    bl_options = {"INTERNAL"}    

    def execute(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:
            get_crop_helper().reset()
            rman_render.rman_scene_sync.update_cropwindow([0.0, 1.0, 0.0, 1.0])      

        return {"FINISHED"}      

class PRMAN_OT_Viewport_Cropwindow(bpy.types.Operator):
    bl_idname = "renderman_viewport.cropwindow"
    bl_label = "crop"
    bl_description = "Cropwindow"
    bl_options = {"INTERNAL"}    

    def __init__(self):
        self.mouse_prev_x = -1
        self.mouse_prev_y = -1

    def execute(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:
            crop_handler = get_crop_helper()
            start_pos_x = crop_handler.start_pos_x
            start_pos_y = crop_handler.start_pos_y
            end_pos_x = crop_handler.end_pos_x
            end_pos_y = crop_handler.end_pos_y

            if start_pos_x == -1 and start_pos_y == -1 and end_pos_x == -1 and end_pos_y == -1:
                return {'FINISHED'}

            region = getattr(context, 'region', None)       

            region_width = region.width
            region_height = region.height

            crop_y_top = region_height - start_pos_y
            crop_y_bottom = region_height - end_pos_y

            remap_start_x = start_pos_x / region_width
            remap_end_x = end_pos_x / region_width
            remap_start_y = crop_y_top / region_height
            remap_end_y = crop_y_bottom / region_height

            if remap_start_x < remap_end_x:
                crop_left_right = [remap_start_x, remap_end_x]
            else:    
                crop_left_right = [remap_end_x, remap_start_x]

            if remap_start_y < remap_end_y:
                crop_top_bottom = [remap_start_y, remap_end_y]
            else:
                crop_top_bottom = [remap_end_y, remap_start_y]

            rman_render.rman_scene_sync.update_cropwindow(crop_left_right + crop_top_bottom)

        return {'FINISHED'}

    def modal(self, context, event):
        crop_handler = get_crop_helper()
        x = event.mouse_region_x
        y = event.mouse_region_y

        region = getattr(context, 'region', None)
        outside_region = False

        # mouse is outside region
        if (x < 0 or y < 0) or (x > region.width or y > region.height):
            context.window.cursor_modal_restore()
            outside_region = True
        else:
            if crop_handler.crop_windowing:
                if crop_handler.is_inside_cropwindow(x, y):
                    context.window.cursor_modal_set('HAND')
                else:
                    context.window.cursor_modal_set('CROSSHAIR')
            else:
                context.window.cursor_modal_set('CROSSHAIR')

        if event.type == 'MOUSEMOVE':  
            if event.value == 'PRESS':
                if not crop_handler.is_inside_cropwindow(x, y):
                    crop_handler.end_pos_x = x
                    crop_handler.end_pos_y = y
                else:
                    diff_x = x - self.mouse_prev_x
                    diff_y = y - self.mouse_prev_y

                    crop_handler.start_pos_x += diff_x
                    crop_handler.start_pos_y += diff_y
                    crop_handler.end_pos_x += diff_x
                    crop_handler.end_pos_y += diff_y                    

        elif event.type == 'LEFTMOUSE':  
            if event.value == 'PRESS':
                if outside_region:
                    context.window.cursor_modal_restore()                   
                    self.execute(context)
                    return {'FINISHED'}
                if not crop_handler.is_inside_cropwindow(x, y):
                    crop_handler.start_pos_x = x
                    crop_handler.start_pos_y = y
                    crop_handler.end_pos_x = x
                    crop_handler.end_pos_y = y
            elif event.value == 'RELEASE':
                self.execute(context)

        elif event.type == 'RET':
            context.window.cursor_modal_restore()
            self.execute(context)
            return {'FINISHED'}

        elif event.type in {'ESC'}: 
            context.window.cursor_modal_restore()
            crop_handler.reset()
            crop_handler.crop_windowing = False
            return {'CANCELLED'}

        self.mouse_prev_x = x
        self.mouse_prev_y = y
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        context.window.cursor_modal_set('CROSSHAIR')
        crop_handler = get_crop_helper()
        crop_handler.crop_windowing = True
        return {'RUNNING_MODAL'}             

def draw_rman_viewport_props(self, context):
    layout = self.layout
    scene = context.scene

    box = layout.box()
    row = box.row()
    if context.engine == "PRMAN_RENDER":
        view = context.space_data
        rman_render = RmanRender.get_rman_render()
        if view.shading.type == 'RENDERED':
            rman_rerender_controls = rfb_icons.get_icon("rman_ipr_cancel")
            row.operator('renderman.stop_ipr', text="",
                            icon_value=rman_rerender_controls.icon_id)  

            # integrators menu
            rman_icon = rfb_icons.get_icon('rman_vp_viz')
            row.menu('PRMAN_MT_Viewport_Integrator_Menu', text='', icon_value=rman_icon.icon_id)
            # decidither
            row.menu('PRMAN_MT_Viewport_Refinement_Menu', text='', icon='IMPORT')            
            if rman_render.rman_is_viewport_rendering:

                # resolution mult
                rman_icon = rfb_icons.get_icon('rman_vp_resolution')
                row.menu('PRMAN_MT_Viewport_Res_Mult_Menu', text='', icon_value=rman_icon.icon_id)
                # channel selection
                rman_icon = rfb_icons.get_icon('rman_vp_aovs')
                row.menu('PRMAN_MT_Viewport_Channel_Sel_Menu', text='', icon_value=rman_icon.icon_id)

                # crop window
                rman_icon = rfb_icons.get_icon('rman_vp_crop')
                if get_crop_helper().crop_windowing:
                    row.operator('renderman_viewport.cropwindow_reset', text='', icon_value=rman_icon.icon_id, emboss=True, depress=True)                
                else:
                    row.operator('renderman_viewport.cropwindow', text='', icon_value=rman_icon.icon_id)   

                # snapshot
                rman_icon = rfb_icons.get_icon('rman_vp_snapshot')
                row.operator('renderman_viewport.snapshot', text='', icon_value=rman_icon.icon_id)            
            
        else:
            get_crop_helper().reset()

            # stop rendering if we're not in viewport rendering
            if rman_render.rman_interactive_running:
                rman_render.stop_render()              
            rman_rerender_controls = rfb_icons.get_icon("rman_ipr_on")
            row.operator('renderman.start_ipr', text="",
                            icon_value=rman_rerender_controls.icon_id)               

classes = [
    PRMAN_MT_Viewport_Integrator_Menu,
    PRMAN_MT_Viewport_Refinement_Menu,
    PRMAN_MT_Viewport_Res_Mult_Menu,
    PRMAN_MT_Viewport_Channel_Sel_Menu,
    PRMAN_OT_Viewport_Integrators,
    PRMAN_OT_Viewport_Refinement,
    PRMAN_OT_Viewport_Resolution_Mult,
    PRMAN_OT_Viewport_Channel_Selector,
    PRMAN_OT_Viewport_Snapshot,
    PRMAN_OT_Viewport_CropWindow_Reset,
    PRMAN_OT_Viewport_Cropwindow
]

def register():
    global __DRAW_CROP_HANDLER__

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.VIEW3D_HT_header.append(draw_rman_viewport_props)

    if not __DRAW_CROP_HANDLER__:
        __DRAW_CROP_HANDLER__ = DrawCropWindowHelper()

def unregister():

    global __DRAW_CROP_HANDLER__

    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass

    bpy.types.VIEW3D_HT_header.remove(draw_rman_viewport_props)    

    if __DRAW_CROP_HANDLER__:
       del __DRAW_CROP_HANDLER__