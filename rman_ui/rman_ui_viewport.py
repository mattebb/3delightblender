from bpy.props import EnumProperty, StringProperty, IntProperty, FloatProperty
from ..rman_render import RmanRender
from .. import rman_bl_nodes
from .. import rfb_icons
from ..rfb_utils.prefs_utils import get_pref
from ..rfb_utils import display_utils
from bpy.types import Menu

import bpy
import math
import gpu
from gpu_extras.batch import batch_for_shader

__HIDDEN_INTEGRATORS__ = ['PxrValidateBxdf', 'PxrDebugShadingContext']
__DRAW_CROP_HANDLER__ = None

class PRMAN_MT_Viewport_Integrator_Menu(Menu):
    bl_label = "Change Integrator"
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
    bl_label = "Interactive Refinement"
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
    bl_label = "Scale Resolution"
    bl_idname = "PRMAN_MT_Viewport_Res_Mult_Menu"

    @classmethod
    def poll(cls, context):
        return context.engine == "PRMAN_RENDER" 

    def get_items(self):
        items=[
            ("1.0", "100%"),
            ("0.5", "50%"),
            ("0.33", "33%"),
            ("0.25", "25%"),
            ("0.125", "12.5%")
        ]        
        return items

    def draw(self, context):
        layout = self.layout
        for val, nm in self.get_items():
            layout.operator_context = 'EXEC_DEFAULT'
            op = layout.operator('renderman_viewport.change_resolution_mult', text=nm)
            op.viewport_res_mult = val

class PRMAN_MT_Viewport_Channel_Sel_Menu(Menu):
    bl_label = "Channel"
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
        rm = context.scene.renderman
        rm.hider_decidither = int(self.viewport_hider_decidither)
        rman_render.rman_scene_sync.update_global_options(context) 

        return {"FINISHED"}        

class PRMAN_OT_Viewport_Resolution_Mult(bpy.types.Operator):
    bl_idname = "renderman_viewport.change_resolution_mult"
    bl_label = "Res Mult"
    bl_description = "Lower the resolution of the viewport. This can help speed up renders."
    bl_options = {"INTERNAL"}       

    viewport_res_mult: StringProperty(name="Resolution Multiplier",
                                      description="",
                                      default='1.0'
                                    )

    def execute(self, context):
        rman_render = RmanRender.get_rman_render()
        bpy.ops.renderman_viewport.cropwindow_reset()
        get_crop_helper().crop_windowing = False
        rm = context.scene.renderman
        rm.viewport_render_res_mult = self.viewport_res_mult
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
        rman_render.rman_scene_sync.update_viewport_chan(context, self.properties.channel_name) 

        return {"FINISHED"}                                                            

