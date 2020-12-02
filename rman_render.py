import time
import os
import rman
import bpy
import sys
from .rman_constants import RFB_VIEWPORT_MAX_BUCKETS
from .rman_scene import RmanScene
from .rman_scene_sync import RmanSceneSync
from. import rman_spool
from. import chatserver
from .rfb_logger import rfb_log
import socketserver
import threading
import subprocess
import ctypes

# for viewport buckets
import gpu
from gpu_extras.batch import batch_for_shader

# utils
from .rfb_utils import filepath_utils
from .rfb_utils import string_utils
from .rfb_utils import display_utils
from .rfb_utils.prefs_utils import get_pref

# config
from .rman_config import __RFB_CONFIG_DICT__ as rfb_config

__RMAN_RENDER__ = None
__RMAN_IT_PORT__ = -1
__BLENDER_DSPY_PLUGIN__ = None
__DRAW_THREAD__ = None

def __turn_off_viewport__():
    rfb_log().debug("Attempting to turn off viewport render")
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'SOLID'    
            area.tag_redraw()                        

def __update_areas__():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()

def __get_render_variant(bl_scene):
    if filepath_utils.is_ncr_license():
        return 'prman'

    return bl_scene.renderman.renderVariant

class ItHandler(chatserver.ItBaseHandler):

    def dspyRender(self):
        global __RMAN_RENDER__
        if not __RMAN_RENDER__.is_running:                        
            bpy.ops.render.render(layer=context.view_layer.name)             

    def dspyIPR(self):
        global __RMAN_RENDER__
        if __RMAN_RENDER__.rman_interactive_running:
            crop = []
            for c in self.msg.getOpt('crop').split(' '):
                crop.append(float(c))
            if len(crop) == 4:
                __RMAN_RENDER__.rman_scene_sync.update_cropwindow(crop)

    def stopRender(self):
        global __RMAN_RENDER__
        rfb_log().debug("Stop Render Requested.")
        if __RMAN_RENDER__.rman_interactive_running:
            __turn_off_viewport__()
        __RMAN_RENDER__.stop_render()      

    def selectObjectById(self):
        global __RMAN_RENDER__

        obj_id = int(self.msg.getOpt('id', '0'))
        if obj_id < 0 or not (obj_id in __RMAN_RENDER__.rman_scene.obj_hash):
            return
        name = __RMAN_RENDER__.rman_scene.obj_hash[obj_id]
        rfb_log().debug('ID: %d Obj Name: %s' % (obj_id, name))
        obj = bpy.context.scene.objects[name]
        if obj:
            if bpy.context.view_layer.objects.active:
                bpy.context.view_layer.objects.active.select_set(False)
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

    def selectSurfaceById(self):
        self.selectObjectById()
        window = bpy.context.window_manager.windows[0]
        if window.screen:
            for a in window.screen.areas:
                if a.type == "PROPERTIES":
                    for s in a.spaces:
                        if s.type == "PROPERTIES":
                            try:
                                s.context = "MATERIAL"
                            except:
                                pass
                            return

def start_cmd_server():

    global __RMAN_IT_PORT__

    if __RMAN_IT_PORT__ != -1:
        return __RMAN_IT_PORT__

    # zero port makes the OS pick one
    host, port = "localhost", 0

    # install handler
    chatserver.protocols['it'] = ItHandler

    # Create the server, binding to localhost on some port
    server = socketserver.TCPServer((host, port),
                                    chatserver.CommandHandler)
    ip, port = server.server_address

    thread = threading.Thread(target=server.serve_forever)

    # Exit the server thread when the main thread terminates
    thread.daemon = True
    thread.start()

    __RMAN_IT_PORT__ = port

    return __RMAN_IT_PORT__        

def draw_threading_func(db):
    refresh_rate = get_pref('rman_viewport_refresh_rate', default=0.01)
    while db.rman_is_live_rendering:
        try:
            db.bl_engine.tag_redraw()
            time.sleep(refresh_rate)
        except ReferenceError as e:
            rfb_log().error("Error calling tag_redraw (%s). Aborting..." % str(e))
            return

