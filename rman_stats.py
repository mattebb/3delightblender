import re
import os
import sys
import json
import bpy
import rman
import threading
import time

from collections import OrderedDict
import rman_utils.stats_config.core as stcore
from . import rman_render
from .rfb_utils import prefs_utils
from .rfb_logger import rfb_log

__oneK2__ = 1024.0*1024.0
__RFB_STATS_MANAGER__ = None

__LIVE_METRICS__ = [
    ["/system.processMemory", "Memory"],
    ["/rman/raytracing.numRays", "Rays/Sec"],
    ["/rman/renderer@progress", None],
    ['/rman@iterationComplete', None],
    ["/rman.timeToFirstRaytrace", "Time to first Ray"],
    ["/rman.timeToFirstPixel", "Time to first Pixel"],
    ["/rman.timeToFirstIteration", "Time to first Iteration"],    
]

class RfBBaseMetric(object):

    def __init__(self, key, label):
        self.key = key
        self.label = label



class RfBStatsManager(object):

    def __init__(self, rman_render):
        global __RFB_STATS_MANAGER__
        global __LIVE_METRICS__

        self.mgr = None
        self.create_stats_manager()        
        self.render_live_stats = OrderedDict()
        self.render_stats_names = OrderedDict()
        self._prevTotalRays = 0
        self._progress = 0
        self._prevTotalRaysValid = True

        for name,label in __LIVE_METRICS__:
            if label:
                self.render_live_stats[label] = '--'
            self.render_stats_names[name] = label

        self.export_stat_label = ''
        self.export_stat_progress = 0.0

        self._integrator = 'PxrPathTracer'
        self._maxSamples = 0
        self._iterations = 0
        self._decidither = 0
        self._res_mult = 0.0
        self.web_socket_enabled = False

        # roz objects
        self.rman_stats_session_name = "RfB Stats Session"
        self.rman_stats_session = None
        self.rman_stats_session_config = None        

        self.rman_render = rman_render
        self.init_stats_session()
        self.boot_strap_thread = None
        self.boot_strap_thread_kill = False
        self.attach()
        __RFB_STATS_MANAGER__ = self

    def __del__(self):
        if self.boot_strap_thread.is_alive():
            self.boot_strap_thread_kill = True
            self.boot_strap_thread.join()

    @classmethod
    def get_stats_manager(self):
        global __RFB_STATS_MANAGER__
        return __RFB_STATS_MANAGER__        

    def reset(self):
        for label in self.render_live_stats.keys():
            self.render_live_stats[label] = '--'
        self._prevTotalRays = 0
        self._progress = 0
        self._prevTotalRaysValid = True      
        self.export_stat_label = ''
        self.export_stat_progress = 0.0              

    def create_stats_manager(self): 
        if self.mgr:
            return

        try:
            self.mgr = stcore.StatsManager(
                            # host_update_config_func=update_config_func,
                            # host_load_config_func=self.load_config_func
                            ) 
            self.is_valid = self.mgr.is_valid
        except:
            self.mgr = None
            self.is_valid = False          

    def init_stats_session(self):   

        self.rman_stats_session_config = rman.Stats.SessionConfig(self.rman_stats_session_name)

        # look for a custom stats.ini file
        rman_stats_config_path = os.environ.get('RMAN_STATS_CONFIG_PATH', None)
        if rman_stats_config_path:
            if os.path.exists(os.path.join(rman_stats_config_path, 'stats.ini')):
                self.rman_stats_session_config.LoadConfigFile(rman_stats_config_path, 'stats.ini')
                          
        self.update_session_config()     
        self.rman_stats_session = rman.Stats.AddSession(self.rman_stats_session_config)  

    def update_session_config(self):

        self.web_socket_enabled = prefs_utils.get_pref('rman_roz_webSocketServer', default=True)

        config_dict = dict()
        config_dict["logLevel"] = int(prefs_utils.get_pref('rman_roz_logLevel', default='3'))
        config_dict["grpcServer"] = prefs_utils.get_pref('rman_roz_grpcServer', default=True)
        config_dict["webSocketServer"] = self.web_socket_enabled

        config_str = json.dumps(config_dict)
        self.rman_stats_session_config.Update(config_str)
        if self.rman_stats_session:
            self.rman_stats_session.Update(self.rman_stats_session_config)            
        if self.web_socket_enabled:
            self.create_stats_manager()
        else:
            del self.mgr
            self.mgr = None

    def boot_strap(self):
        while not self.mgr.clientConnected():
            time.sleep(0.01)
            if self.boot_strap_thread_kill:
                return
            if self.mgr.clientConnected():
                for name,label in __LIVE_METRICS__:
                    # Declare interest
                    self.mgr.enableMetric(name)
                return       
        
    def attach(self):
        """
        """
        # 
        # TODO put WebSocket client host/port into config
        host = "127.0.0.1"
        #port = int(self.mgr.config["webSocketPort"])
        port = 8080

        if not self.mgr:
            return 
        if (self.mgr.clientConnected()):
            # Maybe toggle with disconnect
            return

        # The connectToServer call is a set of asynchronous calls so we set
        # a thread to check the connection and then enable the metrics
        self.mgr.connectToServer(host, port)

        # if the bootstrap thread is still running, kill it
        if self.boot_strap_thread:
            if self.boot_strap_thread.is_alive():
                self.boot_strap_thread_kill = True
                self.boot_strap_thread.join()
            self.boot_strap_thread_kill = False
            self.boot_strap_thread = False

        self.boot_strap_thread = threading.Thread(target=self.boot_strap)
        self.boot_strap_thread.start()

    def is_connected(self):
        return (self.web_socket_enabled and self.mgr and self.mgr.clientConnected())

    def disconnect(self):
        if self.is_connected():
            self.mgr.disconnectFromServer()

    def check_payload(self, jsonData, name):
        try:
            dat = jsonData[name]
            return dat
        except KeyError:
            # could not find the metric name in the JSON
            # try re-registering it again
            self.mgr.enableMetric(name)
            return None

    def update_payloads(self):
        """ Get the latest payload data from Roz via the websocket client in the
            manager object. Data comes back as a JSON-formatted string which is
            then parsed to update the appropriate payload field widgets.
        """
        if not self.is_connected():
            self.draw_stats()
            return

        latest = self.mgr.getLatestData()

        if (latest):
            # Load JSON-formated string into JSON object
            try:
                jsonData = json.loads(latest)
            except json.decoder.JSONDecodeError:
                rfb_log().debug("Could not decode stats payload JSON.")
                jsonData = dict()
                pass

            for name, label in self.render_stats_names.items():
                dat = self.check_payload(jsonData, name)
                if not dat:
                    continue

                if name == "/system.processMemory":
                    # Payload has 3 floats: max, resident, XXX
                    # Convert resident mem to MB : payload[1] / 1024*1024;
                    memPayload = dat["payload"].split(',')
                    maxresMB = ((float)(memPayload[1])) / __oneK2__
                    # Set consistent fixed point output in string
                    
                    self.render_live_stats[label] = "{:.2f} MB".format(maxresMB)
                    
                elif name == "/rman/raytracing.numRays":
                    currentTotalRays = int(dat['payload'])
                    if currentTotalRays <= self._prevTotalRays:
                        self._prevTotalRaysValid = False

                    # Synthesize into per second
                    if self._prevTotalRaysValid:                    
                        # The metric is sampled at 60Hz (1000/16-62.5)
                        diff = currentTotalRays - self._prevTotalRays
                        raysPerSecond = float(diff * 62.5)
                        if raysPerSecond > 1000000000.0:
                            self.render_live_stats[label] = "{:.3f}B".format(raysPerSecond / 1000000000.0)    
                        elif raysPerSecond > 1000000.0:
                            self.render_live_stats[label] = '{:.3f}M'.format(raysPerSecond / 1000000.0)    
                        elif raysPerSecond > 1000.0:
                            self.render_live_stats[label] = '{:.3f}K'.format(raysPerSecond / 1000.0)    
                        else:
                            self.render_live_stats[label] = '{:.3f}'.format(raysPerSecond)
                        
                    self._prevTotalRaysValid = True
                    self._prevTotalRays = currentTotalRays    
                elif name == "/rman@iterationComplete":
                    itr = eval(dat['payload'])[0]
                    self._iterations = itr  
                    self.render_live_stats[label] = '%d / %d' % (itr, self._maxSamples)
                elif name == "/rman/renderer@progress":
                    progressVal = int(float(dat['payload']))
                    self._progress = progressVal                      
                else:
                    self.render_live_stats[label] = str(dat['payload'])           

        self.draw_stats()

    def set_export_stats(self, label, progress):
        self.export_stat_label = label
        self.export_stat_progress = progress

    def draw_stats(self):
        if self.rman_render.rman_is_exporting:
            self.draw_export_stats()
        else:
            self.draw_render_stats()        

    def draw_export_stats(self):
        if self.rman_render.bl_engine:
            try:
                if self.rman_render.rman_interactive_running:
                    progress = int(self.export_stat_progress*100)
                    self.rman_render.bl_engine.update_stats('RenderMan (Stats)', "\n%s: %d%%" % (self.export_stat_label, progress))
                else:
                    progress = int(self.export_stat_progress*100)
                    self.rman_render.bl_engine.update_stats(self.export_stat_label, "%d%%" % progress)

            except:
                rfb_log().debug("Cannot update progress")        

    def draw_render_stats(self):
        if not self.rman_render.rman_running:
            return

        _stats_to_draw = [
            "Memory",
            "Rays/Sec",
        ]

        if self.rman_render.rman_interactive_running:
            message = '\n%s, %d, %d%%' % (self._integrator, self._decidither, self._res_mult)
            if self.is_connected():
                for label in _stats_to_draw:
                    data = self.render_live_stats[label]
                    message = message + '\n%s: %s' % (label, data)
                # iterations
                message = message + '\nIterations: %d / %d' % (self._iterations, self._maxSamples)
            try:
                self.rman_render.bl_engine.update_stats('RenderMan (Stats)', message)
            except ReferenceError as e:
                rfb_log().debug("Error calling update stats (%s). Aborting..." % str(e))
                return
        else:
            message = ''
            if self.is_connected():
                for label in _stats_to_draw:
                    data = self.render_live_stats[label]
                    message = message + '%s: %s ' % (label, data)       
                # iterations                    
                message = message + 'Iterations: %d / %d ' % (self._iterations, self._maxSamples)                             
            else:
                message = '(no stats connection) '          

            try:
                self.rman_render.bl_engine.update_stats(message, "%d%%" % self._progress)  
                progress = float(self._progress) / 100.0  
                self.rman_render.bl_engine.update_progress(progress)
            except ReferenceError as e:
                rfb_log().debug("Error calling update stats (%s). Aborting..." % str(e))
                return                