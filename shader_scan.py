# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2012 Matt Ebb
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# 
#
# ##### END MIT LICENSE BLOCK #####

import threading
import os
import subprocess
import time

import bpy
from .util import init_env
from .util import get_path_list_converted


def shader_visbility_annotation(annotations):
    for an in annotations:
        an_items = [a for a in an.split('"') if a.isalnum()]
        for i, an in enumerate(an_items):
            if an_items[i] == 'visibility' and an_items[i+1] == 'False':
                return False
    return True

# Setup for scanning for available shaders to display in the UI
# This is done in a background thread to avoid blocking the UI while scanning files
shader_cache = {}
shaderscan_lock = threading.Lock()

class BgShaderScan(threading.Thread):
    def __init__(self, lock, path_list, material):
        threading.Thread.__init__(self)
        self.lock = lock
        self.path_list = path_list
        self.material = material
        self.daemon = True   
    
    def run(self):
        global shader_cache
        regenerate = False
        
        # limit to only one BG thread at a time, exit rather than wait
        if not self.lock.acquire(blocking=False):
            return

        # global shader cache for all scenes
        shader_cache = {}
        shader_cache['dirs'] = {}
        shader_cache['shaders'] = {}
        
        # initialise some common ones
        shader_cache['shaders']['surface'] = []
        shader_cache['shaders']['displacement'] = []
        shader_cache['shaders']['interior'] = []
        shader_cache['shaders']['atmosphere'] = []
        shader_cache['shaders']['shader'] = []
        shader_cache['shaders']['light'] = []
                    
        # check to see if any dirs have been modified since the last scan, 
        # and if so prepare to regenerate
        for path in self.path_list:
            #print(path)
            if not path in shader_cache['dirs'].keys():
                shader_cache['dirs'][path] = 0.0

            if shader_cache['dirs'][path] < os.path.getmtime(path):
                regenerate = True
                break

        # return if we don't need to scan shaders
        if not regenerate:
            # block for a couple more seconds, to prevent too much scanning
            time.sleep(2)
            self.lock.release()
            return
        
        shaders = {}
        # we need to regenerate, so rebuild entire shader list from all paths
        for k in shader_cache['shaders'].keys():
            shader_cache['shaders'][k] = ['Loading...']
            shaders[k] = []
        
        for path in self.path_list:
            # store the time of this scan
            shader_cache['dirs'][path] = os.path.getmtime(path)

            # now store the updated shader contents
            for f in os.listdir(path):           
                if os.path.splitext(f)[1] == '.sdl':
                    try:
                        output = subprocess.check_output(["shaderinfo", "-t", os.path.join(path, f)]).decode().split('\n')
                        ann_output = subprocess.check_output(["shaderinfo", "-a", os.path.join(path, f)]).decode().split('\n')
                    except:
                        continue

                    # Use the #pragma annotation "visibility" shader annotation to hide from view
                    ann_output = [o.replace('\r', '') for o in ann_output]
                    if shader_visbility_annotation(ann_output) == False:
                        continue
                    
                    sdlname = output[0].replace('\r', '')
                    sdltype = output[1].replace('\r', '')

                    if not sdltype in shaders.keys():
                        shaders[sdltype] = []

                    shaders[sdltype].append(sdlname)
        
        # set the new shader cache
        shader_cache['shaders'] = shaders
        
        self.lock.release()
        
        # XXX -- SUPER dodgy hack to force redraw of the property editor 
        # when the thread is done, since we have no other way atm
        # modify a property, to get it to send a notifier internally
        if self.material:
            try:
                self.material.diffuse_color = self.material.diffuse_color
            except:
                pass

# scans valid paths on disk for shaders, and caches for later retrieval
def shaders_in_path(prefs, idblock, shader_type='', threaded=True):
    global shaderscan_lock
    global shader_cache

    init_env(prefs)
    
    if type(idblock) == bpy.types.Material:
        material = idblock
    #if hasattr(context, "material"):
    #    material = context.material
    else:
        material = None
    
    path_list = get_path_list_converted(prefs, 'shader')
    
    scanthread = BgShaderScan(shaderscan_lock, path_list, material)
    if threaded:
        scanthread.start()
    else:
        print('run')
        scanthread.run()


    if shader_cache != {}:
        if shader_type != '' and shader_type in shader_cache['shaders'].keys():
            return sorted(shader_cache['shaders'][shader_type], key=str.lower)
        else:
            shaderlist = [l for l in shader_cache['shaders'].values()]
            print('SHADER LIST ----------')
            print(shaderlist)
            return [item for sublist in shaderlist for item in sublist] 
    else:
        return ['Loading...']
