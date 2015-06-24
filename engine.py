# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 Brian Savery
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
#import prman
import bpy
import bpy_types
import math
import os
import time
import subprocess
import mathutils
from mathutils import Matrix, Vector, Quaternion

from . import bl_info

from .util import bpy_newer_257
from .util import BlenderVersionError
from .util import rib, rib_path, rib_ob_bounds
from .util import make_frame_path
from .util import init_exporter_env
from .util import get_sequence_path
from .util import user_path
from .util import get_path_list_converted
from .util import path_list_convert, guess_rmantree, set_pythonpath
from random import randint
import sys

addon_version = bl_info['version']

# global dictionaries
from .export import write_rib, write_preview_rib

#set pythonpath
set_pythonpath(os.path.join(guess_rmantree(), 'bin'))
import prman

def init():
    pass
    
def create(engine, data, scene, region=0, space_data=0, region_data=0):
    #TODO add support for regions (rerendering)
    engine.render_pass = RPass(scene)

def free(engine):
    if hasattr(engine, 'render_pass'):
        if engine.render_pass.is_interactive_running:
            engine.render_pass.end_interactive()
        if engine.render_pass:
            del engine.render_pass

def render(engine):
    if hasattr(engine, 'render_pass'):
        engine.render_pass.render(engine)

def reset(engine, data, scene):
    engine.render_pass.set_scene(scene)

def update(engine, data, scene):
    if engine.is_preview:
        engine.render_pass.gen_preview_rib()
    else:
        engine.render_pass.gen_rib()

#assumes you have already set the scene
def start_interactive(engine):
    engine.render_pass.start_interactive()

def update_interactive(context):
    engine.render_pass.issue_edits(context)


class RPass:    
    def __init__(self, scene):
        self.scene = scene
        init_exporter_env(scene)
        self.initialize_paths(scene)
        
        self.do_render = True
        self.is_interactive_running = False
        self.options = []
        prman.Init()
        self.ri = prman.Ri()

    def __del__(self):
        del self.ri
        prman.Cleanup()


    def initialize_paths(self, scene):
        self.paths = {}
        self.paths['rman_binary'] = scene.renderman.path_renderer
        self.paths['rmantree'] = scene.renderman.path_rmantree
        
        self.paths['rib_output'] = user_path(scene.renderman.path_rib_output, 
                                            scene=scene)
        self.paths['export_dir'] = user_path(os.path.dirname( \
                self.paths['rib_output']), scene=scene)
        
        if not os.path.exists(self.paths['export_dir']):
            os.mkdir(self.paths['export_dir'])
        
        self.paths['render_output'] = os.path.join(self.paths['export_dir'], 
                                        'buffer.tif')
        
        #self.paths['shader'] = get_path_list_converted(scene.renderman, 'shader')
        #self.paths['texture'] = get_path_list_converted(scene.renderman, 'texture')
        #self.paths['procedural'] = get_path_list_converted(scene.renderman, 'procedural')
        #self.paths['archive'] = get_path_list_converted(scene.renderman, 'archive')
    
    
    def render(self, engine):
        DELAY = 1
        render_output = self.paths['render_output']
        if os.path.exists(render_output):
            try:
                os.remove(render_output) # so as not to load the old file
            except:
                print('error removing ' + render_output)
        
        #create command and start process

        options = self.options
        if self.scene.renderman.display_driver == 'blender':
            options = options + ['-checkpoint', '1.0s']
        cmd = [os.path.join(self.paths['rmantree'], 'bin', \
                self.paths['rman_binary'])] + self.options + \
                options + [self.paths['rib_output']]
        
        cdir = os.path.dirname(self.paths['rib_output'])
        environ = os.environ.copy()
        environ['RMANTREE'] = self.paths['rmantree']
        process = subprocess.Popen(cmd, cwd=cdir, 
                                    stdout=subprocess.PIPE, env=environ)


        # Wait for the file to be created
        while not os.path.exists(render_output):
            if engine.test_break():
                try:
                    process.kill()
                except:
                    pass
                break

            if process.poll() != None:
                engine.update_stats("", "PRMan: Failed render")
                break

            time.sleep(DELAY)
        
        if os.path.exists(render_output):
            engine.update_stats("", "PRMan: Rendering")
            do_update = self.scene.renderman.display_driver == 'blender'
        
            prev_size = -1
        
            def update_image():
                result = engine.begin_result(0, 0, 
                            self.scene.render.resolution_x, 
                            self.scene.render.resolution_y)
                lay = result.layers[0]
                # possible the image wont load early on.
                try:
                    lay.load_from_file(render_output)
                except:
                    pass
                engine.end_result(result)


            # Update while rendering
            while True:    
                if process.poll() != None:
                    if do_update:
                        update_image()
                    engine.update_stats("", "PRMan: Done Rendering")
                    break
        
                # user exit
                if engine.test_break():
                    try:
                        process.kill()
                    except:
                        pass
                    break
        
                # check if the file updated
                new_size = os.path.getsize(render_output)
        
                if new_size != prev_size:
                    if do_update:
                        update_image()
                    prev_size = new_size
        
                time.sleep(DELAY)

    def set_scene(self, scene):
        self.scene = scene

    #start the interactive session.  Basically the same as ribgen, only 
    #save the file
    def start_interactive(self):
        pass

    #search through context.scene for is_updated
    #use edit world begin
    def issue_edits(context):
        pass

    #ri.end
    def end_interactive(self):
        pass

    def gen_rib(self):
        write_rib(self, self.scene, self.ri)

    def gen_preview_rib(self):
        write_preview_rib(self, self.scene, self.ri)




