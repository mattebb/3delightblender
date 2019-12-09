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
import bgl

# utils
from .rman_utils import filepath_utils
from .rman_utils import string_utils
from .rman_utils import display_utils

__RMAN_RENDER__ = None
__RMAN_IT_PORT__ = -1

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

def iteration_cb(e, iteration, db):
    db.bl_engine.tag_redraw()

def progress_cb(e, d, db):
    db.bl_engine.update_progress(float(d) / 100.0)

def progress_viewport_cb(e, d, db):
    db.bl_engine.tag_redraw()

def render_cb(e, d, db):
    if d == 0:
        rfb_log().debug("RenderMan has exited.")

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
        self.it_port = -1 

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

    def _load_image_into_blender(self, render_output, bl_scene):
        render = bl_scene.render
        image_scale = 100.0 / render.resolution_percentage
        result = self.bl_engine.begin_result(0, 0,
                                    render.resolution_x * image_scale,
                                    render.resolution_y * image_scale)
        lay = result.layers[0]
        # possible the image wont load early on.
        try:
            lay.load_from_file(render_output)
        except:
             pass
        self.bl_engine.end_result(result)           

    def start_render(self, depsgraph, for_preview=False):

        bl_scene = depsgraph.scene_eval
        rm = bl_scene.renderman

        rfb_log().info("Parsing scene...")
        time_start = time.time()
                
        ec = rman.EventCallbacks.Get()
        ec.RegisterCallback("Progress", progress_cb, self)

        self.sg_scene = self.sgmngr.CreateScene() 
        bl_layer = depsgraph.view_layer
        self.rman_scene.export_for_final_render(depsgraph, self.sg_scene, bl_layer, is_external=False)

        self.rman_running = True
        self._dump_rib_()
        rfb_log().info("Finished parsing scene. Total time: %s" % string_utils._format_time_(time.time() - time_start))             
        self.sg_scene.Render("prman -blocking")

        # try to load image into Blender
        if rm.render_into == 'blender':
            dspy_dict = display_utils.get_dspy_dict(self.rman_scene)
            render_output = dspy_dict['displays']['beauty']['filePath']

            if os.path.exists(render_output):
                self._load_image_into_blender(render_output, bl_scene)

        self.sgmngr.DeleteScene(self.sg_scene)
        self.sg_scene = None
        ec.UnregisterCallback("Progress", progress_cb, self)  
        self.rman_running = False

        return True  

    def start_external_render(self, depsgraph):         

        bl_scene = depsgraph.scene_eval
        rm = bl_scene.renderman

        self.rman_running = True
        if rm.external_animation:
            original_frame = bl_scene.frame_current
            rfb_log().debug("Writing to RIB...")             
            for frame in range(bl_scene.frame_start, bl_scene.frame_end + 1):
                bl_view_layer = depsgraph.view_layer
                self.sg_scene = self.sgmngr.CreateScene() 
                self.bl_engine.frame_set(frame, subframe=0.0)
                self.rman_scene.export_for_final_render(depsgraph, self.sg_scene, bl_view_layer, is_external=True)
                rib_output = string_utils.expand_string(rm.path_rib_output, 
                                                        frame=frame, 
                                                        asFilePath=True)                                                                            
                self.sg_scene.Render("rib %s" % rib_output)   
                self.sgmngr.DeleteScene(self.sg_scene)     

            self.bl_engine.frame_set(original_frame, subframe=0.0)
            

        else:
            self.sg_scene = self.sgmngr.CreateScene() 

            time_start = time.time()
                    
            bl_view_layer = depsgraph.view_layer         
            rfb_log().info("Parsing scene...")             
            self.rman_scene.export_for_final_render(depsgraph, self.sg_scene, bl_view_layer, is_external=True)
            rib_output = string_utils.expand_string(rm.path_rib_output, 
                                                    frame=bl_scene.frame_current, 
                                                    asFilePath=True)            

            rfb_log().debug("Writing to RIB: %s..." % rib_output)
            rib_time_start = time.time()
            self.sg_scene.Render("rib %s" % rib_output)     
            rfb_log().debug("Finished writing RIB. Time: %s" % string_utils._format_time_(time.time() - rib_time_start)) 
            rfb_log().info("Finished parsing scene. Total time: %s" % string_utils._format_time_(time.time() - time_start))
            self.sgmngr.DeleteScene(self.sg_scene)

        spooler = rman_spool.RmanSpool(self, self.rman_scene, depsgraph)
        spooler.batch_render()
        self.rman_running = False
        self.sg_scene = None
        return True          

    def start_interactive_render(self, context, depsgraph):

        self.rman_interactive_running = True
        rm = depsgraph.scene_eval.renderman
        self.it_port = start_cmd_server()    
        render_into_org = '' 
        
        # register the blender display driver
        try:
            if rm.render_into == 'blender':
                ec = rman.EventCallbacks.Get()
                ec.RegisterCallback("Iteration", iteration_cb, self)    
                ec.RegisterCallback("Progress", progress_viewport_cb, self)   
                # turn off dspyserver mode if we're not rendering to "it"           
                rman.Dspy.DisableDspyServer()
                rman.Dspy.GetBlenderDspy()                         
            else:
                rman.Dspy.EnableDspyServer()
        except:
            # force rendering to 'it'
            rfb_log().error('Could not register Blender display driver. Rendering to "it".')
            render_into_org = rm.render_into
            rm.render_into = 'it'

        time_start = time.time()      

        self.sg_scene = self.sgmngr.CreateScene() 
        rfb_log().info("Parsing scene...")        
        self.rman_scene.export_for_interactive_render(context, depsgraph, self.sg_scene)

        self._dump_rib_()      
        rfb_log().info("Finished parsing scene. Total time: %s" % string_utils._format_time_(time.time() - time_start))             
        self.sg_scene.Render("prman -live")

        rfb_log().info("RenderMan Viewport Render Started.")  

        if render_into_org != '':
            rm.render_into = render_into_org    

    def start_export_rib_selected(self, context, rib_path, export_materials=True, export_all_frames=False):

        self.rman_running = True  
        self.sg_scene = self.sgmngr.CreateScene()     
        self.rman_scene.export_for_rib_selection(context, self.sg_scene)
        self.sg_scene.Render("rib " + rib_path + " -archive")
        self.sgmngr.DeleteScene(self.sg_scene)
        self.sg_scene = None
        self.rman_running = False        
        return True                 

    def stop_render(self):   
        if not self.rman_interactive_running and not self.rman_running:
            return

        rfb_log().debug("Telling SceneGraph to stop.")        
        self.sg_scene.Stop()
        rfb_log().debug("Delete Scenegraph scene")
        self.sgmngr.DeleteScene(self.sg_scene)

        # Remove callbacks
        ec = rman.EventCallbacks.Get()
        if self.rman_interactive_running and self.rman_scene.is_viewport_render:
            ec.UnregisterCallback("Iteration", iteration_cb, self)  
            ec.UnregisterCallback("Progress", progress_viewport_cb, self)        
        if self.rman_running:
            ec.UnregisterCallback("Progress", progress_cb, self) 

        self.rman_interactive_running = False
        self.rman_running = False     
        self.sg_scene = None
        rfb_log().debug("RenderMan has Stopped.")
                
    def draw_pixels(self):
        if self.rman_interactive_running:
            try:
                rman.Dspy.DrawBufferToBlender()                   
            except:
                pass

    def update_scene(self, context, depsgraph):
        if self.rman_interactive_running:
            self.rman_scene.update_scene(context, depsgraph)

    def update_view(self, context, depsgraph):
        if self.rman_interactive_running:
            self.rman_scene.update_view(context, depsgraph)