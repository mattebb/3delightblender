from . import shadergraph_utils
from . import object_utils
from ..rfb_logger import rfb_log
import bpy
import sys


# ------------- Atom's helper functions -------------
GLOBAL_ZERO_PADDING = 5
# Objects that can be exported as a polymesh via Blender to_mesh() method.
# ['MESH','CURVE','FONT']
SUPPORTED_INSTANCE_TYPES = ['MESH', 'CURVE', 'FONT', 'SURFACE']
SUPPORTED_DUPLI_TYPES = ['FACES', 'VERTS', 'GROUP']    # Supported dupli types.
# These object types can have materials.
MATERIAL_TYPES = ['MESH', 'CURVE', 'FONT']
# Objects without to_mesh() conversion capabilities.
EXCLUDED_OBJECT_TYPES = ['LIGHT', 'CAMERA', 'ARMATURE']
# Only these light types affect volumes.
VOLUMETRIC_LIGHT_TYPES = ['SPOT', 'AREA', 'POINT']
MATERIAL_PREFIX = "mat_"
TEXTURE_PREFIX = "tex_"
MESH_PREFIX = "me_"
CURVE_PREFIX = "cu_"
GROUP_PREFIX = "group_"
MESHLIGHT_PREFIX = "meshlight_"
PSYS_PREFIX = "psys_"
DUPLI_PREFIX = "dupli_"
DUPLI_SOURCE_PREFIX = "dup_src_"

# ------------- Filtering -------------
def is_visible_layer(scene, ob):
    #
    #FIXME for i in range(len(scene.layers)):
    #    if scene.layers[i] and ob.layers[i]:
    #        return True
    return True

def get_renderman_layer(context):
    rm_rl = None
    layer = context.view_layer  
    rm_rl = layer.renderman 

    return rm_rl    

def get_render_variant(bl_scene):
    if bl_scene.renderman.is_ncr_license and bl_scene.renderman.renderVariant != 'prman':
        rfb_log().warning("XPU is not available for a non-commercial license.")
        return 'prman'

    if sys.platform == ("darwin") and bl_scene.renderman.renderVariant != 'prman':
        rfb_log().warning("XPU is not implemented on OSX: using RIS...")
        return 'prman'

    return bl_scene.renderman.renderVariant    

def get_light_group(light_ob, scene):
    """Return the name of the lightGroup for this
    light, if any

    Args:
    light_ob (bpy.types.Object) - object we are interested in
    scene (byp.types.Scene) - scene file to look for lights

    Returns:
    (str) - light group name
    """

    scene_rm = scene.renderman
    for lg in scene_rm.light_groups:
        for member in lg.members:
            if light_ob == member.light_ob:
                return lg.name
    return ''         

def get_all_lights(scene, include_light_filters=True):
    """Return a list of all lights in the scene, including
    mesh lights

    Args:
    scene (byp.types.Scene) - scene file to look for lights
    include_light_filters (bool) - whether or not light filters should be included in the list

    Returns:
    (list) - list of all lights
    """

    lights = list()
    for ob in scene.objects:
        if ob.type == 'LIGHT':
            if hasattr(ob.data, 'renderman'):
                if include_light_filters:
                    lights.append(ob)
                elif ob.data.renderman.renderman_light_role == 'RMAN_LIGHT':            
                    lights.append(ob)
        else:
            mat = getattr(ob, 'active_material', None)
            if not mat:
                continue
            output = shadergraph_utils.is_renderman_nodetree(mat)
            if not output:
                continue
            if len(output.inputs) > 1:
                socket = output.inputs[1]
                if socket.is_linked:
                    node = socket.links[0].from_node
                    if node.bl_label == 'PxrMeshLight':
                        lights.append(ob)       
    return lights

