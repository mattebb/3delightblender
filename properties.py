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
#from .properties_shader import RendermanCoshader, coshaderShaders

from .util import guess_3dl_path

from .shader_scan import shaders_in_path

from .shader_parameters import rna_type_initialise

from bpy.props import PointerProperty, StringProperty, BoolProperty, EnumProperty, \
IntProperty, FloatProperty, FloatVectorProperty, CollectionProperty

# Shader parameters storage
# --------------------------

def shader_list_items(self, context, shader_type):
    defaults = [('null', 'None', ''), ('custom', 'Custom', '')]
    return defaults + [ (s, s, '') for s in shaders_in_path(context.scene, context.material, shader_type=shader_type)]
    
def shader_list_update(self, context, shader_type):
    # don't overwrite active when set to custom
    if self.shader_list != "custom":
        # For safety, we keep the active shader property separate as a string property,
        # and update when chosen from the shader list
        self.active = str(self.shader_list)

def shader_active_update(self, context, shader_type, location="material"):
    # Also initialise shader parameters when chosen from the shader list
    if location == 'world':
        rm = context.world.renderman
    elif location == 'lamp':
        rm = context.lamp.renderman
    else:
        rm = context.material.renderman


    rna_type_initialise(context.scene, rm, shader_type, True)
    # and for coshaders
    for coshader in rm.coshaders:        
        rna_type_initialise(context.scene, coshader, shader_type, True)
        # BBM



class atmosphereShaders(bpy.types.PropertyGroup):
    def atmosphere_shader_active_update(self, context):
        shader_active_update(self, context, 'atmosphere')
        
    active = StringProperty(
                name="Active Atmosphere Shader",
                description="Shader name to use for atmosphere",
                default="")
    
    def atmosphere_shader_list_items(self, context):
        return shader_list_items(self, context, 'atmosphere')
    
    def atmosphere_shader_list_update(self, context):
        shader_list_update(self, context, 'atmosphere')

    shader_list = EnumProperty(
                name="Active atmosphere Shader",
                description="Shader name to use for surface",
                update=atmosphere_shader_list_update,
                items=atmosphere_shader_list_items)
    
class displacementShaders(bpy.types.PropertyGroup):

    def displacement_shader_active_update(self, context):
        shader_active_update(self, context, 'displacement')
        
    active = StringProperty(
                name="Active Displacement Shader",
                description="Shader name to use for displacement",
                update=displacement_shader_active_update,
                default="null")
                
    def displacement_shader_list_items(self, context):
        return shader_list_items(self, context, 'displacement')
    
    def displacement_shader_list_update(self, context):
        shader_list_update(self, context, 'displacement')

    shader_list = EnumProperty(
                name="Active Displacement Shader",
                description="Shader name to use for surface",
                update=displacement_shader_list_update,
                items=displacement_shader_list_items)

class surfaceShaders(bpy.types.PropertyGroup):

    def surface_shader_active_update(self, context):
        shader_active_update(self, context, 'surface')
    
    active = StringProperty(
                name="Active Surface Shader",
                description="Shader name to use for surface",
                update=surface_shader_active_update,
                default="null"
                )

    def surface_shader_list_items(self, context):
        return shader_list_items(self, context, 'surface')

    def surface_shader_list_update(self, context):
        shader_list_update(self, context, 'surface')

    shader_list = EnumProperty(
                name="Active Surface Shader",
                description="Shader name to use for surface",
                update=surface_shader_list_update,
                items=surface_shader_list_items
                )

class interiorShaders(bpy.types.PropertyGroup):
    
    def interior_shader_active_update(self, context):
        shader_active_update(self, context, 'interior')
    
    active = StringProperty(
                name="Active Interior Shader",
                description="Shader name to use for interior",
                update=interior_shader_active_update,
                default="null")

    def interior_shader_list_items(self, context):
        return shader_list_items(self, context, 'interior')
    
    def interior_shader_list_update(self, context):
        shader_list_update(self, context, 'interior')

    shader_list = EnumProperty(
                name="Active Interior Shader",
                description="Shader name to use for surface",
                update=interior_shader_list_update,
                items=interior_shader_list_items)

#BBM modification begin

class lightShaders(bpy.types.PropertyGroup):
	
    def light_shader_active_update(self, context):
        shader_active_update(self, context, 'light')
	
    active = StringProperty(
                name="Active Light Shader",
                description="Shader name to use for light",
                default="")
	
    def light_shader_list_items(self, context):
        return shader_list_items(self, context, 'light')

    def light_shader_list_update(self, context):
        shader_list_update(self, context, 'light')

    shader_list = EnumProperty(
                name="Active Light",
                description="Light shader",
                update=light_shader_list_update,
                items=light_shader_list_items
                )


# Blender data
# --------------------------

context_items = [(i.identifier, i.name, "") for i in bpy.types.SpaceProperties.bl_rna.properties['context'].enum_items]

# hack! this is a bit of a hack in itself, but should really be in SpaceProperties.
# However, can't be added there, it's non-ID data.
bpy.types.WindowManager.prev_context = EnumProperty(
                name="Previous Context",
                description="Previous context viewed in properties editor",
                items=context_items,
                default=context_items[0][0])

class RendermanPath(bpy.types.PropertyGroup):
    name = StringProperty(
                name="", subtype='DIR_PATH')

class RendermanInlineRIB(bpy.types.PropertyGroup):
    name = StringProperty( name="Text Block" )
    
class RendermanGrouping(bpy.types.PropertyGroup):
    name = StringProperty( name="Group Name" )

class LightLinking(bpy.types.PropertyGroup):
    
    def lights_list_items(self, context):
        items = [('No light chosen','Choose a light','')]
        for lamp in bpy.data.lamps:
            items.append( (lamp.name,lamp.name,'') )
        return items
    
    def update_name( self, context ):
        infostr = ('(Default)', '(Forced On)', '(Forced Off)')
        valstr = ('DEFAULT', 'ON', 'OFF')
        
        self.name = "%s %s" % (self.light, infostr[valstr.index(self.illuminate)])
    
    light = StringProperty(
                name="Light",
                update=update_name )

    illuminate = EnumProperty(
                name="Illuminate",
                update=update_name,
                items=[ ('DEFAULT', 'Default', ''),
				        ('ON', 'On', ''),
				        ('OFF', 'Off', '')] )


