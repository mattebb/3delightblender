import time
import os
import rman
import bpy
import sys
from .rman_scene import RmanScene
from. import rman_spool
from. import chatserver
from .rfb_logger import rfb_log
import socketserver
import threading
import ctypes

# utils
from .rman_utils import filepath_utils
from .rman_utils import string_utils
from .rman_utils import display_utils

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

class ItHandler(chatserver.ItBaseHandler):

    def dspyRender(self):
        global __RMAN_RENDER__
        if not __RMAN_RENDER__.is_running:                        
            bpy.ops.render.render()             

    def dspyIPR(self):
        global __RMAN_RENDER__
        if __RMAN_RENDER__.rman_interactive_running:
            crop = []
            for c in self.msg.getOpt('crop').split(' '):
                crop.append(float(c))
            if len(crop) == 4:
                __RMAN_RENDER__.rman_scene.update_cropwindow(crop)

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
    while db.rman_is_live_rendering:
        db.bl_engine.tag_redraw()
        time.sleep(0.01)


def progress_cb(e, d, db):
    db.bl_engine.update_progress(float(d) / 100.0)
    if db.rman_is_live_rendering and int(d) == 100:
        db.rman_is_live_rendering = False

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
        self.bl_engine = None
        self.rman_running = False
        self.rman_interactive_running = False
        self.rman_swatch_render_running = False
        self.rman_is_live_rendering = False
        self.rman_render_into = 'blender'
        self.it_port = -1 
        self.rman_callbacks = dict()

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

    def _load_image_into_blender(self):
        # try to load image into Blender
        if self.rman_render_into == 'blender': 
            dspy_dict = display_utils.get_dspy_dict(self.rman_scene)
            render_output = dspy_dict['displays']['beauty']['filePath']

            if not os.path.exists(render_output):
                return

            render = self.bl_scene.render
            image_scale = 100.0 / render.resolution_percentage
            result = self.bl_engine.begin_result(0, 0,
                                        render.resolution_x * image_scale,
                                        render.resolution_y * image_scale)
            lay = result.layers[0]
            try:
                lay.load_from_file(render_output)
            except:
                pass
            self.bl_engine.end_result(result)   

    def _load_swatch_image_into_blender(self, render_output):
        # try to load image into Blender

        render = self.bl_scene.render
        image_scale = 100.0 / render.resolution_percentage
        result = self.bl_engine.begin_result(0, 0,
                                    render.resolution_x * image_scale,
                                    render.resolution_y * image_scale)
        lay = result.layers[0]
        try:
            lay.load_from_file(render_output)
        except:
            pass
        self.bl_engine.end_result(result)           


    def start_render(self, depsgraph, for_preview=False):

        self.bl_scene = depsgraph.scene_eval
        rm = self.bl_scene.renderman
        self.it_port = start_cmd_server()    
        rfb_log().info("Parsing scene...")
        time_start = time.time()
        self.rman_render_into = rm.render_into
                
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
        config.SetString("rendervariant", rm.renderVariant)
        self.sg_scene = self.sgmngr.CreateScene(config) 
        bl_layer = depsgraph.view_layer
        self.rman_scene.export_for_final_render(depsgraph, self.sg_scene, bl_layer, is_external=False)

        self.rman_running = True
        self._dump_rib_()
        rfb_log().info("Finished parsing scene. Total time: %s" % string_utils._format_time_(time.time() - time_start)) 
        self.rman_is_live_rendering = True
        self.sg_scene.Render("prman -live")
        while not self.bl_engine.test_break() and self.rman_is_live_rendering:
            time.sleep(0.01)
        self.stop_render()        
        if self.rman_render_into == 'blender': 
            self._load_image_into_blender()

        return True  

    def start_external_render(self, depsgraph):         

        bl_scene = depsgraph.scene_eval
        rm = bl_scene.renderman

        self.rman_running = True
        rib_options = ""
        if rm.rib_compression == "gzip":
            rib_options += " -compression gzip"
        rib_options += " -format %s" % rm.rib_format
        if rm.rib_format == "ascii":
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

    def start_interactive_render(self, context, depsgraph):

        global __DRAW_THREAD__

        self.rman_interactive_running = True
        rm = depsgraph.scene_eval.renderman
        self.it_port = start_cmd_server()    
        render_into_org = '' 
        self.rman_render_into = rm.render_into
        
        self.rman_callbacks.clear()
        # register the blender display driver
        try:
            if self.rman_render_into == 'blender':
                # turn off dspyserver mode if we're not rendering to "it"           
                rman.Dspy.DisableDspyServer()                  
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
        config.SetString("rendervariant", rm.renderVariant)      
        self.sg_scene = self.sgmngr.CreateScene(config) 
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
        if self.rman_render_into == 'blender':
            __DRAW_THREAD__ = threading.Thread(target=draw_threading_func, args=(self, ))
            __DRAW_THREAD__.start()

    def start_swatch_render(self, depsgraph):
        self.bl_scene = depsgraph.scene_eval
        rfb_log().info("Parsing scene...")
        time_start = time.time()                
        self.rman_callbacks.clear()
        ec = rman.EventCallbacks.Get()
        ec.RegisterCallback("Progress", progress_cb, self)
        self.rman_callbacks["Progress"] = progress_cb
        ec.RegisterCallback("Render", render_cb, self)
        self.rman_callbacks["Render"] = render_cb        

        render_output = '/var/tmp/blender_preview.exr'
        if sys.platform == ("win32"):
            render_output = 'C:/tmp/blender_preview.exr'
        
        self.sg_scene = self.sgmngr.CreateScene(rman.Types.RtParamList()) 
        self.rman_scene.export_for_swatch_render(depsgraph, self.sg_scene, render_output)

        self.rman_running = True
        self.rman_swatch_render_running = True
        self._dump_rib_()
        rfb_log().info("Finished parsing scene. Total time: %s" % string_utils._format_time_(time.time() - time_start)) 
        self.rman_is_live_rendering = True
        self.sg_scene.Render("prman -live")
        while not self.bl_engine.test_break() and self.rman_is_live_rendering:
            time.sleep(0.01)
        self.stop_render()        
        self._load_swatch_image_into_blender(render_output)

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
        self.sg_scene.Stop()
        rfb_log().debug("Delete Scenegraph scene")
        self.sgmngr.DeleteScene(self.sg_scene)

        self.rman_interactive_running = False
        self.rman_running = False     
        self.rman_swatch_render_running = False
        self.sg_scene = None
        rfb_log().debug("RenderMan has Stopped.")
                
    def draw_pixels(self):
        if self.rman_interactive_running:
            global __BLENDER_DSPY_PLUGIN__
            try:
                if __BLENDER_DSPY_PLUGIN__ == None:
                    # grab a pointer to the Blender display driver
                    ext = '.so'
                    if sys.platform == ("win32"):
                         ext = '.dll'
                    __BLENDER_DSPY_PLUGIN__ = ctypes.CDLL(os.path.join(filepath_utils.guess_rmantree(), 'lib', 'plugins', 'd_blender%s' % ext))

                # call the DrawBufferToBlender function in the display driver
                __BLENDER_DSPY_PLUGIN__.DrawBufferToBlender()
                   
            except:
                pass

    def update_scene(self, context, depsgraph):
        if self.rman_interactive_running:
            self.rman_scene.update_scene(context, depsgraph)

    def update_view(self, context, depsgraph):
        if self.rman_interactive_running:
            self.rman_scene.update_view(context, depsgraph)