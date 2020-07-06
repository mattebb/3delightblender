from .. import rman_bl_nodes
from ..rfb_icons import get_bxdf_icon, get_light_icon, get_lightfilter_icon

def get_bxdf_items():
 
    items = []
    i = 0
    dflt = 'PxrSurface'
    rman_bxdf_icon = get_bxdf_icon("PxrSurface")
    items.append((dflt, dflt, '', rman_bxdf_icon.icon_id, i))
    i += 1
    for n in rman_bl_nodes.__RMAN_BXDF_NODES__:
        if n.name == dflt:
            continue
        rman_bxdf_icon = get_bxdf_icon(n.name)
        items.append( (n.name, n.name, '', rman_bxdf_icon.icon_id, i))                
        i += 1
    return items     

def get_light_items():
    rman_light_icon = get_light_icon("PxrRectLight")
    items = []
    i = 0
    dflt = 'PxrRectLight'
    items.append((dflt, dflt, '', rman_light_icon.icon_id, i))
    for n in rman_bl_nodes.__RMAN_LIGHT_NODES__:
        if n.name != dflt:
            i += 1
            light_icon = get_light_icon(n.name)
            items.append( (n.name, n.name, '', light_icon.icon_id, i))
    return items    

def get_lightfilter_items():
    items = []
    i = 0
    rman_light_icon = get_lightfilter_icon("PxrBlockerLightFilter")
    dflt = 'PxrBlockerLightFilter'
    items.append((dflt, dflt, '', rman_light_icon.icon_id, i))
    for n in rman_bl_nodes.__RMAN_LIGHTFILTER_NODES__:
        if n.name != dflt:
            i += 1
            light_icon = get_lightfilter_icon(n.name)
            items.append( (n.name, n.name, '', light_icon.icon_id, i))
    return items    