class TraceSet(bpy.types.PropertyGroup):
    
    def groups_list_items(self, context):
        items = [('No group chosen','Choose a trace set','')]
        for grp in context.scene.renderman.grouping_membership:
            items.append( (grp.name,grp.name,'') )
        return items
    
    def update_name( self, context ):
        self.name = self.mode +' '+ self.group
    
    group = EnumProperty    (   name="Group", 
                                update=update_name,
                                items=groups_list_items
                            )
    mode = EnumProperty(  name="Include/Exclude",
                                update=update_name,
	                            items=[ ('included in', 'Include', ''),
								        ('excluded from', 'Exclude', '')]
                             )

# hmmm, re-evaluate this idea later...
class RendermanPass(bpy.types.PropertyGroup):

    name                  = StringProperty(name="")
    type                  = EnumProperty(name="Pass Type",
                    items=[
                        ('SHADOW_MAPS_ALL', 'All Shadow Map', 'Single shadow map'),
                        ('SHADOW_MAP', 'Shadow Map', 'Single shadow map'),
                        ('POINTCLOUD', 'Point Cloud', '')],
                            default='SHADOW_MAPS_ALL')
    motion_blur           = BoolProperty(name="Motion Blur")
    surface_shaders       = BoolProperty(name="Surface Shaders", description="Render surface shaders")
    displacement_shaders  = BoolProperty(name="Displacement Shaders", description="Render displacement shaders")
    atmosphere_shaders    = BoolProperty(name="Atmosphere Shaders", description="Render atmosphere shaders")
    light_shaders         = BoolProperty(name="Light Shaders", description="Render light shaders")



