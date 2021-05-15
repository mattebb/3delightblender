from . import texture_utils
from . import string_utils
from . import shadergraph_utils
from . import prefs_utils
from ..rman_constants import RFB_ARRAYS_MAX_LEN, __RMAN_EMPTY_STRING__, __RESERVED_BLENDER_NAMES__, RFB_FLOAT3
from ..rfb_logger import rfb_log
from collections import OrderedDict
from bpy.props import *
from copy import deepcopy
import bpy
import sys
import os
import shutil
import re


__GAINS_TO_ENABLE__ = {
    'diffuseGain': 'enableDiffuse',
    'specularFaceColor': 'enablePrimarySpecular',
    'specularEdgeColor': 'enablePrimarySpecular',
    'roughSpecularFaceColor': 'enableRoughSpecular',
    'roughSpecularEdgeColor': 'enableRoughSpecular',
    'clearcoatFaceColor': 'enableClearCoat',
    'clearcoatEdgeColor': 'enableClearCoat',
    'iridescenceFaceGain': 'enableIridescence',
    'iridescenceEdgeGain': 'enableIridescence',
    'fuzzGain': 'enableFuzz',
    'subsurfaceGain': 'enableSubsurface',
    'singlescatterGain': 'enableSingleScatter',
    'singlescatterDirectGain': 'enableSingleScatter',
    'refractionGain': 'enableGlass',
    'reflectionGain': 'enableGlass',
    'glowGain': 'enableGlow',
}

def get_property_default(node, prop_name):
    bl_prop_name = __RESERVED_BLENDER_NAMES__.get(prop_name, prop_name)
    prop = node.bl_rna.properties.get(bl_prop_name, None)
    dflt = None
    if prop:
        if getattr(prop, 'default_array', None):
            dflt = [p for p in prop.default_array]
        else:
            dflt = prop.default
            
    return dflt

def set_rix_param(params, param_type, param_name, val, is_reference=False, is_array=False, array_len=-1, node=None):
    """Sets a single parameter in an RtParamList

    Arguments:
        params (RtParamList) - param list to set
        param_type (str) - rman param type
        param_name (str) - rman param name
        val (AnyType) - the value to write to the RtParamList
        is_reference (bool) - whether this is reference parameter
        is_array (bool) - whether we are writing an array param type
        array_len (int) - length of array
        node (AnyType) - the Blender object that this param originally came from. This is necessary
                        so we can grab and compare val with the default value (see get_property_default)
    """


    if is_reference:
        if is_array:
            if param_type == 'float':
                params.SetFloatReferenceArray(param_name, val, array_len)
            elif param_type == 'int':
                params.SetIntegerReferenceArray(param_name, val, array_len)
            elif param_type == 'color':
                params.SetColorReferenceArray(param_name, val, array_len)         
        else:
            if param_type == "float":
                params.SetFloatReference(param_name, val)
            elif param_type == "int":
                params.SetIntegerReference(param_name, val)
            elif param_type == "color":
                params.SetColorReference(param_name, val)
            elif param_type == "point":
                params.SetPointReference(param_name, val)            
            elif param_type == "vector":
                params.SetVectorReference(param_name, val)
            elif param_type == "normal":
                params.SetNormalReference(param_name, val) 
            elif param_type == "struct":
                params.SetStructReference(param_name, val)        
            elif param_type == "bxdf":
                params.SetBxdfReference(param_name, val)       
    else:
        # check if we need to emit this parameter.
        if node != None and not prefs_utils.get_pref('rman_emit_default_params', False):
            dflt = get_property_default(node, param_name)

            # FIXME/TODO: currently, the python version of RtParamList
            # doesn't allow us to retrieve existing values. For now, only do the
            # default check when the param is not in there. Otherwise, we risk
            # not setting the value during IPR, if the user happens to change
            # the param val back to default. 
            if dflt != None and not params.HasParam(param_name):
                if isinstance(val, list):
                    dflt = list(dflt)

                if not is_array and isinstance(val, str):
                    # these explicit conversions are necessary because of EnumProperties
                    if param_type == 'string' and val == __RMAN_EMPTY_STRING__:
                        val = ""
                    elif param_type == 'int':
                        val = int(val)
                        dflt = int(dflt)
                    elif param_type == 'float':
                        val = float(val)
                        dflt = float(dflt)

                # Check if this param is marked always_write.
                # We still have some plugins where the Args file and C++ don't agree
                # on default behavior
                always_write = False
                prop_meta = getattr(node, 'prop_meta', dict())
                if param_name in node.prop_meta:
                    meta = prop_meta.get(param_name)
                    always_write = meta.get('always_write', always_write)

                if not always_write and val == dflt:
                    return                  

        if is_array:
            if param_type == 'float':
                params.SetFloatArray(param_name, val, array_len)
            elif param_type == 'int':
                params.SetIntegerArray(param_name, val, array_len)
            elif param_type == 'color':
                params.SetColorArray(param_name, val, int(array_len/3))
            elif param_type == 'string':
                params.SetStringArray(param_name, val, array_len)
        else:
            if param_type == "float":
                params.SetFloat(param_name, float(val))
            elif param_type == "int":
                params.SetInteger(param_name, int(val))
            elif param_type == "color":
                params.SetColor(param_name, val)
            elif param_type == "string":
                if val == __RMAN_EMPTY_STRING__:
                    val = ""
                params.SetString(param_name, val)
            elif param_type == "point":
                params.SetPoint(param_name, val)                            
            elif param_type == "vector":
                params.SetVector(param_name, val)
            elif param_type == "normal":
                params.SetNormal(param_name, val)               

