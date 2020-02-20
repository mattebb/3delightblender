# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 - 2017 Pixar
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
import os
import sys
import xml.etree.ElementTree as ET
import time
from mathutils import Vector

from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty, BoolVectorProperty

from bpy.app.handlers import persistent
import traceback

from .rman_utils import filepath_utils
from .rfb_logger import rfb_log
from . import rman_render
from . import rman_bl_nodes
from .rman_bl_nodes import rman_bl_nodes_props

# Blender data
# --------------------------

class RendermanPath(bpy.types.PropertyGroup):
    name: StringProperty(
        name="", subtype='DIR_PATH')


class RendermanInlineRIB(bpy.types.PropertyGroup):
    name: StringProperty(name="Text Block")


class RendermanGroup(bpy.types.PropertyGroup):
    name: StringProperty(name="Group Name")
    members: CollectionProperty(type=bpy.types.PropertyGroup,
                                 name='Group Members')
    members_index: IntProperty(min=-1, default=-1)


class LightLinking(bpy.types.PropertyGroup):

    def update_link(self, context):
        pass
        """
        if engine.is_ipr_running():
            engine.ipr.update_light_link(context, self)
        """

    illuminate: EnumProperty(
        name="Illuminate",
        update=update_link,
        items=[
              ('DEFAULT', 'Default', ''),
               ('ON', 'On', ''),
               ('OFF', 'Off', '')])


class RendermanDspyChannel(bpy.types.PropertyGroup):

    def aov_list(self, context):
        items = [
            # (LPE, ID, Extra ID, no entry, sorting order)
            # Basic lpe
            ("", "Basic LPE's", "Basic LPE's", "", 0),
            #("color rgba", "rgba", "Combined (beauty)", "", 1),
            ("color Ci", "Ci", "Beauty", "", 1),
            ("color lpe:C[<.D><.S>][DS]*[<L.>O]",
             "All Lighting", "All Lighting", "", 2),
            ("color lpe:C<.D><L.>", "Diffuse", "Diffuse", "", 3),
            ("color lpe:(C<RD>[DS]+<L.>)|(C<RD>[DS]*O)",
             "IndirectDiffuse", "IndirectDiffuse", "", 4),
            ("color lpe:C<.S><L.>", "Specular", "Specular", "", 5),
            ("color lpe:(C<RS>[DS]+<L.>)|(C<RS>[DS]*O)",
             "IndirectSpecular", "IndirectSpecular", "", 6),
            ("color lpe:(C<TD>[DS]+<L.>)|(C<TD>[DS]*O)",
             "Subsurface", "Subsurface", "", 7),
            ("color lpe:C<RS>([DS]+<L.>)|([DS]*O)",
             "Reflection", "Reflection", "", 8),
            ("color lpe:(C<T[S]>[DS]+<L.>)|(C<T[S]>[DS]*O)",
             "Refraction", "Refraction", "", 9),
            ("color lpe:emission", "Emission", "Emission", "", 10),
            ("color lpe:shadows;C[<.D><.S>]<L.>",
             "Shadows", "Shadows", "", 11),
            ("color lpe:nothruput;noinfinitecheck;noclamp;unoccluded;overwrite;C(U2L)|O",
             "Albedo", "Albedo", "", 12),
            ("color lpe:C<.D>[S]+<L.>", "Caustics", "Caustics", "", 13),
            # Matte ID
            ("", "Matte ID's", "Matte ID's", "", 0),
            ("color MatteID0", "MatteID0", "MatteID0", "", 14),
            ("color MatteID1", "MatteID1", "MatteID1", "", 15),
            ("color MatteID2", "MatteID2", "MatteID2", "", 16),
            ("color MatteID3", "MatteID3", "MatteID3", "", 17),
            ("color MatteID4", "MatteID4", "MatteID4", "", 18),
            ("color MatteID5", "MatteID5", "MatteID5", "", 19),
            ("color MatteID6", "MatteID6", "MatteID6", "", 20),
            ("color MatteID7", "MatteID7", "MatteID7", "", 21),
            # PxrSurface lpe
            ("", "PxrSurface lobe LPE's", "PxrSurface lobe LPE's", "", 0),
            ("color lpe:C<.D2>[<L.>O]",
             "directDiffuseLobe", "", "", 22),
            ("color lpe:C<.D2>[DS]+[<L.>O]",
             "indirectDiffuseLobe", "", "", 23),
            ("color lpe:C<.D3>[DS]*[<L.>O]",
             "subsurfaceLobe", "", "", 24),
            ("color lpe:C<.S2>[<L.>O]",
             "directSpecularPrimaryLobe", "", "", 25),
            ("color lpe:C<.S2>[DS]+[<L.>O]",
             "indirectSpecularPrimaryLobe", "", "", 26),
            ("color lpe:C<.S3>[<L.>O]",
             "directSpecularRoughLobe", "", "", 27),
            ("color lpe:C<.S3>[DS]+[<L.>O]",
             "indirectSpecularRoughLobe", "", "", 28),
            ("color lpe:C<.S4>[<L.>O]",
             "directSpecularClearcoatLobe", "", "", 29),
            ("color lpe:C<.S4>[DS]+[<L.>O]",
             "indirectSpecularClearcoatLobe", "", "", 30),
            ("color lpe:C<.S5>[<L.>O]",
             "directSpecularIridescenceLobe", "", "", 31),
            ("color lpe:C<.S5>[DS]+[<L.>O]",
             "indirectSpecularIridescenceLobe", "", "", 32),
            ("color lpe:C<.S6>[<L.>O]",
             "directSpecularFuzzLobe", "", "", 33),
            ("color lpe:C<.S6>[DS]+[<L.>O]",
             "indirectSpecularFuzzLobe", "", "", 34),
            ("color lpe:C<.S7>[DS]*[<L.>O]",
             "transmissiveSingleScatterLobe", "", "", 35),
            ("color lpe:C<RS8>[<L.>O]",
             "directSpecularGlassLobe", "", "", 36),
            ("color lpe:C<RS8>[DS]+[<L.>O]",
             "indirectSpecularGlassLobe", "", "", 37),
            ("color lpe:C<TS8>[DS]*[<L.>O]",
             "transmissiveGlassLobe", "", "", 38),
            # Data AOV's
            ("", "Data AOV's", "Data AOV's", "", 0),
            ("float a", "a", "Alpha", "", 39),
            ("float id", "id", "Returns the integer assigned via the 'identifier' attribute as the pixel value", "", 40),
            ("float z", "z_depth", "Depth from the camera in world space", "", 41),
            ("float zback", "z_back",
             "Depth at the back of volumetric objects in world space", "", 42),
            ("point P", "P", "Position of the point hit by the incident ray", "", 43),
            ("float PRadius", "PRadius",
             "Cross-sectional size of the ray at the hit point", "", 44),
            ("float cpuTime", "cpuTime",
             "The time taken to render a pixel", "", 45),
            ("float sampleCount", "sampleCount",
             "The number of samples taken for the resulting pixel", "", 46),
            ("normal Nn", "Nn", "Normalized shading normal", "", 47),
            ("normal Ngn", "Ngn", "Normalized geometric normal", "", 48),
            ("vector Tn", "Tn", "Normalized shading tangent", "", 49),
            ("vector Vn", "Vn",
             "Normalized view vector (reverse of ray direction)", "", 50),
            ("float VLen", "VLen", "Distance to hit point along the ray", "", 51),
            ("float curvature", "curvature", "Local surface curvature", "", 52),
            ("float incidentRaySpread", "incidentRaySpread",
             "Rate of spread of incident ray", "", 53),
            ("float mpSize", "mpSize",
             "Size of the micropolygon that the ray hit", "", 54),
            ("float u", "u", "The parametric coordinates on the primitive", "", 55),
            ("float v", "v", "The parametric coordinates on the primitive", "", 56),
            ("float w", "w", "The parametric coordinates on the primitive", "", 57),
            ("float du", "du",
             "Derivatives of u, v, and w to adjacent micropolygons", "", 58),
            ("float dv", "dv",
             "Derivatives of u, v, and w to adjacent micropolygons", "", 59),
            ("float dw", "dw",
             "Derivatives of u, v, and w to adjacent micropolygons", "", 60),
            ("vector dPdu", "dPdu",
             "Direction of maximal change in u, v, and w", "", 61),
            ("vector dPdv", "dPdv",
             "Direction of maximal change in u, v, and w", "", 62),
            ("vector dPdw", "dPdw",
             "Direction of maximal change in u, v, and w", "", 63),
            ("float dufp", "dufp",
             "Multiplier to dPdu, dPdv, dPdw for ray differentials", "", 64),
            ("float dvfp", "dvfp",
             "Multiplier to dPdu, dPdv, dPdw for ray differentials", "", 65),
            ("float dwfp", "dwfp",
             "Multiplier to dPdu, dPdv, dPdw for ray differentials", "", 66),
            ("float time", "time", "Time sample of the ray", "", 67),
            ("vector dPdtime", "dPdtime", "Motion vector", "", 68),
            ("float id", "id", "Returns the integer assigned via the identifier attribute as the pixel value", "", 69),
            ("float outsideIOR", "outsideIOR",
             "Index of refraction outside this surface", "", 70),
            ("point __Pworld", "Pworld", "P in world-space", "", 71),
            ("normal __Nworld", "Nworld", "Nn in world-space", "", 72),
            ("float __depth", "depth", "Multi-purpose AOV\nr : depth from camera in world-space\ng : height in world-space\nb : geometric facing ratio : abs(Nn.V)", "", 73),
            ("float[2] __st", "st", "Texture coords", "", 74),
            ("point __Pref", "Pref",
             "Reference Position primvar (if available)", "", 75),
            ("normal __Nref", "Nref",
             "Reference Normal primvar (if available)", "", 76),
            ("point __WPref", "WPref",
             "Reference World Position primvar (if available)", "", 77),
            ("normal __WNref", "WNref",
             "Reference World Normal primvar (if available)", "", 78),
            # Custom lpe
            ("", "Custom", "Custom", "", 0),
            ("color custom_lpe", "Custom LPE", "Custom LPE", "", 79)
        ]
        return items

    def update_type(self, context):
        types = self.aov_list(context)
        for item in types:
            if self.aov_name == item[0]:
                self.name = item[1]
                self.channel_name = item[1]

    show_advanced: BoolProperty(name='Advanced Options', default=False)

    name: StringProperty(name='Channel Name')

    channel_name: StringProperty()

    aov_name: EnumProperty(name="AOV Type",
                            description="",
                            items=aov_list, update=update_type)

    custom_lpe_string: StringProperty(
        name="lpe String",
        description="This is where you enter the custom lpe string")

    stats_type: EnumProperty(
        name="Statistics",
        description="this is the name of the statistics to display in this AOV (if any)",
        items=[
            ('none', 'None', ''),
            ('variance', 'Variance',
             'estimates the variance of the samples in each pixel'),
            ('mse', 'MSE', 'the estimate of the variance divided by the actual number of samples per pixel'),
            ('even', 'Even', 'this image is created from half the total camera samples'),
            ('odd', 'Odd', 'this image is created from the other half of the camera samples')],
        default='none')

    exposure_gain: FloatProperty(
        name="Gain",
        description="The gain of the exposure.  This is the overall brightness of the image",
        default=1.0)

    exposure_gamma: FloatProperty(
        name="Gamma",
        description="The gamma of the exposure.  This determines how flat the brightness curve is.  Raising gamma leads to lighter shadows",
        default=1.0)

    remap_a: FloatProperty(
        name="a",
        description="A value for remap",
        default=0.0)

    remap_b: FloatProperty(
        name="b",
        description="B value for remap",
        default=0.0)

    remap_c: FloatProperty(
        name="c",
        description="C value for remap",
        default=0.0)

    quantize_zero: IntProperty(
        name="Zero",
        description="Zero value for quantization",
        default=0)

    quantize_one: IntProperty(
        name="One",
        description="One value for quantization",
        default=0)

    quantize_min: IntProperty(
        name="Min",
        description="Minimum value for quantization",
        default=0)

    quantize_max: IntProperty(
        name="Max",
        description="Max value for quantization",
        default=0)

    chan_pixelfilter: EnumProperty(
        name="Pixel Filter",
        description="Filter to use to combine pixel samples.  If 'default' is selected the aov will use the filter set in the render panel",
        items=[('default', 'Default', ''),
               ('box', 'Box', ''),
               ('sinc', 'Sinc', ''),
               ('gaussian', 'Gaussian', ''),
               ('triangle', 'Triangle', ''),
               ('catmull-rom', 'Catmull-Rom', '')],
        default='default')
    chan_pixelfilter_x: IntProperty(
        name="Filter Size X",
        description="Size of the pixel filter in X dimension",
        min=0, max=16, default=2)
    chan_pixelfilter_y: IntProperty(
        name="Filter Size Y",
        description="Size of the pixel filter in Y dimension",
        min=0, max=16, default=2)

    object_group: StringProperty(name='Object Group')
    light_group: StringProperty(name='Light Group')        

