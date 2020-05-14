from .. import rman_config
from .. import rman_bl_nodes
import bpy
import json

def GetConfigurablePanels():
    '''Return the names of RenderForBlender panels that are configurable
    '''

    panels = []
    for config_name,cfg in rman_config.__RMAN_CONFIG__.items():
        for param_name, ndp in cfg.params.items():
            panel = getattr(ndp, 'panel', '')
            if panel == '':
                continue
            if panel not in panels:
                panels.append(ndp.panel)
    print(str(panels))

def GetConfigurablePanelProperties(panel):
    '''Return all properties in a given panel that are configurable

        Args:
            panel (str) - the name of the panel caller is interested in
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

    print(str(props))

def GetPanelPropertyAsJson(panel, prop):
    '''Get a configurable panel property as JSON

        Args:
            panel (str) - the name of the panel caller is interested in
            prop (str) - property name caller is interested in
    '''

    for config_name,cfg in rman_config.__RMAN_CONFIG__.items():
        for param_name, ndp in cfg.params.items():
            if not hasattr(ndp, 'panel'):
                continue
            if ndp.panel == panel and ndp.name == prop:
                print(json.dumps(ndp.as_dict()))
                               