def build_output_param_str(mat_name, from_node, from_socket, convert_socket=False, param_type=''):
    from_node_name = shadergraph_utils.get_node_name(from_node, mat_name)
    from_sock_name = shadergraph_utils.get_socket_name(from_node, from_socket)

    # replace with the convert node's output
    if convert_socket:
        if shadergraph_utils.is_socket_float_type(from_socket):
            return "convert_%s_%s:resultRGB" % (from_node_name, from_sock_name)
        else:
            return "convert_%s_%s:resultF" % (from_node_name, from_sock_name)
    elif param_type == 'bxdf':
       return "%s" % (from_node_name) 
    else:
        return "%s:%s" % (from_node_name, from_sock_name)

# hack!!!
current_group_node = None

def get_output_param_str(node, mat_name, socket, to_socket=None, param_type=''):
    # if this is a node group, hook it up to the input node inside!
    if node.bl_idname == 'ShaderNodeGroup':
        ng = node.node_tree
        group_output = next((n for n in ng.nodes if n.bl_idname == 'NodeGroupOutput'),
                            None)
        if group_output is None:
            return "error:error"

        in_sock = group_output.inputs[socket.name]
        if len(in_sock.links):
            link = in_sock.links[0]
            #instance = string_utils.sanitize_node_name(mat_name + '_' + node.name)
            return build_output_param_str(mat_name, link.from_node, link.from_socket, shadergraph_utils.do_convert_socket(link.from_socket, to_socket), param_type)
        else:
            return "error:error"
    if node.bl_idname == 'NodeGroupInput':
        global current_group_node

        if current_group_node is None:
            return "error:error"

        in_sock = current_group_node.inputs[socket.name]
        if len(in_sock.links):
            link = in_sock.links[0]
            return build_output_param_str(mat_name, link.from_node, link.from_socket, shadergraph_utils.do_convert_socket(link.from_socket, to_socket), param_type)
        else:
            return "error:error"

    if node.bl_idname == 'NodeReroute':
        if not node.inputs[0].is_linked:
            return None
        # for re-route nodes, find the real node that got re-routed
        node, socket = shadergraph_utils.get_rerouted_node(node)
        if node is None:
            return None
        
    return build_output_param_str(mat_name, node, socket, shadergraph_utils.do_convert_socket(socket, to_socket), param_type)    


def is_vstruct_or_linked(node, param):
    meta = node.prop_meta[param]
    if 'vstructmember' not in meta.keys():
        if param in node.inputs:
            return node.inputs[param].is_linked
        return False
    elif param in node.inputs and node.inputs[param].is_linked:
        return True
    else:
        vstruct_name, vstruct_member = meta['vstructmember'].split('.')
        if node.inputs[vstruct_name].is_linked:
            from_socket = node.inputs[vstruct_name].links[0].from_socket
            vstruct_from_param = "%s_%s" % (
                from_socket.identifier, vstruct_member)
            return vstruct_conditional(from_socket.node, vstruct_from_param)
        else:
            return False

# tells if this param has a vstuct connection that is linked and
# conditional met


