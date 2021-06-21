from .. import rman_config
from .. import rman_bl_nodes
import bpy
import json
import pprint

def GetConfigurablePanels():
    '''Return the names of RenderForBlender panels that are configurable.

    Example:
        import RenderManForBlender.rfb_api as rfb_api
        rfb_api.GetConfigurablePanels()

    Returns:
        (dict)

    '''

    panels = dict()
    for config_name,cfg in rman_config.__RMAN_CONFIG__.items():
        for param_name, ndp in cfg.params.items():
            panel = getattr(ndp, 'panel', '')
            if panel == '':
                continue
            if panel not in panels:
                #panels.append(ndp.panel)
                cls = getattr(bpy.types, panel)
                panels[panel] = { 'bl_label': cls.bl_label }
    print("RenderMan Configurable Panels")
    print("------------------------------")
    for panel, props in panels.items():
        print("%s (%s)" % (panel, props['bl_label']))
    print("------------------------------\n")
    return panels

def GetConfigurablePanelProperties(panel):
    '''Return all properties in a given panel that are configurable.

    Example:
        import RenderManForBlender.rfb_api as rfb_api
        rfb_api.GetConfigurablePanelProperties('RENDER_PT_renderman_sampling')  

    Args:
        panel (str) - the name of the panel caller is interested in

    Returns:
        (dict)
    '''
    props = dict()
    for config_name,cfg in rman_config.__RMAN_CONFIG__.items():
        for param_name, ndp in cfg.params.items():
            if not hasattr(ndp, 'panel'):
                continue
            if ndp.panel == panel:
                label = ndp.name
                if hasattr(ndp, 'label'):
                    label = ndp.label
                props[label] = ndp.name
    print("Configurable Properties (%s)" % panel)
    print("------------------------------")
    for label, prop in props.items():
        print("%s (%s)" % (prop, label))
    print("------------------------------\n")
    return props

def GetPanelPropertyAsJson(panel, prop):
    '''Get a configurable panel property as JSON

    Example:
        import RenderManForBlender.rfb_api as rfb_api
        rfb_api.GetPanelPropertyAsJson('RENDER_PT_renderman_sampling', 'hider_maxSamples')

    Args:
        panel (str) - the name of the panel caller is interested in
        prop (str) - property name caller is interested in
    '''

    json_str = ''
    for config_name,cfg in rman_config.__RMAN_CONFIG__.items():
        for param_name, ndp in cfg.params.items():
            if not hasattr(ndp, 'panel'):
                continue
            if ndp.panel == panel and ndp.name == prop:
                json_str = json.dumps(ndp.as_dict())
                break
    return json_str
                               