class RendermanSceneSettings(bpy.types.PropertyGroup):


    pixelsamples_x = IntProperty(
                name="Pixel Samples X",
                description="Number of AA samples to take in X dimension",
                min=0, max=16, default=2)
    pixelsamples_y = IntProperty(
                name="Pixel Samples Y",
                description="Number of AA samples to take in Y dimension",
                min=0, max=16, default=2)

    pixelfilter = EnumProperty(
                name="Pixel Filter",
                description="Filter to use to combine pixel samples",
                items=[('box', 'Box', ''),
                        ('sinc', 'Sinc', '')],
                default='sinc')
    pixelfilter_x = IntProperty(
                name="Filter Size X",
                description="Size of the pixel filter in X dimension",
                min=0, max=16, default=2)
    pixelfilter_y = IntProperty(
                name="Filter Size Y",
                description="Size of the pixel filter in X dimension",
                min=0, max=16, default=2)

    shadingrate = FloatProperty(
                name="Shading Rate",
                description="Maximum distance between shading samples (lower = more detailed shading)",
                default=1.0)

    motion_blur = BoolProperty(
                name="Motion Blur",
                description="Enable motion blur",
                default=False)
    motion_segments = IntProperty(
                name="Motion Segments",
                description="Number of motion segments to take for multi-segment motion blur",
                min=1, max=16, default=1)
    shutter_open = FloatProperty(
                name="Shutter Open",
                description="Shutter open time",
                default=0.0)
    shutter_close = FloatProperty(
                name="Shutter Close",
                description="Shutter close time",
                default=1.0)
                
    shutter_efficiency_open = FloatProperty(
                name="Open Efficiency",
                description="Shutter open efficiency - controls the shape of the shutter opening and closing for motion blur",
                default=0.5)
    shutter_efficiency_close = FloatProperty(
                name="Close Efficiency",
                description="Shutter close efficiency - controls the shape of the shutter opening and closing for motion blur",
                default=0.5)

    depth_of_field = BoolProperty(
                name="Depth of Field",
                description="Enable depth of field blur",
                default=False)
    fstop = FloatProperty(
                name="F-Stop",
                description="Aperture size for depth of field",
                default=4.0)


    threads = IntProperty(
                name="Threads",
                description="Number of processor threads to use",
                min=1, max=32, default=2)
    max_trace_depth = IntProperty(
                name="Max Trace Depth",
                description="Maximum number of ray bounces (0 disables ray tracing)",
                min=0, max=32, default=4)
    max_specular_depth = IntProperty(
                name="Max Specular Depth",
                description="Maximum number of specular ray bounces",
                min=0, max=32, default=2)
    max_diffuse_depth = IntProperty(
                name="Max Diffuse Depth",
                description="Maximum number of diffuse ray bounces",
                min=0, max=32, default=2)
    max_eye_splits = IntProperty(
                name="Max Eye Splits",
                description="Maximum number of times a primitive crossing the eye plane is split before being discarded",
                min=0, max=32, default=6)
    trace_approximation = FloatProperty(
                name="Raytrace Approximation",
                description="Threshold for using approximated geometry during ray tracing. Higher values use more approximated geometry.",
                min=0.0, max=1024.0, default=10.0)
    use_statistics = BoolProperty(
                name="Statistics",
                description="Print statistics to /tmp/stats.txt after render",
                default=False)
    statistics_level = IntProperty(
                name="Statistics Level",
                description="Verbosity level of output statistics",
                min=0, max=3, default=1)

    recompile_shaders = BoolProperty(
                name="Recompile Shaders",
                description="Recompile used shaders at export time to the current 3Delight version. Prevents version mismatch errors at the expense of export speed",
                default=True)


    # RIB output properties

    path_rib_output = StringProperty(
                name="RIB Output Path",
                description="Path to generated .rib files",
                subtype='FILE_PATH',
                default="$OUT/{scene}.rib")
    
    output_action = EnumProperty(
                name="Action",
                description="Action to take when rendering",
                items=[('EXPORT_RENDER', 'Export RIB and Render', 'Generate RIB file and render it with the renderer'),
                    ('EXPORT', 'Export RIB Only', 'Generate RIB file only')],
                default='EXPORT_RENDER')

    '''
    def display_driver_update(self, context):
        if self.output_action = "custom":
            # For safety, we keep the active shader property separate as a string property,
            # and update when chosen from the shader list
            self.active = str(self.shader_list)    
    '''
    
    def display_driver_items(self, context):
        if self.output_action == 'EXPORT_RENDER':
            items = [('AUTO', 'Automatic', 'Render to a temporary file, to be read back into Blender\'s Render Result'),
                    ('idisplay', 'idisplay', 'External 3Delight framebuffer display')]
        elif self.output_action == 'EXPORT':
            items = [('tiff', 'Tiff', '')]
                    #('openexr', 'OpenEXR', '')]
        return items
        
    display_driver = EnumProperty(
                name="Display Driver",
                description="Renderman display driver destination for output pixels",
                items=display_driver_items)
    
    path_display_driver_image = StringProperty(
                name="Display Image",
                description="Render output path to export as the Display in the RIB file. When later rendering the RIB file manually, this will be the raw render result directly from the renderer, and won't pass through blender's render pipeline",
                subtype='FILE_PATH',
                default="$OUT/renders/{scene}_####.tif")
    
    
    # Hider properties
    hider = EnumProperty(
                name="Hider",
                description="Algorithm to use for determining hidden surfaces",
                items=[('hidden', 'Hidden', 'Default hidden surface method'),
                        ('raytrace', 'Raytrace', 'Use ray tracing on the first hit'),
                        ('photon', 'Photon', 'Generate a photon map')],
                default='hidden')
    
    hidden_depthfilter = EnumProperty(
                name="Depth Filter",
                description="Method used for determining sample depth",
                items=[('min', 'Min', 'Minimum z value of all the sub samples in a given pixel'),
                        ('max', 'Max', 'Maximum z value of all the sub samples in a given pixel'),
                        ('average', 'Average', 'Average all sub samples’ z values in a given pixel'),
                        ('midpoint', 'Midpoint', 'For each sub sample in a pixel, the renderer takes the average z value of the two closest surfaces')],
                default='min')

    hidden_jitter = BoolProperty(
                name="Jitter",
                description="Use a jittered grid for sampling",
                default=True)

    hidden_samplemotion = BoolProperty(
                name="Sample Motion",
                description="Disabling this will not render motion blur, but still preserve motion vector information (dPdtime)",
                default=True)
                
    hidden_extrememotiondof = BoolProperty(
                name="Extreme Motion/DoF",
                description="Use a more accurate, but slower algorithm to sample motion blur and depth of field effects. This is useful to fix artifacts caused by extreme amounts of motion or DoF",
                default=False)

    hidden_midpointratio = FloatProperty(
                name="Midpoint Ratio",
                description="Amount of blending between the z values of the first two samples when using the midpoint depth filter",
                default=0.5)

    hidden_maxvpdepth = IntProperty(
                name="Max Visible Point Depth",
                description="The number of visible points to be composited in the hider or included in deep shadow map creation. Putting a limit on the number of visible points can accelerate deep shadow map creation for depth-complex scenes. The default value of -1 means no limit",
                min=-1, max=1024, default=-1)

    raytrace_progressive = BoolProperty(
                name="Progressive Rendering",
                description="Enables progressive rendering. This is only visible with some display drivers (such as idisplay)",
                default=False)
	
    # Rib Box Properties
    bty_inlinerib_texts = CollectionProperty(type=RendermanInlineRIB, name="Beauty-pass Inline RIB")
    bty_inlinerib_index = IntProperty(min=-1, default=-1)
	
	
    bak_inlinerib_texts = CollectionProperty(type=RendermanInlineRIB, name="Bake-pass Inline RIB")
    bak_inlinerib_index = IntProperty(min=-1, default=-1)
    
	
	# Trace Sets (grouping membership)
    grouping_membership = CollectionProperty(type=RendermanGrouping, name="Trace Sets")
    grouping_membership_index = IntProperty(min=-1, default=-1)
                
                
    
    shader_paths = CollectionProperty(type=RendermanPath, name="Shader Paths")
    shader_paths_index = IntProperty(min=-1, default=-1)

    texture_paths = CollectionProperty(type=RendermanPath, name="Texture Paths")
    texture_paths_index = IntProperty(min=-1, default=-1)

    procedural_paths = CollectionProperty(type=RendermanPath, name="Procedural Paths")
    procedural_paths_index = IntProperty(min=-1, default=-1)

    archive_paths = CollectionProperty(type=RendermanPath, name="Archive Paths")
    archive_paths_index = IntProperty(min=-1, default=-1)


    use_default_paths = BoolProperty(
                name="Use 3Delight default paths",
                description="Includes paths for default shaders etc. from 3Delight install",
                default=False)
    use_builtin_paths = BoolProperty(
                name="Use built in paths",
                description="Includes paths for default shaders etc. from Blender->3Delight exporter",
                default=True)

    path_3delight = StringProperty(
                name="3Delight Path",
                description="Path to 3Delight installation folder",
                subtype='DIR_PATH',
                default=guess_3dl_path())
    path_renderer = StringProperty(
                name="Renderer Path",
                description="Path to renderer executable",
                subtype='FILE_PATH',
                default="renderdl")
    path_shader_compiler = StringProperty(
                name="Shader Compiler Path",
                description="Path to shader compiler executable",
                subtype='FILE_PATH',
                default="shaderdl")
    path_shader_info = StringProperty(
                name="Shader Info Path",
                description="Path to shaderinfo executable",
                subtype='FILE_PATH',
                default="shaderinfo")
    path_texture_optimiser = StringProperty(
                name="Texture Optimiser Path",
                description="Path to tdlmake executable",
                subtype='FILE_PATH',
                default="tdlmake")

    render_passes = CollectionProperty(type=RendermanPass, name="Render Passes")
    render_passes_index = IntProperty(min=-1, default=-1)






gi_primary_types = [
            ('gi_pointcloud', 'Point Cloud', ''),
            ('gi_raytrace', 'Ray Tracing', ''),
            ('gi_photon', 'Photon Map', '')
            ]

gi_secondary_types = [
            ('gi_photon', 'Photon Map', ''),
            ('none', 'None', '')
# XXX: multiple bounces            ('gi_raytrace', 'Ray Tracing', '')
            ]


class GIPrimaryShaders(bpy.types.PropertyGroup):
    active = EnumProperty(
                name="Primary GI Method",
                description="GI method for primary bounces",
                items=gi_primary_types,
                default=gi_primary_types[0][0])
                
class GISecondaryShaders(bpy.types.PropertyGroup):
    active = EnumProperty(
                name="Secondary GI Method",
                description="GI method for secondary bounces",
                items=gi_secondary_types,
                default=gi_secondary_types[1][0])