def is_vstruct_and_linked(node, param):
    meta = node.prop_meta[param]

    if 'vstructmember' not in meta.keys():
        return False
    else:
        vstruct_name, vstruct_member = meta['vstructmember'].split('.')
        if node.inputs[vstruct_name].is_linked:
            from_socket = node.inputs[vstruct_name].links[0].from_socket
            # if coming from a shader group hookup across that
            if from_socket.node.bl_idname == 'ShaderNodeGroup':
                ng = from_socket.node.node_tree
                group_output = next((n for n in ng.nodes if n.bl_idname == 'NodeGroupOutput'),
                                    None)
                if group_output is None:
                    return False

                in_sock = group_output.inputs[from_socket.name]
                if len(in_sock.links):
                    from_socket = in_sock.links[0].from_socket
            vstruct_from_param = "%s_%s" % (
                from_socket.identifier, vstruct_member)          
            return vstruct_conditional(from_socket.node, vstruct_from_param)
        else:
            return False

# gets the value for a node walking up the vstruct chain


def get_val_vstruct(node, param):
    if param in node.inputs and node.inputs[param].is_linked:
        from_socket = node.inputs[param].links[0].from_socket
        return get_val_vstruct(from_socket.node, from_socket.identifier)
    elif is_vstruct_and_linked(node, param):
        return True
    else:
        return getattr(node, param)

# parse a vstruct conditional string and return true or false if should link


def vstruct_conditional(node, param):
    if not hasattr(node, 'shader_meta') and not hasattr(node, 'output_meta'):
        return False
    meta = getattr(
        node, 'shader_meta') if node.bl_idname == "PxrOSLPatternNode" else node.output_meta
    if param not in meta:
        return False
    meta = meta[param]
    if 'vstructConditionalExpr' not in meta.keys():
        return True

    expr = meta['vstructConditionalExpr']
    expr = expr.replace('connect if ', '')
    set_zero = False
    if ' else set 0' in expr:
        expr = expr.replace(' else set 0', '')
        set_zero = True

    tokens = expr.split()
    new_tokens = []
    i = 0
    num_tokens = len(tokens)
    while i < num_tokens:
        token = tokens[i]
        prepend, append = '', ''
        while token[0] == '(':
            token = token[1:]
            prepend += '('
        while token[-1] == ')':
            token = token[:-1]
            append += ')'

        if token == 'set':
            i += 1
            continue

        # is connected change this to node.inputs.is_linked
        if i < num_tokens - 2 and tokens[i + 1] == 'is'\
                and 'connected' in tokens[i + 2]:
            token = "is_vstruct_or_linked(node, '%s')" % token
            last_token = tokens[i + 2]
            while last_token[-1] == ')':
                last_token = last_token[:-1]
                append += ')'
            i += 3
        else:
            i += 1
        if hasattr(node, token):
            token = "get_val_vstruct(node, '%s')" % token

        new_tokens.append(prepend + token + append)

    if 'if' in new_tokens and 'else' not in new_tokens:
        new_tokens.extend(['else', 'False'])
    return eval(" ".join(new_tokens))

def set_frame_sensitive(rman_sg_node, prop):
    # check if the prop value has any frame token
    # ex: <f>, <f4>, <F4> etc.
    # if it does, it means we need to issue a material
    # update if the frame changes
    pat = re.compile(r'<[f|F]\d*>')
    m = pat.search(prop)
    if m:
        rman_sg_node.is_frame_sensitive = True        
    else:
        rman_sg_node.is_frame_sensitive = False  

