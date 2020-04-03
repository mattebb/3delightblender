from . import texture_utils
from . import string_utils
from . import shadergraph_utils
from . import node_desc
from ..rman_constants import RFB_ARRAYS_MAX_LEN
from ..rfb_logger import rfb_log
from collections import OrderedDict
from bpy.props import *
from copy import deepcopy
import bpy
import sys


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

# special string to indicate an empty string
# necessary for EnumProperty because it cannot
# take an empty string as an item value
__RMAN_EMPTY_STRING__ = '__empty__'

def set_rix_param(params, param_type, param_name, val, is_reference=False, is_array=False, array_len=-1):
    if is_array:
        if is_reference:
            if param_type == 'float':
                params.SetFloatReferenceArray(param_name, val, array_len)
            elif param_type == 'int':
                params.SetIntegerReferenceArray(param_name, val, array_len)
            elif param_type == 'color':
                params.SetColorReferenceArray(param_name, val, array_len)
        else:
            if param_type == 'float':
                params.SetFloatArray(param_name, val, array_len)
            elif param_type == 'int':
                params.SetIntegerArray(param_name, val, array_len)
            elif param_type == 'color':
                params.SetColorArray(param_name, val, int(array_len/3))
            elif param_type == 'string':
                params.SetStringArray(param_name, val, array_len)

    elif is_reference:
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
        if shadergraph_utils.is_float_type(from_socket):
            return "convert_%s_%s:resultRGB" % (from_node_name, from_sock_name)
        else:
            return "convert_%s_%s:resultF" % (from_node_name, from_sock_name)
    elif param_type == 'bxdf':
       return "%s" % (from_node_name) 
    else:
        return "%s:%s" % (from_node_name, from_sock_name)


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
            return build_output_param_str(mat_name + '_' + node.name, link.from_node, link.from_socket, shadergraph_utils.do_convert_socket(link.from_socket, to_socket), param_type)
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

    return build_output_param_str(mat_name, node, socket, shadergraph_utils.do_convert_socket(socket, to_socket), param_type)    


def is_vstruct_or_linked(node, param):
    meta = node.prop_meta[param]

    if 'vstructmember' not in meta.keys():
        return node.inputs[param].is_linked
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

def generate_array_property(node, prop_names, prop_meta, node_desc_param, update_array_size_func=None, update_array_elem_func=None):
    '''Generate the necessary properties for an array parameter and
    add it to the node

    Arguments:
        node (ShadingNode) - shading node
        prop_names (list) - the current list of property names for the shading node
        prop_meta (dict) - dictionary of the meta data for the properties for the node
        node_desc_param (NodeDescParam) - NodeDescParam object
        update_array_size_func (FunctionType) - callback function for when array size changes
        update_array_elem_func (FunctionType) - callback function for when an array element changes

    Returns:
        bool - True if succeeded. False if not.
    
    ''' 

    def is_array(ndp):          
        ''' A simple function to check if we indeed need to handle this parameter or should just ignore
        it. Ex: color ramps
        '''
        haswidget = hasattr(ndp, 'widget')
        if haswidget:
            if ndp.widget.lower() in ['null', 'colorramp', 'floatramp']:
                return False

        if hasattr(ndp, 'options'):
            for k,v in ndp.options.items():
                if k in ['colorramp', 'floatramp']:
                    return False

        return True

    if not is_array(node_desc_param):
        return False

    param_name = node_desc_param._name
    param_label = getattr(node_desc_param, 'label', param_name)
    prop_meta[param_name] = {'renderman_type': 'array', 
                            'renderman_array_type': node_desc_param.type,
                            'renderman_name':  param_name,
                            'label': param_label,
                            'type': node_desc_param.type
                            }
    prop_names.append(param_name)
    ui_label = "%s_uio" % param_name
    node.__annotations__[ui_label] = BoolProperty(name=ui_label, default=False)
    sub_prop_names = []
    arraylen_nm = '%s_arraylen' % param_name
    prop = IntProperty(name=arraylen_nm, 
                        default=0, soft_min=0, soft_max=RFB_ARRAYS_MAX_LEN,
                        description="Size of array",
                        update=update_array_size_func)
    node.__annotations__[arraylen_nm] = prop  

    for i in range(0, RFB_ARRAYS_MAX_LEN+1):
        ndp = deepcopy(node_desc_param)
        ndp._name = '%s[%d]' % (param_name, i)
        if hasattr(ndp, 'label'):
            ndp.label = '%s[%d]' % (ndp.label, i)
        #ndp.size = None
        ndp.connectable = True
        ndp.widget = ''
        name, meta, prop = generate_property(ndp, update_function=update_array_elem_func)
        meta['renderman_array_name'] = param_name
        sub_prop_names.append(ndp._name)
        prop_meta[ndp._name] = meta
        node.__annotations__[ndp._name] = prop  
            
    setattr(node, param_name, sub_prop_names)   
    return True  

def generate_property(sp, update_function=None):
    options = {'ANIMATABLE'}
    param_name = sp._name
    renderman_name = param_name

    # FIXME: figure out a better to skip
    # manifold struct members coming in from OSL shaders
    if 'manifold.' in renderman_name:
        return (None, None, None)

    # blender doesn't like names with __ but we save the
    # "renderman_name with the real one"
    if param_name[0] == '_':
        param_name = param_name[1:]
    if param_name[0] == '_':
        param_name = param_name[1:]

    param_label = sp.label if hasattr(sp,'label') else param_name
    param_widget = sp.widget.lower() if hasattr(sp,'widget') and sp.widget else 'default'
    param_type = sp.type 

    prop_meta = dict()
    param_default = sp.default
    if hasattr(sp, 'vstruct') and sp.vstruct:
        param_type = 'struct'
        prop_meta['vstruct'] = True
    else:
        param_type = sp.type
    renderman_type = param_type

    if hasattr(sp, 'vstructmember'):
        prop_meta['vstructmember'] = sp.vstructmember

    if hasattr(sp, 'vstructConditionalExpr'):
        prop_meta['vstructConditionalExpr'] = sp.vstructConditionalExpr        
     
    prop = None

    prop_meta['label'] = param_label
    prop_meta['widget'] = param_widget
    prop_meta['options'] = getattr(sp, 'options', OrderedDict())

    if hasattr(sp, 'connectable') and not sp.connectable:
        prop_meta['__noconnection'] = True

    if isinstance(prop_meta['options'], OrderedDict):
        for k,v in prop_meta['options'].items():
            if k in ['colorramp', 'floatramp']:
                return (None, None, None)

    # set this prop as non connectable
    if param_widget in ['null', 'checkbox', 'switch', 'colorramp']:
        prop_meta['__noconnection'] = True        


    if hasattr(sp, 'conditionalVisOps'):
        prop_meta['conditionalVisOp'] = sp.conditionalVisOps

    param_help = ''
    if hasattr(sp, 'help'):
        param_help = sp.help

    if hasattr(sp, 'riopt'):
        prop_meta['riopt'] = sp.riopt

    if hasattr(sp, 'riattr'):
        prop_meta['riattr'] = sp.riattr

    if hasattr(sp, 'primvar'):
        prop_meta['primvar'] = sp.primvar

    if hasattr(sp, 'inheritable'):
        prop_meta['inheritable'] = sp.inheritable
    
    if hasattr(sp, 'inherit_true_value'):
        prop_meta['inherit_true_value'] = sp.inherit_true_value

    if 'float' == param_type:
        if sp.is_array():
            prop = FloatProperty(name=param_label,
                                       default=0.0, precision=3,
                                       description=param_help,
                                       update=update_function)       
        else:
            if param_widget == 'checkbox' or param_widget == 'switch':
                
                prop = BoolProperty(name=param_label,
                                    default=bool(param_default),
                                    description=param_help, update=update_function)
            elif param_widget == 'mapper':
                items = []
                for k,v in sp.options.items():
                    items.append((str(v), k, ''))
                
                bl_default = ''
                for item in items:
                    if item[0] == str(param_default):
                        bl_default = item[0]
                        break                

                prop = EnumProperty(name=param_label,
                                    items=items,
                                    default=bl_default,
                                    description=param_help, update=update_function)
            else:
                param_min = sp.min if hasattr(sp, 'min') else (-1.0 * sys.float_info.max)
                param_max = sp.max if hasattr(sp, 'max') else sys.float_info.max
                param_min = sp.slidermin if hasattr(sp, 'slidermin') else param_min
                param_max = sp.slidermax if hasattr(sp, 'slidermax') else param_max   

                prop = FloatProperty(name=param_label,
                                     default=param_default, precision=3,
                                     soft_min=param_min, soft_max=param_max,
                                     description=param_help, update=update_function)


        renderman_type = 'float'

    elif param_type == 'int' or param_type == 'integer':
        if sp.is_array(): 
            prop = IntProperty(name=param_label,
                                default=0,
                                description=param_help, update=update_function)            
        else:
            param_default = int(param_default) if param_default else 0
            # make invertT default 0
            if param_name == 'invertT':
                param_default = 0

            if param_widget in ['checkbox', 'switch']:
                prop = BoolProperty(name=param_label,
                                    default=bool(param_default),
                                    description=param_help, update=update_function)

            elif param_widget == 'mapper':
                items = []
                for k,v in sp.options.items():
                    v = str(v)
                    if len(v.split(':')) > 1:
                        tokens = v.split(':')
                        v = tokens[1]
                        k = '%s:%s' % (k, tokens[0])
                    items.append((str(v), k, ''))
                
                bl_default = ''
                for item in items:
                    if item[0] == str(param_default):
                        bl_default = item[0]
                        break

                prop = EnumProperty(name=param_label,
                                    items=items,
                                    default=bl_default,
                                    description=param_help, update=update_function)
            else:
                pass
                param_min = int(sp.min) if hasattr(sp, 'min') else 0
                param_max = int(sp.max) if hasattr(sp, 'max') else 2 ** 31 - 1

                prop = IntProperty(name=param_label,
                                   default=param_default,
                                   soft_min=param_min,
                                   soft_max=param_max,
                                   description=param_help, update=update_function)
        renderman_type = 'int'

    elif param_type == 'color':
        if sp.is_array():
            prop = FloatVectorProperty(name=param_label,
                                    default=(1.0, 1.0, 1.0), size=3,
                                    subtype="COLOR",
                                    soft_min=0.0, soft_max=1.0,
                                    description=param_help, update=update_function)
        else:
            if param_default == 'null' or param_default is None:
                param_default = (0.0,0.0,0.0)
            prop = FloatVectorProperty(name=param_label,
                                    default=param_default, size=3,
                                    subtype="COLOR",
                                    soft_min=0.0, soft_max=1.0,
                                    description=param_help, update=update_function)
        renderman_type = 'color'
    elif param_type == 'shader':
        param_default = ''
        prop = StringProperty(name=param_label,
                              default=param_default,
                              description=param_help, update=update_function)
        renderman_type = 'string'
    elif param_type == 'string' or param_type == 'struct' or param_type == 'bxdf':
        if param_default is None:
            param_default = ''
        #else:
        #    param_default = str(param_default)

        if '__' in param_name:
            param_name = param_name[2:]

        if (param_widget in ['fileinput','assetidinput','assetidoutput']):
            prop = StringProperty(name=param_label,
                                  default=param_default, subtype="FILE_PATH",
                                  description=param_help, update=update_function)
        elif param_widget == 'mapper':
            items = []
            for k,v in sp.options.items():
                if v == '' or v == "''":
                    v = __RMAN_EMPTY_STRING__
                items.append((str(v), str(k), ''))
            
            if param_default == '' or param_default == "''":
                param_default = __RMAN_EMPTY_STRING__

            prop = EnumProperty(name=param_label,
                                default=param_default, description=param_help,
                                items=items,
                                update=update_function)

        elif param_widget == 'popup':
            items = []
            for k,v in sp.options.items():
                if v == '' or v == "''":
                    v = __RMAN_EMPTY_STRING__
                items.append((v, k, ''))                
            if param_default == '' or param_default == "''":
                param_default = __RMAN_EMPTY_STRING__

            prop = EnumProperty(name=param_label,
                                default=param_default, description=param_help,
                                items=items, update=update_function)

        elif param_widget == 'scenegraphlocation':
            reference_type = eval(sp.options['nodeType'])
            prop = PointerProperty(name=param_label, 
                        description=param_help,
                        type=reference_type)            

        else:
            prop = StringProperty(name=param_label,
                                default=str(param_default),
                                description=param_help, update=update_function)            
        renderman_type = param_type

    elif param_type == 'vector' or param_type == 'normal':
        if param_default is None:
            param_default = '0 0 0'
        prop = FloatVectorProperty(name=param_label,
                                   default=param_default, size=3,
                                   subtype="NONE",
                                   description=param_help, update=update_function)
    elif param_type == 'point':
        if param_default is None:
            param_default = '0 0 0'
        prop = FloatVectorProperty(name=param_label,
                                   default=param_default, size=3,
                                   subtype="XYZ",
                                   description=param_help, update=update_function)
        renderman_type = param_type
    elif param_type == 'int2':
        param_type = 'int'
        is_array = 2
        prop = IntVectorProperty(name=param_label,
                                 default=param_default, size=2,
                                 description=param_help, update=update_function)
        renderman_type = 'int'
        prop_meta['arraySize'] = 2   

    elif param_type == 'float2':
        param_type = 'float'
        is_array = 2
        prop = FloatVectorProperty(name=param_label,
                                 default=param_default, size=2,
                                 description=param_help, update=update_function)
        renderman_type = 'float'
        prop_meta['arraySize'] = 2      

    prop_meta['renderman_type'] = renderman_type
    prop_meta['renderman_name'] = renderman_name
    prop_meta['label'] = param_label
    prop_meta['type'] = param_type

    return (param_name, prop_meta, prop)

def set_material_rixparams(node, rman_sg_node, params, mat_name=None):
    # If node is OSL node get properties from dynamic location.
    if node.bl_idname == "PxrOSLPatternNode":

        if getattr(node, "codetypeswitch") == "EXT":
            prefs = bpy.context.preferences.addons[__package__].preferences
            osl_path = user_path(getattr(node, 'shadercode'))
            FileName = os.path.basename(osl_path)
            FileNameNoEXT,ext = os.path.splitext(FileName)
            out_file = os.path.join(
                user_path(prefs.env_vars.out), "shaders", FileName)
            if ext == ".oso":
                if not os.path.exists(out_file) or not os.path.samefile(osl_path, out_file):
                    if not os.path.exists(os.path.join(user_path(prefs.env_vars.out), "shaders")):
                        os.mkdir(os.path.join(user_path(prefs.env_vars.out), "shaders"))
                    shutil.copy(osl_path, out_file)
        for input_name, input in node.inputs.items():
            prop_type = input.renderman_type
            if input.is_linked:
                to_socket = input
                from_socket = input.links[0].from_socket

                param_type = prop_type
                param_name = input_name

                val = get_output_param_str(from_socket.node, mat_name, from_socket, to_socket, param_type)

                set_rix_param(params, param_type, param_name, val, is_reference=True)    

            elif type(input) != RendermanNodeSocketStruct:

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
                pass

            if(prop_name in ['sblur', 'tblur', 'notes']):
                pass

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
                    else:
                        val = get_output_param_str(
                                from_node, mat_name, from_socket, to_socket, param_type)

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
                            temp_mat_name = mat_name + '.' + from_socket.node.name

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
                    isArray = False
                    arrayLen = 0

                    # if this is a gain on PxrSurface and the lobe isn't
                    # enabled
                    
                    if node.bl_idname == 'PxrSurfaceBxdfNode' and \
                            prop_name in __GAINS_TO_ENABLE__ and \
                            not getattr(node, __GAINS_TO_ENABLE__[prop_name]):
                        val = [0, 0, 0] if meta[
                            'renderman_type'] == 'color' else 0

                    elif meta['renderman_type'] == 'string':
                        # FIXME: Need a better way to check for a frame variable
                        if '{F' in prop:
                            rman_sg_node.is_frame_sensitive = True
                        else:
                            rman_sg_node.is_frame_sensitive = False  

                        val = val = string_utils.convert_val(prop, type_hint=meta['renderman_type'])
                        if meta['widget'] in ['fileinput', 'assetidinput']:
                            options = meta['options']
                            # txmanager doesn't currently deal with ptex
                            if node.bl_idname == "PxrPtexturePatternNode":
                                val = string_utils.expand_string(val, display='ptex', asFilePath=True)        
                            # ies profiles don't need txmanager for converting                       
                            elif 'ies' in options:
                                val = string_utils.expand_string(val, display='ies', asFilePath=True)
                            # this is a texture
                            elif ('texture' in options) or ('env' in options):
                                tx_node_id = texture_utils.generate_node_id(node, param_name)
                                val = texture_utils.get_txmanager().get_txfile_from_id(tx_node_id)
                        elif meta['widget'] == 'assetidoutput':
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
                                val_ref_array.append(val)
                            else:
                                prop = getattr(node, nm)
                                val = string_utils.convert_val(prop, type_hint=param_type)
                                if param_type in node_desc.FLOAT3:
                                    val_array.extend(val)
                                else:
                                    val_array.append(val)
                        if val_ref_array:
                            set_rix_param(params, param_type, param_name, val_ref_array, is_reference=True, is_array=True, array_len=len(val_ref_array))
                        else:
                            set_rix_param(params, param_type, param_name, val_array, is_reference=False, is_array=True, array_len=len(val_array))
                        continue
                    else:

                        val = string_utils.convert_val(prop, type_hint=meta['renderman_type'])

                    if isArray:
                        pass
                    else:
                        set_rix_param(params, param_type, param_name, val, is_reference=False)
                        

    if node.plugin_name == 'PxrRamp':
        nt = bpy.data.node_groups[node.node_group]
        if nt:
            dummy_ramp = nt.nodes['ColorRamp']
            colors = []
            positions = []
            # double the start and end points
            positions.append(float(dummy_ramp.color_ramp.elements[0].position))
            colors.extend(dummy_ramp.color_ramp.elements[0].color[:3])
            for e in dummy_ramp.color_ramp.elements:
                positions.append(float(e.position))
                colors.extend(e.color[:3])
            positions.append(
                float(dummy_ramp.color_ramp.elements[-1].position))
            colors.extend(dummy_ramp.color_ramp.elements[-1].color[:3])

            params.SetFloatArray("colorRamp_Knots", positions, len(positions))
            params.SetColorArray("colorRamp_Colors", colors, len(positions))

            rman_interp_map = { 'LINEAR': 'linear', 'CONSTANT': 'constant'}
            interp = rman_interp_map.get(dummy_ramp.color_ramp.interpolation,'catmull-rom')
            params.SetString("colorRamp_Interpolation", interp )
    return params      

def set_rixparams(node, rman_sg_node, params, light):
    for prop_name, meta in node.prop_meta.items():
        if not hasattr(node, prop_name):
            continue
        prop = getattr(node, prop_name)
        # if property group recurse
        if meta['renderman_type'] == 'page' or prop_name == 'notes' or meta['renderman_type'] == 'enum':
            continue
        else:
            type = meta['renderman_type']
            name = meta['renderman_name']

            if 'renderman_array_name' in meta:
                continue
            elif meta['renderman_type'] == 'array':
                array_len = getattr(node, '%s_arraylen' % prop_name)
                sub_prop_names = getattr(node, prop_name)
                sub_prop_names = sub_prop_names[:array_len]
                val_array = []
                param_type = meta['renderman_array_type']
                
                for nm in sub_prop_names:
                    prop = getattr(node, nm)
                    val = string_utils.convert_val(prop, type_hint=param_type)
                    if param_type in node_desc.FLOAT3:
                        val_array.extend(val)
                    else:
                        val_array.append(val)
                set_rix_param(params, param_type, param_name, val_array, is_reference=False, is_array=True, array_len=len(val_array))
                continue

            elif meta['renderman_type'] == 'string':
                # FIXME: Need a better way to check for a frame variable
                if '{F' in prop:
                    rman_sg_node.is_frame_sensitive = True
                else:
                    rman_sg_node.is_frame_sensitive = False  
                                            
                val = val = string_utils.convert_val(prop, type_hint=meta['renderman_type'])
                if meta['widget'] in ['fileinput', 'assetidinput']:
                    options = meta['options']
                    # txmanager doesn't currently deal with ptex
                    if node.bl_idname == "PxrPtexturePatternNode":
                        val = string_utils.expand_string(val, display='ptex', asFilePath=True)        
                    # ies profiles don't need txmanager for converting                       
                    elif 'ies' in options:
                        val = string_utils.expand_string(val, display='ies', asFilePath=True)
                    # this is a texture
                    elif ('texture' in options) or ('env' in options):
                        tx_node_id = texture_utils.generate_node_id(node, prop_name)
                        val = texture_utils.get_txmanager().get_txfile_from_id(tx_node_id)
                elif meta['widget'] == 'assetidoutput':
                    display = 'openexr'
                    if 'texture' in meta['options']:
                        display = 'texture'
                    val = string_utils.expand_string(val, display='texture', asFilePath=True)      

                set_rix_param(params, type, name, val)      

            else:
                val = string_utils.convert_val(prop, type_hint=type)
                set_rix_param(params, type, name, val)

        if node.plugin_name in ['PxrBlockerLightFilter', 'PxrRampLightFilter', 'PxrRodLightFilter']:
            rm = light.renderman
            nt = light.node_tree
            if nt and rm.float_ramp_node in nt.nodes.keys():
                knot_param = 'ramp_Knots' if node.plugin_name == 'PxrRampLightFilter' else 'falloff_Knots'
                float_param = 'ramp_Floats' if node.plugin_name == 'PxrRampLightFilter' else 'falloff_Floats'
                params.Remove('%s' % knot_param)
                params.Remove('%s' % float_param)
                float_node = nt.nodes[rm.float_ramp_node]
                curve = float_node.mapping.curves[0]
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

                params.SetFloatArray(knot_param, knots, len(knots))
                params.SetFloatArray(float_param, vals, len(vals))

            if nt and rm.color_ramp_node in nt.nodes.keys():
                params.Remove('colorRamp_Knots')
                color_node = nt.nodes[rm.color_ramp_node]
                color_ramp = color_node.color_ramp
                colors = []
                positions = []
                # double the start and end points
                positions.append(float(color_ramp.elements[0].position))
                colors.extend(color_ramp.elements[0].color[:3])
                for e in color_ramp.elements:
                    positions.append(float(e.position))
                    colors.extend(e.color[:3])
                positions.append(
                    float(color_ramp.elements[-1].position))
                colors.extend(color_ramp.elements[-1].color[:3])

                params.SetFloatArray('colorRamp_Knots', positions, len(positions))
                params.SetColorArray('colorRamp_Colors', colors, len(positions))               


def property_group_to_rixparams(node, rman_sg_node, sg_node, light=None, mat_name=None):

    params = sg_node.params
    if mat_name:
        set_material_rixparams(node, rman_sg_node, params, mat_name=mat_name)
    else:
        set_rixparams(node, rman_sg_node, params, light=light)


def portal_inherit_dome_params(portal_node, dome, dome_node, rixparams):

    tx_node_id = texture_utils.generate_node_id(dome_node, 'lightColorMap')
    tex = string_utils.convert_val(texture_utils.get_txmanager().get_txfile_from_id(tx_node_id))
    rixparams.SetString('domeColorMap', string_utils.convert_val(texture_utils.get_txmanager().get_txfile_from_id(tx_node_id)))

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