class PRMAN_OT_Viewport_Snapshot(bpy.types.Operator):
    bl_idname = "renderman_viewport.snapshot"
    bl_label = "Snapshot"
    bl_description = "Save a snapshot of the current viewport render. Image is saved into the Image Editor."
    bl_options = {"INTERNAL"} 

    def execute(self, context):
        rman_render = RmanRender.get_rman_render()
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

        self.cw_c1 = (-1, -1)
        self.cw_c2 = (-1, -1)
        self.cw_c3 = (-1, -1)
        self.cw_c4 = (-1, -1)

        self.del_c1 = (-1, -1)
        self.del_c2 = (-1, -1)
        self.del_c3 = (-1, -1)
        self.del_c4 = (-1, -1)

        self.crop_windowing = False    
        self.edit_cropwindow = False

    @property
    def crop_windowing(self):
        return self.__crop_windowing

    @crop_windowing.setter
    def crop_windowing(self, crop_windowing):
        self.__crop_windowing = crop_windowing      

    @property
    def edit_cropwindow(self):
        return self.__edit_cropwindow

    @edit_cropwindow.setter
    def edit_cropwindow(self, edit_cropwindow):
        self.__edit_cropwindow = edit_cropwindow                               

    def valid_crop_window(self):
        return not (self.cw_c1[0] == -1 and self.cw_c1[0] == -1 and self.cw_c2[0] == -1 and self.cw_c2[0] == -1 and self.cw_c3[0] == -1 and self.cw_c3[0] == -1 and  self.cw_c4[0] == -1 and self.cw_c4[0] == -1 )

    def draw(self):
        if not self.valid_crop_window():
            return 

        self.crop_windowing = True

        vertices = [self.cw_c1,self.cw_c2,self.cw_c3,self.cw_c4]
        indices = [(0, 1), (1, 2), (2,3), (3, 0)]

        # draw delete box
        if self.__edit_cropwindow:
            x0 = self.cw_c3[0]
            y0 = self.cw_c3[1]            
            x1 = x0+ 10
            y1 = y0 + 10

            self.del_c1 = (x0, y0 )
            self.del_c2 = (x1, y0)
            self.del_c3 = (x1, y1)
            self.del_c4 = (x0, y1)
            vertices.append(self.del_c1)
            vertices.append(self.del_c2)
            vertices.append(self.del_c3)
            vertices.append(self.del_c4)
            indices.append((4, 5))
            indices.append((5,6)) 
            indices.append((6,7)) 
            indices.append((7,4)) 
            indices.append((7,5))
            indices.append((6,4))

        shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'LINES', {"pos": vertices}, indices=indices)

        shader.bind()
        shader.uniform_float("color", get_pref('rman_viewport_crop_color', default=(0.0, 0.498, 1.0, 1.0)))
        batch.draw(shader)     

    def is_inside_cropwindow(self, x, y):
        '''
        Check if point is inside the crop window
        '''
        if not self.__edit_cropwindow:
            return False          

        if not self.valid_crop_window():
            return False

        inside_x = False
        inside_y = False

        if x > self.cw_c1[0] and x < self.cw_c2[0]:
            inside_x = True

        if y > self.cw_c1[1] and y < self.cw_c3[1]:
            inside_y = True

        return (inside_x and inside_y)

    def is_inside_del_box(self, x, y):      

        if not self.__edit_cropwindow:
            return False   

        if not self.valid_crop_window():
            return False                  

        inside_x = False
        inside_y = False

        if x > self.del_c1[0] and x < self.del_c2[0]:
            inside_x = True

        if y > self.del_c2[1] and y < self.del_c3[1]:
            inside_y = True

        return (inside_x and inside_y)                    

    def is_top_left_corner(self, x, y):
        if not self.__edit_cropwindow:
            return False         

        if not self.valid_crop_window():
            return False

        if int(math.fabs(x - self.cw_c4[0])) < 10 and int(math.fabs( y - self.cw_c4[1])) < 10:
            return True

        return False

    def is_bottom_right_corner(self, x, y):
        if not self.__edit_cropwindow:
            return False         

        if not self.valid_crop_window():
            return False

        if int(math.fabs(x - self.cw_c2[0])) < 10 and int(math.fabs( y - self.cw_c2[1])) < 10:
            return True

        return False        


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
    bl_label = "Edit Cropwindow"
    bl_description = "Cropwindow"
    bl_options = {"INTERNAL"}    

    def __init__(self):
        self.crop_handler = get_crop_helper()
        self.mouse_prev_x = -1
        self.mouse_prev_y = -1
        self.crop_handler.edit_cropwindow = True

        self.start_pos_x = -1
        self.start_pos_y = -1
        self.end_pos_x = -1
        self.end_pos_y = -1

        self.reset()

    def __del__(self):
        try:
            if self.crop_handler:
                self.crop_handler.edit_cropwindow = False        
        except:
            pass

    def reset(self):
        self.outside_region = False
        self.drawing_crop_window = False
        self.resize_from_left = False
        self.resize_from_right = False
        self.moving_crop_window = False        
        self.is_inside_del_box = False

    def execute(self, context):
        rman_render = RmanRender.get_rman_render()
        if rman_render.rman_interactive_running:

            if not self.crop_handler.valid_crop_window():
                return {'FINISHED'}

            region = getattr(context, 'region', None)       

            region_width = region.width
            region_height = region.height

            x0 = self.crop_handler.cw_c1[0]
            x1 = self.crop_handler.cw_c2[0]           
            y1= region_height - self.crop_handler.cw_c4[1]
            y0 = region_height - self.crop_handler.cw_c1[1] 

            remap_start_x = x0 / region_width
            remap_end_x = x1 / region_width
            remap_start_y = y1 / region_height
            remap_end_y = y0 / region_height

            rman_render.rman_scene_sync.update_cropwindow([remap_start_x, remap_end_x, remap_start_y, remap_end_y])

        return {'FINISHED'}

    def set_crop_corners(self, context):
        x0 = self.start_pos_x
        x1 = self.end_pos_x
        if self.end_pos_x < self.start_pos_x:
            x0 = self.end_pos_x
            x1 = self.start_pos_x
        y0 = self.start_pos_y
        y1 = self.end_pos_y
        if self.end_pos_y < self.start_pos_y:
            y0 = self.end_pos_y
            y1 = self.start_pos_y

        self.crop_handler.cw_c1 = (x0, y0)
        self.crop_handler.cw_c2 = (x1, y0)
        self.crop_handler.cw_c3 = (x1, y1)
        self.crop_handler.cw_c4 = (x0, y1)  

    def move_crop_window(self, context, diff_x, diff_y):     
        c1_x = self.crop_handler.cw_c1[0]
        c1_y = self.crop_handler.cw_c1[1]        
        c2_x = self.crop_handler.cw_c2[0]
        c2_y = self.crop_handler.cw_c2[1]          
        c4_x = self.crop_handler.cw_c4[0]
        c4_y = self.crop_handler.cw_c4[1]        
        c3_x = self.crop_handler.cw_c3[0]
        c3_y = self.crop_handler.cw_c3[1]  

        self.crop_handler.cw_c1 = (c1_x + diff_x, c1_y + diff_y)
        self.crop_handler.cw_c2 = (c2_x + diff_x, c2_y + diff_y)
        self.crop_handler.cw_c3 = (c3_x + diff_x, c3_y + diff_y)
        self.crop_handler.cw_c4 = (c4_x + diff_x, c4_y + diff_y)

    def resize_left(self, context, x, y, diff_x, diff_y):
        c1_x = self.crop_handler.cw_c1[0]
        c1_y = self.crop_handler.cw_c1[1]        
        c2_x = self.crop_handler.cw_c2[0]
        c2_y = self.crop_handler.cw_c2[1]          
        c4_x = self.crop_handler.cw_c4[0]
        c4_y = self.crop_handler.cw_c4[1]        
        c3_x = self.crop_handler.cw_c3[0]
        c3_y = self.crop_handler.cw_c3[1]  

        # don't allow resize beyond edge
        if y < c1_y or x > c2_x:
            return False

        self.crop_handler.cw_c1 = (c1_x + diff_x, c1_y)
        self.crop_handler.cw_c4 = (c4_x + diff_x, c4_y + diff_y)
        self.crop_handler.cw_c3 = (c3_x, c3_y + diff_y)
    

    def resize_right(self, context, x, y, diff_x, diff_y):
        c1_x = self.crop_handler.cw_c1[0]
        c1_y = self.crop_handler.cw_c1[1]        
        c2_x = self.crop_handler.cw_c2[0]
        c2_y = self.crop_handler.cw_c2[1]          
        c4_x = self.crop_handler.cw_c4[0]
        c4_y = self.crop_handler.cw_c4[1]        
        c3_x = self.crop_handler.cw_c3[0]
        c3_y = self.crop_handler.cw_c3[1]  

        # don't allow resize beyond edge
        if y > c3_y or x < c4_x:
            return False

        self.crop_handler.cw_c1 = (c1_x, c1_y + diff_y)
        self.crop_handler.cw_c2 = (c2_x + diff_x, c2_y + diff_y)
        self.crop_handler.cw_c3 = (c3_x + diff_x, c3_y)

    def modal(self, context, event):
        x = event.mouse_region_x
        y = event.mouse_region_y

        region = getattr(context, 'region', None)

        # mouse is outside region
        self.outside_region = False
        if (x < 0 or y < 0) or (x > region.width or y > region.height):
            context.window.cursor_modal_restore()
            self.outside_region = True

        if event.type == 'MOUSEMOVE':  
            if self.outside_region:
                return {'RUNNING_MODAL'}
            if event.value == 'PRESS':
                diff_x = x - self.mouse_prev_x
                diff_y = y - self.mouse_prev_y                
                if self.resize_from_right:
                    self.resize_right(context, x, y, diff_x, diff_y)
                elif self.resize_from_left:
                    self.resize_left(context, x, y, diff_x, diff_y)                    
                elif self.moving_crop_window:
                    self.move_crop_window(context, diff_x, diff_y)
                else:
                    self.end_pos_x = x
                    self.end_pos_y = y
                    self.set_crop_corners(context)
            else:
                if self.crop_handler.crop_windowing:
                    if self.crop_handler.is_inside_cropwindow(x, y):
                        context.window.cursor_modal_set('HAND')
                    elif self.crop_handler.is_inside_del_box(x, y):
                        context.window.cursor_modal_restore()   
                    elif self.crop_handler.is_top_left_corner(x, y):
                        context.window.cursor_modal_set('PAINT_CROSS')
                    elif self.crop_handler.is_bottom_right_corner(x, y):
                        context.window.cursor_modal_set('PAINT_CROSS')                 
                    else:
                        context.window.cursor_modal_set('CROSSHAIR')
                else:
                    context.window.cursor_modal_set('CROSSHAIR')                  

        elif event.type == 'LEFTMOUSE':  
            self.drawing_crop_window = False
            self.resize_from_left = False
            self.resize_from_right = False
            self.moving_crop_window = False        
            self.is_inside_del_box = False            
            if event.value == 'PRESS':
                if self.outside_region:
                    context.window.cursor_modal_restore()                   
                    self.execute(context)
                    return {'FINISHED'}

                elif self.crop_handler.is_inside_del_box(x, y):
                    context.window.cursor_modal_restore()
                    bpy.ops.renderman_viewport.cropwindow_reset()
                    self.crop_handler.crop_windowing = False
                    return {'CANCELLED'}
                elif self.crop_handler.is_top_left_corner(x, y):
                    context.window.cursor_modal_set('PAINT_CROSS')
                    self.resize_from_left = True                    
                elif self.crop_handler.is_bottom_right_corner(x, y):
                    context.window.cursor_modal_set('PAINT_CROSS')
                    self.resize_from_right = True
                elif self.crop_handler.is_inside_cropwindow(x, y):
                    context.window.cursor_modal_set('HAND')
                    self.moving_crop_window = True
                else:
                    self.start_pos_x = x
                    self.start_pos_y = y
                    self.end_pos_x = x
                    self.end_pos_y = y
            elif event.value == 'RELEASE':
                self.execute(context)

        elif event.type in {'ESC', 'RET'}:
            context.window.cursor_modal_restore()
            self.execute(context)
            return {'FINISHED'}

        else:
            if self.crop_handler.crop_windowing:
                if self.crop_handler.is_inside_cropwindow(x, y):
                    context.window.cursor_modal_set('HAND')
                elif self.crop_handler.is_inside_del_box(x, y):
                    context.window.cursor_modal_restore()   
                elif self.crop_handler.is_top_left_corner(x, y):
                    context.window.cursor_modal_set('PAINT_CROSS')
                elif self.crop_handler.is_bottom_right_corner(x, y):
                    context.window.cursor_modal_set('PAINT_CROSS')                 
                else:
                    context.window.cursor_modal_set('CROSSHAIR')
            else:
                context.window.cursor_modal_set('CROSSHAIR')            

        self.mouse_prev_x = x
        self.mouse_prev_y = y
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        context.window.cursor_modal_set('CROSSHAIR')
        self.crop_handler.crop_windowing = True
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
                depress = get_crop_helper().edit_cropwindow
                row.operator('renderman_viewport.cropwindow', text='', icon_value=rman_icon.icon_id, depress=depress)

                # snapshot
                rman_icon = rfb_icons.get_icon('rman_vp_snapshot')
                row.operator('renderman_viewport.snapshot', text='', icon_value=rman_icon.icon_id)    
            # texture cache clear      
            rman_icon = rfb_icons.get_icon('rman_lightning_grey')
            row.operator('rman_txmgr_list.clear_all_cache', text='', icon_value=rman_icon.icon_id)  
            
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
       __DRAW_CROP_HANDLER__ = None