def set_node_rixparams(node, rman_sg_node, params, ob=None, mat_name=None):
    # If node is OSL node get properties from dynamic location.
    if node.bl_idname == "PxrOSLPatternNode":

        if getattr(node, "codetypeswitch") == "EXT":
            prefs = prefs_utils.get_addon_prefs()
            osl_path = string_utils.expand_string(getattr(node, 'shadercode'))
            FileName = os.path.basename(osl_path)
            FileNameNoEXT,ext = os.path.splitext(FileName)
            shaders_path = os.path.join(string_utils.expand_string('<OUT>'), "shaders")
            out_file = os.path.join(shaders_path, FileName)
            if ext == ".oso":
                if not os.path.exists(out_file) or not os.path.samefile(osl_path, out_file):
                    if not os.path.exists(shaders_path):
                        os.mkdir(shaders_path)
                    shutil.copy(osl_path, out_file)
        for input_name, input in node.inputs.items():
            prop_type = input.renderman_type
            if input.is_linked:
                to_socket = input
                from_socket = input.links[0].from_socket

                param_type = prop_type
                param_name = input_name

                val = get_output_param_str(from_socket.node, mat_name, from_socket, to_socket, param_type)
                if val:
                    set_rix_param(params, param_type, param_name, val, is_reference=True)    

            elif type(input).__name__ != 'RendermanNodeSocketStruct':

                param_type = prop_type
                param_name = input_name
                val = string_utils.convert_val(input.default_value, type_hint=prop_type)
                set_rix_param(params, param_type, param_name, val, is_reference=False)                


    # Special case for SeExpr Nodes. Assume that the code will be in a file so
    # that needs to be extracted.
    elif node.bl_idname == "PxrSeExprPatternNode":
        fileInputType = node.codetypeswitch

        for prop_name, meta in node.prop_meta.items():
            if prop_name in ["codetypeswitch", 'filename']:
                pass
            elif prop_name == "internalSearch" and fileInputType == 'INT':
                if node.internalSearch != "":
                    script = bpy.data.texts[node.internalSearch]

                    params.SetString("expression", script.as_string() )
            elif prop_name == "shadercode" and fileInputType == "NODE":
                params.SetString("expression", node.expression)
            else:
                prop = getattr(node, prop_name)
                # if input socket is linked reference that
                if prop_name in node.inputs and \
                        node.inputs[prop_name].is_linked:

                    to_socket = node.inputs[prop_name]
                    from_socket = to_socket.links[0].from_socket
                    from_node = to_socket.links[0].from_node

                    param_type = meta['renderman_type']
                    param_name = meta['renderman_name']

                    val = get_output_param_str(
                            from_socket.node, mat_name, from_socket, to_socket, param_type)
                    if val:
                        set_rix_param(params, param_type, param_name, val, is_reference=True)                            
                # else output rib
                else:
                    param_type = meta['renderman_type']
                    param_name = meta['renderman_name']

                    val = string_utils.convert_val(prop, type_hint=meta['renderman_type'])
                    set_rix_param(params, param_type, param_name, val, is_reference=False)                          

    else:

        for prop_name, meta in node.prop_meta.items():
            if node.plugin_name == 'PxrRamp' and prop_name in ['colors', 'positions']:
                continue

            param_widget = meta.get('widget', 'default')
            if param_widget == 'null' and 'vstructmember' not in meta:
                # if widget is marked null, don't export parameter and rely on default
                # unless it has a vstructmember
                continue

            else:
                prop = getattr(node, prop_name)
                # if property group recurse
                if meta['renderman_type'] == 'page':
                    continue
                elif prop_name == 'inputMaterial' or \
                        ('vstruct' in meta and meta['vstruct'] is True) or \
                        ('type' in meta and meta['type'] == 'vstruct'):
                    continue

                # if input socket is linked reference that
                elif hasattr(node, 'inputs') and prop_name in node.inputs and \
                        node.inputs[prop_name].is_linked:

                    to_socket = node.inputs[prop_name]
                    from_socket = to_socket.links[0].from_socket
                    from_node = to_socket.links[0].from_node

                    param_type = meta['renderman_type']
                    param_name = meta['renderman_name']

                    if 'arraySize' in meta:
                        pass
                    elif 'renderman_array_name' in meta:
                        continue                    
                    else:
                        val = get_output_param_str(
                                from_node, mat_name, from_socket, to_socket, param_type)
                        if val:
                            set_rix_param(params, param_type, param_name, val, is_reference=True)                  

                # see if vstruct linked
                elif is_vstruct_and_linked(node, prop_name):
                    vstruct_name, vstruct_member = meta[
                        'vstructmember'].split('.')
                    from_socket = node.inputs[
                        vstruct_name].links[0].from_socket

                    temp_mat_name = mat_name

                    if from_socket.node.bl_idname == 'ShaderNodeGroup':
                        ng = from_socket.node.node_tree
                        group_output = next((n for n in ng.nodes if n.bl_idname == 'NodeGroupOutput'),
                                            None)
                        if group_output is None:
                            return False

                        in_sock = group_output.inputs[from_socket.name]
                        if len(in_sock.links):
                            from_socket = in_sock.links[0].from_socket
                            #temp_mat_name = mat_name + '.' + from_socket.node.name
                            temp_mat_name = mat_name
                            
                    vstruct_from_param = "%s_%s" % (
                        from_socket.identifier, vstruct_member)
                    if vstruct_from_param in from_socket.node.output_meta:
                        actual_socket = from_socket.node.output_meta[
                            vstruct_from_param]

                        param_type = meta['renderman_type']
                        param_name = meta['renderman_name']

                        node_meta = getattr(
                            node, 'shader_meta') if node.bl_idname == "PxrOSLPatternNode" else node.output_meta                        
                        node_meta = node_meta.get(vstruct_from_param)
                        is_reference = True
                        val = get_output_param_str(
                               from_socket.node, temp_mat_name, actual_socket, to_socket=None, param_type=param_type)
                        if node_meta:
                            expr = node_meta.get('vstructConditionalExpr')
                            # check if we should connect or just set a value
                            if expr:
                                if expr.split(' ')[0] == 'set':
                                    val = 1
                                    is_reference = False      
                        if val:                  
                            set_rix_param(params, param_type, param_name, val, is_reference=is_reference)

                    else:
                        rfb_log().warning('Warning! %s not found on %s' %
                              (vstruct_from_param, from_socket.node.name))

                # else output rib
                else:
                    # if struct is not linked continue
                    if meta['renderman_type'] in ['struct', 'enum']:
                        continue

                    param_type = meta['renderman_type']
                    param_name = meta['renderman_name']
                    val = None
                    arrayLen = 0

                    # if this is a gain on PxrSurface and the lobe isn't
                    # enabled
                    
                    if node.bl_idname == 'PxrSurfaceBxdfNode' and \
                            prop_name in __GAINS_TO_ENABLE__ and \
                            not getattr(node, __GAINS_TO_ENABLE__[prop_name]):
                        val = [0, 0, 0] if meta[
                            'renderman_type'] == 'color' else 0

                    elif meta['renderman_type'] == 'string':
                        if rman_sg_node:
                            set_frame_sensitive(rman_sg_node, prop)

                        val = string_utils.expand_string(prop)
                        if param_widget in ['fileinput', 'assetidinput']:
                            options = meta['options']
                            # txmanager doesn't currently deal with ptex
                            if node.bl_idname == "PxrPtexturePatternNode":
                                val = string_utils.expand_string(val, display='ptex', asFilePath=True)        
                            # ies profiles don't need txmanager for converting                       
                            elif 'ies' in options:
                                val = string_utils.expand_string(val, display='ies', asFilePath=True)
                            # this is a texture
                            elif ('texture' in options) or ('env' in options) or ('imageplane' in options):
                                tx_node_id = texture_utils.generate_node_id(node, param_name, ob=ob)
                                tx_val = texture_utils.get_txmanager().get_output_tex_from_id(tx_node_id)
                                val = tx_val if tx_val != '' else val
                        elif param_widget == 'assetidoutput':
                            display = 'openexr'
                            if 'texture' in meta['options']:
                                display = 'texture'
                            val = string_utils.expand_string(val, display='texture', asFilePath=True)

                    elif 'renderman_array_name' in meta:
                        continue
                    elif meta['renderman_type'] == 'array':
                        array_len = getattr(node, '%s_arraylen' % prop_name)
                        sub_prop_names = getattr(node, prop_name)
                        sub_prop_names = sub_prop_names[:array_len]
                        val_array = []
                        val_ref_array = []
                        param_type = meta['renderman_array_type']
                        
                        for nm in sub_prop_names:
                            if hasattr(node, 'inputs')  and nm in node.inputs and \
                                node.inputs[nm].is_linked:

                                to_socket = node.inputs[nm]
                                from_socket = to_socket.links[0].from_socket
                                from_node = to_socket.links[0].from_node

                                val = get_output_param_str(
                                    from_node, mat_name, from_socket, to_socket, param_type)
                                if val:
                                    val_ref_array.append(val)
                            else:
                                prop = getattr(node, nm)
                                val = string_utils.convert_val(prop, type_hint=param_type)
                                if param_type in RFB_FLOAT3:
                                    val_array.extend(val)
                                else:
                                    val_array.append(val)
                        if val_ref_array:
                            set_rix_param(params, param_type, param_name, val_ref_array, is_reference=True, is_array=True, array_len=len(val_ref_array))
                        else:
                            set_rix_param(params, param_type, param_name, val_array, is_reference=False, is_array=True, array_len=len(val_array))
                        continue
                    elif meta['renderman_type'] == 'colorramp':
                        nt = bpy.data.node_groups[node.rman_fake_node_group]
                        if nt:
                            ramp_name =  prop
                            color_ramp_node = nt.nodes[ramp_name]                            
                            colors = []
                            positions = []
                            # double the start and end points
                            positions.append(float(color_ramp_node.color_ramp.elements[0].position))
                            colors.append(color_ramp_node.color_ramp.elements[0].color[:3])
                            for e in color_ramp_node.color_ramp.elements:
                                positions.append(float(e.position))
                                colors.append(e.color[:3])
                            positions.append(
                                float(color_ramp_node.color_ramp.elements[-1].position))
                            colors.append(color_ramp_node.color_ramp.elements[-1].color[:3])

                            params.SetInteger('%s' % prop_name, len(positions))
                            params.SetFloatArray("%s_Knots" % prop_name, positions, len(positions))
                            params.SetColorArray("%s_Colors" % prop_name, colors, len(positions))

                            rman_interp_map = { 'LINEAR': 'linear', 'CONSTANT': 'constant'}
                            interp = rman_interp_map.get(color_ramp_node.color_ramp.interpolation,'catmull-rom')
                            params.SetString("%s_Interpolation" % prop_name, interp )         
                        continue               
                    elif meta['renderman_type'] == 'floatramp':
                        nt = bpy.data.node_groups[node.rman_fake_node_group]
                        if nt:
                            ramp_name =  prop
                            float_ramp_node = nt.nodes[ramp_name]                            

                            curve = float_ramp_node.mapping.curves[0]
                            knots = []
                            vals = []
                            # double the start and end points
                            knots.append(curve.points[0].location[0])
                            vals.append(curve.points[0].location[1])
                            for p in curve.points:
                                knots.append(p.location[0])
                                vals.append(p.location[1])
                            knots.append(curve.points[-1].location[0])
                            vals.append(curve.points[-1].location[1])

                            params.SetInteger('%s' % prop_name, len(knots))
                            params.SetFloatArray('%s_Knots' % prop_name, knots, len(knots))
                            params.SetFloatArray('%s_Floats' % prop_name, vals, len(vals))    
                            
                            # Blender doesn't have an interpolation selection for float ramps. Default to catmull-rom
                            interp = 'catmull-rom'
                            params.SetString("%s_Interpolation" % prop_name, interp )                          
                        continue
                    else:

                        val = string_utils.convert_val(prop, type_hint=meta['renderman_type'])

                    set_rix_param(params, param_type, param_name, val, is_reference=False, node=node)
                        
    return params      