def get_light_groups_in_scene(scene):
    """ Return a dictionary of light groups in the scene

    Args:
    scene (byp.types.Scene) - scene file to look for lights

    Returns:
    (dict) - dictionary of light gropus to lights
    """

    lgt_grps = dict()
    for light in get_all_lights(scene, include_light_filters=False):
        light_shader = shadergraph_utils.get_light_node(light, include_light_filters=False)
        lgt_grp_nm = getattr(light_shader, 'lightGroup', '')
        if lgt_grp_nm:
            lights_list = lgt_grps.get(lgt_grp_nm, list())
            lights_list.append(light)
            lgt_grps[lgt_grp_nm] = lights_list

    return lgt_grps

def find_node_owner(node, context=None):
    """ Return the owner of this node

    Args:
    node (bpy.types.ShaderNode) - the node that the caller is trying to find its owner
    context (bpy.types.Context) - Blender context

    Returns:
    (id_data) - The owner of this node
    """    
    nt = node.id_data

    for mat in bpy.data.materials:
        if mat.node_tree == nt:
            return mat

    for world in bpy.data.worlds:
        if world.node_tree == nt:
            return world

    for ob in bpy.data.objects:
        if ob.type == 'LIGHT':
            light = ob.data
            if light.node_tree == nt:
                return ob
        elif ob.type == 'CAMERA':
            if shadergraph_utils.find_projection_node(ob) == node:
                return ob

    return None

def find_node_by_name(node_name, ob_name):
    """ Finder shader node and object by name(s)

    Args:
    node_name (str) - name of the node we are trying to find
    ob_name (str) - object name we are trying to look for that has node_name

    Returns:
    (list) - node and object
    """    

    mat = bpy.data.materials.get(ob_name, None)
    if mat:
        node = mat.node_tree.nodes.get(node_name, None)
        if node:
            return (node, mat)

    world = bpy.data.worlds.get(ob_name, None)
    if world:
        node = world.node_tree.nodes.get(node_name, None)
        if node:
            return (node, world)

    obj = bpy.data.objects.get(ob_name, None)
    if obj:
        rman_type = object_utils._detect_primitive_(obj)
        if rman_type in ['LIGHT', 'LIGHTFILTER']:
            light_node = shadergraph_utils.get_light_node(obj, include_light_filters=True)
            return (light_node, obj)
        elif rman_type == 'CAMERA':
            node = shadergraph_utils.find_projection_node(obj)
            if node:
                return (node, obj)

    return (None, None)

def is_renderable(scene, ob):
    return (is_visible_layer(scene, ob) and not ob.hide_render) or \
        (ob.type in ['ARMATURE', 'LATTICE', 'EMPTY'] and ob.instance_type not in SUPPORTED_DUPLI_TYPES)
    # and not ob.type in ('CAMERA', 'ARMATURE', 'LATTICE'))


def is_renderable_or_parent(scene, ob):
    if ob.type == 'CAMERA':
        return True
    if is_renderable(scene, ob):
        return True
    elif hasattr(ob, 'children') and ob.children:
        for child in ob.children:
            if is_renderable_or_parent(scene, child):
                return True
    return False


def is_data_renderable(scene, ob):
    return (is_visible_layer(scene, ob) and not ob.hide_render and ob.type not in ('EMPTY', 'ARMATURE', 'LATTICE'))


def renderable_objects(scene):
    return [ob for ob in scene.objects if (is_renderable(scene, ob) or is_data_renderable(scene, ob))]

def _get_subframes_(segs, scene):
    if segs == 0:
        return []
    min = -1.0
    rm = scene.renderman
    shutter_interval = rm.shutter_angle / 360.0
    if rm.shutter_timing == 'FRAME_CENTER':
        min = 0 - .5 * shutter_interval
    elif rm.shutter_timing == 'FRAME_CLOSE':
        min = 0 - shutter_interval
    elif rm.shutter_timing == 'FRAME_OPEN':
        min = 0

    return [min + i * shutter_interval / (segs - 1) for i in range(segs)]