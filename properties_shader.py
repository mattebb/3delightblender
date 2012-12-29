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

import bpy
from bpy.props import PointerProperty, StringProperty, BoolProperty, EnumProperty, \
IntProperty, FloatProperty, FloatVectorProperty, CollectionProperty

'''
Currently:

Material
 \
  - Renderman
   \
    - Surface Shader Settings
     \ 
      - Active Surface Shader
      - Shader Foo Settings (dynamically generated RNA type)
       \
        - Parameter A
        - Parameter B
    - Shader Bar Settings (dynamically generated RNA type)
     \
      - Parameter X
    - Displacement Shader Settings



Perhaps:

Material
 \
  - Renderman
   \
    - Surface Shader
     \
      - Surface Shader Name
      - Parameters
       \
        - Parameter A
        - Parameter B
    - Displacement Shader
     \
      - Displacement Shader Name
      - Parameters  (dynamically generated RNA type)
       \
        - Parameter Z

'''

class coshaderShaders(bpy.types.PropertyGroup):

    def coshader_shader_active_update(self, context):
        # BBM addition begin
        if self.id_data.name == 'World': # world coshaders
            location = 'world'
            mat_rm = context.scene.world.renderman
        elif bpy.context.active_object.name in bpy.data.lamps.keys(): # lamp coshaders
            location = 'lamp'
            lamp = bpy.data.lamps.get(bpy.context.active_object.name)
            mat_rm = lamp.renderman
        else: # material coshaders
            location = 'material'
            mat_rm = context.active_object.active_material.renderman
        shader_active_update(self, context, 'shader', location) # BBM modified (from 'surface' to 'shader')
        cosh_index = mat_rm.coshaders_index
        active_cosh = mat_rm.coshaders[cosh_index]
        active_cosh_name = active_cosh.shader_shaders.active
        if active_cosh_name == 'null':
            coshader_name = active_cosh_name
        else:
            all_cosh = [ (cosh.name) for cosh in mat_rm.coshaders ]
            same_name = 1
            for cosh in all_cosh:
                if cosh.startswith( active_cosh_name ):
                    same_name += 1
            coshader_name = ('%s_%d' % (active_cosh_name, same_name))
        active_cosh.name = coshader_name
        # BBM addition end
    
    active = StringProperty(
                name="Active Co-Shader",
                description="Shader name to use for coshader",
                update=coshader_shader_active_update,
                default="null"
                )

    def coshader_shader_list_items(self, context):
        print('----coshader list items')
        print(shader_list_items(self, context, 'shader'))
        return shader_list_items(self, context, 'shader')

    def coshader_shader_list_update(self, context):
        shader_list_update(self, context, 'shader')

    shader_list = EnumProperty(
                name="Active Co-Shader",
                description="Shader name to use for coshader",
                update=coshader_shader_list_update,
                items=coshader_shader_list_items
                )

class RendermanCoshader(bpy.types.PropertyGroup):
    name = StringProperty(
                name="Name (Handle)",
                description="Handle to refer to this co-shader from another shader")
    
    #BBM replace begin
    #surface_shaders = PointerProperty( 
    #            type=surfaceShaders,
    #            name="Surface Shader Settings")
    #by
    shader_shaders = PointerProperty(
                type=coshaderShaders,
                name="Coshader Shader Settings")
#BBM modification end