class RendermanAOV(bpy.types.PropertyGroup):

    name: StringProperty(name='Display Name')
    aov_display_driver: EnumProperty(
        name="Display Driver",
        description="File Type for output pixels",
        items=[
            ('openexr', 'OpenEXR',
             'Render to an OpenEXR file.'),
            ('deepexr', 'Deep OpenEXR',
             'Render to a deep OpenEXR file.'),             
            ('tiff', 'Tiff',
             'Render to a TIFF file.'),
            ('png', 'PNG',
            'Render to a PNG file.')
        ], default='openexr')    
    dspy_channels: CollectionProperty(type=RendermanDspyChannel,
                                     name='Display Channels')
    dspy_channels_index: IntProperty(min=-1, default=-1)    
    camera: PointerProperty(name="Camera", 
                        description="Camera to use to render this AOV. If not specified the main scene camera is used.",
                        type=bpy.types.Camera)
    denoise: BoolProperty(name='Denoise', default=False)
    denoise_mode: EnumProperty(
        name="Denoise Mode",
        description="Denoise mode",
        items=[
            ('singleframe', 'Single Frame',
             'Single frame mode'),
            ('crossframe', 'Cross Frame',
            'Denoise in crossframe mode.')
        ], default='singleframe')     

   

class RendermanRenderLayerSettings(bpy.types.PropertyGroup):
    render_layer: StringProperty()
    custom_aovs: CollectionProperty(type=RendermanAOV,
                                     name='Custom AOVs')
    custom_aov_index: IntProperty(min=-1, default=-1)
    #camera: StringProperty()
    object_group: StringProperty(name='Object Group')
    light_group: StringProperty(name='Light Group')

    export_multilayer: BoolProperty(
        name="Export Multilayer",
        description="Enabling this will combine passes and output as a multilayer file",
        default=False)

    exr_format_options: EnumProperty(
        name="EXR Bit Depth",
        description="Sets the bit depth of the .exr file.  Leaving at 'default' will use the RenderMan defaults",
        items=[
            ('default', 'Default', ''),
            ('half', 'Half (16 bit)', ''),
            ('float', 'Float (32 bit)', '')],
        default='default')

    use_deep: BoolProperty(
        name="Use Deep Data",
        description="The output file will contain extra 'deep' information that can aid with compositing.  This can increase file sizes dramatically.  Z channels will automatically be generated so they do not need to be added to the AOV panel",
        default=False)

    denoise_aov: BoolProperty(
        name="Denoise AOVs",
        default=False)

    exr_compression: EnumProperty(
        name="EXR Compression",
        description="Determined the compression used on the EXR file.  Leaving at 'default' will use the RenderMan defaults",
        items=[
            ('default', 'Default', ''),
            ('none', 'None', ''),
            ('rle', 'rle', ''),
            ('zip', 'zip', ''),
            ('zips', 'zips', ''),
            ('pixar', 'pixar', ''),
            ('b44', 'b44', ''),
            ('piz', 'piz', '')],
        default='default')

    exr_storage: EnumProperty(
        name="EXR Storage Mode",
        description="This determines how the EXR file is formatted.  Tile-based may reduce the amount of memory used by the display buffer",
        items=[
            ('scanline', 'Scanline Storage', ''),
            ('tiled', 'Tiled Storage', '')],
        default='scanline')


