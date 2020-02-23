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
import time

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
from . import rman_bl_nodes

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

    def displaydriver_items(self, context):
        items = []        
        for n in rman_bl_nodes.__RMAN_DISPLAY_NODES__:
            dspy = n.name.split('d_')[1]
            items.append((dspy, dspy, ''))
        return items

    displaydriver: EnumProperty(
        name="Display Driver",
        description="Display driver for rendering",
        items=displaydriver_items)

    show_displaydriver_settings: BoolProperty(
        name="Display Driver Settings",
        description="Show Display Driver Settings",
        default=False
    )

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




'''
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
'''
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

'''
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
'''

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

'''
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
'''

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
    
           RendermanParticlePrimVar,
           
           
           RendermanParticleSettings,
           #RendermanWorldSettings,
           RendermanDspyChannel,
           RendermanAOV,
           RendermanRenderLayerSettings,           
           
           
           Tab_CollectionGroup
           ]

def register():

    # dynamically find integrators from args
    # register_integrator_settings(RendermanSceneSettings)
    # dynamically find camera from args
    # register_camera_settings()

    for cls in classes:
        bpy.utils.register_class(cls)

    
    #bpy.types.World.renderman = PointerProperty(
    #    type=RendermanWorldSettings, name="Renderman World Settings")

    bpy.types.ParticleSettings.renderman = PointerProperty(
        type=RendermanParticleSettings, name="Renderman Particle Settings")
        

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    #bpy.utils.unregister_class(RmanObjectSettings)
    #FIXME bpy.utils.unregister_module(__name__)