class IntegratorShaders(bpy.types.PropertyGroup):
    active = EnumProperty(
                name="Integrator",
                description="Integrator to use for light calculation",
                items=[('integrator', 'Ray Tracing Integrator', '')],
                default='integrator')


class RendermanGIPrimary(bpy.types.PropertyGroup):

    light_shaders = PointerProperty(
                type=GIPrimaryShaders, name="Primary GI Shader Settings")

class RendermanGISecondary(bpy.types.PropertyGroup):
    
    light_shaders = PointerProperty(
                type=GISecondaryShaders, name="Secondary GI Shader Settings")

class RendermanIntegrator(bpy.types.PropertyGroup):
    
    surface_shaders = PointerProperty(
                type=IntegratorShaders, name="Integrator Shader Settings")


# Photon Secondary bounce (render) properties
    photon_count = IntProperty(
                name="Photon Count",
                description="Number of photons to emit",
                default=10000)
    photon_map_global = StringProperty(
                name="Global Photon Map",
                description="Name of gloabl photon map",
                default="DefaultGlobal")
    photon_map_caustic = StringProperty(
                name="Global Caustic Map",
                description="Name of gloabl caustics map",
                default="DefaultCaustic")
    
    ptc_generate_auto = BoolProperty(
                name="Generate Point Cloud Automatically",
                description="Generate a point cloud before each render, when point cloud global illumation is enabled",
                default=True)
    ptc_path = StringProperty(
                name="Point Cloud Path",
                description="Path to the temporary pointcloud file",
                default="$PTC/{scene}.ptc",
                subtype='FILE_PATH')
    ptc_coordsys = StringProperty(
                name="Point Cloud Coordinate system",
                description="Coordinate system to bake the point cloud in",
                default="world")
    ptc_shadingrate = FloatProperty(
                name="Point Cloud Shading Rate",
                description="Controls the amount of fine detail in the baked point cloud",
                default=6)
                

class RendermanWorldSettings(bpy.types.PropertyGroup):

    atmosphere_shaders = PointerProperty(
                type=atmosphereShaders, name="Atmosphere Shader Settings")
  
    global_illumination = BoolProperty(
                name="Global Illumination",
                description="",
                default=False)

    gi_primary = PointerProperty(
                type=RendermanGIPrimary, name="Primary GI Settings")
    
    gi_secondary = PointerProperty(
                type=RendermanGISecondary, name="Secondary GI Settings")

    integrator = PointerProperty(
                type=RendermanIntegrator, name="Integrator Settings")
	
    # BBM addition begin
    #coshaders = CollectionProperty(type=RendermanCoshader, name="World Co-Shaders")
    #coshaders_index = IntProperty(min=-1, default=-1)
	# BBM addition end

class RendermanMaterialSettings(bpy.types.PropertyGroup):
    
    nodetree = StringProperty(
                name="Node Tree",
                description="Name of the shader node tree for this material",
                default="")

    surface_shaders = PointerProperty( 
                type=surfaceShaders,
                name="Surface Shader Settings")

    displacement_shaders = PointerProperty(
                type=displacementShaders,
                name="Displacement Shader Settings")

    interior_shaders = PointerProperty(
                type=interiorShaders,
                name="Interior Shader Settings")

    atmosphere_shaders = PointerProperty(
                type=atmosphereShaders,
                name="Atmosphere Shader Settings")
	
    #coshaders = CollectionProperty(type=RendermanCoshader, name="Material Co-Shaders")
    #coshaders_index = IntProperty(min=-1, default=-1)
	

    displacementbound = FloatProperty(
                name="Displacement Bound",
                description="Maximum distance the displacement shader can displace vertices",
                precision=4,
                default=0.5)

    photon_shadingmodel = EnumProperty(
                name="Photon Shading Model",
                description="How the object appears to photons",
                items=[('matte', 'Matte', 'Diffuse reflection'),
                    ('chrome', 'Chrome', 'Perfect specular reflection'),
                    ('water', 'Water', 'Perfect specular transmission'),
                    ('glass', 'Glass', 'Perfect specular reflection/transmission'),
                    ('transparent', 'Transparent', 'Pass through photons without refraction')], 
                default='matte')

    inherit_world_atmosphere = BoolProperty(
                name="Inherit from World",
                description="Override this material's atmosphere shader with the world atmosphere shader",
                default=True)

    preview_render_type = EnumProperty(
                name="Preview Render Type",
                description="Object to display in material preview",
                items=[('SPHERE', 'Sphere', ''),
                    ('CUBE', 'Cube', '')],
                default='SPHERE')
    preview_render_shadow = BoolProperty(
                name="Display Shadow",
                description="Render a raytraced shadow in the material preview",
                default=True)


    # SSS Baking properties
    sss_do_bake = BoolProperty(
                name="Bake Subsurface Scattering",
                description="Bake this object/group to a point cloud for SSS computation",
                default=False)
    sss_scale = FloatProperty(
                name="Scale",
                description="Conversion factor from scene scale to sss parameters (defined in millimetres)",
                precision=4,
                default=0.001)
    sss_ior = FloatProperty(
                name="IOR",
                description="Index of refraction (higher values are denser)",
                default=1.3)
    sss_meanfreepath = FloatVectorProperty(
                name="Radius",
                description="The average distance that light will travel in the medium",
                subtype="COLOR",
                size=3,
                default=[1.0,1.0,1.0])
    sss_use_reflectance = BoolProperty(
                name="Use SSS Reflectance",
                description="Override default diffuse color with this color for SSS calculations",
                default=False)
    sss_reflectance = FloatVectorProperty(
                name="Reflectance",
                description="Diffuse reflectance",
                subtype="COLOR",
                size=3,
                min=0,
                max=0.99,
                default=[0.8,0.8,0.8])
    sss_shadingrate = FloatProperty(
                name="SSS Shading Rate",
                description="Controls the amount of irradiance samples taken during the precomputation phase",
                default=8)
    sss_group = StringProperty(
                name="Subsurface Group",
                description="Define a group of objects to be considered as the one solid object for SSS calculation. Default empty: this material only",
                default="")