class RendermanSceneSettings(bpy.types.PropertyGroup):
    display_filters: CollectionProperty(
        type=rman_bl_nodes_props.RendermanDisplayFilterSettings, name='Display Filters')
    display_filters_index: IntProperty(min=-1, default=-1)
    sample_filters: CollectionProperty(
        type=rman_bl_nodes_props.RendermanSampleFilterSettings, name='Sample Filters')
    sample_filters_index: IntProperty(min=-1, default=-1)

    light_groups: CollectionProperty(type=RendermanGroup,
                                      name='Light Groups')
    light_groups_index: IntProperty(min=-1, default=-1)

    ll: CollectionProperty(type=LightLinking,
                            name='Light Links')

    # we need these in case object/light selector changes
    def reset_ll_light_index(self, context):
        self.ll_light_index = -1

    def reset_ll_object_index(self, context):
        self.ll_object_index = -1

    ll_light_index: IntProperty(min=-1, default=-1)
    ll_object_index: IntProperty(min=-1, default=-1)
    ll_light_type: EnumProperty(
        name="Select by",
        description="Select by",
        items=[('light', 'Lights', ''),
               ('group', 'Light Groups', '')],
        default='group', update=reset_ll_light_index)

    ll_object_type: EnumProperty(
        name="Select by",
        description="Select by",
        items=[('object', 'Objects', ''),
               ('group', 'Object Groups', '')],
        default='group', update=reset_ll_object_index)

    render_layers: CollectionProperty(type=RendermanRenderLayerSettings,
                                       name='Custom AOVs')


    def update_scene_solo_light(self, context):
        rr = rman_render.RmanRender.get_rman_render()        
        if rr.rman_interactive_running:
            if self.solo_light:
                rr.rman_scene.update_solo_light(context)
            else:
                rr.rman_scene.update_un_solo_light(context)

    solo_light: BoolProperty(name="Solo Light", update=update_scene_solo_light, default=False)

    pixelsamples_x: IntProperty(
        name="Pixel Samples X",
        description="Number of AA samples to take in X dimension",
        min=0, max=16, default=2)
    pixelsamples_y: IntProperty(
        name="Pixel Samples Y",
        description="Number of AA samples to take in Y dimension",
        min=0, max=16, default=2)

    pixelfilter: EnumProperty(
        name="Pixel Filter",
        description="Filter to use to combine pixel samples",
        items=[('box', 'Box', ''),
               ('sinc', 'Sinc', ''),
               ('gaussian', 'Gaussian', ''),
               ('triangle', 'Triangle', ''),
               ('catmull-rom', 'Catmull-Rom', '')],
        default='gaussian')
    pixelfilter_x: IntProperty(
        name="Filter Size X",
        description="Size of the pixel filter in X dimension",
        min=0, max=16, default=2)
    pixelfilter_y: IntProperty(
        name="Filter Size Y",
        description="Size of the pixel filter in Y dimension",
        min=0, max=16, default=2)

    pixel_variance: FloatProperty(
        name="Pixel Variance",
        description="If a pixel changes by less than this amount when updated, it will not receive further samples in adaptive mode.  Lower values lead to increased render times and higher quality images",
        min=0, max=1, default=.01, precision=3)

    dark_falloff: FloatProperty(
        name="Dark Falloff",
        description="Deprioritizes adaptive sampling in dark areas. Raising this can potentially reduce render times but may increase noise in dark areas",
        min=0, max=1, default=.025, precision=3)

    min_samples: IntProperty(
        name="Min Samples",
        description="The minimum number of camera samples per pixel.  If this is set to '0' then the min samples will be the square root of the max_samples",
        min=0, default=4)
    max_samples: IntProperty(
        name="Max Samples",
        description="The maximum number of camera samples per pixel.  This should be set in 'power of two' numbers (1, 2, 4, 8, 16, etc)",
        min=0, default=128)

    bucket_shape: EnumProperty(
        name="Bucket Order",
        description="The order buckets are rendered in",
        items=[('HORIZONTAL', 'Horizontal', 'Render scanline from top to bottom'),
               ('VERTICAL', 'Vertical',
                'Render scanline from left to right'),
               ('ZIGZAG-X', 'Reverse Horizontal',
                'Exactly the same as Horizontal but reverses after each scan'),
               ('ZIGZAG-Y', 'Reverse Vertical',
                'Exactly the same as Vertical but reverses after each scan'),
               ('SPACEFILL', 'Hilber spacefilling curve',
                'Renders the buckets along a hilbert spacefilling curve'),
               ('SPIRAL', 'Spiral rendering',
                'Renders in a spiral from the center of the image or a custom defined point'),
               ('RANDOM', 'Random', 'Renders buckets in a random order WARNING: Inefficient memory footprint')],
        default='SPIRAL')

    bucket_sprial_x: IntProperty(
        name="X",
        description="X coordinate of bucket spiral start",
        min=-1, default=-1)

    bucket_sprial_y: IntProperty(
        name="Y",
        description="Y coordinate of bucket spiral start",
        min=-1, default=-1)

    render_selected_objects_only: BoolProperty(
        name="Only Render Selected",
        description="Render only the selected object(s)",
        default=False)

    shadingrate: FloatProperty(
        name="Micropolygon Length",
        description="Default maximum distance between displacement samples.  This can be left at 1 unless you need more detail on displaced objects",
        default=1.0)

    dicing_strategy: EnumProperty(
        name="Dicing Strategy",
        description="Sets the method that RenderMan uses to tessellate objects.",
        items=[
            ("objectdistance", "Object Distance", ""),             
            ("worlddistance", "World Distance", "Tessellation is determined using distances measured in world space units compared to the current micropolygon length"),
            ("instanceprojection", "Instance Projection", "")],
        default="instanceprojection")

    worlddistancelength: FloatProperty(
        name="World Distance Length",
        description="If this is a value above 0, it sets the length of a micropolygon after tessellation",
        default=-1.0)

    motion_blur: BoolProperty(
        name="Motion Blur",
        description="Enable motion blur",
        default=False)
    sample_motion_blur: BoolProperty(
        name="Sample Motion Blur",
        description="Determines if motion blur is rendered in the final image.  If this is disabled the motion vectors are still calculated and can be exported with the dPdTime AOV.  This allows motion blur to be added as a post process effect",
        default=True)
    motion_segments: IntProperty(
        name="Motion Samples",
        description="Number of motion samples to take for motion blur.  Set this higher if you notice segment artifacts in blurs",
        min=2, max=16, default=2)
    shutter_timing: EnumProperty(
        name="Shutter Timing",
        description="Controls when the shutter opens for a given frame",
        items=[('CENTER', 'Center on frame', 'Motion is centered on frame #.'),
               ('PRE', 'Pre frame', 'Motion ends on frame #'),
               ('POST', 'Post frame', 'Motion starts on frame #')],
        default='CENTER')

    shutter_angle: FloatProperty(
        name="Shutter Angle",
        description="Fraction of time that the shutter is open (360 is one full second).  180 is typical for North America 24fps cameras, 172.8 is typical in Europe",
        default=180.0, min=0.0, max=360.0)

    shutter_efficiency_open: FloatProperty(
        name="Shutter open speed",
        description="Shutter open efficiency - controls the speed of the shutter opening.  0 means instantaneous, > 0 is a gradual opening",
        default=0.0)
    shutter_efficiency_close: FloatProperty(
        name="Shutter close speed",
        description="Shutter close efficiency - controls the speed of the shutter closing.  1 means instantaneous, < 1 is a gradual closing",
        default=1.0)

    threads: IntProperty(
        name="Rendering Threads",
        description="Number of processor threads to use.  Note, 0 uses all cores, -1 uses all cores but one",
        min=-32, max=32, default=-1)

    override_threads: BoolProperty(
        name="Override Threads",
        description="Overrides thread count for spooled render",
        default=False)

    external_threads: IntProperty(
        name="Spool Rendering Threads",
        description="Number of processor threads to use.  Note, 0 uses all cores, -1 uses all cores but one",
        default=0, min=-32, max=32)

    max_trace_depth: IntProperty(
        name="Max Trace Depth",
        description="Maximum number of times a ray can bounce before the path is ended.  Lower settings will render faster but may change lighting",
        min=0, max=32, default=10)
    max_specular_depth: IntProperty(
        name="Max Specular Depth",
        description="Maximum number of specular ray bounces",
        min=0, max=32, default=4)
    max_diffuse_depth: IntProperty(
        name="Max Diffuse Depth",
        description="Maximum number of diffuse ray bounces",
        min=0, max=32, default=1)
    use_metadata: BoolProperty(
        name="Use Metadata",
        description="The output file will contain extra image metadata that can aid with production workflows. Information includes camera (focallength, fstop, sensor size and focal distance), version (Blender and RfB), username, blender scene path, statistic xml path and integrator settings.",
        default=True)
    custom_metadata: StringProperty(
        name="Metadata Comment",
        description="Add a custom comment to the EXR Metadata.",
        default='')    
    use_statistics: BoolProperty(
        name="Statistics",
        description="Print statistics to stats.xml after render",
        default=False)
    editor_override: StringProperty(
        name="Text Editor",
        description="The editor to open RIB file in (Overrides system default!)",
        default="")
    statistics_level: IntProperty(
        name="Statistics Level",
        description="Verbosity level of output statistics",
        min=0, max=3, default=1)

    # RIB output properties

    path_rib_output: StringProperty(
        name="RIB Output Path",
        description="Path to generated .rib files",
        subtype='FILE_PATH',
        default=os.path.join('{OUT}', '{blend}', '{scene}.{layer}.{F4}.rib'))

    path_object_archive_static: StringProperty(
        name="Object archive RIB Output Path",
        description="Path to generated rib file for a non-deforming objects' geometry",
        subtype='FILE_PATH',
        default=os.path.join('$ARC', 'static', '{object}.rib'))

    path_object_archive_animated: StringProperty(
        name="Object archive RIB Output Path",
        description="Path to generated rib file for an animated objects geometry",
        subtype='FILE_PATH',
        default=os.path.join('$ARC', '####', '{object}.rib'))

    path_texture_output: StringProperty(
        name="Teture Output Path",
        description="Path to generated .tex files",
        subtype='FILE_PATH',
        default=os.path.join('{OUT}', 'textures'))

    out_dir: StringProperty(
        name="Shader Output Path",
        description="Path to compiled .oso files",
        subtype='FILE_PATH',
        default="./shaders")

    rib_format: EnumProperty(
        name="RIB Format",
        items=[
            ("ascii", "ASCII", ""),
            ("binary", "Binary", "")],
        default="binary")

    rib_compression: EnumProperty(
        name="RIB Compression",
        items=[
            ("none", "None", ""),
            ("gzip", "GZip", "")],
        default="none")

    texture_cache_size: IntProperty(
        name="Texture Cache Size (MB)",
        description="Maximum number of megabytes to devote to texture caching",
        default=2048
    )

    geo_cache_size: IntProperty(
        name="Tesselation Cache Size (MB)",
        description="Maximum number of megabytes to devote to tesselation cache for tracing geometry",
        default=2048
    )

    opacity_cache_size: IntProperty(
        name="Opacity Cache Size (MB)",
        description="Maximum number of megabytes to devote to caching opacity and presence values.  0 turns this off",
        default=1000
    )

    output_action: EnumProperty(
        name="Action",
        description="Action to take when rendering",
        items=[('EXPORT_RENDER', 'Export RIB and Render', 'Generate RIB file and render it with the renderer'),
               ('EXPORT', 'Export RIB Only', 'Generate RIB file only')],
        default='EXPORT_RENDER')

    lazy_rib_gen: BoolProperty(
        name="Cache Rib Generation",
        description="On unchanged objects, don't re-emit rib.  Will result in faster spooling of renders",
        default=True)

    always_generate_textures: BoolProperty(
        name="Always Recompile Textures",
        description="Recompile used textures at export time to the current rib folder. Leave this unchecked to speed up re-render times",
        default=False)

    hider_decidither: IntProperty(
        name="Interactive Refinement",
        description="This value is only applied during IPR. The value determines how much refinement (in a dither pattern) will be applied to the image during interactive rendering. 0 means full refinement up to a value of 6 which is the least refinement per iteration.",
        min=0, max=6, default=0)

    hider_type: EnumProperty(
        name="Hider Type",
        description="Hider Type",
        items=[('BAKE', 'BAKE', 'Bake Hider'),
               ('RAYTRACE', 'RAYTRACE', 'Raytrace Hider')],
        default='RAYTRACE')

    # preview settings
    preview_pixel_variance: FloatProperty(
        name="Preview Pixel Variance",
        description="If a pixel changes by less than this amount when updated, it will not receive further samples in adaptive mode",
        min=0, max=1, default=.05, precision=3)

    preview_bucket_order: EnumProperty(
        name="Preview Bucket Order",
        description="Bucket order to use when rendering",
        items=[('HORIZONTAL', 'Horizontal', 'Render scanline from top to bottom'),
               ('VERTICAL', 'Vertical',
                'Render scanline from left to right'),
               ('ZIGZAG-X', 'Reverse Horizontal',
                'Exactly the same as Horizontal but reverses after each scan'),
               ('ZIGZAG-Y', 'Reverse Vertical',
                'Exactly the same as Vertical but reverses after each scan'),
               ('SPACEFILL', 'Hilber spacefilling curve',
                'Renders the buckets along a hilbert spacefilling curve'),
               ('SPIRAL', 'Spiral rendering',
                'Renders in a spiral from the center of the image or a custom defined point'),
               ('RANDOM', 'Random', 'Renders buckets in a random order WARNING: Inefficient memory footprint')],
        default='SPIRAL')

    preview_min_samples: IntProperty(
        name="Preview Min Samples",
        description="The minimum number of camera samples per pixel.  Setting this to '0' causes the min_samples to be set to the square root of max_samples",
        min=0, default=0)
    preview_max_samples: IntProperty(
        name="Preview Max Samples",
        description="The maximum number of camera samples per pixel.  This should be set lower than the final render setting to imporove speed",
        min=0, default=64)

    preview_max_specular_depth: IntProperty(
        name="Max Preview Specular Depth",
        description="Maximum number of specular ray bounces",
        min=0, max=32, default=2)
    preview_max_diffuse_depth: IntProperty(
        name="Max Preview Diffuse Depth",
        description="Maximum number of diffuse ray bounces",
        min=0, max=32, default=1)

    enable_external_rendering: BoolProperty(
        name="Enable External Rendering",
        description="This will allow extended rendering modes, which allow batch rendering to RenderMan outside of Blender",
        default=False)

    display_driver: EnumProperty(
        name="Display Driver",
        description="File Type for output pixels, 'it' will send to an external framebuffer",
        items=[
            ('openexr', 'OpenEXR',
             'Render to an OpenEXR file.'),
            ('tiff', 'Tiff',
             'Render to a TIFF file.'),
            ('it', 'it', 'External framebuffer display.')
        ], default='openexr')

    exr_format_options: EnumProperty(
        name="Bit Depth",
        description="Sets the bit depth of the main EXR file.  Leaving at 'default' will use the RenderMan defaults",
        items=[
            ('default', 'Default', ''),
            ('half', 'Half (16 bit)', ''),
            ('float', 'Float (32 bit)', '')],
        default='default')

    exr_compression: EnumProperty(
        name="Compression",
        description="Determined the compression used on the main EXR file.  Leaving at 'default' will use the RenderMan defaults",
        items=[
            ('default', 'Default', ''),
            ('none', 'None', ''),
            ('rle', 'rle', ''),
            ('zip', 'zip', ''),
            ('zips', 'zips', ''),
            ('pixar', 'pixar', ''),
            ('b44', 'b44', ''),
            ('piz', 'piz', '')],
        default='default')

    render_into: EnumProperty(
        name="Render to",
        description="Render to Blender or Image Tool framebuffer. This also controls where viewport renders will render to.",
        items=[('blender', 'Blender', 'Render to the Image Editor'),
               ('it', 'it', 'Image Tool framebuffer display')],
        default='blender')

    export_options: BoolProperty(
        name="Export Options",
        default=False)

    generate_rib: BoolProperty(
        name="Generate RIBs",
        description="Generates RIB files for the scene information",
        default=True)

    generate_object_rib: BoolProperty(
        name="Generate object RIBs",
        description="Generates RIB files for each object",
        default=True)

    generate_alf: BoolProperty(
        name="Generate ALF files",
        description="Generates an ALF file.  This file contains a sequential list of commmands used for rendering",
        default=True)

    convert_textures: BoolProperty(
        name="Convert Textures",
        description="Add commands to the ALF file to convert textures to .tex files",
        default=True)

    generate_render: BoolProperty(
        name="Generate render commands",
        description="Add render commands to the ALF file",
        default=True)

    do_render: BoolProperty(
        name="Initiate Renderer",
        description="Spool RIB files to RenderMan",
        default=True)

    alf_options: BoolProperty(
        name="ALF Options",
        default=False)

    custom_alfname: StringProperty(
        name="Custom Spool Name",
        description="Allows a custom name for the spool .alf file.  This would allow you to export multiple spool files for the same scene",
        default='spool')

    queuing_system: EnumProperty(
        name="Spool to",
        description="System to spool to",
        items=[('lq', 'LocalQueue', 'Spool to LocalQueue and render on your local machine.'),
               ('tractor', 'Tractor', 'Tractor, must have tractor setup')],
        default='lq')

    recover: BoolProperty(
        name="Enable Recovery",
        description="Attempt to resume render from a previous checkpoint (if possible)",
        default=False)

    custom_cmd: StringProperty(
        name="Custom Render Commands",
        description="Inserts a string of custom command arguments into the render process",
        default='')

    denoise_cmd: StringProperty(
        name="Custom Denoise Commands",
        description="Inserts a string of custom commands arguments into the denoising process, if selected",
        default='')

    spool_denoise_aov: BoolProperty(
        name="Process denoisable AOV's",
        description="Denoises tagged AOV's",
        default=False)

    denoise_gpu: BoolProperty(
        name="Use GPU for denoising",
        description="The denoiser will attempt to use the GPU (if available)",
        default=True)

    external_animation: BoolProperty(
        name="Render Animation",
        description="Spool Animation",
        default=False)

    enable_checkpoint: BoolProperty(
        name="Enable Checkpointing",
        description="Allows partial images to be output at specific intervals while the renderer continued to run.  The user may also set a point at which the render will terminate",
        default=False)

    checkpoint_type: EnumProperty(
        name="Checkpoint Method",
        description="Sets the method that the checkpointing will use",
        items=[('i', 'Iterations', 'Number of samples per pixel'),
               ('s', 'Seconds', ''),
               ('m', 'Minutes', ''),
               ('h', 'Hours', ''),
               ('d', 'Days', '')],
        default='s')

    checkpoint_interval: IntProperty(
        name="Interval",
        description="The interval between checkpoint images",
        default=60)

    render_limit: IntProperty(
        name="Limit",
        description="The maximum interval that will be reached before the render terminates.  0 will disable this option",
        default=0)

    asfinal: BoolProperty(
        name="Final Image as Checkpoint",
        description="Saves the final image as a checkpoint.  This allows you to resume it after raising the sample count",
        default=False)

    header_rib_boxes: StringProperty(
        name="External RIB File",
        description="Injects an external RIB into the header of the output file",
        subtype='FILE_PATH',
        default="")

    do_denoise: BoolProperty(
        name="Denoise Post-Process",
        description="Use RenderMan's image denoiser to post process your render.  This allows you to use a higher pixel variance (and therefore faster render) while still producing a high quality image",
        default=False)

    external_denoise: BoolProperty(
        name="Denoise Post-Process",
        description="Use RenderMan's image denoiser to post process your render.  This allows you to use a higher pixel variance (and therefore faster render) while still producing a high quality image",
        default=False)

    crossframe_denoise: BoolProperty(
        name="Crossframe Denoise",
        description="Only available when denoising an external render.\n  This is more efficient especially with motion blur",
        default=False)

    update_frequency: IntProperty(
        name="Update frequency",
        description="Number of seconds between display update when rendering to Blender",
        min=0, default=10)

    import_images: BoolProperty(
        name="Import AOV's into Blender",
        description="Imports all AOV's from the render session into Blender's image editor",
        default=True)

    incremental: BoolProperty(
        name="Incremental Render",
        description="When enabled every pixel is sampled once per render pass.  This allows the user to quickly see the entire image during rendering, and as each pass completes the image will become clearer.  NOTE-This mode is automatically enabled with some render integrators (PxrVCM)",
        default=True)

    raytrace_progressive: BoolProperty(
        name="Progressive Rendering",
        description="Enables progressive rendering (the entire image is refined at once).\nThis is only visible with some display drivers (such as it)",
        default=False)

    def update_integrator(self, context):
        rr = rman_render.RmanRender.get_rman_render()
        if rr.rman_interactive_running:
            rr.rman_scene.update_integrator(context)

    def integrator_items(self, context):
        items = []
        # Make PxrPathTracer be the first item, so
        # it's the default
        items.append(('PxrPathTracer', 'PxrPathTracer', ''))
        for n in rman_bl_nodes.__RMAN_INTEGRATOR_NODES__:
            if n.name != 'PxrPathTracer':
                items.append((n.name, n.name, ''))
        return items

    integrator: EnumProperty(
        name="Integrator",
        description="Integrator for rendering",
        items=integrator_items,
        update=update_integrator)

    show_integrator_settings: BoolProperty(
        name="Integration Settings",
        description="Show Integrator Settings",
        default=False
    )

    # Rib Box Properties
    frame_rib_box: StringProperty(
        name="Frame RIB box",
        description="Injects RIB into the 'frame' block",
        default="")

    # Trace Sets (grouping membership)
    object_groups: CollectionProperty(
        type=RendermanGroup, name="Trace Sets")
    object_groups_index: IntProperty(min=-1, default=-1)

    use_default_paths: BoolProperty(
        name="Use 3Delight default paths",
        description="Includes paths for default shaders etc. from 3Delight install",
        default=True)
    use_builtin_paths: BoolProperty(
        name="Use built in paths",
        description="Includes paths for default shaders etc. from Blender->3Delight exporter",
        default=False)

    path_rmantree: StringProperty(
        name="RMANTREE Path",
        description="Path to RenderManProServer installation folder",
        subtype='DIR_PATH',
        default=filepath_utils.guess_rmantree())
    path_renderer: StringProperty(
        name="Renderer Path",
        description="Path to renderer executable",
        subtype='FILE_PATH',
        default="prman")
    path_shader_compiler: StringProperty(
        name="Shader Compiler Path",
        description="Path to shader compiler executable",
        subtype='FILE_PATH',
        default="shader")
    path_shader_info: StringProperty(
        name="Shader Info Path",
        description="Path to shaderinfo executable",
        subtype='FILE_PATH',
        default="sloinfo")
    path_texture_optimiser: StringProperty(
        name="Texture Optimiser Path",
        description="Path to tdlmake executable",
        subtype='FILE_PATH',
        default="txmake")

    do_holdout_matte: EnumProperty(
        name="Render Holdouts",
        description="Render a holdout matte.",
        items=[('OFF', 'Off', ''),
               ('ALPHA', 'In Alpha', ''),
               ('AOV', 'Separate AOV', '')
               ],        
        default='OFF')        