def property_group_to_rixparams(node, rman_sg_node, sg_node, ob=None, mat_name=None):

    params = sg_node.params
    set_node_rixparams(node, rman_sg_node, params, ob=ob, mat_name=mat_name)

def portal_inherit_dome_params(portal_node, dome, dome_node, rixparams):

    tx_node_id = texture_utils.generate_node_id(dome_node, 'lightColorMap', ob=dome)
    tx_val = texture_utils.get_txmanager().get_output_tex_from_id(tx_node_id)
    rixparams.SetString('domeColorMap', tx_val) 

    prop = getattr(portal_node, 'colorMapGamma')
    if string_utils.convert_val(prop) == (1.0, 1.0, 1.0):
        prop = getattr(dome_node, 'colorMapGamma')
        rixparams.SetVector('colorMapGamma', string_utils.convert_val(prop, type_hint='vector'))

    prop = getattr(portal_node, 'colorMapSaturation')
    if string_utils.convert_val(prop) == 1.0:
        prop = getattr(dome_node, 'colorMapSaturation')
        rixparams.SetFloat('colorMapSaturation', string_utils.convert_val(prop, type_hint='float'))

    prop = getattr(portal_node, 'enableTemperature')
    if string_utils.convert_val(prop):
        prop = getattr(dome_node, 'enableTemperature')
        rixparams.SetInteger('enableTemperature', string_utils.convert_val(prop, type_hint='int'))        
        prop = getattr(dome_node, 'temperature')
        rixparams.SetFloat('temperature', string_utils.convert_val(prop, type_hint='float'))   

    prop = getattr(dome_node, 'intensity')
    rixparams.SetFloat('intensity', string_utils.convert_val(prop, type_hint='float'))        
    prop = getattr(dome_node, 'exposure')
    rixparams.SetFloat('exposure', string_utils.convert_val(prop, type_hint='float')) 
    prop = getattr(dome_node, 'specular')
    rixparams.SetFloat('specular', string_utils.convert_val(prop, type_hint='float'))  
    prop = getattr(dome_node, 'diffuse')
    rixparams.SetFloat('diffuse', string_utils.convert_val(prop, type_hint='float'))   
    prop = getattr(dome_node, 'lightColor')
    rixparams.SetColor('lightColor', string_utils.convert_val(prop, type_hint='color')) 