import os
import bpy

RFB_ADDON_VERSION_MAJOR = 24
RFB_ADDON_VERSION_MINOR = 0
RFB_ADDON_VERSION_PATCH = 0
RFB_ADDON_VERSION = (RFB_ADDON_VERSION_MAJOR, RFB_ADDON_VERSION_MINOR, RFB_ADDON_VERSION_PATCH)
RFB_ADDON_VERSION_STRING = '%d.%d.%d' % (RFB_ADDON_VERSION_MAJOR, RFB_ADDON_VERSION_MINOR, RFB_ADDON_VERSION_PATCH)
RFB_ADDON_PATH = os.path.dirname(os.path.abspath(__file__))

BLENDER_VERSION_MAJOR = bpy.app.version[0]
BLENDER_VERSION_MINOR = bpy.app.version[1]
BLENDER_VERSION_PATCH = bpy.app.version[2]

BLENDER_VERSION = bpy.app.version

BLENDER_SUPPORTED_VERSION_MAJOR = 2
BLENDER_SUPPORTED_VERSION_MINOR = 83
BLENDER_SUPPORTED_VERSION_PATCH = 0
BLENDER_SUPPORTED_VERSION = (BLENDER_SUPPORTED_VERSION_MAJOR, BLENDER_SUPPORTED_VERSION_MINOR, BLENDER_SUPPORTED_VERSION_PATCH)

RMAN_SUPPORTED_VERSION_MAJOR = 24
RMAN_SUPPORTED_VERSION_MINOR = 0
RMAN_SUPPORTED_VERSION_BETA = ''
RMAN_SUPPORTED_VERSION = (RMAN_SUPPORTED_VERSION_MAJOR, RMAN_SUPPORTED_VERSION_MINOR, RMAN_SUPPORTED_VERSION_BETA)
RMAN_SUPPORTED_VERSION_STRING = '%d.%d%s' % (RMAN_SUPPORTED_VERSION_MAJOR, RMAN_SUPPORTED_VERSION_MINOR, RMAN_SUPPORTED_VERSION_BETA)


RFB_ADDON_DESCRIPTION = 'RenderMan %d.%d integration' % (RMAN_SUPPORTED_VERSION_MAJOR, RMAN_SUPPORTED_VERSION_MINOR)

NODE_LAYOUT_SPLIT = 0.5
RFB_ARRAYS_MAX_LEN = 50
RFB_MAX_USER_TOKENS = 10
RFB_VIEWPORT_MAX_BUCKETS = 10
RFB_PREFS_NAME = "RenderManForBlender"

RFB_FLOAT3 = ['color', 'point', 'vector', 'normal']
RFB_FLOATX = ['color', 'point', 'vector', 'normal', 'matrix']

RMAN_STYLIZED_FILTERS = [
    "PxrStylizedHatching",
    "PxrStylizedLines",
    "PxrStylizedToon"
]    

RMAN_STYLIZED_PATTERNS = ["PxrStylizedControl"]
RMAN_UTILITY_PATTERN_NAMES = [
                            "utilityPattern",
                            "userColor",
                            "inputAOV",
                            "utilityInteger"]

# special string to indicate an empty string
# necessary for EnumProperty because it cannot
# take an empty string as an item value
__RMAN_EMPTY_STRING__ = '__empty__'

# these are reserved property names for Blender's nodes
__RESERVED_BLENDER_NAMES__ = {
    'dimensions' : 'rman_dimensions',
    'inputs': 'rman_inputs',
    'outputs': 'rman_outputs',
    'resolution': 'rman_resolution'
}

CYCLES_NODE_MAP = {
    'ShaderNodeAttribute': 'node_attribute',
    'ShaderNodeBlackbody': 'node_blackbody',
    'ShaderNodeTexBrick': 'node_brick_texture',
    'ShaderNodeBrightContrast': 'node_brightness',
    'ShaderNodeTexChecker': 'node_checker_texture',
    'ShaderNodeBump': 'node_bump',
    'ShaderNodeCameraData': 'node_camera',
    'ShaderNodeTexChecker': 'node_checker_texture',
    'ShaderNodeCombineHSV': 'node_combine_hsv',
    'ShaderNodeCombineRGB': 'node_combine_rgb',
    'ShaderNodeCombineXYZ': 'node_combine_xyz',
    'ShaderNodeTexEnvironment': 'node_environment_texture',
    'ShaderNodeFresnel': 'node_fresnel',
    'ShaderNodeGamma': 'node_gamma',
    'ShaderNodeNewGeometry': 'node_geometry',
    'ShaderNodeTexGradient': 'node_gradient_texture',
    'ShaderNodeHairInfo': 'node_hair_info',
    'ShaderNodeInvert': 'node_invert',
    'ShaderNodeHueSaturation': 'node_hsv',
    'ShaderNodeTexImage': 'node_image_texture',
    'ShaderNodeHueSaturation': 'node_hsv',
    'ShaderNodeLayerWeight': 'node_layer_weight',
    'ShaderNodeLightFalloff': 'node_light_falloff',
    'ShaderNodeLightPath': 'node_light_path',
    'ShaderNodeTexMagic': 'node_magic_texture',
    'ShaderNodeMapping': 'node_mapping',
    'ShaderNodeMath': 'node_math',
    'ShaderNodeMixRGB': 'node_mix',
    'ShaderNodeTexMusgrave': 'node_musgrave_texture',
    'ShaderNodeTexNoise': 'node_noise_texture',
    'ShaderNodeNormal': 'node_normal',
    'ShaderNodeNormalMap': 'node_normal_map',
    'ShaderNodeObjectInfo': 'node_object_info',
    'ShaderNodeParticleInfo': 'node_particle_info',
    'ShaderNodeRGBCurve': 'node_rgb_curves',
    'ShaderNodeValToRGB': 'node_rgb_ramp',
    'ShaderNodeSeparateHSV': 'node_separate_hsv',
    'ShaderNodeSeparateRGB': 'node_separate_rgb',
    'ShaderNodeSeparateXYZ': 'node_separate_xyz',
    'ShaderNodeTexSky': 'node_sky_texture',
    'ShaderNodeTangent': 'node_tangent',
    'ShaderNodeTexCoord': 'node_texture_coordinate',
    'ShaderNodeUVMap': 'node_uv_map',
    'ShaderNodeValue': 'node_value',
    'ShaderNodeVectorCurves': 'node_vector_curves',
    'ShaderNodeVectorMath': 'node_vector_math',
    'ShaderNodeVectorTransform': 'node_vector_transform',
    'ShaderNodeTexVoronoi': 'node_voronoi_texture',
    'ShaderNodeTexWave': 'node_wave_texture',
    'ShaderNodeWavelength': 'node_wavelength',
    'ShaderNodeWireframe': 'node_wireframe',
    'ShaderNodeDisplacement': 'node_displacement'
}

# map types in args files to socket types
__RMAN_SOCKET_MAP__ = {
    'float': 'RendermanNodeSocketFloat',
    'color': 'RendermanNodeSocketColor',
    'string': 'RendermanNodeSocketString',
    'int': 'RendermanNodeSocketInt',
    'integer': 'RendermanNodeSocketInt',
    'struct': 'RendermanNodeSocketStruct',
    'normal': 'RendermanNodeSocketNormal',
    'vector': 'RendermanNodeSocketVector',
    'point': 'RendermanNodeSocketPoint',
    'void': 'RendermanNodeSocketStruct',
    'vstruct': 'RendermanNodeSocketVStruct',
    'bxdf': 'RendermanNodeSocketBxdf'
}
