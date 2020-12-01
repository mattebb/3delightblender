from . import shadergraph_utils
from ..rman_config import __RMAN_DISPLAY_CHANNELS__


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
    if rm.shutter_timing == 'CENTER':
        min = 0 - .5 * shutter_interval
    elif rm.shutter_timing == 'PRE':
        min = 0 - shutter_interval
    elif rm.shutter_timing == 'POST':
        min = 0

    return [min + i * shutter_interval / (segs - 1) for i in range(segs)]

def _fix_displays(context):
    scene = context.scene
    rm = scene.renderman
    rm_rl = None
    active_layer = context.view_layer
    for l in rm.render_layers:
        if l.render_layer == active_layer.name:
            rm_rl = l
            break
    if rm_rl:
        for aov in rm_rl.custom_aovs:
            for chan in aov.dspy_channels:
                settings = __RMAN_DISPLAY_CHANNELS__.get(chan.name, None)
                if settings:
                    print("Fixing channel: %s" % chan.name)
                    chan.channel_type = settings['channelType']
