import bpy

from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty, BoolVectorProperty
    
from ... import rman_bl_nodes

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

    object_group: StringProperty(name='Object Group')
    light_group: StringProperty(name='Light Group')
   

class RendermanRenderLayerSettings(bpy.types.PropertyGroup):
    render_layer: StringProperty()
    custom_aovs: CollectionProperty(type=RendermanAOV,
                                     name='Custom AOVs')
    custom_aov_index: IntProperty(min=-1, default=-1)

classes = [
    RendermanDspyChannel,
    RendermanAOV,
    RendermanRenderLayerSettings,           
]

def register():

    for cls in classes:
        bpy.utils.register_class(cls)

        

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
