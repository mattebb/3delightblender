from . import scene_utils
from .rman_socket_utils import node_add_inputs
from .rman_socket_utils import node_add_outputs
from .rman_socket_utils import update_inputs
from ..rfb_logger import rfb_log
import bpy

def assetid_update_func(self, context, param_name):
    from . import texture_utils
    from . import filepath_utils

    node = self.node if hasattr(self, 'node') else self

    # get the real path if the value is the weird Blender relative path
    file_path = None
    if param_name in node:
        file_path = filepath_utils.get_real_path(node[param_name])
        node[param_name] = file_path

    if not hasattr(node, 'renderman_node_type'):
        return

    light = None
    mat = None
    ob = None
    active = None

    ob = scene_utils.find_node_owner(node, context)
    ob_type = type(ob)
    if ob_type == bpy.types.Material:
        mat = ob
    elif ob_type == bpy.types.World:
        active = ob
    elif ob.type == 'LIGHT':
        light = ob.data
        active = ob

    texture_utils.update_texture(node, light=light, mat=mat, ob=ob)

    if file_path:
        # update colorspace param from txmanager
        txfile = texture_utils.get_txmanager().txmanager.get_txfile_from_path(file_path)
        if txfile:
            params = txfile.params          
            param_colorspace = '%s_colorspace'  % param_name
            try:
                mdict = texture_utils.get_txmanager().txmanager.color_manager.colorspace_names()
                val = 0
                for i, nm in enumerate(mdict):
                    if nm == params.ocioconvert:
                        val = i+1
                        break

                node[param_colorspace] = val
            except AttributeError:
                pass                
    
    if mat:
        node.update_mat(mat)  
    if light:
        active.update_tag(refresh={'DATA'})

def update_conditional_visops(node):
    for param_name, prop_meta in getattr(node, 'prop_meta').items():
        conditionalVisOps = prop_meta.get('conditionalVisOps', None)
        if conditionalVisOps:
            cond_expr = conditionalVisOps.get('expr', None)
            if cond_expr:
                try:
                    hidden = not eval(cond_expr)
                    setattr(node, '%s_hidden' % param_name, hidden)
                    if hasattr(node, 'inputs') and param_name in node.inputs:
                        node.inputs[param_name].hide = hidden
                except:
                    rfb_log().debug("Error in conditional visop: %s" % (cond_expr))

def update_func_with_inputs(self, context):
    # check if this prop is set on an input
    node = self.node if hasattr(self, 'node') else self

    if context and hasattr(context, 'active_object'):
        if context.active_object:
            if context.active_object.type in ['CAMERA', 'LIGHT']:
                context.active_object.update_tag(refresh={'DATA'})

    if context and hasattr(context, 'material'):
        mat = context.material
        if mat:
            node.update_mat(mat)
    elif context and hasattr(context, 'node'):
        mat = context.space_data.id
        if mat:
            node.update_mat(mat)

    # update the conditional_vis_ops
    update_conditional_visops(node)

    if node.bl_idname in ['PxrLayerPatternOSLNode', 'PxrSurfaceBxdfNode']:
        node_add_inputs(node, node.name, node.prop_names)
    else:
        update_inputs(node)

    # set any inputs that are visible and param is hidden to hidden
    prop_meta = getattr(node, 'prop_meta')
    if hasattr(node, 'inputs'):
        for input_name, socket in node.inputs.items():
            if 'hidden' in prop_meta[input_name]:
                socket.hide = prop_meta[input_name]['hidden']

def update_array_size_func(self, context):
    '''
    Callback function for changes to array size/length property

    If there's a change in the size, we first remove all of the input/sockets
    from the ShadingNode related to arrays. We then re-add the input/socktes
    with the new size via the rman_socket_utils.node_add_inputs function. 
    We need to do this because Blender seems to draw all inputs in the node
    properties panel. This is a problem if the array size gets smaller.
    '''

    # check if this prop is set on an input
    node = self.node if hasattr(self, 'node') else self

    if context and hasattr(context, 'active_object'):
        if context.active_object:
            if context.active_object.type in ['CAMERA', 'LIGHT']:
                context.active_object.update_tag(refresh={'DATA'})

    if context and hasattr(context, 'material'):
        mat = getattr(context, 'material', None)
        if mat:
            node.update_mat(mat)
    elif context and hasattr(context, 'node'):
        mat = getattr(context.space_data, 'id', None)
        if mat:
            node.update_mat(mat)
    
    # first remove all sockets/inputs from the node related to arrays
    for prop_name,meta in node.prop_meta.items():
        renderman_type = meta.get('renderman_type', '')
        if renderman_type == 'array':
            sub_prop_names = getattr(node, prop_name)
            for nm in sub_prop_names:
                if nm in node.inputs.keys():
                    node.inputs.remove(node.inputs[nm])

    # now re-add all sockets/inputs
    node_add_inputs(node, node.name, node.prop_names)
           

def update_func(self, context):
    # check if this prop is set on an input
    node = self.node if hasattr(self, 'node') else self

    if context and hasattr(context, 'active_object'):
        if context.active_object:
            if context.active_object.type in ['CAMERA', 'LIGHT']:
                context.active_object.update_tag(refresh={'DATA'})

    if context and hasattr(context, 'material'):
        mat = getattr(context, 'material', None)
        if mat:
            node.update_mat(mat)

    elif context and hasattr(context, 'node'):
        mat = getattr(context.space_data, 'id', None)
        if mat:
            node.update_mat(mat)
    # update the conditional_vis_ops
    update_conditional_visops(node)

    # set any inputs that are visible and param is hidden to hidden
    prop_meta = getattr(node, 'prop_meta')
    if hasattr(node, 'inputs'):
        for input_name, socket in node.inputs.items():
            if input_name not in prop_meta:
                continue 
            if 'hidden' in prop_meta[input_name] \
                    and prop_meta[input_name]['hidden'] and not socket.hide:
                socket.hide = True      

def update_integrator_func(self, context):
    from .. import rman_render
    rr = rman_render.RmanRender.get_rman_render()
    rr.rman_scene_sync.update_integrator(context)            

def update_options_func(self, context):
    from .. import rman_render
    rr = rman_render.RmanRender.get_rman_render()
    rr.rman_scene_sync.update_global_options(context)   

def update_root_node_func(self, context):
    from .. import rman_render
    rr = rman_render.RmanRender.get_rman_render()
    rr.rman_scene_sync.update_root_node_func(context)      