class RendermanAnimSequenceSettings(bpy.types.PropertyGroup):
    animated_sequence = BoolProperty(
                name="Animated Sequence",
                description="Interpret this texture as an animated sequence (converts #### in file path to frame number)",
                default=False)
    sequence_in = IntProperty(
                name="Sequence In Point",
                description="The first numbered image file to use",
                default=1)
    sequence_out = IntProperty(
                name="Sequence Out Point",
                description="The last numbered image file to use",
                default=24)
    blender_start = IntProperty(
                name="Blender Start Frame",
                description="The frame in Blender to begin playing back the sequence",
                default=1)
    '''
    extend_in = EnumProperty(
                name="Extend In",
                items=[('HOLD', 'Hold', ''),
                    ('LOOP', 'Loop', ''),
                    ('PINGPONG', 'Ping-pong', '')],
                default='HOLD')
    extend_out = EnumProperty(
                name="Extend In",
                items=[('HOLD', 'Hold', ''),
                    ('LOOP', 'Loop', ''),
                    ('PINGPONG', 'Ping-pong', '')],
                default='HOLD')
    '''


class RendermanTextureSettings(bpy.types.PropertyGroup):
    # animation settings

    anim_settings = PointerProperty(
                type=RendermanAnimSequenceSettings,
                name="Animation Sequence Settings")
    
    # texture optimiser settings
    '''
    type = bpy.props.EnumProperty(
                name="Data type",
                description="Type of external file",
                items=[('NONE', 'None', ''),
                    ('IMAGE', 'Image', ''),
                    ('POINTCLOUD', 'Point Cloud', '')],
                default='NONE')
    '''
    format = bpy.props.EnumProperty(
                name="Format",
                description="Image representation",
                items=[('TEXTURE', 'Texture Map', ''),
                    ('ENV_LATLONG', 'LatLong Environment Map', '')
                    ],
                default='TEXTURE')
    auto_generate_texture = BoolProperty(
                name="Auto-Generate Optimized",
                description="Use the texture optimiser to convert image for rendering",
                default=False)
    file_path = StringProperty(
                name="Source File Path",
                description="Path to original image",
                subtype='FILE_PATH',
                default="")
    wrap_s = EnumProperty(
                name="Wrapping S",
                items=[('black', 'Black', ''),
                    ('clamp', 'Clamp', ''),
                    ('periodic', 'Periodic', '')],
                default='clamp')
    wrap_t = EnumProperty(
                name="Wrapping T",
                items=[('black', 'Black', ''),
                    ('clamp', 'Clamp', ''),
                    ('periodic', 'Periodic', '')],
                default='clamp')
    flip_s = BoolProperty(
                name="Flip S",
                description="Mirror the texture in S",
                default=False)
    flip_t = BoolProperty(
                name="Flip T",
                description="Mirror the texture in T",
                default=False)


    filter_type = EnumProperty(
                name="Downsampling Filter",
                items=[('DEFAULT', 'Default', ''),
                    ('box', 'Box', ''),
                    ('triangle', 'Triangle', ''),
                    ('gaussian', 'Gaussian', ''),
                    ('sinc', 'Sinc', ''),
                    ('catmull-rom', 'Catmull-Rom', ''),
                    ('bessel', 'Bessel', '')],
                default='DEFAULT',
                description='Downsampling filter for generating mipmaps')
    filter_window = EnumProperty(
                name="Filter Window",
                items=[('DEFAULT', 'Default', ''),
                    ('lanczos', 'Lanczos', ''),
                    ('hamming', 'Hamming', ''),
                    ('hann', 'Hann', ''),
                    ('blackman', 'Blackman', '')],
                default='DEFAULT',
                description='Downsampling filter window for infinite support filters')

    filter_width_s = FloatProperty(
                name="Filter Width S",
                description="Filter diameter in S",
                min=0.0, soft_max=1.0, default=1.0)
    filter_width_t = FloatProperty(
                name="Filter Width T",
                description="Filter diameter in T",
                min=0.0, soft_max=1.0, default=1.0)
    filter_blur = FloatProperty(
                name="Filter Blur",
                description="Blur factor: > 1.0 is blurry, < 1.0 is sharper",
                min=0.0, soft_max=1.0, default=1.0)

    input_color_space = EnumProperty(
                name="Input Color Space",
                items=[('srgb', 'sRGB', ''),
                    ('linear', 'Linear RGB', ''),
                    ('GAMMA', 'Gamma', '')],
                default='srgb',
                description='Color space of input image')
    input_gamma = FloatProperty(
                name="Input Gamma",
                description="Gamma value of input image if using gamma color space",
                min=0.0, soft_max=3.0, default=2.2)
                
    output_color_depth = EnumProperty(
                name="Output Color Depth",
                items=[('UBYTE', '8-bit unsigned', ''),
                    ('SBYTE', '8-bit signed', ''),
                    ('USHORT', '16-bit unsigned', ''),
                    ('SSHORT', '16-bit signed', ''),
                    ('FLOAT', '32 bit float', '')],
                default='UBYTE',
                description='Color depth of output image')
                
    output_compression = EnumProperty(
                name="Output Compression",
                items=[('LZW', 'LZW', ''),
                    ('ZIP', 'Zip', ''),
                    ('PACKBITS', 'PackBits', ''),
                    ('LOGLUV', 'LogLUV (float only)', ''),
                    ('UNCOMPRESSED', 'Uncompressed', '')],
                default='ZIP',
                description='Compression of output image data')
                
    generate_if_nonexistent = BoolProperty(
                name="Generate if Non-existent",
                description="Generate if optimised image does not exist in the same folder as source image path",
                default=True)
    generate_if_older = BoolProperty(
                name="Generate if Optimised is Older",
                description="Generate if optimised image is older than corresponding source image",
                default=True)

