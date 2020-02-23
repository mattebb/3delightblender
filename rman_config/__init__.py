from ..rman_utils.node_desc import NodeDescParamJSON
from ..rman_utils import property_utils
from ..rfb_logger import rfb_log
from bpy.props import StringProperty
import json
import os

__RMAN_CONFIG__ = dict()

class RmanBasePropertyGroup:
    """Base class that can be inhreited for custom PropertyGroups
    who want to use the JSON config files to dynamically add their properties.
    _add_properties should be called before the class is registerd. For example:

    classes = [         
        MyWonderfulSettings
    ]   

    for cls in classes:
        cls._add_properties(cls, 'my_wonderful_settings')
        bpy.utils.register_class(cls)      

    Attributes:

    """

    @staticmethod
    def _add_properties(cls, rman_config_name):
        """Dynamically add properties to a PropertyGroup class

        Args:
            cls (class) - class to add the properties
            rman_config_name (str) - Config name to use to add properties from
        """

        if not rman_config_name in __RMAN_CONFIG__:
            return

        config = __RMAN_CONFIG__[rman_config_name]

        prop_names = []
        prop_meta = {}
        for param_name, ndp in config.params.items():
            name, meta, prop = property_utils.generate_property(ndp, update_function=None)
            if prop:
                cls.__annotations__[ndp._name] = prop
                prop_names.append(ndp.name)
                prop_meta[ndp.name] = meta
        setattr(cls, 'prop_names', prop_names)
        setattr(cls, 'prop_meta', prop_meta)

class RmanConfig:
    """A class to reprsent a json config file.

    Attributes:
        jsonfile (str): Path to JSON file on disk
        params (NodeDescParamJSON): Dictionary of parm names to NodeDescParamJSON objects
    """
    def __init__(self, jsonfile):
        self.jsonfile = jsonfile
        self.params = dict()

        self._parse_json_file()

    def _parse_json_file(self):

        jdata = json.load(open(self.jsonfile))
        mandatoryAttrList = ['name']
        for attr in mandatoryAttrList:
            setattr(self, attr, jdata[attr])

        if 'params' in jdata:
            for pdata in jdata['params']:
                try:
                    param = NodeDescParamJSON(pdata)
                except:
                    rfb_log().error('FAILED to parse param: %s' % pdata)
                    raise
                self.params[param.name] = param

def get_factory_config_path():
    """Get the factory config path.

    Returns:
        str: The path to the factory config files
    """

    cur_dir = os.path.dirname(os.path.realpath(__file__))
    config_dir = os.path.join(cur_dir, 'config')

    return config_dir

def get_override_paths():
    """Get the override config path(s). Consults the envrionment vairiable
    RFB_SITE_PATH, RFB_SHOW_PATH, and RFB_USER_PATH

    Returns:
        str: The path(s) to the override config files
    """    

    paths = []

    # first, RFB_SITE_PATH
    RFB_SITE_PATH = os.environ.get('RFB_SITE_PATH', None)
    if RFB_SITE_PATH:
        for path in RFB_SITE_PATH.split(':'):
            paths.append(path)

    # next, RFB_SHOW_PATH
    RFB_SHOW_PATH = os.environ.get('RFB_SHOW_PATH', None)
    if RFB_SHOW_PATH:
        for path in RFB_SHOW_PATH.split(':'):
            paths.append(path)

    # finally, RFB_USER_PATH
    RFB_USER_PATH = os.environ.get('RFB_USER_PATH', None)
    if RFB_USER_PATH:
        for path in RFB_USER_PATH.split(':'):
            paths.append(path)                        

    return paths

# only allow these attrs to be overriden
__ALLOWABLE_ATTR_OVERRIDES__ = ['default', 'label', 'help', 'min', 'max', 'options']

def apply_overrides(rman_config_org, rman_config_override):
    """Given two RmanConfig objects, apply the overrides from the second
    one to the first one. Only certian attributes will be overridden. See
    __ALLOWABLE_ATTR_OVERRIDES__ above.

    Args:
        rman_config_org (RmanConfig): The original RmanConfig object
        rman_config_override (RmanConfig): The second RmanConfig object with overrides
    """     

    for param_name, ndp in rman_config_override.params.items():
        if param_name in rman_config_org.params:
            ndp_org = rman_config_org.params[param_name]
            for attr in __ALLOWABLE_ATTR_OVERRIDES__:
                if hasattr(ndp, attr):
                    setattr(ndp_org, attr, getattr(ndp, attr))
        else:
            # if it doesn't exist, add it
            rman_config_org.params[param_name] = ndp

def register():

    config_path = get_factory_config_path()
    for f in os.listdir(config_path):
        if not f.endswith('.json'):
            continue
        jsonfile = os.path.join(config_path, f)
        rman_config = RmanConfig(jsonfile)
        __RMAN_CONFIG__[rman_config.name] = rman_config

    # Look for overrides
    override_paths = get_override_paths()
    for path in override_paths:
        for f in os.listdir(path):
            if not f.endswith('.json'):
                continue
            jsonfile = os.path.join(path, f)
            rman_config_override = RmanConfig(jsonfile)
            if rman_config_override.name in __RMAN_CONFIG__:
                rman_config_original = __RMAN_CONFIG__[rman_config_override.name]
                apply_overrides(rman_config_original, rman_config_override)
                __RMAN_CONFIG__[rman_config_override.name] = rman_config_original