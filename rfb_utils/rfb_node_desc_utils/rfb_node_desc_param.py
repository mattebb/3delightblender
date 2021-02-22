"""Specialize shader parameter parsing for Blender."""

from collections import OrderedDict
# pylint: disable=import-error
from ..node_desc_base.node_desc_param import (NodeDescParam,
                                        NodeDescParamXML,
                                        NodeDescParamOSL,
                                        NodeDescParamJSON)

# Override static class variable
NodeDescParam.optional_attrs = NodeDescParam.optional_attrs + ['uiStruct']
NodeDescParamJSON.keywords = NodeDescParamJSON.keywords + ['uiStruct', 'do_not_display']

# Globals
INTERP_RMAN_TO_MAYA = {'linear': 1,
                       'catmull-rom': 2,
                       'bspline': 3,
                       'constant': 0,
                       'none': 0}


def blender_finalize(obj):
    """Post-process some parameters for Blender.
    """

    if obj.type in ['int', 'matrix']:
        # these are NEVER connectable
        obj.connectable = False

    if hasattr(obj, 'help'):
        obj.help = obj.help.replace('"', '\\"')

class RfbNodeDescParamXML(NodeDescParamXML):
    """Specialize NodeDescParamXML for Blender"""

    def __init__(self, *args, **kwargs):
        super(RfbNodeDescParamXML, self).__init__(*args, **kwargs)
        blender_finalize(self)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    def _set_widget(self, pdata):
        super(RfbNodeDescParamXML, self)._set_widget(pdata)

class RfbNodeDescParamOSL(NodeDescParamOSL):
    """Specialize NodeDescParamOSL for Blender"""

    def __init__(self, *args, **kwargs):
        super(RfbNodeDescParamOSL, self).__init__(*args, **kwargs)
        blender_finalize(self)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    def _set_widget(self, pdata):
        super(RfbNodeDescParamOSL, self)._set_widget(pdata)


class RfbNodeDescParamJSON(NodeDescParamJSON):
    """Specialize NodeDescParamJSON for Blender"""

    keywords = NodeDescParamJSON.keywords + ['panel', 'inheritable', 
                'inherit_true_value', 'update_function_name', 'update_function']    

    @staticmethod
    def valid_keyword(kwd):
        """Return True if the keyword is in the list of known tokens."""
        return kwd in RfbNodeDescParamJSON.keywords                

    def __init__(self, *args, **kwargs):
        super(RfbNodeDescParamJSON, self).__init__(*args, **kwargs)
        blender_finalize(self)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
