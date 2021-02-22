"""Classes to parse and store node descriptions.
"""

# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 - 2021 Pixar
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#
# ##### END MIT LICENSE BLOCK #####

# TODO: NodeDesc.node_type should be an enum.

# pylint: disable=import-error
# pylint: disable=relative-import
# pylint: disable=invalid-name
# pylint: disable=superfluous-parens

import re
from ..node_desc_base.node_desc_param import osl_metadatum
from ..node_desc_base.node_desc import NodeDesc
from .conditional_visibility import build_condvis_expr
from .rfb_node_desc_param import (
    RfbNodeDescParamXML,
    RfbNodeDescParamOSL,
    RfbNodeDescParamJSON)

# globals
LIGHTFILTER_CLASSIF = "classification:rendernode/RenderMan/lightfilter"


class RfbNodeDesc(NodeDesc):
    """Specialize NodeDesc for Blender.

    Arguments:
        NodeDesc {object} -- Generic class encapsulating shader parameters
    """

    def __init__(self, *args):
        args2 = args + (build_condvis_expr,)
        kwargs = {'xmlparamclass': RfbNodeDescParamXML,
                  'oslparamclass': RfbNodeDescParamOSL,
                  'jsonparamclass': RfbNodeDescParamJSON, }
        super(RfbNodeDesc, self).__init__(*args2, **kwargs)
        # declare our attributes
        self.nodeid = None
        self.classification = None
        self.file_extension = None
        self.on_create = []
        self.unique = False
        self.params_only_ae = False
        self._ctlname = None
        # finish our own parsing
        self._parse_shader_metadata()
        self._set_ctlname()
        self._backward_compatibility()
        # free memory
        self.clear_parsed_data()

    def _set_ctlname(self):
        """remove any illegal character for a maya ui object."""
        self._ctlname = re.sub(r'[^\w]', '', self._name)

    @property
    def ctlname(self):
        """Return the ui control name used by maya."""
        if self._ctlname is None and self._name is not None:
            self._ctlname = re.sub(r'[^\w]', '', self._name)
        return self._ctlname

    def _parse_shader_metadata(self):
        data_type = self.parsed_data_type()
        if data_type == 'xml':
            xml = self.parsed_data()
            rfmdata = xml.getElementsByTagName('rfmdata')
            if rfmdata:
                # mandatory attributes: classification
                self.classification = rfmdata[0].getAttribute('classification')
                # display driver file extension - xml only
                self.file_extension = rfmdata[0].getAttribute('fileextension')
                if self.file_extension in ('', 'null'):
                    self.file_extension = None

        elif data_type == 'json':
            # mandatory attributes: nodeid and classification
            jdata = self.parsed_data()
            mandatory_attr_list = ['classification']
            for attr in mandatory_attr_list:
                setattr(self, attr, jdata[attr])
            # additional metadata
            optional_attr_list = [
                ('on_create', 'onCreate', []), ('unique', 'unique', False),
                ('params_only_ae', 'params_only_AE', False)]
            for attr, key, default in optional_attr_list:
                setattr(self, attr, jdata.get(key, default))

        elif data_type == 'oso':
            # mandatory attributes: classification
            oinfo = self.parsed_data()
            meta = {p['name']: p for p in oinfo.shadermetadata()}
            self.classification = osl_metadatum(meta, 'rfm_classification')
            # categorize osl shaders as patterns by default, if metadata didn't
            # say.
            if not self.classification:
                self.classification = 'rendernode/RenderMan/pattern/'
            self.help = osl_metadatum(meta, 'help')

    def _backward_compatibility(self):
        # in RIS, displacement should translate to displace
        # NOTE: is this still useful now that REYES is gone ?
        if self.node_type == 'displacement':
            self.node_type = 'displace'

    def __str__(self):
        """debugging method

        Returns:
            str -- a human-readable dump of the node.
        """
        ostr = 'ShadingNode: %s ------------------------------\n' % self.name
        ostr += 'node_type: %s\n' % self.node_type
        ostr += 'rman_node_type: %s\n' % self.rman_node_type
        ostr += 'nodeid: %s\n' % self.nodeid
        ostr += 'classification: %s\n' % self.classification
        if hasattr(self, 'help'):
            ostr += 'help: %s\n' % self.help
        ostr += '\nINPUTS:\n'
        for prm in self.params:
            ostr += '  %s\n' % prm
        ostr += '\nOUTPUTS\n:'
        for opt in self.outputs:
            ostr += '%s\n' % opt
        ostr += '\nATTRIBUTES:\n'
        for attr in self.attributes:
            ostr += '%s\n' % attr
        ostr += '-' * 79
        return ostr        