class RendermanLightSettings(bpy.types.PropertyGroup):

    nodetree = StringProperty(
                name="Node Tree",
                description="Name of the shader node tree for this light",
                default="")

    light_shaders = PointerProperty(
                type=lightShaders,
                name="Light Shader Settings")

    emit_photons = BoolProperty(
                name="Emit Photons",
                description="Emit Photons from this light source",
                default=True)

    shadow_method = EnumProperty(
                name="Shadow Method",
                description="How to calculate shadows",
                items=[('NONE', 'None', 'No Shadows'),
                    ('SHADOW_MAP', 'Shadow Map', 'Shadow Map'),
                    ('RAYTRACED', 'Raytraced', 'Raytraced')],
                default='SHADOW_MAP')

    path_shadow_map = StringProperty(
                name="Shadow Map Path",
                description="Path to generated shadow maps",
                subtype='FILE_PATH',
                default="$SHD/{object}")

    shadow_map_generate_auto = BoolProperty(
                name="Generate Shadow Map Automatically",
                description="Generate a shadow map for this light before each render, when shadow maps are enabled",
                default=True)

    shadow_transparent = BoolProperty(
                name="Transparent shadows",
                description="Use deep shadow maps",
                default=True)
    
    shadow_map_resolution = IntProperty(
                name="Shadow Map Resolution",
                description="Size of the generated shadow map in pixels",
                default=256)

    pixelsamples_x = IntProperty(
                name="Pixel Samples X",
                description="Number of AA shadow map samples to take in X dimension",
                min=0, max=16, default=2)

    pixelsamples_y = IntProperty(
                name="Pixel Samples Y",
                description="Number of AA shadow map samples to take in Y dimension",
                min=0, max=16, default=2)

    shadingrate = FloatProperty(
                name="Shading Rate",
                description="Maximum distance between shading samples when rendering a shadow map (lower = more detailed shading)",
                default=1.0)         

    ortho_scale = FloatProperty(
                name="Ortho Scale",
                description="Scale factor for orthographic shadow maps",
                default=1.0)
				
    # Rib Box Properties
    shd_inlinerib_texts = CollectionProperty(type=RendermanInlineRIB, name='Shadow map pass Inline RIB')
    shd_inlinerib_index = IntProperty(min=-1, default=-1)
	
	# illuminate
    illuminates_by_default = BoolProperty(
                name="Illuminates by default",
                description="Illuminates by default",
                default=True)

    
	# BBM addition begin
    #coshaders = CollectionProperty(type=RendermanCoshader, name="Light Co-Shaders")
    #coshaders_index = IntProperty(min=-1, default=-1)
	# BBM addition end


class RendermanMeshPrimVar(bpy.types.PropertyGroup):
    name = StringProperty(
                name="Variable Name",
                description="Name of the exported renderman primitive variable")
    data_name = StringProperty(
                name="Data Name",
                description="Name of the Blender data to export as the primitive variable")
    data_source = EnumProperty(
                name="Data Source",
                description="Blender data type to export as the primitive variable",
                items=[('VERTEX_GROUP', 'Vertex Group', ''),
                    ('VERTEX_COLOR', 'Vertex Color', ''),
                    ('UV_TEXTURE', 'UV Texture', '')
                    ]
                    )

class RendermanParticlePrimVar(bpy.types.PropertyGroup):
    name = StringProperty(
                name="Variable Name",
                description="Name of the exported renderman primitive variable")
    data_source = EnumProperty(
            name="Data Source",
            description="Blender data type to export as the primitive variable",
            items= [('SIZE', 'Size', ''),
                    ('VELOCITY', 'Velocity', ''),
                    ('ANGULAR_VELOCITY', 'Angular Velocity', ''),
                    ('AGE', 'Age', ''),
                    ('BIRTH_TIME', 'Birth Time', ''),
                    ('DIE_TIME', 'Die Time', ''),
                    ('LIFE_TIME', 'Lifetime', '')
                    ]   # XXX: Would be nice to have particle ID, needs adding in RNA
                    )

class RendermanParticleSettings(bpy.types.PropertyGroup):

    material_id = IntProperty(
                name="Material",
                description="Material ID to use for particle shading",
                default=1)

    particle_type_items = [('particle', 'Particle', 'Point primitive'),
                    ('blobby', 'Blobby', 'Implicit Surface (metaballs)'),
                    ('sphere', 'Sphere', 'Two-sided sphere primitive'),
                    ('disk', 'Disk', 'One-sided disk primitive'),
                    ('OBJECT', 'Object', 'Instanced objects at each point')
                    ]

    particle_type = EnumProperty(
                name="Point Type",
                description="Geometric primitive for points to be rendered as",
                items=particle_type_items, 
                default='particle')
    particle_instance_object = StringProperty(
                name="Instance Object",
                description="Object to instance on every particle",
                default="")

    constant_width = BoolProperty(
                name="Constant Width",
                description="Override particle sizes with constant width value",
                default=True)

    width = FloatProperty(
                name="Width",
                description="With used for constant width across all particles",
                precision=4,
                default=0.05)

    export_default_size = BoolProperty(
                name="Export Default size",
                description="Export the particle size as the default 'width' primitive variable",
                default=True)

    prim_vars = CollectionProperty(type=RendermanParticlePrimVar, name="Primitive Variables")
    prim_vars_index = IntProperty(min=-1, default=-1)


class RendermanMeshGeometrySettings(bpy.types.PropertyGroup):
    export_default_uv = BoolProperty(
                name="Export Default UVs",
                description="Export the active UV set as the default 'st' primitive variable",
                default=True)
    export_default_vcol = BoolProperty(
                name="Export Default Vertex Color",
                description="Export the active Vertex Color set as the default 'Cs' primitive variable",
                default=True)
    export_smooth_normals = BoolProperty(
                name="Export Smooth Normals",
                description="Export smooth per-vertex normals for PointsPolygons Geometry",
                default=False)

    prim_vars = CollectionProperty(type=RendermanMeshPrimVar, name="Primitive Variables")
    prim_vars_index = IntProperty(min=-1, default=-1)

class RendermanCurveGeometrySettings(bpy.types.PropertyGroup):
    '''
    export_default_uv = BoolProperty(
                name="Export Default UVs",
                description="Export the active UV set as the default 'st' primitive variable",
                default=True)
    export_default_vcol = BoolProperty(
                name="Export Default Vertex Color",
                description="Export the active Vertex Color set as the default 'Cs' primitive variable",
                default=True)
    export_smooth_normals = BoolProperty(
                name="Export Smooth Normals",
                description="Export smooth per-vertex normals for PointsPolygons Geometry",
                default=True)

    prim_vars = CollectionProperty(type=RendermanMeshPrimVar, name="Primitive Variables")
    prim_vars_index = IntProperty(min=-1, default=-1)
    '''
         
