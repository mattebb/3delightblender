"""Specialize shader parameter parsing for Blender."""

from collections import OrderedDict
# pylint: disable=import-error
from rman_utils.node_desc_param import (NodeDescParam,
                                        NodeDescParamXML,
                                        NodeDescParamOSL,
                                        NodeDescParamJSON)

# Override static class variable
NodeDescParam.optional_attrs = NodeDescParam.optional_attrs + []
NodeDescParamJSON.keywords = NodeDescParamJSON.keywords + ['panel', 'inheritable', 
                'inherit_true_value', 'update_function_name', 'update_function']  

def blender_finalize(obj):
    """Post-process some parameters for Blender.
    """

    if obj.type in ['int', 'matrix']:
        # these are NEVER connectable
        obj.connectable = False

    if hasattr(obj, 'help'):
        obj.help = obj.help.replace('"', '\\"')
        obj.help = obj.help.replace('<br>', '\n')

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

    def __init__(self, *args, **kwargs):
        super(RfbNodeDescParamJSON, self).__init__(*args, **kwargs)
        blender_finalize(self)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