class RendermanMaterialSettings(bpy.types.PropertyGroup):
    instance_num: IntProperty(name='Instance number for IPR', default=0)

    preview_render_type: EnumProperty(
        name="Preview Render Type",
        description="Object to display in material preview",
        items=[('SPHERE', 'Sphere', ''),
               ('CUBE', 'Cube', '')],
        default='SPHERE')

    copy_color_params: BoolProperty(
        name="Copy Color Parameters",
        description="""Copy Blender material color parameters when adding a new RenderMan node tree. Copies
                    diffuse_color, diffuse_intensity, and specular_color. Only used if we are unable
                    to convert a Cycles shading network.""",
        default=False)

class RendermanAnimSequenceSettings(bpy.types.PropertyGroup):
    animated_sequence: BoolProperty(
        name="Animated Sequence",
        description="Interpret this archive as an animated sequence (converts #### in file path to frame number)",
        default=False)
    sequence_in: IntProperty(
        name="Sequence In Point",
        description="The first numbered file to use",
        default=1)
    sequence_out: IntProperty(
        name="Sequence Out Point",
        description="The last numbered file to use",
        default=24)
    blender_start: IntProperty(
        name="Blender Start Frame",
        description="The frame in Blender to begin playing back the sequence",
        default=1)
    '''
    extend_in: EnumProperty(
                name="Extend In",
                items=[('HOLD', 'Hold', ''),
                    ('LOOP', 'Loop', ''),
                    ('PINGPONG', 'Ping-pong', '')],
                default='HOLD')
    extend_out: EnumProperty(
                name="Extend In",
                items=[('HOLD', 'Hold', ''),
                    ('LOOP', 'Loop', ''),
                    ('PINGPONG', 'Ping-pong', '')],
                default='HOLD')
    '''