class RendermanObjectSettings(bpy.types.PropertyGroup):

    geometry_source = EnumProperty(
                name="Geometry Source",
                description="Where to get the geometry data for this object",
                items=[('BLENDER_SCENE_DATA', 'Blender Scene Data', 'Exports and renders blender scene data directly from memory'),
                        ('ARCHIVE', 'Archive', 'Renders a prevously exported RIB archive'),
                        ('DELAYED_LOAD_ARCHIVE', 'Delayed Load Archive', 'Loads and renders geometry from an archive only when its bounding box is visible'),
                        ('PROCEDURAL_RUN_PROGRAM', 'Procedural Run Program', 'Generates procedural geometry at render time from an external program'),
                        ('DYNAMIC_LOAD_DSO', 'Dynamic Load DSO', 'Generates procedural geometry at render time from a dynamic shared object library')
                        ],
                default='BLENDER_SCENE_DATA')
    
    archive_anim_settings = PointerProperty(
                type=RendermanAnimSequenceSettings,
                name="Animation Sequence Settings")
    
    path_archive = StringProperty(
                name="Archive Path",
                description="Path to archive file",
                subtype='FILE_PATH',
                default="")
                
    procedural_bounds = EnumProperty(
                name="Procedural Bounds",
                description="The bounding box of the renderable geometry",
                items=[ ('BLENDER_OBJECT', 'Blender Object', "Use the blender object's bounding box for the archive's bounds"),
                        ('MANUAL', 'Manual', 'Manually enter the bounding box coordinates')
                        ],
                default="BLENDER_OBJECT")

    path_runprogram = StringProperty(
                name="Program Path",
                description="Path to external program",
                subtype='FILE_PATH',
                default="")
    path_runprogram_args = StringProperty(
                name="Program Arguments",
                description="Command line arguments to external program",
                default="")
    path_dso = StringProperty(
                name="DSO Path",
                description="Path to DSO library file",
                subtype='FILE_PATH',
                default="")
    path_dso_initial_data = StringProperty(
                name="DSO Initial Data",
                description="Parameters to send the DSO",
                default="")
    procedural_bounds_min = FloatVectorProperty(
                name="Min Bounds",
                description="Minimum corner of bounding box for this procedural geometry",
                size=3,
                default=[0.0,0.0,0.0])
    procedural_bounds_max = FloatVectorProperty(
                name="Max Bounds",
                description="Maximum corner of bounding box for this procedural geometry",
                size=3,
                default=[1.0,1.0,1.0])
                
    
    primitive = EnumProperty(
                name="Primitive Type",
                description="Representation of this object's geometry in the renderer",
                items=[('AUTO', 'Automatic', 'Automatically determine the object type from context and modifiers used'),
                        ('POLYGON_MESH', 'Polygon Mesh', 'Mesh object'),
                        ('SUBDIVISION_MESH', 'Subdivision Mesh', 'Smooth subdivision surface formed by mesh cage'),
                        ('POINTS', 'Points', 'Renders object vertices as single points'),
                        ('SPHERE', 'Sphere', 'Parametric sphere primitive'),
                        ('CYLINDER', 'Cylinder', 'Parametric cylinder primitive'),
                        ('CONE', 'Cone', 'Parametric cone primitive'),
                        ('DISK', 'Disk', 'Parametric 2D disk primitive'),
                        ('TORUS', 'Torus', 'Parametric torus primitive')
                        ],
                default='AUTO')

    export_archive = BoolProperty(
                name="Export as Archive",
                description="At render export time, store this object as a RIB archive",
                default=False)
    export_archive_path = StringProperty(
                name="Archive Export Path",
                description="Path to automatically save this object as a RIB archive",
                subtype='FILE_PATH',
                default="")
                
    primitive_radius = FloatProperty(
                name="Radius",
                default=1.0)
    primitive_zmin = FloatProperty(
                name="Z min",
                description="Minimum height clipping of the primitive",
                default=-1.0)
    primitive_zmax = FloatProperty(
                name="Z max",
                description="Maximum height clipping of the primitive",
                default=1.0)
    primitive_sweepangle = FloatProperty(
                name="Sweep Angle",
                description="Angle of clipping around the Z axis",
                default=360.0)
    primitive_height = FloatProperty(
                name="Height",
                description="Height offset above XY plane",
                default=0.0)
    primitive_majorradius = FloatProperty(
                name="Major Radius",
                description="Radius of Torus ring",
                default=2.0)
    primitive_minorradius = FloatProperty(
                name="Minor Radius",
                description="Radius of Torus cross-section circle",
                default=0.5)
    primitive_phimin = FloatProperty(
                name="Minimum Cross-section",
                description="Minimum angle of cross-section circle",
                default=0.0)
    primitive_phimax = FloatProperty(
                name="Maximum Cross-section",
                description="Maximum angle of cross-section circle",
                default=360.0)
    primitive_point_type = EnumProperty(
                name="Point Type",
                description="Geometric primitive for points to be rendered as",
                items=[('particle', 'Particle', 'Point primitive'),
                    ('blobby', 'Blobby', 'Implicit Surface (metaballs)'),
                    ('sphere', 'Sphere', 'Two-sided sphere primitive'),
                    ('disk', 'Disk', 'One-sided disk primitive')
                    ], 
                default='particle')
    primitive_point_width = FloatProperty(
                name="Point Width",
                description="Size of the rendered points",
                default=0.1)

    shadingrate_override = BoolProperty(
                name="Override Shading Rate",
                description="Override the global shading rate for this object",
                default=False)
    shadingrate = FloatProperty(
                name="Shading Rate",
                description="Maximum distance between shading samples (lower = more detailed shading)",
                default=1.0)
    geometric_approx_motion = FloatProperty(
                name="Motion Approximation",
                description="Shading Rate is scaled up by motionfactor/16 times the number of pixels of motion",
                default=1.0)
    geometric_approx_focus = FloatProperty(
                name="Focus Approximation",
                description="Shading Rate is scaled proportionally to the radius of DoF circle of confusion, multiplied by this value",
                default=1.0)

    motion_segments_override = BoolProperty(
                name="Override Motion Segments",
                description="Override the global number of motion segments for this object",
                default=False)
    motion_segments = IntProperty(
                name="Motion Segments",
                description="Number of motion segments to take for multi-segment motion blur",
                min=1, max=16, default=1)
                
    shadinginterpolation = EnumProperty(
                name="Shading Interpolation",
                description="Method of interpolating shade samples across micropolygons",
                items=[('constant', 'Constant', 'Flat shaded micropolygons'),
                        ('smooth', 'Smooth', 'Gourard shaded micropolygons')],
                default='smooth')

    matte = BoolProperty(
                name="Matte Object",
                description="Render the object as a matte cutout (alpha 0.0 in final frame)",
                default=False)
    visibility_camera = BoolProperty(
                name="Visible to Camera",
                description="Visibility to Camera",
                default=True)
    visibility_trace_diffuse = BoolProperty(
                name="Visible to Diffuse Rays",
                description="Visibility to Diffuse Rays (eg. gather(), indirectdiffuse() and occlusion())",
                default=True)
    trace_diffuse_hitmode = EnumProperty(
                name="Diffuse Hit Mode",
                description="How the surface calculates are result when hit by diffuse rays",
                items=[('primitive', 'Primitive', 'Returns the un-shaded primitive object color (Cs)'),
                        ('shader', 'Shader', 'Runs the object\'s shader to return a color (Ci)')],
                default='shader')
    visibility_trace_specular = BoolProperty(
                name="Visible to Specular Rays",
                description="Visibility to Specular Rays (eg. gather(), trace() and environment())",
                default=True)
    trace_specular_hitmode = EnumProperty(
                name="Diffuse Hit Mode",
                description="How the surface calculates are result when hit by diffuse rays",
                items=[('primitive', 'Primitive', 'Returns the un-shaded primitive object color (Cs)'),
                        ('shader', 'Shader', 'Runs the object\'s shader to return a color (Ci)')],
                default='shader')
    visibility_trace_transmission = BoolProperty(
                name="Visible to Transmission Rays",
                description="Visibility to Transmission Rays (eg. shadow() and transmission())",
                default=True)
    trace_transmission_hitmode = EnumProperty(
                name="Transmission Hit Mode",
                description="How the surface calculates are result when hit by diffuse rays",
                items=[('primitive', 'Primitive', 'Returns the un-shaded primitive object color (Cs)'),
                        ('shader', 'Shader', 'Runs the object\'s shader to return a color (Ci)')],
                default='shader')
    visibility_photons = BoolProperty(
                name="Visible to Photons",
                description="Visibility to Photons",
                default=True)
    visibility_shadowmaps = BoolProperty(
                name="Visible to Shadow Maps",
                description="Visibility to Shadow Maps",
                default=True)


    trace_displacements = BoolProperty(
                name="Trace Displacements",
                description="Enable high resolution displaced geometry for ray tracing",
                default=False)
                
    trace_samplemotion = BoolProperty(
                name="Trace Motion Blur",
                description="Rays cast from this object can intersect other motion blur objects",
                default=False)


    photon_reflectance = FloatVectorProperty(
                name="Photon Reflectance",
                description="Tint color for photon bounces",
                subtype="COLOR",
                size=3,
                default=[1.0,1.0,1.0])

    export_coordsys = BoolProperty(
                name="Export Coordinate System",
                description="Export a named coordinate system set to this object's name",
                default=False)
    coordsys = StringProperty(
                name="Coordinate System Name",
                description="Export a named coordinate system with this name",
                default="CoordSys")

    transmission_items = [('transparent', 'Transparent', 'Does not cast shadows on any other object'),
                        ('opaque', 'Opaque', 'Casts a shadow as a completely opaque object'),
                        ('Os', 'Opacity', 'Casts a shadow according to the opacity value (RiOpacity or Os)'),
                        ('shader', 'Shader', 'Casts shadows according to the opacity value computed by the surface shader')]
    transmission_default = 'opaque'
    transmission = EnumProperty(
                name="Transmission",
                description="How the object appears to transmission-like rays",
                items=transmission_items,
                default=transmission_default)
	
	# Light-Linking
    light_linking = CollectionProperty(type=LightLinking, name='Light Linking')
    light_linking_index = IntProperty(min=-1, default=-1)
    
    # Trace Sets
    trace_set = CollectionProperty(type=TraceSet, name='Trace Set')
    trace_set_index = IntProperty(min=-1, default=-1)

