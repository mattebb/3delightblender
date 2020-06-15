from .. import rman_bl_nodes
from ..icons.icons import load_icons

def get_bxdf_items():
    icons = load_icons()
    rman_unknown_icon = icons.get("out_unknown.png")    
    items = []
    i = 0
    dflt = 'PxrSurface'
    rman_bxdf_icon = icons.get("out_PxrSurface.png")
    items.append((dflt, dflt, '', rman_bxdf_icon.icon_id, i))
    i += 1
    for n in rman_bl_nodes.__RMAN_BXDF_NODES__:
        if n.name == dflt:
            continue
        rman_bxdf_icon = icons.get("out_%s.png" % n.name, None)
        if not rman_bxdf_icon:
            items.append( (n.name, n.name, '', rman_unknown_icon.icon_id, i))
        else:
            items.append( (n.name, n.name, '', rman_bxdf_icon.icon_id, i))                
        i += 1
    return items     

def get_light_items():
    icons = load_icons()
    rman_light_icon = icons.get("out_PxrRectLight.png")
    items = []
    i = 0
    dflt = 'PxrRectLight'
    items.append((dflt, dflt, '', rman_light_icon.icon_id, i))
    for n in rman_bl_nodes.__RMAN_LIGHT_NODES__:
        if n.name != dflt:
            i += 1
            light_icon = icons.get("out_%s.png" % n.name, None)
            if not light_icon:
                items.append( (n.name, n.name, '', rman_light_icon.icon_id, i))
            else:
                items.append( (n.name, n.name, '', light_icon.icon_id, i))
    return items    

def get_lightfilter_items():
    icons = load_icons()
    items = []
    i = 0
    rman_light_icon = icons.get("out_PxrBlockerLightFilter.png")
    dflt = 'PxrBlockerLightFilter'
    items.append((dflt, dflt, '', rman_light_icon.icon_id, i))
    for n in rman_bl_nodes.__RMAN_LIGHTFILTER_NODES__:
        if n.name != dflt:
            i += 1
            light_icon = icons.get("out_%s.png" % n.name, None)
            if not light_icon:                
                items.append( (n.name, n.name, '', rman_light_icon.icon_id, i))
            else:
                items.append( (n.name, n.name, '', light_icon.icon_id, i))
    return items    