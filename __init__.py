# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2011 Matt Ebb
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

bl_info = {
    "name": "BlenderMan",
    "author": "Brian Savery",
    "version": (0, 1, 1),
    "blender": (2, 74, 0),
    "location": "Info Header, render engine menu",
    "description": "RenderMan 20.0 integration",
    "warning": "",
    "category": "Render"}

import bpy
#import prman
import sys

from . import engine

class Blenderman(bpy.types.RenderEngine):
    bl_idname = 'PRMAN_RENDER'
    bl_label = "BlenderMan"
    bl_use_preview = True
    bl_use_save_buffers = True

    def __init__(self):
        #print('initing')
        self.render_pass = None
        
    def __del__(self):
        #print('deleting')
        engine.free(self)
        

    # main scene render
    def update(self, data, scene):
        if self.is_preview:
            #print('preview')
            if not self.render_pass:
                engine.create(self, data, scene)
        else:
            if not self.render_pass:
                engine.create(self, data, scene)
            else:
                engine.reset(self, data, scene)
        
        engine.update(self, data, scene)
        #print('updated scene, wrote rib')

    def render(self, scene):
        #print('rendering')
        engine.render(self)
        #print('done rendering')

    #TODO
    # view_update for rerendering
    # view_draw for rerendering

def register():
    from . import ui
    from . import preferences
    from . import properties
    from . import operators
    from . import nodes

    preferences.register()
    properties.register()
    operators.register()
    ui.register()
    nodes.register()
    bpy.utils.register_module(__name__)
    

def unregister():
    from . import ui
    from . import preferences
    from . import properties
    from . import operators
    from . import nodes

    preferences.register()
    properties.register()
    operators.register()
    ui.register()
    nodes.register()
    bpy.utils.unregister_module(__name__)