# collection of property group classes that need to be registered on module startup
classes = [atmosphereShaders,
            displacementShaders,
            surfaceShaders,
            interiorShaders,
            lightShaders,
            RendermanPath,
			RendermanInlineRIB,
            RendermanGrouping,
			LightLinking,
            TraceSet,
            RendermanPass,
            RendermanMeshPrimVar,
            RendermanParticlePrimVar,
            GIPrimaryShaders,
            GISecondaryShaders,
            IntegratorShaders,
            RendermanIntegrator,
            RendermanGIPrimary,
            RendermanGISecondary,
            RendermanMaterialSettings,
            RendermanAnimSequenceSettings,
            RendermanTextureSettings,
            RendermanLightSettings,
            RendermanParticleSettings,
            
            RendermanSceneSettings,
            RendermanWorldSettings,
            RendermanMeshGeometrySettings,
            RendermanCurveGeometrySettings,
            RendermanObjectSettings
           ]

def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.renderman = PointerProperty(
                type=RendermanSceneSettings, name="Renderman Scene Settings")
    bpy.types.World.renderman = PointerProperty(
                type=RendermanWorldSettings, name="Renderman World Settings")
    bpy.types.Material.renderman = PointerProperty(
                type=RendermanMaterialSettings, name="Renderman Material Settings")
    bpy.types.Texture.renderman = PointerProperty(
                type=RendermanTextureSettings, name="Renderman Texture Settings")
    bpy.types.Lamp.renderman = PointerProperty(
                type=RendermanLightSettings, name="Renderman Light Settings")
    bpy.types.ParticleSettings.renderman = PointerProperty(
                type=RendermanParticleSettings, name="Renderman Particle Settings")
    bpy.types.Mesh.renderman = PointerProperty(
                type=RendermanMeshGeometrySettings, name="Renderman Mesh Geometry Settings")
    bpy.types.Object.renderman = PointerProperty(
                type=RendermanObjectSettings, name="Renderman Object Settings")



def unregister():
    bpy.utils.unregister_module(__name__)