class RendermanTextureSettings(bpy.types.PropertyGroup):
    # animation settings

    anim_settings: PointerProperty(
        type=RendermanAnimSequenceSettings,
        name="Animation Sequence Settings")

    # texture optimiser settings
    '''
    type: EnumProperty(
                name="Data type",
                description="Type of external file",
                items=[('NONE', 'None', ''),
                    ('IMAGE', 'Image', ''),
                    ('POINTCLOUD', 'Point Cloud', '')],
                default='NONE')
    '''
    format: EnumProperty(
        name="Format",
        description="Image representation",
        items=[('TEXTURE', 'Texture Map', ''),
               ('ENV_LATLONG', 'LatLong Environment Map', '')
               ],
        default='TEXTURE')
    auto_generate_texture: BoolProperty(
        name="Auto-Generate Optimized",
        description="Use the texture optimiser to convert image for rendering",
        default=False)
    file_path: StringProperty(
        name="Source File Path",
        description="Path to original image",
        subtype='FILE_PATH',
        default="")
    wrap_s: EnumProperty(
        name="Wrapping S",
        items=[('black', 'Black', ''),
               ('clamp', 'Clamp', ''),
               ('periodic', 'Periodic', '')],
        default='clamp')
    wrap_t: EnumProperty(
        name="Wrapping T",
        items=[('black', 'Black', ''),
               ('clamp', 'Clamp', ''),
               ('periodic', 'Periodic', '')],
        default='clamp')
    flip_s: BoolProperty(
        name="Flip S",
        description="Mirror the texture in S",
        default=False)
    flip_t: BoolProperty(
        name="Flip T",
        description="Mirror the texture in T",
        default=False)

    filter_type: EnumProperty(
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
    filter_window: EnumProperty(
        name="Filter Window",
        items=[('DEFAULT', 'Default', ''),
               ('lanczos', 'Lanczos', ''),
               ('hamming', 'Hamming', ''),
               ('hann', 'Hann', ''),
               ('blackman', 'Blackman', '')],
        default='DEFAULT',
        description='Downsampling filter window for infinite support filters')

    filter_width_s: FloatProperty(
        name="Filter Width S",
        description="Filter diameter in S",
        min=0.0, soft_max=1.0, default=1.0)
    filter_width_t: FloatProperty(
        name="Filter Width T",
        description="Filter diameter in T",
        min=0.0, soft_max=1.0, default=1.0)
    filter_blur: FloatProperty(
        name="Filter Blur",
        description="Blur factor: > 1.0 is blurry, < 1.0 is sharper",
        min=0.0, soft_max=1.0, default=1.0)

    input_color_space: EnumProperty(
        name="Input Color Space",
        items=[('srgb', 'sRGB', ''),
               ('linear', 'Linear RGB', ''),
               ('GAMMA', 'Gamma', '')],
        default='srgb',
        description='Color space of input image')
    input_gamma: FloatProperty(
        name="Input Gamma",
        description="Gamma value of input image if using gamma color space",
        min=0.0, soft_max=3.0, default=2.2)

    output_color_depth: EnumProperty(
        name="Output Color Depth",
        items=[('UBYTE', '8-bit unsigned', ''),
               ('SBYTE', '8-bit signed', ''),
               ('USHORT', '16-bit unsigned', ''),
               ('SSHORT', '16-bit signed', ''),
               ('FLOAT', '32 bit float', '')],
        default='UBYTE',
        description='Color depth of output image')

    output_compression: EnumProperty(
        name="Output Compression",
        items=[('LZW', 'LZW', ''),
               ('ZIP', 'Zip', ''),
               ('PACKBITS', 'PackBits', ''),
               ('LOGLUV', 'LogLUV (float only)', ''),
               ('UNCOMPRESSED', 'Uncompressed', '')],
        default='ZIP',
        description='Compression of output image data')

    generate_if_nonexistent: BoolProperty(
        name="Generate if Non-existent",
        description="Generate if optimised image does not exist in the same folder as source image path",
        default=True)
    generate_if_older: BoolProperty(
        name="Generate if Optimised is Older",
        description="Generate if optimised image is older than corresponding source image",
        default=True)

class RendermanWorldSettings(bpy.types.PropertyGroup):

    def get_light_node(self):
        return getattr(self, self.light_node) if self.light_node else None

    def get_light_node_name(self):
        return self.light_node.replace('_settings', '')

    # do this to keep the nice viewport update
    def update_light_type(self, context):
        world = context.scene.world
        world_type = world.renderman.renderman_type
        if world_type == 'NONE':
            return
        # use pxr area light for everything but env, sky
        light_shader = 'PxrDomeLight'
        if world_type == 'SKY':
            light_shader = 'PxrEnvDayLight'

        self.light_node = light_shader + "_settings"

    def update_vis(self, context):
        light = context.scene.world

        """
        from . import engine
        if engine.is_ipr_running():
            engine.ipr.update_light_visibility(light)
        """

    renderman_type: EnumProperty(
        name="World Type",
        update=update_light_type,
        items=[
            ('NONE', 'None', 'No World'),
            ('ENV', 'Environment', 'Environment Light'),
            ('SKY', 'Sky', 'Simulated Sky'),
        ],
        default='NONE'
    )

    use_renderman_node: BoolProperty(
        name="Use RenderMans World Node",
        description="Will enable RenderMan World Nodes, opening more options",
        default=False, update=update_light_type)

    light_node: StringProperty(
        name="Light Node",
        default='')

    light_primary_visibility: BoolProperty(
        name="Light Primary Visibility",
        description="Camera visibility for this light",
        update=update_vis,
        default=True)

    shadingrate: FloatProperty(
        name="Light Shading Rate",
        description="Shading Rate for lights.  Keep this high unless banding or pixellation occurs on detailed light maps",
        default=100.0)

    world_rib_box: StringProperty(
        name="World RIB box",
        description="Injects RIB into the 'world' block",
        default="")

    # illuminate
    illuminates_by_default: BoolProperty(
        name="Illuminates by default",
        description="Illuminates objects by default",
        default=True)


class RendermanMeshPrimVar(bpy.types.PropertyGroup):
    name: StringProperty(
        name="Variable Name",
        description="Name of the exported renderman primitive variable")
    data_name: StringProperty(
        name="Data Name",
        description="Name of the Blender data to export as the primitive variable")
    data_source: EnumProperty(
        name="Data Source",
        description="Blender data type to export as the primitive variable",
        items=[('VERTEX_GROUP', 'Vertex Group', ''),
               ('VERTEX_COLOR', 'Vertex Color', ''),
               ('UV_TEXTURE', 'UV Texture', '')
               ]
    )


class RendermanParticlePrimVar(bpy.types.PropertyGroup):
    name: StringProperty(
        name="Variable Name",
        description="Name of the exported renderman primitive variable")
    data_source: EnumProperty(
        name="Data Source",
        description="Blender data type to export as the primitive variable",
        items=[('SIZE', 'Size', ''),
               ('VELOCITY', 'Velocity', ''),
               ('ANGULAR_VELOCITY', 'Angular Velocity', ''),
               ('AGE', 'Age', ''),
               ('BIRTH_TIME', 'Birth Time', ''),
               ('DIE_TIME', 'Die Time', ''),
               ('LIFE_TIME', 'Lifetime', ''),
               ('ID', 'ID', '')
               ]   # XXX: Would be nice to have particle ID, needs adding in RNA
    )


class RendermanParticleSettings(bpy.types.PropertyGroup):

    particle_type_items = [('particle', 'Particle', 'Point primitive'),
                           ('blobby', 'Blobby',
                            'Implicit Surface (metaballs)'),
                           ('sphere', 'Sphere', 'Two-sided sphere primitive'),
                           ('disk', 'Disk', 'One-sided disk primitive'),
                           ('OBJECT', 'Object',
                            'Instanced objects at each point')
                           ]

    def update_psys(self, context):
        active = context.active_object
        active.update_tag(refresh={'DATA'})

    use_object_material: BoolProperty(
        name="Use Master Object's Material",
        description="Use the master object's material for instancing",
        default=True,
        update=update_psys
    )

    def update_point_type(self, context):
        return
        """
        global engine
        if engine.is_ipr_running():
            active = context.view_layer.objects.active
            psys = active.particle_systems.active
            engine.ipr.issue_rman_particle_prim_type_edit(active, psys)
        """

    particle_type: EnumProperty(
        name="Point Type",
        description="Geometric primitive for points to be rendered as",
        items=particle_type_items,
        default='particle',
        update=update_point_type)

    particle_instance_object: StringProperty(
        name="Instance Object",
        description="Object to instance on every particle",
        default="")

    round_hair: BoolProperty(
        name="Round Hair",
        description="Render curves as round cylinders or ribbons.  Round is faster and recommended for hair",
        default=True)

    constant_width: BoolProperty(
        name="Constant Width",
        description="Override particle sizes with constant width value",
        update=update_psys,
        default=False)

    width: FloatProperty(
        name="Width",
        description="With used for constant width across all particles",
        update=update_psys,
        precision=4,
        default=0.01)

    export_default_size: BoolProperty(
        name="Export Default size",
        description="Export the particle size as the default 'width' primitive variable",
        default=True)

    export_scalp_st: BoolProperty(
        name="Export Emitter UV",
        description="On hair, export the u/v from the emitter where the hair originates.  Use the variables 'scalpS' and 'scalpT' in your manifold node",
        default=False
    )

    prim_vars: CollectionProperty(
        type=RendermanParticlePrimVar, name="Primitive Variables")
    prim_vars_index: IntProperty(min=-1, default=-1)


class RendermanMeshGeometrySettings(bpy.types.PropertyGroup):
    export_default_uv: BoolProperty(
        name="Export Default UVs",
        description="Export the active UV set as the default 'st' primitive variable",
        default=True)
    export_default_vcol: BoolProperty(
        name="Export Default Vertex Color",
        description="Export the active Vertex Color set as the default 'Cs' primitive variable",
        default=True)
    export_flipv: EnumProperty(
        name="FlipV",
        description="Use this to flip the V texture coordinate on the exported geometry when rendering. The origin on Renderman texture coordinates are top-left (ie. Photoshop) of image, UV texture coordinates (ie. Maya) generally use the bottom-left of the image as the origin. It's generally better to do this flip using a pattern like PxrTexture or PxrManifold2d",
        items=[('NONE', 'No Flip', 'Do not do anything to the UVs.'),
               ('TILE', 'Flip Tile Space', 'Flips V in tile space. Works with UDIM.'),
               ('UV', 'Flip UV Space', 'Flips V in UV space. This is here for backwards compatability.')],
        default='NONE')
    interp_boundary: IntProperty(
        name="Subdivision Edge Interpolation Mode",
        description="Defines how a subdivided mesh interpolates its boundary edges",
        default=1,
        min=0, max=2)
    face_boundary: IntProperty(
        name="Subdivision UV Interpolation Mode",
        description="Defines how a subdivided mesh interpolates its UV coordinates",
        default=3,
        min=0, max=3)

    prim_vars: CollectionProperty(
        type=RendermanMeshPrimVar, name="Primitive Variables")
    prim_vars_index: IntProperty(min=-1, default=-1)


class RendermanCurveGeometrySettings(bpy.types.PropertyGroup):
    export_default_uv: BoolProperty(
        name="Export Default UVs",
        description="Export the active UV set as the default 'st' primitive variable",
        default=True)
    export_default_vcol: BoolProperty(
        name="Export Default Vertex Color",
        description="Export the active Vertex Color set as the default 'Cs' primitive variable",
        default=True)
    export_smooth_normals: BoolProperty(
        name="Export Smooth Normals",
        description="Export smooth per-vertex normals for PointsPolygons Geometry",
        default=True)

    prim_vars: CollectionProperty(
        type=RendermanMeshPrimVar, name="Primitive Variables")
    prim_vars_index: IntProperty(min=-1, default=-1)


class OpenVDBChannel(bpy.types.PropertyGroup):
    name: StringProperty(name="Channel Name")
    type: EnumProperty(name="Channel Type",
                        items=[
                            ('float', 'Float', ''),
                            ('vector', 'Vector', ''),
                            ('color', 'Color', ''),
                        ])


class RendermanObjectSettings(bpy.types.PropertyGroup):

    openvdb_channels: CollectionProperty(
        type=OpenVDBChannel, name="OpenVDB Channels")
    openvdb_channel_index: IntProperty(min=-1, default=-1)

    archive_anim_settings: PointerProperty(
        type=RendermanAnimSequenceSettings,
        name="Animation Sequence Settings")

    path_archive: StringProperty(
        name="Archive Path",
        description="Path to archive file",
        subtype='FILE_PATH',
        default="")

    procedural_bounds: EnumProperty(
        name="Procedural Bounds",
        description="The bounding box of the renderable geometry",
        items=[('BLENDER_OBJECT', 'Blender Object', "Use the blender object's bounding box for the archive's bounds"),
               ('MANUAL', 'Manual',
                'Manually enter the bounding box coordinates')
               ],
        default="BLENDER_OBJECT")

    path_runprogram: StringProperty(
        name="Program Path",
        description="Path to external program",
        subtype='FILE_PATH',
        default="")
    path_runprogram_args: StringProperty(
        name="Program Arguments",
        description="Command line arguments to external program",
        default="")
    path_dso: StringProperty(
        name="DSO Path",
        description="Path to DSO library file",
        subtype='FILE_PATH',
        default="")
    path_dso_initial_data: StringProperty(
        name="DSO Initial Data",
        description="Parameters to send the DSO",
        default="")
    procedural_bounds_min: FloatVectorProperty(
        name="Min Bounds",
        description="Minimum corner of bounding box for this procedural geometry",
        size=3,
        default=[0.0, 0.0, 0.0])
    procedural_bounds_max: FloatVectorProperty(
        name="Max Bounds",
        description="Maximum corner of bounding box for this procedural geometry",
        size=3,
        default=[1.0, 1.0, 1.0])

    def primitive_items(scene, context):
        items = []
    
        items=[('AUTO', 'Automatic', 'Automatically determine the object type from context and modifiers used'),
               ('MESH', 'Mesh', 'Mesh object'),
               ('RI_VOLUME', 'Volume', 'Volume primitive'),
               ('POINTS', 'Points',
                'Renders object vertices as single points'),
               ('QUADRIC', 'Quadric', 'Parametric primitive') 
               ]
        
        items.append(('OPENVDB', 'OpenVDB File',
        'Renders a prevously exported OpenVDB file'))
        items.append(('DELAYED_LOAD_ARCHIVE', 'Delayed Load Archive',
        'Loads and renders geometry from an archive only when its bounding box is visible'))
        items.append(('PROCEDURAL_RUN_PROGRAM', 'Procedural Run Program',
        'Generates procedural geometry at render time from an external program'))
        items.append(('DYNAMIC_LOAD_DSO', 'Dynamic Load DSO',
        'Generates procedural geometry at render time from a dynamic shared object library')) 

        return items

    primitive: EnumProperty(
        name="Primitive Type",
        description="Representation of this object's geometry in the renderer",
        items=primitive_items)
        #default='AUTO')

    rman_quadric_type: EnumProperty(
        name='Quadric Type',
        description='Quadric type to render',
        items=[('SPHERE', 'Sphere', 'Parametric sphere primitive'),
               ('CYLINDER', 'Cylinder', 'Parametric cylinder primitive'),
               ('CONE', 'Cone', 'Parametric cone primitive'),
               ('DISK', 'Disk', 'Parametric 2D disk primitive'),
               ('TORUS', 'Torus', 'Parametric torus primitive')
        ]
    )

    rman_subdiv_scheme: EnumProperty(
        name='Subdivision Scheme',
        description='Which subdivision scheme to use. Select None for regular polygon mesh. Note, if not set to None, this will take precedence over any modifiers attached.',
        items=[('none', 'None', ''),
               ('catmull-clark', 'Catmull-Clark', ''),
               ('loop', 'Loop', ''),
               ('bilinear', 'Bilinear', '')
        ]        
    )

    export_archive: BoolProperty(
        name="Export as Archive",
        description="At render export time, store this object as a RIB archive",
        default=False)
    export_archive_path: StringProperty(
        name="Archive Export Path",
        description="Path to automatically save this object as a RIB archive",
        subtype='FILE_PATH',
        default="")

    primitive_radius: FloatProperty(
        name="Radius",
        default=1.0,)
    primitive_zmin: FloatProperty(
        name="Z min",
        description="Minimum height clipping of the primitive",
        default=-1.0)
    primitive_zmax: FloatProperty(
        name="Z max",
        description="Maximum height clipping of the primitive",
        default=1.0)
    primitive_sweepangle: FloatProperty(
        name="Sweep Angle",
        description="Angle of clipping around the Z axis",
        default=360.0)
    primitive_height: FloatProperty(
        name="Height",
        description="Height offset above XY plane",
        default=0.0)
    primitive_majorradius: FloatProperty(
        name="Major Radius",
        description="Radius of Torus ring",
        default=2.0)
    primitive_minorradius: FloatProperty(
        name="Minor Radius",
        description="Radius of Torus cross-section circle",
        default=0.5)
    primitive_phimin: FloatProperty(
        name="Minimum Cross-section",
        description="Minimum angle of cross-section circle",
        default=0.0)
    primitive_phimax: FloatProperty(
        name="Maximum Cross-section",
        description="Maximum angle of cross-section circle",
        default=360.0)
        
    primitive_point_type: EnumProperty(
        name="Point Type",
        description="Geometric primitive for points to be rendered as",
        items=[('particle', 'Particle', 'Point primitive'),
               ('blobby', 'Blobby', 'Implicit Surface (metaballs)'),
               ('sphere', 'Sphere', 'Two-sided sphere primitive'),
               ('disk', 'Disk', 'One-sided disk primitive')
               ],
        default='particle')
    primitive_point_width: FloatProperty(
        name="Point Width",
        description="Size of the rendered points",
        default=0.1)

    shading_override: BoolProperty(
        name="Override Default Shading Rate",
        description="Override the default shading rate for this object",
        default=False)
    shadingrate: FloatProperty(
        name="Micropolygon Length",
        description="Maximum distance between displacement samples (lower = more detailed shading)",
        default=1.0)
    watertight: BoolProperty(
        name="Watertight Dicing",
        description="Enables watertight dicing, which can solve cases where displacement causes visible seams in objects",
        default=False)
    geometric_approx_motion: FloatProperty(
        name="Motion Approximation",
        description="Shading Rate is scaled up by motionfactor/16 times the number of pixels of motion",
        default=1.0)
    geometric_approx_focus: FloatProperty(
        name="Focus Approximation",
        description="Shading Rate is scaled proportionally to the radius of DoF circle of confusion, multiplied by this value",
        default=-1.0)

    motion_segments_override: BoolProperty(
        name="Override Motion Samples",
        description="Override the global number of motion samples for this object",
        default=False)
    motion_segments: IntProperty(
        name="Motion Samples",
        description="Number of motion samples to take for multi-segment motion blur.  This should be raised if you notice segment artifacts in blurs. Set to 1 to disable for this object.",
        min=1, max=16, default=2)

    displacementbound: FloatProperty(
        name="Displacement Bound",
        description="Maximum distance the displacement shader can displace vertices.  This should be increased if you notice raised details being sharply cut off",
        precision=4,
        default=0.5)        

    shadinginterpolation: EnumProperty(
        name="Shading Interpolation",
        description="Method of interpolating shade samples across micropolygons",
        items=[('constant', 'Constant', 'Flat shaded micropolygons'),
               ('smooth', 'Smooth', 'Smooth Gourard shaded micropolygons')],
        default='smooth')

    matte: BoolProperty(
        name="Matte Object",
        description="Render the object as a matte cutout (alpha 0.0 in final frame)",
        default=False)

    holdout: BoolProperty(
        name="Holdout",
        description="Render the object as a holdout",
        default=False)

    visibility_camera: BoolProperty(
        name="Visible to Camera Rays",
        description="Object visibility to Camera Rays",
        default=True)
    visibility_trace_indirect: BoolProperty(
        name="All Indirect Rays",
        description="Sets all the indirect transport modes at once (specular & diffuse)",
        default=True)
    visibility_trace_transmission: BoolProperty(
        name="Visible to Transmission Rays",
        description="Object visibility to Transmission Rays (eg. shadow() and transmission())",
        default=True)

    raytrace_override: BoolProperty(
        name="Ray Trace Override",
        description="Override default RenderMan ray tracing behavior. Recommended for advanced users only",
        default=False)
    raytrace_pixel_variance: FloatProperty(
        name="Relative Pixel Variance",
        description="Allows this object to render to a different quality level than the main scene.  Actual pixel variance will be this number multiplied by the main pixel variance",
        default=1.0)
    raytrace_maxdiffusedepth: IntProperty(
        name="Max Diffuse Depth",
        description="Limit the number of diffuse bounces",
        min=1, max=16, default=1)
    raytrace_maxspeculardepth: IntProperty(
        name="Max Specular Depth",
        description="Limit the number of specular bounces",
        min=1, max=16, default=2)
    raytrace_tracedisplacements: BoolProperty(
        name="Trace Displacements",
        description="Ray Trace true displacement in rendered results",
        default=True)
    raytrace_autobias: BoolProperty(
        name="Ray Origin Auto Bias",
        description="Bias value is automatically computed",
        default=True)
    raytrace_bias: FloatProperty(
        name="Ray Origin Bias Amount",
        description="Offset applied to the ray origin, moving it slightly away from the surface launch point in the ray direction",
        default=0.01)
    raytrace_samplemotion: BoolProperty(
        name="Sample Motion Blur",
        description="Motion blur of other objects hit by rays launched from this object will be used",
        default=False)
    raytrace_decimationrate: IntProperty(
        name="Decimation Rate",
        description="Specifies the tessellation decimation for ray tracing. The most useful values are 1, 2, 4, and 16",
        default=1)
    raytrace_intersectpriority: IntProperty(
        name="Intersect Priority",
        description="Dictates a priority used when ray tracing overlapping materials",
        default=0)
    raytrace_ior: FloatProperty(
        name="Index of Refraction",
        description="When using nested dielectrics (overlapping materials), this should be set to the same value as the ior of your material",
        default=1.0)

    trace_displacements: BoolProperty(
        name="Trace Displacements",
        description="Enable high resolution displaced geometry for ray tracing",
        default=True)

    trace_samplemotion: BoolProperty(
        name="Trace Motion Blur",
        description="Rays cast from this object can intersect other motion blur objects",
        default=False)

    export_coordsys: BoolProperty(
        name="Export Coordinate System",
        description="Export a named coordinate system set to this object's name",
        default=False)
    coordsys: StringProperty(
        name="Coordinate System Name",
        description="Export a named coordinate system with this name",
        default="CoordSys")

    MatteID0: FloatVectorProperty(
        name="Matte ID 0",
        description="Matte ID 0 Color, you also need to add the PxrMatteID node to your bxdf",
        size=3,
        subtype='COLOR',
        default=[0.0, 0.0, 0.0], soft_min=0.0, soft_max=1.0)

    MatteID1: FloatVectorProperty(
        name="Matte ID 1",
        description="Matte ID 1 Color, you also need to add the PxrMatteID node to your bxdf",
        size=3,
        subtype='COLOR',
        default=[0.0, 0.0, 0.0], soft_min=0.0, soft_max=1.0)

    MatteID2: FloatVectorProperty(
        name="Matte ID 2",
        description="Matte ID 2 Color, you also need to add the PxrMatteID node to your bxdf",
        size=3,
        subtype='COLOR',
        default=[0.0, 0.0, 0.0], soft_min=0.0, soft_max=1.0)

    MatteID3: FloatVectorProperty(
        name="Matte ID 3",
        description="Matte ID 3 Color, you also need to add the PxrMatteID node to your bxdf",
        size=3,
        subtype='COLOR',
        default=[0.0, 0.0, 0.0], soft_min=0.0, soft_max=1.0)

    MatteID4: FloatVectorProperty(
        name="Matte ID 4",
        description="Matte ID 4 Color, you also need to add the PxrMatteID node to your bxdf",
        size=3,
        subtype='COLOR',
        default=[0.0, 0.0, 0.0], soft_min=0.0, soft_max=1.0)

    MatteID5: FloatVectorProperty(
        name="Matte ID 5",
        description="Matte ID 5 Color, you also need to add the PxrMatteID node to your bxdf",
        size=3,
        subtype='COLOR',
        default=[0.0, 0.0, 0.0], soft_min=0.0, soft_max=1.0)

    MatteID6: FloatVectorProperty(
        name="Matte ID 6",
        description="Matte ID 6 Color, you also need to add the PxrMatteID node to your bxdf",
        size=3,
        subtype='COLOR',
        default=[0.0, 0.0, 0.0], soft_min=0.0, soft_max=1.0)

    MatteID7: FloatVectorProperty(
        name="Matte ID 7",
        description="Matte ID 7 Color, you also need to add the PxrMatteID node to your bxdf",
        size=3,
        subtype='COLOR',
        default=[0.0, 0.0, 0.0], soft_min=0.0, soft_max=1.0)


class Tab_CollectionGroup(bpy.types.PropertyGroup):

    #################
    #       Tab     #
    #################

    bpy.types.Scene.rm_ipr = BoolProperty(
        name="IPR settings",
        description="Show some useful setting for the Interactive Rendering",
        default=False)

    bpy.types.Scene.rm_render = BoolProperty(
        name="Render settings",
        description="Show some useful setting for the Rendering",
        default=False)

    bpy.types.Scene.rm_render_external = BoolProperty(
        name="Render settings",
        description="Show some useful setting for external rendering",
        default=False)

    bpy.types.Scene.rm_help = BoolProperty(
        name="Help",
        description="Show some links about RenderMan and the documentation",
        default=False)

    bpy.types.Scene.rm_env = BoolProperty(
        name="Envlight",
        description="Show some settings about the selected Env light",
        default=False)

    bpy.types.Scene.rm_area = BoolProperty(
        name="AreaLight",
        description="Show some settings about the selected Area Light",
        default=False)

    bpy.types.Scene.rm_daylight = BoolProperty(
        name="DayLight",
        description="Show some settings about the selected Day Light",
        default=False)

    bpy.types.Scene.prm_cam = BoolProperty(
        name="Renderman Camera",
        description="Show some settings about the camera",
        default=False)


initial_aov_channels = [("a", "alpha", ""),
                        ("id", "id", "Returns the integer assigned via the 'identifier' attribute as the pixel value"),
                        ("z", "z_depth", "Depth from the camera in world space"),
                        ("zback", "z_back",
                         "Depth at the back of volumetric objects in world space"),
                        ("P", "P", "Position of the point hit by the incident ray"),
                        ("PRadius", "PRadius",
                         "Cross-sectional size of the ray at the hit point"),
                        ("cpuTime", "cpuTime", "The time taken to render a pixel"),
                        ("sampleCount", "sampleCount",
                         "The number of samples taken for the resulting pixel"),
                        ("Nn", "Nn", "Normalized shading normal"),
                        ("Ngn", "Ngn", "Normalized geometric normal"),
                        ("Tn", "Tn", "Normalized shading tangent"),
                        ("Vn", "Vn", "Normalized view vector (reverse of ray direction)"),
                        ("VLen", "VLen", "Distance to hit point along the ray"),
                        ("curvature", "curvature", "Local surface curvature"),
                        ("incidentRaySpread", "incidentRaySpread",
                         "Rate of spread of incident ray"),
                        ("mpSize", "mpSize",
                         "Size of the micropolygon that the ray hit"),
                        ("u", "u", "The parametric coordinates on the primitive"),
                        ("v", "v", "The parametric coordinates on the primitive"),
                        ("w", "w", "The parametric coordinates on the primitive"),
                        ("du", "du", "Derivatives of u, v, and w to adjacent micropolygons"),
                        ("dv", "dv", "Derivatives of u, v, and w to adjacent micropolygons"),
                        ("dw", "dw", "Derivatives of u, v, and w to adjacent micropolygons"),
                        ("dPdu", "dPdu", "Direction of maximal change in u, v, and w"),
                        ("dPdv", "dPdv", "Direction of maximal change in u, v, and w"),
                        ("dPdw", "dPdw", "Direction of maximal change in u, v, and w"),
                        ("dufp", "dufp",
                         "Multiplier to dPdu, dPdv, dPdw for ray differentials"),
                        ("dvfp", "dvfp",
                         "Multiplier to dPdu, dPdv, dPdw for ray differentials"),
                        ("dwfp", "dwfp",
                         "Multiplier to dPdu, dPdv, dPdw for ray differentials"),
                        ("time", "time", "Time sample of the ray"),
                        ("dPdtime", "dPdtime", "Motion vector"),
                        ("id", "id", "Returns the integer assigned via the identifier attribute as the pixel value"),
                        ("outsideIOR", "outsideIOR",
                         "Index of refraction outside this surface"),
                        ("__Pworld", "Pworld", "P in world-space"),
                        ("__Nworld", "Nworld", "Nn in world-space"),
                        ("__depth", "depth", "Multi-purpose AOV\nr : depth from camera in world-space\ng : height in world-space\nb : geometric facing ratio : abs(Nn.V)"),
                        ("__st", "st", "Texture coords"),
                        ("__Pref", "Pref", "Reference Position primvar (if available)"),
                        ("__Nref", "Nref", "Reference Normal primvar (if available)"),
                        ("__WPref", "WPref",
                         "Reference World Position primvar (if available)"),
                        ("__WNref", "WNref", "Reference World Normal primvar (if available)")]

@persistent
def initial_groups(scene):
    scene = bpy.context.scene
    if 'collector' not in scene.renderman.object_groups.keys():
        default_group = scene.renderman.object_groups.add()
        default_group.name = 'collector'
    if 'All' not in scene.renderman.light_groups.keys():
        default_group = scene.renderman.light_groups.add()
        default_group.name = 'All'


# collection of property group classes that need to be registered on
# module startup
classes = [RendermanPath,
           RendermanInlineRIB,
           RendermanGroup,
           LightLinking,
           RendermanMeshPrimVar,
           RendermanParticlePrimVar,
           RendermanMaterialSettings,
           RendermanAnimSequenceSettings,
           RendermanTextureSettings,
           RendermanParticleSettings,
           RendermanWorldSettings,
           RendermanDspyChannel,
           RendermanAOV,
           RendermanRenderLayerSettings,           
           RendermanSceneSettings,
           RendermanMeshGeometrySettings,
           RendermanCurveGeometrySettings,
           OpenVDBChannel,
           RendermanObjectSettings,
           Tab_CollectionGroup
           ]

def test_dynamic_settings():
    groupName = "RmanObjectSettings"
    attributes = {}
    #attributes['trace_displacements'] = FloatProperty(name='TRACE DISPS', default=0.5)
    #propertyGroupClass = type(groupName, (bpy.types.PropertyGroup,), attributes)

    def test_update_method(self, context):
        print("THIS IS AN UPDATE!")

    annotations = {'trace_displacements': FloatProperty(name='TRACE DISPS', default=0.5, update=test_update_method)  }
    attributes['__annotations__'] = annotations
    propertyGroupClass = type(groupName, (bpy.types.PropertyGroup,), attributes)
    setattr(propertyGroupClass, 'test_update_method', test_update_method)

    bpy.utils.register_class(propertyGroupClass)
    bpy.types.Object.rman = PointerProperty(
        type=propertyGroupClass, name="Rman Object Settings")


def register():

    # dynamically find integrators from args
    # register_integrator_settings(RendermanSceneSettings)
    # dynamically find camera from args
    # register_camera_settings()

    for cls in classes:
        bpy.utils.register_class(cls)

    #test_dynamic_settings()

    bpy.types.Scene.renderman = PointerProperty(
        type=RendermanSceneSettings, name="Renderman Scene Settings")
    bpy.types.World.renderman = PointerProperty(
        type=RendermanWorldSettings, name="Renderman World Settings")
    bpy.types.Material.renderman = PointerProperty(
        type=RendermanMaterialSettings, name="Renderman Material Settings")
    bpy.types.Texture.renderman = PointerProperty(
        type=RendermanTextureSettings, name="Renderman Texture Settings")
    bpy.types.ParticleSettings.renderman = PointerProperty(
        type=RendermanParticleSettings, name="Renderman Particle Settings")
    bpy.types.Mesh.renderman = PointerProperty(
        type=RendermanMeshGeometrySettings,
        name="Renderman Mesh Geometry Settings")
    bpy.types.Curve.renderman = PointerProperty(
        type=RendermanCurveGeometrySettings,
        name="Renderman Curve Geometry Settings")
    bpy.types.Object.renderman = PointerProperty(
        type=RendermanObjectSettings, name="Renderman Object Settings")

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    #bpy.utils.unregister_class(RmanObjectSettings)
    #FIXME bpy.utils.unregister_module(__name__)
