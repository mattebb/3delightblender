# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 - 2021 Pixar
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
import bpy
import bgl
import blf
import time
from .rfb_utils.prefs_utils import get_pref
from .rfb_utils import string_utils
from .rfb_logger import rfb_log
from .rfb_utils.envconfig_utils import envconfig

bl_info = {
    "name": "RenderMan For Blender",
    "author": "Pixar",
    "version": (24, 0, 0),
    "blender": (2, 83, 0),
    "location": "Info Header, render engine menu",
    "description": "RenderMan 24.0 integration",
    "warning": "",
    "category": "Render"}

__RMAN_ADDON_LOADED__ = False

class PRManRender(bpy.types.RenderEngine):
    bl_idname = 'PRMAN_RENDER'
    bl_label = "RenderMan"
    bl_use_preview = True # Turn off preview renders
    bl_use_save_buffers = True
    bl_use_shading_nodes = True # We support shading nodes
    bl_use_shading_nodes_custom = False
    bl_use_eevee_viewport = True # Use Eevee for look dev viewport mode

    def __init__(self):
        from . import rman_render
        self.rman_render = rman_render.RmanRender.get_rman_render()
        if self.is_preview and self.rman_render.rman_swatch_render_running:
            # if a preview render is requested and a swatch render is 
            # already in progress, ignore this render request
            return
        if self.rman_render.rman_interactive_running:
            # If IPR is already running, just return. 
            # We report an error in render() if this is a render attempt
            return 
        self.rman_render.bl_engine = self

    def __del__(self):
        pass

    def update(self, data, depsgraph):
        pass

    def view_update(self, context, depsgraph):
        '''
        For viewport renders. Blender calls view_update when starting viewport renders
        and/or something changes in the scene.
        '''

        # check if we are already doing a regular render
        if self.rman_render.is_regular_rendering():
            return
        
        # if interactive rendering has not started, start it
        if not self.rman_render.rman_interactive_running and self.rman_render.sg_scene is None:
            self.rman_render.start_interactive_render(context, depsgraph)

        if self.rman_render.rman_interactive_running:
            self.rman_render.update_scene(context, depsgraph)   

    def view_draw(self, context, depsgraph):
        '''
        For viewport renders. Blender calls view_draw whenever it redraws the 3D viewport.
        This is where we check for camera moves and draw pxiels from our
        Blender display driver.
        '''
        if self.rman_render.rman_interactive_running:               
            self.rman_render.update_view(context, depsgraph)

        self._draw_pixels(context, depsgraph)

    def _increment_version_tokens(self, external_render=False):
        bl_scene = bpy.context.scene
        vi = get_pref('rman_scene_version_increment', default='MANUALLY')
        ti = get_pref('rman_scene_take_increment', default='MANUALLY')

        if (vi == 'RENDER' and not external_render) or (vi == 'BATCH_RENDER' and external_render):
            bl_scene.renderman.version_token += 1
            string_utils.set_var('version', bl_scene.renderman.version_token)
        
        if (ti == 'RENDER' and not external_render) or (ti == 'BATCH_RENDER' and external_render):
            bl_scene.renderman.take_token += 1
            string_utils.set_var('take', bl_scene.renderman.take_token)            

    def render(self, depsgraph):
        '''
        Main render entry point. Blender calls this when doing final renders or preview renders.
        '''
   
        bl_scene = depsgraph.scene_eval
        rm = bl_scene.renderman
        baking = (rm.hider_type in ['BAKE', 'BAKE_BRICKMAP_SELECTED'])

        if self.rman_render.rman_interactive_running:
            # report an error if a render is trying to start while IPR is running
            if self.is_preview and get_pref('rman_do_preview_renders', False):
                self.report({'ERROR'}, 'Cannot start a preview render when IPR is running')
            elif not self.is_preview:
                self.report({'ERROR'}, 'Cannot start a render when IPR is running')
            return
        elif self.is_preview:
            # double check we're not already viewport rendering
            if self.rman_render.rman_interactive_running:
                if get_pref('rman_do_preview_renders', False):
                    rfb_log().error("Cannot preview render while viewport rendering.")
                return            
            if not get_pref('rman_do_preview_renders', False):
                # user has turned off preview renders, just load the placeholder image
                self.rman_render.bl_scene = depsgraph.scene_eval
                self.rman_render._load_placeholder_image()
                return    
            if self.rman_render.rman_swatch_render_running:
                return                     
            self.rman_render.start_swatch_render(depsgraph)
        elif baking:
            if rm.enable_external_rendering:
                self.rman_render.start_external_bake_render(depsgraph) 
            elif not self.rman_render.start_bake_render(depsgraph, for_background=bpy.app.background):
                return
        elif rm.enable_external_rendering:
            self.rman_render.start_external_render(depsgraph)         
            self._increment_version_tokens(external_render=True)                 
        else:
            for_background = bpy.app.background                
            if not self.rman_render.start_render(depsgraph, for_background=for_background):
                return    
            if not for_background:
                self._increment_version_tokens(external_render=False)

    def _draw_pixels(self, context, depsgraph):     

        scene = depsgraph.scene
        w = context.region.width
        h = context.region.height          

        # Draw text area that RenderMan is running.        
        if get_pref('draw_ipr_text', False) and not self.rman_render.rman_is_viewport_rendering:

            pos_x = w / 2 - 100
            pos_y = 20
            blf.enable(0, blf.SHADOW)
            blf.shadow_offset(0, 1, -1)
            blf.shadow(0, 5, 0.0, 0.0, 0.0, 0.8)
            blf.size(0, 32, 36)
            blf.position(0, pos_x, pos_y, 0)
            blf.color(0, 1.0, 0.0, 0.0, 1.0)
            blf.draw(0, "%s" % ('RenderMan Interactive Mode Running'))
            blf.disable(0, blf.SHADOW)   

        if not self.rman_render.rman_is_viewport_rendering:
            return             

        # Bind shader that converts from scene linear to display space,
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBlendFunc(bgl.GL_ONE, bgl.GL_ONE_MINUS_SRC_ALPHA)
        self.bind_display_space_shader(scene)

        self.rman_render.draw_pixels(w, h)

        self.unbind_display_space_shader()
        bgl.glDisable(bgl.GL_BLEND)        

def load_addon():
    global __RMAN_ADDON_LOADED__

    if envconfig():
        from . import rman_config
        from . import rman_presets
        from . import rman_operators
        from . import rman_ui
        from . import rman_bl_nodes
        from . import rman_properties
        from . import rman_handlers

        rman_config.register()
        rman_presets.register()        
        rman_operators.register()
        rman_bl_nodes.register()
        rman_properties.register()          
        rman_ui.register()      
        rman_handlers.register()

        __RMAN_ADDON_LOADED__ = True

    else:
        rfb_log().error(
            "Error loading addon.  Correct RMANTREE setting in addon preferences.")

classes = [
    PRManRender,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    from . import preferences
    preferences.register()
    load_addon()

def unregister():
    global __ADDON_LOADED__

    from . import preferences
    preferences.unregister()

    if __RMAN_ADDON_LOADED__:
        rman_presets.unregister()
        rman_handlers.unregister()
        rman_bl_nodes.unregister()    
        rman_ui.unregister()
        rman_properties.unregister()
        rman_operators.unregister()    
    
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass

