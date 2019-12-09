from . import string_utils
from . import prefs_utils
from .. import rman_constants
from collections import OrderedDict
import bpy
import os

def get_channel_name(aov, layer_name):
    aov_name = aov.name.replace(' ', '')
    aov_channel_name = aov.channel_name
    if not aov.aov_name or not aov.channel_name:
        return ''
    elif aov.aov_name == "color rgba":
        aov_channel_name = "Ci,a"
    # Remaps any color lpe channel names to a denoise friendly one
    elif aov_name in channel_name_map.keys():
        aov_channel_name = '%s_%s_%s' % (
            channel_name_map[aov_name], aov_name, layer_name)

    elif aov.aov_name == "color custom_lpe":
        aov_channel_name = aov.name

    else:
        aov_channel_name = '%s_%s' % (
            aov_name, layer_name)

    return aov_channel_name

def _default_dspy_params():
    d = {}
    d[u'enable'] = { 'type': u'int', 'value': True}
    d[u'lpeLightGroup'] = { 'type': u'string', 'value': None}
    d[u'remap_a'] = { 'type': u'float', 'value': 0.0}
    d[u'remap_b'] = { 'type': u'float', 'value': 0.0}
    d[u'remap_c'] = { 'type': u'float', 'value': 0.0}  
    d[u'exposure'] = { 'type': u'float2', 'value': [1.0, 1.0] }
    d[u'filter'] = {'type': u'string', 'value': 'default'}
    d[u'filterwidth'] = { 'type': u'float2', 'value': [2,2]}   
    d[u'statistics'] = { 'type': u'string', 'value': 'none'}

    return d    

def _add_denoiser_channels(dspys_dict, dspy_params):
    """
    Add the necessary dspy channels for denoiser. We assume
    the beauty display will be used as the variance file
    """

    denoise_aovs = [
        # (name, declare type/name, source, statistics, filter)
        ("Ci", 'color', None, None, None),
        ("a", 'float', None, None, None),
        ("mse", 'color', 'color Ci', 'mse', None),
        ("albedo", 'color',
        'color lpe:nothruput;noinfinitecheck;noclamp;unoccluded;overwrite;C(U2L)|O',
        None, None),
        ("albedo_var", 'color', 'color lpe:nothruput;noinfinitecheck;noclamp;unoccluded;overwrite;C(U2L)|O',
        "variance", None),
        ("diffuse", 'color', 'color lpe:C(D[DS]*[LO])|O', None, None),
        ("diffuse_mse", 'color', 'color lpe:C(D[DS]*[LO])|O', 'mse', None),
        ("specular", 'color', 'color lpe:CS[DS]*[LO]', None, None),
        ("specular_mse", 'color', 'color lpe:CS[DS]*[LO]', 'mse', None),
        ("zfiltered", 'float', 'zfiltered', None, True),
        ("zfiltered_var", 'float', 'zfiltered', "variance", True),
        ("normal", 'normal', 'normal Nn', None, None),
        ("normal_var", 'normal', 'normal Nn', "variance", None),
        ("forward", 'vector', 'vector motionFore', None, None),
        ("backward", 'vector', 'vector motionBack', None, None)
    ]
    for aov, declare_type, source, statistics, do_filter in denoise_aovs:
        dspy_channels = dspys_dict['displays']['beauty']['params']['displayChannels']
        if aov in dspy_channels:
            continue

        if aov not in dspys_dict['channels']:
            d = _default_dspy_params()

            if source:
                d[u'channelSource'] = {'type': u'string', 'value': source}
            d[u'channelType'] = { 'type': u'string', 'value': declare_type}
            d[u'statistics'] = { 'type': u'string', 'value': statistics}
            dspys_dict['channels'][aov] =  d  

        dspys_dict['displays']['beauty']['params']['displayChannels'].append(aov)

    filePath = dspys_dict['displays']['beauty']['filePath']
    f,ext = os.path.splitext(filePath)
    dspys_dict['displays']['beauty']['filePath'] = f + '_variance' + ext

def _get_dspy_dict_viewport(rm_rl, rman_scene, expandTokens=True):

    dspys_dict = {'displays': OrderedDict(), 'channels': {}}
    display_driver = 'blender'

    dspy_params = {}                        
    dspy_params['displayChannels'] = []

    d = _default_dspy_params()
    d[u'channelSource'] = {'type': u'string', 'value': 'Ci'}
    d[u'channelType'] = { 'type': u'string', 'value': 'color'}       
    dspys_dict['channels']['Ci'] = d
    d = _default_dspy_params()
    d[u'channelSource'] = {'type': u'string', 'value': 'a'}
    d[u'channelType'] = { 'type': u'string', 'value': 'float'}          
    dspys_dict['channels']['a'] = d     
    dspy_params['displayChannels'].append('Ci')
    dspy_params['displayChannels'].append('a')

    dspys_dict['displays']['beauty'] = {
        'driverNode': display_driver,
        'filePath': 'beauty',
        'denoise': False,
        'denoise_mode': 'singleframe',
        'camera': None,
        'params': dspy_params}

    return dspys_dict   

def get_dspy_dict(rman_scene, expandTokens=True):
    """
    Create a dictionary of display channels and displays. The layout:

        { 'channels': {
        u'Ci': { u'channelSource': { 'type': u'string', 'value': u'Ci'},
                 u'channelType': { 'type': u'string', 'value': u'color'},
                 u'enable': { 'type': u'int', 'value': True},
                 u'lpeLightGroup': { 'type': u'string', 'value': None},
                 u'remap_a': { 'type': u'float', 'value': 0.0},
                 u'remap_b': { 'type': u'float', 'value': 0.0},
                 u'remap_c': { 'type': u'float', 'value': 0.0}
               },
        u'a': { u'channelSource': { 'type': u'string', 'value': u'a'},
                u'channelType': { 'type': u'string', 'value': u'float'},
                u'enable': { 'type': u'int', 'value': True},
                u'lpeLightGroup': { 'type': u'string', 'value': None},
                u'remap_a': { 'type': u'float', 'value': 0.0},
                u'remap_b': { 'type': u'float', 'value': 0.0},
                u'remap_c': { 'type': u'float', 'value': 0.0}
              }
      },
      'displays': { u'rmanDefaultDisplay':
                      { 'driverNode': u'd_openexr1',
                        'filePath': u'{OUT}/{blender}/images/{scene}.{F4}.{ext}',
                        'params': { u'enable': { 'type': u'int', 'value': True},
                                    u'displayChannels': { 'type': u'message', 'value': [ u'Ci', u'a']},
                                    u'displayType': { 'type': u'message', 'value': u'd_openexr'},
                                    u'exposure': { 'type': u'float2', 'value': [1.0, 1.0]},
                                    u'filter': { 'type': u'string', 'value': 'default},
                                    u'filterwidth': { 'type': u'float2', 'value': [1.0, 1.0]},
                                    u'remap_a': { 'type': u'float', 'value': 0.0},
                                    u'remap_b': { 'type': u'float', 'value': 0.0},
                                    u'remap_c': { 'type': u'float', 'value': 0.0}
                                  }
                      }
                  }
        }

    """

    rm = rman_scene.bl_scene.renderman
    rm_rl = rman_scene.rm_rl
    layer = rman_scene.bl_view_layer
    dspys_dict = {'displays': OrderedDict(), 'channels': {}}
    addon_prefs = prefs_utils.get_addon_prefs()   
    display_driver = None

    if rman_scene.is_interactive:

        if rman_scene.is_viewport_render:
            display_driver = 'blender'
        else:
            display_driver = 'it'

    elif (not rman_scene.external_render) and (rm.render_into == 'it'):
        display_driver = 'it'
        
    if rm_rl:
        if rman_scene.is_viewport_render:
            dspys_dict = _get_dspy_dict_viewport(rm_rl, rman_scene, expandTokens=expandTokens)
            return dspys_dict

        for aov in rm_rl.custom_aovs:
            if aov.name == '':
                continue
            if len(aov.dspy_channels) < 1:
                continue

            dspy_params = {}            
            dspy_params['displayChannels'] = []

            for chan in aov.dspy_channels:
                ch_name = chan.channel_name
                dspy_params['displayChannels'].append(ch_name)
                # add the channel if not already in list
                if ch_name not in dspys_dict['channels']:
                    d = _default_dspy_params()
                    lgt_grp = None
                    source_type, source = chan.aov_name.split()

                    if 'custom_lpe' in source:
                        source = chan.custom_lpe_string

                    if lgt_grp:
                        if "<L.>" in src:
                            source = source.replace("<L.>", "<L.'%s'>" % lgt_grp)
                        else:
                            source = source.replace("L", "<L.'%s'>" % lgt_grp)

                    d[u'channelSource'] = {'type': u'string', 'value': source}
                    d[u'channelType'] = { 'type': u'string', 'value': source_type}
                    d[u'lpeLightGroup'] = { 'type': u'string', 'value': lgt_grp}
                    d[u'remap_a'] = { 'type': u'float', 'value': chan.remap_a}
                    d[u'remap_b'] = { 'type': u'float', 'value': chan.remap_b}
                    d[u'remap_c'] = { 'type': u'float', 'value': chan.remap_c}
                    d[u'exposure'] = { 'type': u'float2', 'value': [chan.exposure_gain, chan.exposure_gamma] }
                    d[u'filter'] = {'type': u'string', 'value': chan.chan_pixelfilter}
                    d[u'filterwidth'] = { 'type': u'float2', 'value': [chan.chan_pixelfilter_x, chan.chan_pixelfilter_y]}
                    d[u'statistics'] = { 'type': u'string', 'value': chan.stats_type}
                    dspys_dict['channels'][ch_name] = d

            if not display_driver:
                display_driver = aov.aov_display_driver      

            
            if aov.name == 'beauty':
                filePath = addon_prefs.path_display_driver_image
                if expandTokens:
                    filePath = string_utils.expand_string(filePath,
                                                    display=display_driver, 
                                                    frame=rman_scene.bl_frame_current,
                                                    asFilePath=True)
            else:
                filePath = addon_prefs.path_aov_image
                if expandTokens:                 
                    token_dict = {'aov': aov.name}
                    filePath = string_utils.expand_string(filePath, 
                                                    display=display_driver, 
                                                    frame=rman_scene.bl_frame_current,
                                                    token_dict=token_dict,
                                                    asFilePath=True)

            dspys_dict['displays'][aov.name] = {
                'driverNode': display_driver,
                'filePath': filePath,
                'denoise': aov.denoise,
                'denoise_mode': aov.denoise_mode,
                'camera': aov.camera,
                'params': dspy_params}

            if aov.denoise and not rman_scene.is_interactive:
                _add_denoiser_channels(dspys_dict, dspy_params)

            if aov.name == 'beauty' and rman_scene.is_interactive:

                if rman_scene.is_viewport_render:
                    return dspys_dict                
                
                # Add ID pass
                dspy_params = {}                        
                dspy_params['displayChannels'] = []            
                d = _default_dspy_params()
                d[u'channelSource'] = {'type': u'string', 'value': 'id'}
                d[u'channelType'] = { 'type': u'string', 'value': 'integer'}     
                dspys_dict['channels']['id'] = d     
                dspy_params['displayChannels'].append('id')
                filePath = 'id_pass'
                
                dspys_dict['displays']['id_pass'] = {
                    'driverNode': display_driver,
                    'filePath': filePath,
                    'denoise': False,
                    'denoise_mode': 'singleframe',
                    'camera': aov.camera,
                    'params': dspy_params}                 

    else:
        if not display_driver:
            display_driver = 'openexr'

        # add beauty (Ci,a)
        dspy_params = {}                        
        dspy_params['displayChannels'] = []

        d = _default_dspy_params()
        d[u'channelSource'] = {'type': u'string', 'value': 'Ci'}
        d[u'channelType'] = { 'type': u'string', 'value': 'color'}       
        dspys_dict['channels']['Ci'] = d
        d = _default_dspy_params()
        d[u'channelSource'] = {'type': u'string', 'value': 'a'}
        d[u'channelType'] = { 'type': u'string', 'value': 'float'}          
        dspys_dict['channels']['a'] = d     
        dspy_params['displayChannels'].append('Ci')
        dspy_params['displayChannels'].append('a')
        filePath = addon_prefs.path_display_driver_image
        if expandTokens:
            filePath = string_utils.expand_string(addon_prefs.path_display_driver_image,
                                                display=display_driver, 
                                                frame=rman_scene.bl_frame_current,
                                                asFilePath=True)
        dspys_dict['displays']['beauty'] = {
            'driverNode': display_driver,
            'filePath': filePath,
            'denoise': False,
            'denoise_mode': 'singleframe',
            'camera': None,
            'params': dspy_params}

        if rman_scene.is_viewport_render:
            # early out
            return dspys_dict

        if rman_scene.is_interactive and display_driver == "it":
            # Add ID pass
            dspy_params = {}                        
            dspy_params['displayChannels'] = []            
            d = _default_dspy_params()
            d[u'channelSource'] = {'type': u'string', 'value': 'id'}
            d[u'channelType'] = { 'type': u'string', 'value': 'integer'}               
            dspys_dict['channels']['id'] = d     
            dspy_params['displayChannels'].append('id')
            filePath = 'id_pass'
            
            dspys_dict['displays']['id_pass'] = {
                'driverNode': display_driver,
                'filePath': filePath,
                'denoise': False,
                'denoise_mode': 'singleframe',  
                'camera': None,              
                'params': dspy_params}           

        # so use built in aovs
        blender_aovs = [
            # (name, do?, declare type/name, source)
            ("z", layer.use_pass_z, rman_scene.rman.Tokens.Rix.k_float, None),
            ("Nn", layer.use_pass_normal, rman_scene.rman.Tokens.Rix.k_normal, None),
            ("dPdtime", layer.use_pass_vector, rman_scene.rman.Tokens.Rix.k_vector, None),
            ("u", layer.use_pass_uv, rman_scene.rman.Tokens.Rix.k_float, None),
            ("v", layer.use_pass_uv, rman_scene.rman.Tokens.Rix.k_float, None),
            ("id", layer.use_pass_object_index, rman_scene.rman.Tokens.Rix.k_float, None),
            ("shadows", layer.use_pass_shadow, rman_scene.rman.Tokens.Rix.k_color,
            "color lpe:shadowcollector"),
            ("diffuse", layer.use_pass_diffuse_direct, rman_scene.rman.Tokens.Rix.k_color,
            "color lpe:diffuse"),
            ("indirectdiffuse", layer.use_pass_diffuse_indirect,
            rman_scene.rman.Tokens.Rix.k_color, "color lpe:indirectdiffuse"),
            ("albedo", layer.use_pass_diffuse_color, rman_scene.rman.Tokens.Rix.k_color,
            "color lpe:nothruput;noinfinitecheck;noclamp;unoccluded;overwrite;C(U2L)|O"),
            ("specular", layer.use_pass_glossy_direct, rman_scene.rman.Tokens.Rix.k_color,
            "color lpe:specular"),
            ("indirectspecular", layer.use_pass_glossy_indirect,
            rman_scene.rman.Tokens.Rix.k_color, "color lpe:indirectspecular"),
            ("subsurface", layer.use_pass_subsurface_indirect,
            rman_scene.rman.Tokens.Rix.k_color, "color lpe:subsurface"),
            ("emission", layer.use_pass_emit, rman_scene.rman.Tokens.Rix.k_color,
            "color lpe:emission"),
        ]

        # declare display channels
        for aov, doit, declare_type, source in blender_aovs:
            filePath = addon_prefs.path_aov_image
            if expandTokens:
                token_dict = {'aov': aov}
                filePath = string_utils.expand_string(filePath, 
                                                    display=display_driver, 
                                                    frame=rman_scene.bl_frame_current,
                                                    token_dict=token_dict,
                                                    asFilePath=True)
            if doit and declare_type:
                dspy_params = {}                        
                dspy_params['displayChannels'] = []
                
                d = _default_dspy_params()

                d[u'channelSource'] = {'type': u'string', 'value': source}
                d[u'channelType'] = { 'type': u'string', 'value': declare_type}              

                dspys_dict['channels'][aov] = d
                dspy_params['displayChannels'].append(aov)
                dspys_dict['displays'][aov] = {
                'driverNode': display_driver,
                'filePath': filePath,
                'denoise': False,
                'denoise_mode': 'singleframe',  
                'camera': None,                 
                'params': dspy_params}

    if rm.do_holdout_matte != "OFF":

        dspy_params = {}                        
        dspy_params['displayChannels'] = []
        d = _default_dspy_params()
        occluded_src = "color lpe:holdouts;C[DS]+<L.>"
        d[u'channelSource'] = {'type': u'string', 'value': occluded_src}
        d[u'channelType'] = { 'type': u'string', 'value': 'color'}       
        dspys_dict['channels']['occluded'] = d
        dspy_params['displayChannels'].append('occluded')

        dspys_dict['displays']['occluded'] = {
            'driverNode': 'null',
            'filePath': 'occluded',
            'denoise': False,
            'denoise_mode': 'singleframe',   
            'camera': None,         
            'params': dspy_params}        

        dspy_params = {}                        
        dspy_params['displayChannels'] = []
        d = _default_dspy_params()
        holdout_matte_src = "color lpe:holdouts;unoccluded;C[DS]+<L.>"
        d[u'channelSource'] = {'type': u'string', 'value': holdout_matte_src}
        d[u'channelType'] = { 'type': u'string', 'value': 'color'}          
        dspys_dict['channels']['holdoutMatte'] = d   
        dspy_params['displayChannels'].append('holdoutMatte')

        # user wants separate AOV for matte
        if rm.do_holdout_matte == "AOV":
            filePath = addon_prefs.path_display_driver_image
            f, ext = os.path.splitext(filePath)
            filePath = f + '_holdoutMatte' + ext      
            if expandTokens:      
                filePath = string_utils.expand_string(filePath,
                                                    display=display_driver, 
                                                    frame=rman_scene.bl_frame_current,
                                                    asFilePath=True)



            dspys_dict['displays']['holdoutMatte'] = {
                'driverNode': display_driver,
                'filePath': filePath,
                'denoise': False,
                'denoise_mode': 'singleframe',
                'camera': None,
                'params': dspy_params}
        else:
            dspys_dict['displays']['holdoutMatte'] = {
                'driverNode': 'null',
                'filePath': 'holdoutMatte',
                'denoise': False,
                'denoise_mode': 'singleframe',
                'camera': None,
                'params': dspy_params}

    return dspys_dict


def make_dspy_info(scene):
    """
    Create some render parameter from scene and pass it to image tool.

    If current scene renders to "it", collect some useful infos from scene
    and send them alongside the render job to RenderMan's image tool. Applies to
    renderpass result only, does not affect postprocessing like denoise.
    """
    params = {}
    rm = scene.renderman
    from time import localtime, strftime
    ts = strftime("%a %x, %X", localtime())
    ts = bytes(ts, 'ascii', 'ignore').decode('utf-8', 'ignore')

    dspy_notes = "Render start:\t%s\r\r" % ts
    dspy_notes += "Integrator:\t%s\r\r" % rm.integrator
    dspy_notes += "Samples:\t%d - %d\r" % (rm.min_samples, rm.max_samples)
    dspy_notes += "Pixel Variance:\t%f\r\r" % rm.pixel_variance

    # moved this in front of integrator check. Was called redundant in
    # both cases
    integrator = getattr(rm, "%s_settings" % rm.integrator)

    if rm.integrator == 'PxrPathTracer':
        dspy_notes += "Mode:\t%s\r" % integrator.sampleMode
        dspy_notes += "Light:\t%d\r" % integrator.numLightSamples
        dspy_notes += "Bxdf:\t%d\r" % integrator.numBxdfSamples

        if integrator.sampleMode == 'bxdf':
            dspy_notes += "Indirect:\t%d\r\r" % integrator.numIndirectSamples
        else:
            dspy_notes += "Diffuse:\t%d\r" % integrator.numDiffuseSamples
            dspy_notes += "Specular:\t%d\r" % integrator.numSpecularSamples
            dspy_notes += "Subsurface:\t%d\r" % integrator.numSubsurfaceSamples
            dspy_notes += "Refraction:\t%d\r" % integrator.numRefractionSamples

    elif rm.integrator == "PxrVCM":
        dspy_notes += "Light:\t%d\r" % integrator.numLightSamples
        dspy_notes += "Bxdf:\t%d\r\r" % integrator.numBxdfSamples

    return dspy_notes

def export_metadata(scene, params):
    rm = scene.renderman
    if "Camera" not in bpy.data.cameras:
        return
    if "Camera" not in bpy.data.objects:
        return
    cam = bpy.data.cameras["Camera"]
    obj = bpy.data.objects["Camera"]
    if cam.dof.focus_object:
        dof_distance = (obj.location - cam.dof.focus_object.location).length
    else:
        dof_distance = cam.dof.focus_distance
    output_dir = string_utils.expand_string(rm.path_rib_output, 
                                            frame=scene.frame_current, 
                                            asFilePath=True)  
    output_dir = os.path.dirname(output_dir)
    statspath=os.path.join(output_dir, 'stats.%04d.xml' % scene.frame_current)

    params.SetString('exrheader_dcc', 'Blender %s\nRenderman for Blender %s' % (bpy.app.version, rman_constants.RFB_ADDON_VERSION_STRING))

    params.SetFloat('exrheader_fstop', cam.dof.aperture_fstop )
    params.SetFloat('exrheader_focaldistance', dof_distance )
    params.SetFloat('exrheader_focal', cam.lens )
    params.SetFloat('exrheader_haperture', cam.sensor_width )
    params.SetFloat('exrheader_vaperture', cam.sensor_height )

    params.SetString('exrheader_renderscene', bpy.data.filepath)
    params.SetString('exrheader_user', os.getenv('USERNAME'))
    params.SetString('exrheader_statistics', statspath)
    params.SetString('exrheader_integrator', rm.integrator)
    params.SetFloatArray('exrheader_samples', [rm.min_samples, rm.max_samples], 2)
    params.SetFloat('exrheader_pixelvariance', rm.pixel_variance)
    params.SetString('exrheader_comment', rm.custom_metadata)