def viewport_progress_cb(e, d, db):
    if float(d) > 99.0:
        # clear bucket markers
        db.draw_viewport_buckets = False
        db.viewport_buckets.clear()
    else:
        if float(d) < 1.0:
            # clear bucket markers if we are back to 0 progress
            db.viewport_buckets.clear()
        db.draw_viewport_buckets = True

def progress_cb(e, d, db):
    db.bl_engine.update_progress(float(d) / 100.0)
    if db.rman_is_live_rendering and int(d) == 100:
        db.rman_is_live_rendering = False

def bake_progress_cb(e, d, db):
    db.bl_engine.update_progress(float(d) / 100.0)     

def render_cb(e, d, db):
    if d == 0:
        rfb_log().debug("RenderMan has exited.")
        if db.rman_is_live_rendering:
            db.rman_is_live_rendering = False

def scene_cb(e, d, db):
    if d == 0:
        rfb_log().debug("RixSGScene destroyed.")

class RmanRender(object):
    '''
    RmanRender class. This class is responsible for starting and stopping
    the renderer. There should only be one instance of this class per session.

    Do not create an instance of this class directly. Use RmanRender.get_rman_render()
    '''

    def __init__(self):
        global __RMAN_RENDER__
        self.rictl = rman.RiCtl.Get()
        self.sgmngr = rman.SGManager.Get()
        self.rman = rman
        self.sg_scene = None
        self.rman_scene = RmanScene(rman_render=self)
        self.rman_scene_sync = None
        self.bl_engine = None
        self.rman_running = False
        self.rman_interactive_running = False
        self.rman_swatch_render_running = False
        self.rman_is_live_rendering = False
        self.rman_is_viewport_rendering = False
        self.rman_render_into = 'blender'
        self.it_port = -1 
        self.rman_callbacks = dict()
        self.viewport_res_x = -1
        self.viewport_res_y = -1
        self.viewport_buckets = list()
        self.draw_viewport_buckets = False

        self._start_prman_begin()

    @classmethod
    def get_rman_render(self):
        global __RMAN_RENDER__
        if __RMAN_RENDER__ is None:
            __RMAN_RENDER__ = RmanRender()

        return __RMAN_RENDER__

    @property
    def bl_engine(self):
        return self.__bl_engine

    @bl_engine.setter
    def bl_engine(self, bl_engine):
        self.__bl_engine = bl_engine        

    def _start_prman_begin(self):

        argv = []
        argv.append("prman") 
        argv.append("-progress")  
        argv.append("-dspyserver")
        argv.append("it")

        woffs = ',' . join(rfb_config['woffs'])
        if woffs:
            argv.append('-woff')
            argv.append(woffs)

        self.rictl.PRManBegin(argv)  

    def __del__(self):   
        self.rictl.PRManEnd()

    def _dump_rib_(self):
        if 'RFB_DUMP_RIB' in os.environ:
            rfb_log().debug("Writing to RIB...")
            rib_time_start = time.time()
            if sys.platform == ("win32"):
                self.sg_scene.Render("rib C:/tmp/blender.rib")
            else:
                self.sg_scene.Render("rib /var/tmp/blender.rib")     
            rfb_log().debug("Finished writing RIB. Time: %s" % string_utils._format_time_(time.time() - rib_time_start))            

    def _load_placeholder_image(self):   
        placeholder_image = os.path.join(filepath_utils.guess_rmantree(), 'lib', 'textures', 'placeholder.png')

        render = self.bl_scene.render
        image_scale = 100.0 / render.resolution_percentage
        result = self.bl_engine.begin_result(0, 0,
                                    render.resolution_x * image_scale,
                                    render.resolution_y * image_scale)
        lay = result.layers[0]
        try:
            lay.load_from_file(placeholder_image)
        except:
            pass
        self.bl_engine.end_result(result)               

    def _call_brickmake_for_selected(self):  
        rm = self.bl_scene.renderman
        ob = bpy.context.active_object
        if rm.external_animation:
            for frame in range(bl_scene.frame_start, bl_scene.frame_end + 1):        
                expanded_str = string_utils.expand_string(ob.renderman.bake_filename_attr, frame=self.bl_scene.frame_current) 
                ptc_file = '%s.ptc' % expanded_str            
                bkm_file = '%s.bkm' % expanded_str
                args = []
                args.append('%s/bin/brickmake' % filepath_utils.guess_rmantree())
                args.append('-progress')
                args.append('2')
                args.append(ptc_file)
                args.append(bkm_file)
                subprocess.run(args)
        else:     
            expanded_str = string_utils.expand_string(ob.renderman.bake_filename_attr, frame=self.bl_scene.frame_current) 
            ptc_file = '%s.ptc' % expanded_str            
            bkm_file = '%s.bkm' % expanded_str
            args = []
            args.append('%s/bin/brickmake' % filepath_utils.guess_rmantree())
            args.append('-progress')
            args.append('2')
            args.append(ptc_file)
            args.append(bkm_file)
            subprocess.run(args)               

    def start_render(self, depsgraph, for_background=False):

        self.bl_scene = depsgraph.scene_eval
        rm = self.bl_scene.renderman
        self.it_port = start_cmd_server()    
        rfb_log().info("Parsing scene...")
        time_start = time.time()

        if for_background:
            self.rman_render_into = ''
            is_external = True
            self.rman_callbacks.clear()
            ec = rman.EventCallbacks.Get()
            ec.RegisterCallback("Render", render_cb, self)
            self.rman_callbacks["Render"] = render_cb       
            rman.Dspy.DisableDspyServer()          
        else:

            self.rman_render_into = rm.render_into
            is_external = False                    
            self.rman_callbacks.clear()
            ec = rman.EventCallbacks.Get()
            ec.RegisterCallback("Progress", progress_cb, self)
            self.rman_callbacks["Progress"] = progress_cb
            ec.RegisterCallback("Render", render_cb, self)
            self.rman_callbacks["Render"] = render_cb        
            
            try:
                if self.rman_render_into == 'it':
                    rman.Dspy.EnableDspyServer()
                else:
                    rman.Dspy.DisableDspyServer()
            except:
                pass

        config = rman.Types.RtParamList()
        config.SetString("rendervariant", __get_render_variant(self.bl_scene))
        self.sg_scene = self.sgmngr.CreateScene(config) 
        bl_layer = depsgraph.view_layer
        self.rman_scene.export_for_final_render(depsgraph, self.sg_scene, bl_layer, is_external=is_external)

        self.rman_running = True
        self._dump_rib_()
        rfb_log().info("Finished parsing scene. Total time: %s" % string_utils._format_time_(time.time() - time_start)) 

        self.rman_is_live_rendering = True
        self.sg_scene.Render("prman -live")

        if self.rman_render_into == 'blender':        
            dspy_dict = display_utils.get_dspy_dict(self.rman_scene)
            
            render = self.rman_scene.bl_scene.render
            render_view = self.bl_engine.active_view_get()
            image_scale = render.resolution_percentage / 100.0
            width = int(render.resolution_x * image_scale)
            height = int(render.resolution_y * image_scale)

            bl_images = dict()
            # register any AOV's as passes
            for i, dspy_nm in enumerate(dspy_dict['displays'].keys()):
                if i == 0:
                    continue     
                self.bl_engine.add_pass(dspy_nm, 4, 'RGBA')

            result = self.bl_engine.begin_result(0, 0,
                                        width,
                                        height,
                                        view=render_view)

            for i, dspy_nm in enumerate(dspy_dict['displays'].keys()):
                if i == 0:
                    lyr = result.layers[0].passes.find_by_name("Combined", render_view)           
                else:
                    lyr = result.layers[0].passes.find_by_name(dspy_nm, render_view)
                bl_images[i] = lyr            
            
            while not self.bl_engine.test_break() and self.rman_is_live_rendering:
                time.sleep(0.01)        
                for i, img in bl_images.items():
                    buffer = self._get_buffer(width, height, image_num=i, as_flat=False)
                    if buffer:
                        img.rect = buffer
        
                self.bl_engine.update_result(result)        

            self.stop_render()           
            if result:   
                self.bl_engine.end_result(result)  
        else:
            while not self.bl_engine.test_break() and self.rman_is_live_rendering:
                time.sleep(0.01)      
            self.stop_render()                                

        return True   

    def start_external_render(self, depsgraph):         

        bl_scene = depsgraph.scene_eval
        rm = bl_scene.renderman

        self.rman_running = True
        self.rman_render_into = ''
        rib_options = ""
        if rm.rib_compression == "gzip":
            rib_options += " -compression gzip"
        rib_format = 'ascii'
        if rm.rib_format == 'binary':
            rib_format = 'binary' 
        rib_options += " -format %s" % rib_format
        if rib_format == "ascii":
            rib_options += " -indent"

        if rm.external_animation:
            original_frame = bl_scene.frame_current
            rfb_log().debug("Writing to RIB...")             
            for frame in range(bl_scene.frame_start, bl_scene.frame_end + 1):
                bl_view_layer = depsgraph.view_layer
                self.sg_scene = self.sgmngr.CreateScene(rman.Types.RtParamList()) 
                self.bl_engine.frame_set(frame, subframe=0.0)
                self.rman_scene.export_for_final_render(depsgraph, self.sg_scene, bl_view_layer, is_external=True)
                rib_output = string_utils.expand_string(rm.path_rib_output, 
                                                        frame=frame, 
                                                        asFilePath=True)                                                                            
                self.sg_scene.Render("rib %s %s" % (rib_output, rib_options))
                self.sgmngr.DeleteScene(self.sg_scene)     

            self.bl_engine.frame_set(original_frame, subframe=0.0)
            

        else:
            self.sg_scene = self.sgmngr.CreateScene(rman.Types.RtParamList()) 

            time_start = time.time()
                    
            bl_view_layer = depsgraph.view_layer         
            rfb_log().info("Parsing scene...")             
            self.rman_scene.export_for_final_render(depsgraph, self.sg_scene, bl_view_layer, is_external=True)
            rib_output = string_utils.expand_string(rm.path_rib_output, 
                                                    frame=bl_scene.frame_current, 
                                                    asFilePath=True)            

            rfb_log().debug("Writing to RIB: %s..." % rib_output)
            rib_time_start = time.time()
            self.sg_scene.Render("rib %s %s" % (rib_output, rib_options))     
            rfb_log().debug("Finished writing RIB. Time: %s" % string_utils._format_time_(time.time() - rib_time_start)) 
            rfb_log().info("Finished parsing scene. Total time: %s" % string_utils._format_time_(time.time() - time_start))
            self.sgmngr.DeleteScene(self.sg_scene)

        if rm.queuing_system != 'none':
            spooler = rman_spool.RmanSpool(self, self.rman_scene, depsgraph)
            spooler.batch_render()
        self.rman_running = False
        self.sg_scene = None
        return True          

    def start_bake_render(self, depsgraph, for_background=False):

        self.bl_scene = depsgraph.scene_eval
        rm = self.bl_scene.renderman
        self.it_port = start_cmd_server()    
        rfb_log().info("Parsing scene...")
        time_start = time.time()

        if for_background:
            is_external = True
            self.rman_callbacks.clear()
            ec = rman.EventCallbacks.Get()
            ec.RegisterCallback("Render", render_cb, self)
            self.rman_callbacks["Render"] = render_cb       
            rman.Dspy.DisableDspyServer()          
        else:
            is_external = False                    
            self.rman_callbacks.clear()
            ec = rman.EventCallbacks.Get()
            ec.RegisterCallback("Progress", bake_progress_cb, self)
            self.rman_callbacks["Progress"] = bake_progress_cb
            ec.RegisterCallback("Render", render_cb, self)
            self.rman_callbacks["Render"] = render_cb        

        self.rman_render_into = ''
        rman.Dspy.DisableDspyServer()
        config = rman.Types.RtParamList()
        self.sg_scene = self.sgmngr.CreateScene(config) 
        bl_layer = depsgraph.view_layer
        self.rman_scene.export_for_bake_render(depsgraph, self.sg_scene, bl_layer, is_external=is_external)

        self.rman_running = True
        self._dump_rib_()
        rfb_log().info("Finished parsing scene. Total time: %s" % string_utils._format_time_(time.time() - time_start)) 
        self.sg_scene.Render("prman -blocking")
        self.stop_render()
        if rm.hider_type == 'BAKE_BRICKMAP_SELECTED':
            self._call_brickmake_for_selected()
        return True        

    def start_external_bake_render(self, depsgraph):         

        bl_scene = depsgraph.scene_eval
        rm = bl_scene.renderman

        self.rman_running = True
        self.rman_render_into = ''
        rib_options = ""
        if rm.rib_compression == "gzip":
            rib_options += " -compression gzip"
        rib_format = 'ascii'
        if rm.rib_format == 'binary':
            rib_format = 'binary' 
        rib_options += " -format %s" % rib_format
        if rib_format == "ascii":
            rib_options += " -indent"

        if rm.external_animation:
            original_frame = bl_scene.frame_current
            rfb_log().debug("Writing to RIB...")             
            for frame in range(bl_scene.frame_start, bl_scene.frame_end + 1):
                bl_view_layer = depsgraph.view_layer
                self.sg_scene = self.sgmngr.CreateScene(rman.Types.RtParamList()) 
                self.bl_engine.frame_set(frame, subframe=0.0)
                self.rman_scene.export_for_bake_render(depsgraph, self.sg_scene, bl_view_layer, is_external=True)
                rib_output = string_utils.expand_string(rm.path_rib_output, 
                                                        frame=frame, 
                                                        asFilePath=True)                                                                            
                self.sg_scene.Render("rib %s %s" % (rib_output, rib_options))
                self.sgmngr.DeleteScene(self.sg_scene)     

            self.bl_engine.frame_set(original_frame, subframe=0.0)
            

        else:
            self.sg_scene = self.sgmngr.CreateScene(rman.Types.RtParamList()) 

            time_start = time.time()
                    
            bl_view_layer = depsgraph.view_layer         
            rfb_log().info("Parsing scene...")             
            self.rman_scene.export_for_bake_render(depsgraph, self.sg_scene, bl_view_layer, is_external=True)
            rib_output = string_utils.expand_string(rm.path_rib_output, 
                                                    frame=bl_scene.frame_current, 
                                                    asFilePath=True)            

            rfb_log().debug("Writing to RIB: %s..." % rib_output)
            rib_time_start = time.time()
            self.sg_scene.Render("rib %s %s" % (rib_output, rib_options))     
            rfb_log().debug("Finished writing RIB. Time: %s" % string_utils._format_time_(time.time() - rib_time_start)) 
            rfb_log().info("Finished parsing scene. Total time: %s" % string_utils._format_time_(time.time() - time_start))
            self.sgmngr.DeleteScene(self.sg_scene)

        if rm.queuing_system != 'none':
            spooler = rman_spool.RmanSpool(self, self.rman_scene, depsgraph)
            spooler.batch_render()
        self.rman_running = False
        self.sg_scene = None
        return True                  

    def start_interactive_render(self, context, depsgraph):

        global __DRAW_THREAD__
        global __DRAW_SIMPLE_SHADING_HANDLER__

        self.rman_interactive_running = True
        __update_areas__()
        self.bl_scene = depsgraph.scene_eval
        rm = depsgraph.scene_eval.renderman
        self.it_port = start_cmd_server()    
        render_into_org = '' 
        self.rman_render_into = rm.render_into
        
        self.rman_callbacks.clear()
        # register the blender display driver
        try:
            if self.rman_render_into == 'blender':
                # turn off dspyserver mode if we're not rendering to "it"
                self.rman_is_viewport_rendering = True    
                rman.Dspy.DisableDspyServer()             
                self.rman_callbacks.clear()
                ec = rman.EventCallbacks.Get()
                ec.RegisterCallback("Progress", viewport_progress_cb, self)
                self.rman_callbacks["Progress"] = viewport_progress_cb       
                self.viewport_buckets.clear()
                self.draw_viewport_buckets = True                           
            else:
                rman.Dspy.EnableDspyServer()
        except:
            # force rendering to 'it'
            rfb_log().error('Could not register Blender display driver. Rendering to "it".')
            render_into_org = rm.render_into
            rm.render_into = 'it'
            self.rman_render_into = 'it'
            rman.Dspy.EnableDspyServer()

        time_start = time.time()      

        config = rman.Types.RtParamList()
        config.SetString("rendervariant", __get_render_variant(self.bl_scene))      
        self.sg_scene = self.sgmngr.CreateScene(config) 
        self.rman_scene_sync = RmanSceneSync(rman_render=self, rman_scene=self.rman_scene, sg_scene=self.sg_scene)
        rfb_log().info("Parsing scene...")        
        self.rman_scene.export_for_interactive_render(context, depsgraph, self.sg_scene)

        self._dump_rib_()      
        rfb_log().info("Finished parsing scene. Total time: %s" % string_utils._format_time_(time.time() - time_start))     
        self.rman_is_live_rendering = True        
        self.sg_scene.Render("prman -live")

        rfb_log().info("RenderMan Viewport Render Started.")  

        if render_into_org != '':
            rm.render_into = render_into_org    
        
        # start a thread to periodically call engine.tag_redraw()
        if self.rman_is_viewport_rendering:
            __DRAW_THREAD__ = threading.Thread(target=draw_threading_func, args=(self, ))
            __DRAW_THREAD__.start()

    def start_swatch_render(self, depsgraph):
        self.bl_scene = depsgraph.scene_eval

        rfb_log().debug("Parsing scene...")
        time_start = time.time()                
        self.rman_callbacks.clear()
        ec = rman.EventCallbacks.Get()
        rman.Dspy.DisableDspyServer()
        ec.RegisterCallback("Progress", progress_cb, self)
        self.rman_callbacks["Progress"] = progress_cb        
        ec.RegisterCallback("Render", render_cb, self)
        self.rman_callbacks["Render"] = render_cb        
        
        self.sg_scene = self.sgmngr.CreateScene(rman.Types.RtParamList()) 
        self.rman_scene.export_for_swatch_render(depsgraph, self.sg_scene)

        self.rman_running = True
        self.rman_swatch_render_running = True
        self._dump_rib_()
        rfb_log().debug("Finished parsing scene. Total time: %s" % string_utils._format_time_(time.time() - time_start)) 
        self.rman_is_live_rendering = True
        self.sg_scene.Render("prman -live")
        render = self.rman_scene.bl_scene.render
        render_view = self.bl_engine.active_view_get()
        image_scale = render.resolution_percentage / 100.0
        width = int(render.resolution_x * image_scale)
        height = int(render.resolution_y * image_scale)
        result = self.bl_engine.begin_result(0, 0,
                                    width,
                                    height,
                                    view=render_view)
        layer = result.layers[0].passes.find_by_name("Combined", render_view)        
        while not self.bl_engine.test_break() and self.rman_is_live_rendering:
            time.sleep(0.001)
            if layer:
                buffer = self._get_buffer(width, height, image_num=0, as_flat=False)
                if buffer:
                    layer.rect = buffer
                    self.bl_engine.update_result(result)
        # try to get the buffer one last time before exiting
        if layer:
            buffer = self._get_buffer(width, height, image_num=0, as_flat=False)
            if buffer:
                layer.rect = buffer
                self.bl_engine.update_result(result)        
        self.stop_render()              
        self.bl_engine.end_result(result)           
       
        return True  

    def start_export_rib_selected(self, context, rib_path, export_materials=True, export_all_frames=False):

        self.rman_running = True  
        self.sg_scene = self.sgmngr.CreateScene(rman.Types.RtParamList())     
        self.rman_scene.export_for_rib_selection(context, self.sg_scene)
        self.sg_scene.Render("rib " + rib_path + " -archive")
        self.sgmngr.DeleteScene(self.sg_scene)
        self.sg_scene = None
        self.rman_running = False        
        return True                 

    def stop_render(self):
        global __DRAW_THREAD__

        if not self.rman_interactive_running and not self.rman_running:
            return

        # Remove callbacks
        ec = rman.EventCallbacks.Get()
        rfb_log().debug("Unregister any callbacks")
        for k,v in self.rman_callbacks.items():
            ec.UnregisterCallback(k, v, self)
        self.rman_callbacks.clear()          

        self.rman_is_live_rendering = False

        # wait for the drawing thread to finish
        if __DRAW_THREAD__:
            __DRAW_THREAD__.join()
            __DRAW_THREAD__ = None

        rfb_log().debug("Telling SceneGraph to stop.")    
        if self.sg_scene:    
            self.sg_scene.Stop()
            rfb_log().debug("Delete Scenegraph scene")
            self.sgmngr.DeleteScene(self.sg_scene)

        self.rman_interactive_running = False
        self.rman_running = False     
        self.rman_swatch_render_running = False
        self.rman_is_viewport_rendering = False
        self.sg_scene = None
        self.rman_scene_sync = None
        self.rman_scene.reset()
        self.viewport_buckets.clear()
        self.draw_viewport_buckets = False                
        __update_areas__()
        rfb_log().debug("RenderMan has Stopped.")

    def get_blender_dspy_plugin(self):
        global __BLENDER_DSPY_PLUGIN__
        if __BLENDER_DSPY_PLUGIN__ == None:
            # grab a pointer to the Blender display driver
            ext = '.so'
            if sys.platform == ("win32"):
                    ext = '.dll'
            __BLENDER_DSPY_PLUGIN__ = ctypes.CDLL(os.path.join(filepath_utils.guess_rmantree(), 'lib', 'plugins', 'd_blender%s' % ext))

        return __BLENDER_DSPY_PLUGIN__
                
    def draw_pixels(self, width, height):
        self.viewport_res_x = width
        self.viewport_res_y = height
        if self.rman_is_viewport_rendering:
            dspy_plugin = self.get_blender_dspy_plugin()

            # (the driver will handle pixel scaling to the given viewport size)
            dspy_plugin.DrawBufferToBlender(ctypes.c_int(width), ctypes.c_int(height))

            image_num = 0
            arXMin = ctypes.c_int(0)
            arXMax = ctypes.c_int(0)
            arYMin = ctypes.c_int(0)
            arYMax = ctypes.c_int(0)            
            dspy_plugin.GetActiveRegion(ctypes.c_size_t(image_num), ctypes.byref(arXMin), ctypes.byref(arXMax), ctypes.byref(arYMin), ctypes.byref(arYMax))
            # draw bucket indicators
            if self.draw_viewport_buckets and ( (arXMin.value + arXMax.value + arYMin.value + arYMax.value) > 0):
                yMin = height-1 - arYMin.value
                yMax = height-1 - arYMax.value
                xMin = arXMin.value
                xMax = arXMax.value
                if self.rman_scene.viewport_render_res_mult != 1.0:
                    # render resolution multiplier is set, we need to re-scale the bucket markers
                    scaled_width = width * self.rman_scene.viewport_render_res_mult
                    xMin = int(width * ((arXMin.value) / (scaled_width)))
                    xMax = int(width * ((arXMax.value) / (scaled_width)))

                    scaled_height = height * self.rman_scene.viewport_render_res_mult
                    yMin = height-1 - int(height * ((arYMin.value) / (scaled_height)))
                    yMax = height-1 - int(height * ((arYMax.value) / (scaled_height)))
                   
                vertices = []
                c1 = (xMin, yMin)
                c2 = (xMax, yMin)
                c3 = (xMax, yMax)
                c4 = (xMin, yMax)
                vertices.append(c1)
                vertices.append(c2)
                vertices.append(c3)
                vertices.append(c4)
                indices = [(0, 1), (1, 2), (2,3), (3, 0)]

                # we've reach our max buckets, pop the oldest one off the list
                if len(self.viewport_buckets) > RFB_VIEWPORT_MAX_BUCKETS:
                    self.viewport_buckets.pop()
                self.viewport_buckets.insert(0,[vertices, indices])
                bucket_color =  get_pref('rman_viewport_bucket_color', default=(0.0, 0.498, 1.0, 1.0))

                # draw from newest to oldest
                for v, i in (self.viewport_buckets):      
                    shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
                    shader.uniform_float("color", bucket_color)                                  
                    batch = batch_for_shader(shader, 'LINES', {"pos": v}, indices=i)
                    shader.bind()
                    batch.draw(shader)              

    def _get_buffer(self, width, height, image_num=0, as_flat=True):
        dspy_plugin = self.get_blender_dspy_plugin()
        num_channels = dspy_plugin.GetNumberOfChannels(ctypes.c_size_t(image_num))
        if num_channels > 4 or num_channels < 0:
            rfb_log().debug("Could not get buffer. Incorrect number of channels: %d" % num_channels)
            return None

        ArrayType = ctypes.c_float * (width * height * num_channels)
        f = dspy_plugin.GetFloatFramebuffer
        f.restype = ctypes.POINTER(ArrayType)

        try:
            buffer = f(ctypes.c_size_t(image_num)).contents
            pixels = list()

            # we need to flip the image
            # also, Blender is expecting a 4 channel image

            if as_flat:
                # return the buffer as a flat list
                for y in range(height-1, -1, -1):
                    i = (width * y * num_channels)
                    
                    # if this is already a 4 channel image, just slice it
                    if num_channels == 4:
                        j = i + (num_channels * (width))          
                        pixels.extend(buffer[i:j])
                        continue

                    for x in range(0, width):
                        j = i + (num_channels * x)
                        if num_channels == 3:
                            pixels.append(buffer[j])
                            pixels.append(buffer[j+1])
                            pixels.append(buffer[j+2])
                            pixels.append(1.0)
                        elif num_channels == 2:
                            pixels.append(buffer[j])
                            pixels.append(buffer[j+1])
                            pixels.append(1.0)                        
                            pixels.append(1.0)                        
                        elif num_channels == 1:
                            pixels.append(buffer[j])
                            pixels.append(buffer[j])
                            pixels.append(buffer[j])   
                            pixels.append(1.0)                               
            else:
                # return the buffer as a list of lists
                for y in range(height-1, -1, -1):
                    i = (width * y * num_channels)

                    for x in range(0, width):
                        j = i + (num_channels * x)
                        pixel = []
                        pixel.append(buffer[j])    
                        if num_channels == 4:
                            pixel.append(buffer[j+1])
                            pixel.append(buffer[j+2])
                            pixel.append(buffer[j+3])                            
                        elif num_channels == 3:
                            pixel.append(buffer[j+1])
                            pixel.append(buffer[j+2])
                            pixel.append(1.0)
                        elif num_channels == 2:
                            pixel.append(buffer[j+1])
                            pixel.append(1.0)                        
                            pixel.append(1.0)                        
                        elif num_channels == 1:
                            pixel.append(buffer[j])
                            pixel.append(buffer[j])      
                            pixel.append(1.0)  

                        pixels.append(pixel)            

            return pixels
        except Exception as e:
            rfb_log().error("Could not get buffer: %s" % str(e))
            return None                             

    def save_viewport_snapshot(self, frame=1):
        if not self.rman_is_viewport_rendering:
            return

        width = self.viewport_res_x
        height = self.viewport_res_y

        pixels = self._get_buffer(width, height)
        if not pixels:
            rfb_log().error("Could not save snapshot.")
            return

        nm = 'rman_viewport_snapshot_{F4}_%d' % len(bpy.data.images)
        nm = string_utils.expand_string(nm, frame=frame)
        img = bpy.data.images.new(nm, width, height, float_buffer=True, alpha=True)                
        img.pixels = pixels
        img.update()
       
    def update_scene(self, context, depsgraph):
        if self.rman_interactive_running:
            self.rman_scene_sync.update_scene(context, depsgraph)

    def update_view(self, context, depsgraph):
        if self.rman_interactive_running:
            self.rman_scene_sync.update_view(context, depsgraph)
