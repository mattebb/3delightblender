# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 - 2017 Pixar
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

from rman_utils.rman_assets import core as ra
from rman_utils.rman_assets import lib as ral
from rman_utils.rman_assets.core import RmanAsset
from rman_utils.rman_assets.common.definitions import TrMode, TrStorage, TrSpace, TrType
from rman_utils.filepath import FilePath

import os
import os.path
import re
import sys
import time
import bpy as mc  # just a test
import bpy
import mathutils
from math import radians
from ..rfb_utils import filepath_utils
from ..rfb_utils import string_utils
from ..rfb_utils import shadergraph_utils
from ..rfb_utils import object_utils   
from ..rfb_utils import transform_utils
from ..rfb_utils import texture_utils
from ..rfb_utils.prefs_utils import get_pref, get_addon_prefs
from ..rfb_utils.property_utils import __GAINS_TO_ENABLE__
from ..rman_bl_nodes import __BL_NODES_MAP__, __RMAN_NODE_TYPES__

def default_label_from_file_name(filename):
    # print filename
    lbl = os.path.splitext(os.path.basename(filename))[0]
    # print lbl
    lbl = re.sub('([A-Z]+)', r' \1', lbl)
    # print lbl
    lbl = lbl.replace('_', ' ')
    return lbl.strip().capitalize()

def asset_name_from_label(label):
    """Builds a filename from the asset label string.

    Args:
    - label (str): User-friendly label

    Returns:
    - the asset file name
    """
    assetDir = re.sub(r'[^\w]', '', re.sub(' ', '_', label)) + '.rma'
    return assetDir



class BlenderHostPrefs(ral.HostPrefs):
    def __init__(self):
        super(BlenderHostPrefs, self).__init__('24.0')
        self.debug = False

        # === Library Prefs ===
        #
        self.rpbConfigFile = FilePath(self.getHostPref('rpbConfigFile', u''))
        # the list of user libraries from Maya prefs
        self.rpbUserLibraries = self.getHostPref('rpbUserLibraries', [])
        # We don't initialize the library configuration just yet. We want
        # to do it only once the prefs objects has been fully contructed.
        # This is currently done in rman_assets.ui.Ui.__init__()
        self.cfg = None

        # === UI Prefs ===
        #
        # our prefered swatch size in the UI.
        self.rpbSwatchSize = self.getHostPref('rpbSwatchSize', 64)
        # the last selected preview type
        self.rpbSelectedPreviewEnv = self.getHostPref(
            'rpbSelectedPreviewEnv', 0)
        # the last selected category
        self.rpbSelectedCategory = self.getHostPref('rpbSelectedCategory', u'')
        # the last selected preset
        self.rpbSelectedPreset = self.getHostPref('rpbSelectedPreset', u'')

        # the last selected library
        self.rpbSelectedLibrary = FilePath(self.getHostPref(
            'rpbSelectedLibrary', u''))
    
        # store these to make sure we render the previews with the same version.
        self.hostTree = os.environ.get('RFMTREE', '')
        self.rmanTree = os.environ.get('RMANTREE', '')

        # === User Prefs ===
        #
        # render all HDR environments ?
        self.rpbRenderAllHDRs = self.getHostPref('rpbRenderAllHDRs', 0)
        self.rpbHideFactoryLib = self.getHostPref('rpbHideFactoryLib', 0)

        self._nodesToExport = list()

    def getHostPref(self, prefName, defaultValue): # pylint: disable=unused-argument
        if prefName == 'rpbUserLibraries':
            val = list()
            prefs = get_addon_prefs()
            for p in prefs.rpbUserLibraries:
                val.append(p.path)
        else:
            val = get_pref(pref_name=prefName, default=defaultValue)
        return val

    def setHostPref(self, prefName, value): # pylint: disable=unused-argument
        """Save the given value in the host's preferences.
        First look at the value's type and call the matching host API.

        Args:
            prefName (str): The class attribute name for that pref.
            value (any): The value we should pass to the delegate.

        Raises:
            RmanAssetLibError: If we don't support the given data type.
        """
        isArray = isinstance(value, list)
        tvalue = value
        prefs = get_addon_prefs()
        if isArray:
            tvalue = value[0]
        if isinstance(tvalue, int):
            if isArray:
                pass
            else:
                setattr(prefs, prefName, value) 
        elif isinstance(tvalue, str):
            if isArray:
                if prefName == 'rpbUserLibraries':
                    prefs = get_addon_prefs()
                    prefs.rpbUserLibraries.clear()
                    for val in value:
                        p = prefs.rpbUserLibraries.add()
                        p.path = val
            else:
                setattr(prefs, prefName, value)                
        else:
            arrayStr = ''
            if isArray:
                arrayStr = ' array'
            msg = ('HostPrefs.setHostPref: %s%s NOT supported !' %
                   (type(tvalue), arrayStr))
            pass
        bpy.ops.wm.save_userpref()        

    def saveAllPrefs(self):
        self.setHostPref('rpbUserLibraries', self.rpbUserLibraries)
        self.setHostPref('rpbSelectedLibrary', self.rpbSelectedLibrary)
        self.setHostPref('rpbSelectedCategory', self.rpbSelectedCategory)
        self.setHostPref('rpbSelectedPreset', self.rpbSelectedPreset)

    def updateLibraryConfig(self):
        self.cfg.buildLibraryList(updateFromPrefs=True)

    def getSelectedCategory(self):
        return self.rpbSelectedCategory

    def setSelectedCategory(self, val):
        self.rpbSelectedCategory = val

    def getSelectedPreset(self):
        return self.rpbSelectedPreset

    def setSelectedPreset(self, val):
        self.rpbSelectedPreset = val        

    def getSelectedLibrary(self):
        return self.rpbSelectedLibrary

    def setSelectedLibrary(self, path):
        self.rpbSelectedLibrary = path

    def getSwatchSize(self):
        return self.rpbSwatchSize

    def setSwatchSize(self, value):
        self.rpbSwatchSize = min(max(value, 64), 128)

    def doAssign(self):
        return True

    def gather_material_nodes(self, mat):
        out = shadergraph_utils.is_renderman_nodetree(mat)
        nodes = shadergraph_utils.gather_nodes(out)
        self._nodesToExport.extend(nodes)

    def preExportCheck(self, mode, hdr=None, context=None): # pylint: disable=unused-argument
        if mode == 'material':
            ob = context.active_object
            mat = ob.active_material
            self.gather_material_nodes(mat)            
        elif mode == 'lightrigs':
            selected_light_objects = []
            if context.selected_objects:
                for obj in context.selected_objects:  
                    if object_utils._detect_primitive_(obj) == 'LIGHT':
                        selected_light_objects.append(obj)
            if not selected_light_objects:
                return False
            self._nodesToExport.extend(selected_light_objects)
        elif mode == 'envmap':
            if not hdr.exists():
                rfm_log().warning('hdr file does not exist: %s', hdr)
                return False
            self._nodesToExport = [hdr]
            self._defaultLabel = default_label_from_file_name(hdr)
            return True
        else:
            print('preExportCheck: unknown mode: %s', repr(mode))
            return False
        return True

    def exportMaterial(self, categorypath, infodict, previewtype): # pylint: disable=unused-argument
        return export_asset(self._nodesToExport, 'nodeGraph', infodict, categorypath,
                            self.cfg)

    def exportLightRig(self, categorypath, infodict): # pylint: disable=unused-argument
        return export_asset(self._nodesToExport, 'nodeGraph', infodict, categorypath,
                            self.cfg)

    def exportEnvMap(self, categorypath, infodict): # pylint: disable=unused-argument
        return export_asset(self._nodesToExport, 'envMap', infodict, categorypath,
                            self.cfg)

    def importAsset(self, asset, assignToSelected=False): # pylint: disable=unused-argument
        # IMPLEMENT ME
        pass

    def getAllCategories(self, asDict=False):
        return sorted(ral.getAllCategories(self.cfg, asDict=asDict))

    def getAssetList(self, relpath):
        return ral.getAssetList(self.cfg, relpath)

__BLENDER_PRESETS_HOST_PREFS__ = None

def get_host_prefs():
    global __BLENDER_PRESETS_HOST_PREFS__
    if not __BLENDER_PRESETS_HOST_PREFS__:
        __BLENDER_PRESETS_HOST_PREFS__ = BlenderHostPrefs()
        __BLENDER_PRESETS_HOST_PREFS__.initConfig()

        # restore the last library selection
        try:
            __BLENDER_PRESETS_HOST_PREFS__.cfg.setCurrentLibraryByPath(
                __BLENDER_PRESETS_HOST_PREFS__.getSelectedLibrary())
        except BaseException:
            # the last library selected by the client app can not be found.
            # we fallback to the first available library and update the
            # client's prefs.
            __BLENDER_PRESETS_HOST_PREFS__.cfg.setCurrentLibraryByName(None)
            __BLENDER_PRESETS_HOST_PREFS__.setSelectedLibrary(
                __BLENDER_PRESETS_HOST_PREFS__.cfg.getCurrentLibraryPath())       

    return __BLENDER_PRESETS_HOST_PREFS__

##
# @brief      Exception class to tell the world about our miserable failings.
#
class RmanAssetBlenderError(Exception):

    def __init__(self, value):
        self.value = "RmanAssetBlender Error: %s" % value

    def __str__(self):
        return repr(self.value)


##############################
#                            #
#           GLOBALS          #
#                            #
##############################

# store the list of maya nodes we translate to patterns
# without telling anyone...
#
g_BlenderToPxrNodes = {}

for name, node_class in __RMAN_NODE_TYPES__.items():
    g_BlenderToPxrNodes[name] = node_class.bl_label

# fix material output
g_BlenderToPxrNodes['RendermanOutputNode'] = 'shadingEngine'
g_validNodeTypes = ['shadingEngine']
g_validNodeTypes += g_BlenderToPxrNodes.keys()

# wrapper to avoid global access in code
def isValidNodeType(nodetype):
    global g_validNodeTypes
    # if nodetype not in g_validNodeTypes:
    #     print '!! %s is not a valid node type !!' % nodetype
    return (nodetype in g_validNodeTypes)

#
#   END of GLOBALS
#

##
# @brief      Class used by rfm.rmanAssetsLib.renderAssetPreview to report
#             progress back to the host application.
#
class BlenderProgress:
    def __init__(self,):
        self._val = -1
        self._pbar = bpy.context.window_manager
        # print 'Progress init: using %s' % self._pbar

    def Start(self):
        self._pbar.progress_begin(0,100)

    def Update(self, val, msg=None):
        self._pbar.progress_update(val)

    def End(self):
        self._pbar.progress_end()


def fix_blender_name(name):
    return name.replace(' ', '').replace('.', '')

##
# @brief    Class representing a node in Maya's DAG
#
#
class BlenderNode:
    __float3 = ['color', 'point', 'vector', 'normal']
    __safeToIgnore = ['Maya_UsePref', 'Maya_Pref']
    __conversionNodeTypes = ['PxrToFloat', 'PxrToFloat3']

    def __init__(self, node, nodetype):
        # the node name / handle
        self.name = fix_blender_name(node.name)
        self.node = node
        # the maya node type
        self.blenderNodeType = nodetype
        # The rman node it translates to. Could be same as mayaNodeType or not.
        self.rmanNodeType = None
        # either 16 or 9 floats (matrix vs. TranslateRotateScale)
        self.transform = []
        self.hasTransform = None
        self.tr_type = None
        self.tr_mode = None
        self.tr_storage = None
        self.tr_space = None
        # 3d manifolds need special treatment
        self.has3dManifold = False
        # node params
        self._params = {}
        self._paramsOrder = []

        # find the corresponding RenderMan node if need be.
        global g_BlenderToPxrNodes
        self.rmanNodeType = self.blenderNodeType
        if self.blenderNodeType in g_BlenderToPxrNodes:
            self.rmanNodeType = g_BlenderToPxrNodes[self.blenderNodeType]

        # special case: osl objects can be injected though the PxrOSL node.
        self.oslPath = None
        if node.bl_label == 'PxrOSL':
            osl = getattr(node, 'shadercode')
            if not os.path.exists(osl):
                err = ('Cant read osl file: %s' % osl)
                raise RmanAssetBlenderError(err)
            path, fileext = os.path.split(osl)
            self.rmanNodeType = os.path.splitext(fileext)[0]
            self.oslPath = path

        self.ReadParams()

    ##
    # @brief      simple method to make sure we respect the natural parameter
    #             order in our output.
    #
    # @param      self      The object
    # @param      name      The name
    # @param      datadict  The datadict
    #
    # @return     None
    #
    def AddParam(self, name, datadict):
        # print '+ %s : adding %s %s' % (self.name, datadict['type'], name)
        self._paramsOrder.append(name)
        self._params[name] = datadict

    def OrderedParams(self):
        return self._paramsOrder

    def ParamDict(self, name):
        return self._params[name]

    def StoreTransformValues(self, Tnode):
        worldSpace = (self.tr_space == TrSpace.k_world)
        if self.tr_storage == TrStorage.k_TRS:
            # get translate, rotate and scale in world-space and store
            # them in that order in self.transform
            tmp = mc.xform(Tnode, ws=worldSpace, q=True,
                           translation=True)
            self.transform = tmp
            tmp = mc.xform(Tnode, ws=worldSpace, q=True,
                           rotation=True)
            self.transform += tmp
            tmp = mc.xform(Tnode, ws=worldSpace, q=True,
                           scale=True)
            self.transform += tmp
            # print 'k_TRS : %s' % self.transform
        elif self.tr_storage == TrStorage.k_matrix:
            # get the world-space transformation matrix and store
            # in self.transform
            self.transform = mc.xform(Tnode, ws=worldSpace, q=True,
                                      matrix=True)
            # print 'k_matrix: %s' % self.transform

    def HasTransform(self, storage=TrStorage.k_matrix,
                     space=TrSpace.k_world, mode=TrMode.k_flat):
        # we already know and the data has been stored.
        if self.hasTransform is not None:
            return self.hasTransform

        if not mc.objExists(self.name):
            # We may have 'inserted' nodes in our graph that don't exist in
            # maya. 'inserted' nodes are typically color->float3 nodes.
            self.hasTransform = False
            return self.hasTransform

        # get a list of inherited classes for that node
        inherited = mc.nodeType(self.name, inherited=True)

        if 'dagNode' in inherited:
            self.hasTransform = True

            # This is a transform-able node.
            # We store the transformation settings for later use.
            self.tr_mode = mode
            self.tr_storage = storage
            self.tr_space = space

            # we only support flat transformations for now.
            #
            if mode == TrMode.k_flat:
                pass
            elif mode == TrMode.k_hierarchical:
                raise RmanAssetBlenderError('Hierarchical transforms '
                                         'not implemented yet !')
            else:
                raise RmanAssetBlenderError('Unknown transform mode !')

            if 'shape' in inherited:
                transformNodes = mc.listRelatives(self.name, allParents=True,
                                                  type='transform')

                if transformNodes is None:
                    raise RmanAssetBlenderError('This is wrong : '
                                             'no transfom for this shape: %s' %
                                             self.name)

                # print 'we have valid transform nodes : %s' % transformNodes
                Tnode = transformNodes[0]
                # the node is under a transform node
                self.tr_type = TrType.k_nodeTransform
                self.StoreTransformValues(Tnode)
            elif 'transform' in inherited:
                # the node itself is a transform, like place3dTexture...
                self.tr_type = TrType.k_coordsys
                self.StoreTransformValues(self.name)
            else:
                err = 'Unexpected dagNode: %s = %s' % (self.name, inherited)
                raise RmanAssetBlenderError(err)
        else:
            self.hasTransform = False

        return self.hasTransform

    def BlenderGetAttr(self, nodeattr):
        fail = False
        arraysize = -1

        # get actual parameter value
        pvalue = None
        try:
            pvalue = getattr(self.node, nodeattr)
            if type(pvalue) in (mathutils.Vector, mathutils.Color) or\
                    pvalue.__class__.__name__ == 'bpy_prop_array'\
                    or pvalue.__class__.__name__ == 'Euler':
                # BBM modified from if to elif
                pvalue = list(pvalue)[:3]
            meta = getattr(self.node, 'prop_meta')[nodeattr]
            if 'renderman_type' in meta and meta['renderman_type'] == 'int':
                pvalue = int(pvalue)
            if 'renderman_type' in meta and meta['renderman_type'] == 'float':
                pvalue = float(pvalue)
        except:
            fail = True

        if fail:
            # ignore unreadable but warn
            print("Ignoring un-readable parameter : %s" % nodeattr)
            return None

        return pvalue

    def ReadParams(self):
        # get node parameters
        #
        params = []
        if self.blenderNodeType == 'RendermanOutputNode':
            params = blenderParams(self.blenderNodeType)
        else:
            # This is a rman node
            rmanNode = ra.RmanShadingNode(self.rmanNodeType,
                                          osoPath=self.oslPath)
            params = rmanNode.params()

        if self.node.bl_label == "PxrOSL":
            for inp in self.node.inputs:
                ptype = inp.renderman_type
                if inp.is_linked:
                    self.SetConnected(inp.name, ptype)
                else:
                    self.AddParam(inp.name, {'type': ptype, 'value': inp.default_value})
            return

        # loop through parameters
        #
        prop_meta = getattr(self.node, 'prop_meta', None)
        for param in params:
            p_name = param['name']
            ptype = param['type']
            node = self.node
            # safety check
            if not p_name in node.prop_meta:
                self.AddParam(p_name, {'type': ptype,
                                   'value': param['default']})
                if p_name not in self.__safeToIgnore and not ptype.startswith('output'):
                    print("Setting missing parameter to default"
                               " value :" + " %s = %s (%s)" %
                               (node.name + '.' + p_name, param['default'],
                                self.blenderNodeType))

            # if the attr is a float3 and one or more components are connected
            # we need to find out.
            elif p_name in node.inputs and node.inputs[p_name].is_linked:
                link = node.inputs[p_name].links[0]
                # connected parameter
                self.SetConnected(p_name, ptype)
            
            # arrays
            elif '[' in ptype:
                array_len = getattr(self.node, '%s_arraylen' % p_name, -1)
                if array_len < 1:
                    continue

                rman_type = ptype.split('[')[0]
                ptype = '%s[%d]' % (rman_type, array_len)
                is_any_connected = False
                # check if there's any connections:
                for i in range(0, array_len):
                    nodeattr = '%s[%d]' % (p_name, i)
                    if nodeattr in node.inputs and node.inputs[nodeattr].is_linked:
                        is_any_connected = True
                        break
                
                if is_any_connected:
                    self.SetConnected(p_name, ptype)
                else:
                    pvalues = []
                    for i in range(0, array_len):
                        nodeattr = '%s[%d]' % (p_name, i)
                        pvalue = self.BlenderGetAttr(nodeattr)
                        pvalues.append(pvalue)
                    self.AddParam(p_name, {'type': ptype, 'value': pvalue})

            else:
                # skip vstruct and structs
                # these should be connections
                if ptype in ['vstruct', 'struct']:
                    continue

                # get actual parameter value
                pvalue = self.BlenderGetAttr(p_name)

                if pvalue is None:
                    # unreadable : skip
                    continue
                # set basic data
                self.AddParam(p_name, {'type': ptype, 'value': pvalue})

            self.AddParamMetadata(p_name, param)

    def DefaultParams(self):
            rmanNode = ra.RmanShadingNode(self.rmanNodeType)
            params = rmanNode.params()
            for p in params:
                self.AddParam(p['name'], {'type': p['type'],
                                          'value': p['default']})

    def SetConnected(self, pname, ptype=None):
        # print 'connected: %s.%s' % (self.name, pname)
        if ptype is None:
            ptype = self._params[pname]['type']
        if 'reference' in ptype:
            return
        self.AddParam(pname, {'type': 'reference %s' % ptype, 'value': None})

    def AddParamMetadata(self, pname, pdict):
        for k, v in pdict.items():
            if k == 'type' or k == 'value':
                continue
            self._params[pname][k] = v

    def __str__(self):
        return ('[[name: %s   mayaNodeType: %s   rmanNodeType: %s]]' %
                (self.name, self.blenderNodeType, self.rmanNodeType))

    def __repr__(self):
        return str(self)


##
# @brief    Represents a Maya shading network.
#
#           Graph nodes will be stored as represented in the maya DAG.
#           The graph analysis will :
#               - store connectivity infos
#               - recognise nodes that need special treatment and process them.
#
#           We need to make sure the final asset is host-agnostic enough to be
#           used in another host. To do so, we decouple the maya DAG from the
#           prman DAG. Effectively, the json file stores RenderMan's graph
#           representation. This class will translate from maya to prman.
#
#           RfM applies special treatment to a number of nodes :
#           - Native maya nodes are translated to PxrMaya* nodes.
#           - Some nodes are ignored (unitConversion, etc).
#           - Some nodes are translated into more than one node.
#               - place3dTexture translates to 2 nodes : PxrMayaPlacement3d and
#                 a scoped coordinate system.
#           - Some connections (float->color, etc) are created by inserting an
#             additionnal node in the graph (PxrToFloat3, PxrToFloat).
#           It is safer to handle these exceptions once the graph has been
#           parsed.
#
class BlenderGraph:
    __CompToAttr = {'R': 'inputR', 'X': 'inputR',
                    'G': 'inputG', 'Y': 'inputG',
                    'B': 'inputB', 'Z': 'inputB'}
    __CompToIdx = {'R': 0, 'X': 0,
                   'G': 1, 'Y': 1,
                   'B': 2, 'Z': 2}

    def __init__(self):
        self._nodes = {}
        self._invalids = []
        self._connections = []
        self._extras = {}

    def NodeList(self):
        return self._nodes

    def AddNode(self, node, nodetype=None):
        global g_validNodeTypes

        # make sure we always consider the node if we get 'node.attr'
        #node = nodename.split('.')[0]

        if node in self._invalids:
            # print '    already in invalids'
            print('%s invalid' % node.name)
            return False
       
        if node.bl_label not in __BL_NODES_MAP__:
            self._invalids.append(node)
            # we must warn the user, as this is not really supposed to happen.
            print('%s is not a valid node type (%s)' %
                       (node.name, node.__class__.__name__))
            # print '    not a valid node type -> %s' % nodetype
            return False

        if node not in self._nodes:
            #print('adding %s ' % node.name)
            if node.renderman_node_type == 'output':
                self._nodes[node] = BlenderNode(node, 'RendermanOutputNode')
            else:
                self._nodes[node] = BlenderNode(node, node.plugin_name)
            # print '    add to node list'
            return True

        # print '    %s already in node list ? ( %s )' % (node, nodetype)
        return False

    ##
    # @brief      builds topological information and optionaly inserts
    #             floatToFloat3 or float3ToFloat nodes when necessary.
    #
    # @param      self  The object
    #
    # @return     None
    #
    def Process(self):
        global g_validNodeTypes

        # analyse topology
        #
        for node in self._nodes:

            # get incoming connections (both plugs)
            cnx = [l for inp in node.inputs for l in inp.links ]
            # print 'topo: %s -> %s' % (node, cnx)
            if not cnx:
                continue

            for l in cnx:
                # don't store connections to un-related nodes.
                #

                ignoreDst = l.to_node.bl_label not in __BL_NODES_MAP__
                ignoreSrc = l.from_node.bl_label not in __BL_NODES_MAP__

                if ignoreDst or ignoreSrc:
                    print("Ignoring connection %s -> %s" % (l.from_node.name, l.to_node.name))
                    continue

                self._connections.append(("%s.%s" % (fix_blender_name(l.from_node.name), l.from_socket.name),
                                          "%s.%s" % (fix_blender_name(l.to_node.name), l.to_socket.name)))

        # remove duplicates
        self._connections = list(set(self._connections))

        # add the extra conversion nodes to the node list
        #for k, v in self._extras.iteritems():
        #    self._nodes[k] = v

    ##
    # @brief      prepare data for the jason file
    #
    # @param      self   The object
    # @param      Asset  The asset
    #
    # @return     None
    #
    def Serialize(self, Asset):
        global g_validNodeTypes

        # register connections
        #
        for srcPlug, dstPlug in self._connections:
            # print '%s -> %s' % (srcPlug, dstPlug)
            Asset.addConnection(srcPlug, dstPlug)

        # register nodes
        #
        for nodeNm, node in self._nodes.items():

            # Add node to asset
            #
            rmanNode = None
            nodeClass = None
            rmanNodeName = node.rmanNodeType
            if node.blenderNodeType == 'RendermanOutputNode':
                nodeClass = 'root'
                oslPath=None
            else:
                # print 'Serialize %s' % node.mayaNodeType
                oslPath = node.oslPath if node.name == 'PxrOSL' else None
                rmanNode = ra.RmanShadingNode(node.rmanNodeType,
                                              osoPath=oslPath)
                nodeClass = rmanNode.nodeType()
                rmanNodeName = rmanNode.rmanNode()
                # Register the oso file as a dependency that should be saved with
                # the asset.
                if oslPath:
                    osoFile = os.path.join(node.oslPath,
                                           '%s.oso' % node.rmanNodeType)
                    Asset.processExternalFile(osoFile)

            Asset.addNode(node.name, node.rmanNodeType,
                          nodeClass, rmanNodeName,
                          externalosl=(oslPath is not None))

            # some nodes may have an associated transformation
            # keep it simple for now: we support a single world-space
            # matrix or the TRS values in world-space.
            #
            # if node.HasTransform():
            #     Asset.addNodeTransform(node.name, node.transform,
            #                            trStorage=node.tr_storage,
            #                            trSpace=node.tr_space,
            #                            trMode=node.tr_mode,
            #                            trType=node.tr_type)

            for pname, prop in node._params.items():
                Asset.addParam(node.name, pname, prop)

            # if the node is a native maya node, add it to the hostNodes
            # compatibility list.
            #
            #if node.mayaNodeType != node.rmanNodeType:
            #    Asset.registerHostNode(node.rmanNodeType)

    def _parentPlug(self, plug):
        tokens = plug.split('.')
        parent = mc.attributeQuery(tokens[-1], node=tokens[0],
                                   listParent=True)
        if parent is None:
            raise RmanAssetBlenderError('%s is not a child plug !')
        tokens[-1] = parent[0]
        return '.'.join(tokens)

    def _isParentPlug(self, plug):
        tokens = plug.split('.')
        parents = mc.attributeQuery(tokens[-1], node=tokens[0],
                                    listParent=True)
        return (parents is None)

    def _isChildPlug(self, plug):
        tokens = plug.split('.')
        parents = mc.attributeQuery(tokens[-1], node=tokens[0],
                                    listParent=True)
        return (parents is not None)

    def _conversionNodeName(self, plug):
        return re.sub('[\W]', '_', plug)

    def _f3_to_f1_connection(self, srcPlug, dstPlug):
        #
        #   Insert a PxrToFloat node:
        #
        #   texture.resultRGBR->srf.presence
        #   becomes:
        #   texture.resultRGB->srf_presence.input|resultF->srf.presence
        #
        convNode = self._conversionNodeName(dstPlug)
        if convNode not in self._extras:
            self._extras[convNode] = MayaNode(convNode,
                                              'PxrToFloat')

        # connect the conversion node's out to the dstPlug's
        # attr
        #
        convOutPlug = '%s.resultF' % convNode
        self._connections.append((convOutPlug, dstPlug))

        # connect the src parent plug to the conversion node's
        # input.
        #
        srcParentPlug = self._parentPlug(srcPlug)
        convInPlug = '%s.input' % (convNode)
        self._connections.append((srcParentPlug, convInPlug))
        # Tell the PxrToFloat node to use the correct channel.
        comp = srcPlug[-1]
        self._extras[convNode]._params['mode']['value'] = \
            self.__CompToIdx[comp]

        # register the connect the plug as connected
        #
        self._extras[convNode].SetConnected('input')

        # print '\noriginal cnx: %s -> %s ---' % (srcPlug, dstPlug)
        # print ('new cnx: %s -> %s | %s -> %s' %
        #        (srcParentPlug, convInPlug, convOutPlug, dstPlug))

    def _f1_to_f3_connection(self, srcPlug, dstPlug):
        #
        #   Insert a PxrToFloat3 node:
        #
        #   noise.resultF->srf.colorR
        #   becomes:
        #   noise.resultF->srf_color.inputR|resultRGB->srf.color
        #
        # create a conversion node
        #
        dstParentPlug = self._parentPlug(dstPlug)
        convNode = self._conversionNodeName(dstParentPlug)
        if convNode not in self._extras:
            self._extras[convNode] = MayaNode(convNode,
                                              'PxrToFloat3')

        # connect the conversion node's out to the dstPlug's
        # parent attr
        #
        convOutPlug = '%s.resultRGB' % convNode
        self._connections.append((convOutPlug, dstParentPlug))

        # connect the src plug to the conversion node's input
        #
        comp = dstPlug[-1]
        convAttr = self.__CompToAttr[comp]
        convInPlug = '%s.%s' % (convNode, convAttr)
        self._connections.append((srcPlug, convInPlug))

        # print '\noriginal cnx: %s -> %s ---' % (srcPlug, dstPlug)
        # print ('new cnx: %s -> %s | %s -> %s' %
        #        (srcPlug, convInPlug, convOutPlug, dstParentPlug))

        # register the conversion plug as connected
        #
        self._extras[convNode].SetConnected(convAttr)

    def _f3_to_f3_connection(self, srcPlug, dstPlug):
        #
        #   Insert a PxrToFloat->PxrToFloat3 node chain:
        #
        #   tex.resultRGBR->srf.colorG
        #   becomes:
        #   tex.resultRGB->srf_colorComp.input|mode=R|resultF->
        #       ->srf_color.inputG|resultRGB->srf.color
        #

        # create PxrToFloat3->dstNode
        parentPlug = self._parentPlug(dstPlug)
        convDst = self._conversionNodeName(parentPlug)
        if convDst not in self._extras:
            self._extras[convDst] = MayaNode(convDst,
                                             'PxrToFloat3')

        # create srcNode->PxrToFloat
        # this time we use the child plug to name the node as each
        # child plug could create a new conversion node.
        convSrc = self._conversionNodeName(srcPlug)
        if convSrc not in self._extras:
            self._extras[convSrc] = MayaNode(convSrc,
                                             'PxrToFloat')

        # connect the srcOutPlug to convSrcInPlug (color->color)
        srcParentPlug = self._parentPlug(srcPlug)
        convSrcInPlug = '%s.input' % convSrc
        self._connections.append((srcParentPlug, convSrcInPlug))
        comp = srcPlug[-1]
        # set the matching channel
        self._extras[convSrc]._params['mode']['value'] = self.__CompToIdx[comp]

        # connect convSrcOutPlug to convDstInPlug
        convSrcOutPlug = '%s.resultF' % convSrc
        comp = dstPlug[-1]
        convDstAttr = self.__CompToAttr[comp]
        convDstInPlug = '%s.%s' % (convDst, convDstAttr)
        self._connections.append((convSrcOutPlug, convDstInPlug))

        # finally, connect convDstOutPlug to dstPlug's parent
        convDstOutPlug = "%s.resultRGB" % convDst
        dstParentPlug = self._parentPlug(dstPlug)
        self._connections.append((convDstOutPlug, dstParentPlug))

        # print '\noriginal cnx: %s -> %s ---' % (srcPlug, dstPlug)
        # print ('new cnx: %s -> %s | %s -> %s | %s -> %s' %
        #        (srcParentPlug, convSrcInPlug, convSrcOutPlug,
        #         convDstInPlug, convDstOutPlug, dstParentPlug))

        # register connected plugs
        self._extras[convSrc].SetConnected('input')
        self._extras[convDst].SetConnected(convDstAttr)

    def __str__(self):
        return ('_nodes = %s\n_connections = %s' %
                (self._nodes, self._connections))

    def __repr__(self):
        return str(self)

##
# @brief      Returns a params array similar to the one returned by
#             rmanShadingNode. This allows us to deal with maya nodes.
#
# @param      nodetype  the maya node type
#
# @return     Array of structs
#
def blenderParams(nodetype):
    params = []
    if nodetype == 'shadingEngine':
        params.append({'type': 'float[]', 'name': 'surfaceShader'})
        params.append({'type': 'float[]', 'name': 'displacementShader'})
        params.append({'type': 'float[]', 'name': 'volumeShader'})
    elif nodetype == 'place3dTexture':
        params.append({'type': 'float[]', 'name': 'translate'})
        params.append({'type': 'float[]', 'name': 'rotate'})
        params.append({'type': 'float[]', 'name': 'scale'})
    else:
        print('Ignoring unsupported node type: %s !' % nodetype)
    return params


##
# @brief      Parses a Maya node graph, starting from 'node'.
#
# @param      node   root of the graph
# @param      Asset  RmanAsset object to store the nodeGraph
#
# @return     none
#
def parseNodeGraph(nodes_to_convert, Asset):

    #out = next((n for n in nodes_to_convert if hasattr(n, 'renderman_node_type') and
    #                    n.renderman_node_type == 'output'), None)

    graph = BlenderGraph()
    #graph.AddNode(out)

    for node in nodes_to_convert:
        # some "nodes" are actually tuples
        if type(node) != type((1,2,3)):
            graph.AddNode(node)

    graph.Process()
    graph.Serialize(Asset)

def exportLightRig(obs, Asset):
    for ob in obs:
        bl_node = shadergraph_utils.get_light_node(ob)

        nodeName = bl_node.name
        nodeType = bl_node.bl_label
        nodeClass = 'light'
        rmanNodeName = bl_node.bl_label

        Asset.addNode(nodeName, nodeType,
                        nodeClass, rmanNodeName,
                        externalosl=False)

        mtx = ob.matrix_world
        floatVals = list()
        floatVals = transform_utils.convert_matrix(mtx)
        Asset.addNodeTransform(nodeName, floatVals )

        for prop_name, meta in bl_node.prop_meta.items():
            if not hasattr(bl_node, prop_name):
                continue
            prop = getattr(bl_node, prop_name)   
            if meta['renderman_type'] == 'page' or prop_name == 'notes' or meta['renderman_type'] == 'enum':
                continue

            elif meta['widget'] == 'null':
                continue

            ptype = meta['renderman_type']
            pname = meta['renderman_name']  
            param_widget = meta['widget']           

            if ptype == 'string':
                val = string_utils.convert_val(prop, type_hint=ptype)
                if param_widget in ['fileinput', 'assetidinput']:
                    options = meta['options']
                    # txmanager doesn't currently deal with ptex
                    if bl_node.bl_idname == "PxrPtexturePatternNode":
                        val = string_utils.expand_string(val, display='ptex', asFilePath=True)        
                    # ies profiles don't need txmanager for converting                       
                    elif 'ies' in options:
                        val = string_utils.expand_string(val, display='ies', asFilePath=True)
                    # this is a texture
                    elif ('texture' in options) or ('env' in options) or ('imageplane' in options):
                        tx_node_id = texture_utils.generate_node_id(bl_node, pname, ob=ob)
                        tx_val = texture_utils.get_txmanager().get_txfile_from_id(tx_node_id)
                        val = tx_val if tx_val != '' else val
                elif param_widget == 'assetidoutput':
                    display = 'openexr'
                    if 'texture' in meta['options']:
                        display = 'texture'
                    val = string_utils.expand_string(val, display='texture', asFilePath=True)         
            else:
                val = string_utils.convert_val(prop, type_hint=ptype)                    

            pdict = {'type': ptype, 'value': val}
            Asset.addParam(nodeName, pname, pdict)

##
# @brief      Gathers infos from the image header
#
# @param      imagePath  the image path
# @param      Asset  The asset in which infos will be stored.
#
def parse_texture(imagePath, Asset):
    """Gathers infos from the image header

    Args:
        imagePath {list} -- A list of texture paths.
        Asset {RmanAsset} -- the asset in which the infos will be stored.
    """
    img = FilePath(imagePath)
    # gather info on the envMap
    #
    Asset.addTextureInfos(img)

def export_asset(nodes, atype, infodict, category, cfg, renderPreview='std',
                 alwaysOverwrite=False):
    """Exports a nodeGraph or envMap as a RenderManAsset.

    Args:
        nodes (str) -- Maya node used as root
        atype (str) -- Asset type : 'nodeGraph' or 'envMap'
        infodict (dict) -- dict with 'label', 'author' & 'version'
        category (str) -- Category as a path, i.e.: "/Lights/LookDev"

    Kwargs:
        renderPreview (str) -- Render an asset preview ('std', 'fur', None).\
                        Render the standard preview swatch by default.\
                        (default: {'std'})
        alwaysOverwrite {bool) -- Will ask the user if the asset already \
                        exists when not in batch mode. (default: {False})
    """
    label = infodict['label']
    Asset = RmanAsset(assetType=atype, label=label, previewType=renderPreview)

    asset_type = ''
    if atype == 'nodeGraph':
        hostPrefs = get_host_prefs()
        rel_path = os.path.relpath(category, hostPrefs.getSelectedLibrary())   
        if rel_path.startswith('Materials'):
            asset_type = 'Materials'
        else:
            asset_type = 'LightRigs'    

    # Add user metadata
    #
    for k, v in infodict.items():
        if k == 'label':
            continue
        Asset.addMetadata(k, v)

    # Compatibility data
    # This will help other application decide if they can use this asset.
    #
    prmanversion = "%d.%d.%s" % filepath_utils.get_rman_version(filepath_utils.guess_rmantree())
    Asset.setCompatibility(hostName='Blender',
                           hostVersion=bpy.app.version,
                           rendererVersion=prmanversion)                           

    # parse maya scene
    #
    if atype is "nodeGraph":
        if asset_type == 'Materials':
            parseNodeGraph(nodes, Asset)
        else:
            exportLightRig(nodes, Asset)
    elif atype is "envMap":
        parse_texture(nodes[0], Asset)
    else:
        raise RmanRmanAssetBlenderError("%s is not a known asset type !" % atype)

    #  Get path to our library
    #
    assetPath = FilePath(category)

    #  Create our directory
    #
    assetDir = asset_name_from_label(label)
    dirPath = assetPath.join(assetDir)
    if not dirPath.exists():
        os.mkdir(dirPath)

    #   Check if we are overwriting an existing asset
    #
    jsonfile = dirPath.join("asset.json")

    #  Save our json file
    #
    # print("export_asset: %s..." %   dirPath)
    Asset.save(jsonfile, compact=False)

    if asset_type == 'Materials':
        ral.renderAssetPreview(Asset, progress=None, rmantree=filepath_utils.guess_rmantree())
    elif asset_type == 'LightRigs':
        ral.renderAssetPreview(Asset, progress=None, rmantree=filepath_utils.guess_rmantree())
    elif Asset._type == 'envMap':
        ral.renderAssetPreview(Asset, progress=None, rmantree=filepath_utils.guess_rmantree())

    return True        


##
# @brief      Sets param values of a nodeGraph node
#
# @param      nodeName    string
# @param      paramsList  list of RmanAssetNodeParam objects
#
# @return     none
#
def setParams(node, paramsList):
    '''Set param values.
       Note: we are only handling a subset of maya attribute types.'''
    float3 = ['color', 'point', 'vector', 'normal']
    for param in paramsList:
        pname = param.name()
        ptype = param.type()

        # arrays
        if '[' in ptype:
            # always set the array length

            # try to get array length
            rman_type = ptype.split('[')[0]
            array_len = ptype.split('[')[1].split(']')[0]
            if array_len == '':
                continue
            array_len = int(array_len)
            setattr(node, '%s_arraylen' % pname, array_len)    

            pval = param.value()

            if pval is None or pval == []:
                # connected param
                continue    

            plen = len(pval)
            if rman_type in ['integer', 'float', 'string']:
                for i in range(0, plen):
                    val = pval[i]
                    parm_nm = '%s[%d]' % (pname, (i))
                    setattr(node, parm_nm, val)
            # float3 types
            elif rman_type in float3:
                j = 1
                if isinstance(pval[0], list):
                    for i in range(0, plen):
                        parm_nm = '%s[%d]' % (pname, (j))
                        val = (pval[i][0], pval[i][0], pval[i][0])
                        setattr(node, parm_nm, val)
                        j +=1
                else:        
                    for i in range(0, plen, 3):
                        parm_nm = '%s[%d]' % (pname, (j))
                        val = (pval[i], pval[i+1], pval[i+2])
                        setattr(node, parm_nm, val)                                
                        j = j+1            

        elif pname in node.bl_rna.properties.keys():
            if ptype is None or ptype in ['vstruct', 'struct']:
                # skip vstruct and struct params : they are only useful when connected.
                continue

            pval = param.value()

            if pval is None or pval == []:
                # connected param
                continue

            if pname == "placementMatrix":
                # this param is always connected.
                continue
            if 'string' in ptype:
                setattr(node, pname, pval)
            elif ptype in float3:
                try:
                   setattr(node, pname, pval)
                except:
                    print('setParams float3 FAILED: %s  ptype: %s  pval: %s' %
                          (nattr, ptype, repr(pval)))
            else:
                try:
                    if type(getattr(node,pname)) == type(""):
                        setattr(node, pname, str(pval))
                    else:
                        setattr(node, pname, pval)
                except:
                    if type(getattr(node, pname)) == bpy.types.EnumProperty:
                        setattr(node, pname, str(pval))

    # if this is a PxrSurface and default != val, then turn on the enable.
    if hasattr(node, 'plugin_name') and node.plugin_name == 'PxrSurface':
        setattr(node, 'enableDiffuse', (getattr(node, 'diffuseGain') != 0))
        for gain,enable in __GAINS_TO_ENABLE__.items():
            val = getattr(node, gain)
            param = next((x for x in paramsList if x.name() == gain), None)
            if param and "reference" in param.type():
                setattr(node, enable, True)
            elif val and node.bl_rna.properties[gain].default != getattr(node, gain):
                if type(val) == float:
                    if val == 0.0:
                        continue
                else:
                    for i in val:
                        if i:
                            break
                    else:
                        continue
                setattr(node, enable, True)

                        # if ptype == 'riattr':
                        #     mayatype = mc.getAttr(nattr, type=True)
                        #     try:
                        #         mc.setAttr(nattr, pval, type=mayatype)
                        #     except:
                        #         print('setParams scalar FAILED: %s  ptype: %s'
                        #               '  pval:" %s  mayatype: %s' %
                        #               (nattr, ptype, repr(pval), mayatype))
                        # else:
                        #     print('setParams scalar FAILED: %s  ptype: %s'
                        #           '  pval:" %s  mayatype: %s' %
                        #           (nattr, ptype, repr(pval), mayatype))


##
# @brief      Set the transform values of the maya node.
# @note       We only support flat transformations for now, which means that we
#             don't rebuild hierarchies of transforms.
#
# @param      name  The name of the tranform node
# @param      fmt   The format data
# @param      vals  The transformation values
#
# @return     None
#
def setTransform(name, fmt, vals):
    if fmt[2] == TrMode.k_flat:
        if fmt[0] == TrStorage.k_matrix:
            mc.xform(name, ws=True, matrix=vals)
        elif fmt[0] == TrStorage.k_TRS:
            # much simpler
            mc.setAttr((name + '.translate'), *vals[0:3], type='float3')
            mc.setAttr((name + '.rotate'), *vals[3:6], type='float3')
            mc.setAttr((name + '.scale'), *vals[6:9], type='float3')
    else:
        raise RmanAssetBlenderError('Unsupported transform mode ! (hierarchical)')


##
# @brief      Creates all maya nodes defined in the asset's nodeGraph and sets
#             their param values. Nodes will be renamed by Maya and the mapping
#             from original name to actual name retuned as a dict, to allow us
#             to connect the newly created nodes later.
#
# @param      Asset  RmanAsset object containing a nodeGraph
#
# @return     dict mapping the graph id to the actual maya node names.
#
def createNodes(Asset):

    nodeDict = {}
    nt = None

    mat = bpy.data.materials.new(Asset.label())
    mat.use_nodes = True
    nt = mat.node_tree       

    # create output node
    output_node = nt.nodes.new('RendermanOutputNode')

    curr_x = 250
    for node in Asset.nodeList():
        nodeId = node.name()
        nodeType = node.type()
        nodeClass = node.nodeClass()
        # print('%s %s: %s' % (nodeId, nodeType, nodeClass))
        fmt, vals, ttype = node.transforms()
        # print('+ %s %s: %s' % (fmt, vals, ttype))

        if nodeClass == 'bxdf':
            bl_node_name = __BL_NODES_MAP__.get(nodeType, None)
            if not bl_node_name:
                continue
            created_node = nt.nodes.new(bl_node_name)
            created_node.location[0] = -curr_x
            curr_x = curr_x + 250
            created_node.name = nodeId
            created_node.label = nodeId

            nt.links.new(created_node.outputs['Bxdf'], output_node.inputs['Bxdf'])            
        elif nodeClass == 'displace':
            bl_node_name = __BL_NODES_MAP__.get(nodeType, None)
            if not bl_node_name:
                continue
            created_node = nt.nodes.new(bl_node_name)            
            created_node.location[0] = -curr_x
            curr_x = curr_x + 250
            created_node.name = nodeId
            created_node.label = nodeId

            nt.links.new(created_node.outputs['Displacement'], output_node.inputs['Displacement'])            
        elif nodeClass == 'pattern':
            if node.externalOSL():
                # if externalOSL() is True, it is a dynamic OSL node i.e. one
                # loaded through a PxrOSL node.
                # if PxrOSL is used, we need to find the oso in the asset to
                # use it in a PxrOSL node.
                oso = Asset.getDependencyPath(nodeType + '.oso')
                if oso is None:
                    err = ('createNodes: OSL file is missing "%s"'
                           % nodeType)
                    raise RmanAssetBlenderError(err)
                created_node = nt.nodes.new('PxrOSLPatternNode')
                created_node.location[0] = -curr_x
                curr_x = curr_x + 250
                created_node.codetypeswitch = 'EXT'
                created_node.shadercode = oso
                created_node.RefreshNodes({}, nodeOR=created_node)
            else:
                bl_node_name = __BL_NODES_MAP__.get(nodeType, None)
                if not bl_node_name:
                    continue
                created_node = nt.nodes.new(bl_node_name)   
                created_node.location[0] = -curr_x
                curr_x = curr_x + 250
                created_node.name = nodeId
                created_node.label = nodeId                             

        elif nodeClass == 'root':
            continue
        elif nodeClass == 'light':
            # we don't deal with mesh lights
            if nodeType == 'PxrMeshLight':
                continue

            bpy.ops.object.rman_add_light(rman_light_name=nodeType)
            light = bpy.context.active_object

            light.name = nodeId
            light.data.name = nodeId    
           
            if fmt[2] == TrMode.k_flat:
                if fmt[0] == TrStorage.k_matrix:                   
                    light.matrix_world[0] = vals[0:4]
                    light.matrix_world[1] = vals[4:8]
                    light.matrix_world[2] = vals[8:12]
                    light.matrix_world[3] = vals[12:]
                    light.matrix_world.transpose()
                elif fmt[0] == TrStorage.k_TRS:  
                    light.location = vals[0:3]                    
                    light.scale = vals[6:9]

                    # rotation
                    light.rotation_euler = (radians(vals[3]), radians(vals[4]), radians(vals[5]))

            try:
                cdata = Asset._assetData['compatibility']
                if cdata['host']['name'] != 'Blender':
                    # assume that if a lightrig did not come from Blender,
                    # we need convert from Y-up to Z-up
                    yup_to_zup = mathutils.Matrix.Rotation(radians(90.0), 4, 'X')
                    light.matrix_world = yup_to_zup @ light.matrix_world
            except:
                pass

            created_node = light.data.renderman.get_light_node()
            mat = light
            nt = light.data.node_tree 

        if created_node:
            nodeDict[nodeId] = created_node.name
            setParams(created_node, node.paramsDict())

        if nodeClass == 'bxdf':
            created_node.update_mat(mat)

    # # restore selection
    # mc.select(sel)
    return mat,nt,nodeDict


##
# @brief      Connect all nodes in the nodeGraph. Failed connections are only
#             reported as warning.
#
# @param      Asset     a RmanAssetNode object containg a nodeGraph
# @param      nodeDict  map from graph node name to maya node name. If there
#                       was already a node with the same name as the graph
#                       node, this maps to the new node name.
#
# @return     none
#
def connectNodes(Asset, nt, nodeDict):
    for con in Asset.connectionList():
        #print('+ %s.%s -> %s.%s' % (nodeDict[con.srcNode()](), con.srcParam(),
        #                             nodeDict[con.dstNode()](), con.dstParam()))

        srcName = nodeDict.get(con.srcNode(), '')
        dstName = nodeDict.get(con.dstNode(), '')
        if srcName == '' or dstName == '':
            continue

        srcNode = nt.nodes.get(srcName, None)
        dstNode = nt.nodes.get(dstName, None)

        if srcNode == None or dstNode == None:
            continue

        srcSocket = con.srcParam()
        dstSocket = con.dstParam()
        if srcSocket in srcNode.outputs and dstSocket in dstNode.inputs:
            nt.links.new(srcNode.outputs[srcSocket], dstNode.inputs[dstSocket])
        elif dstSocket == 'surfaceShader' or dstSocket == 'rman__surface':
            nt.links.new(srcNode.outputs['Bxdf'], dstNode.inputs['Bxdf'])
        elif dstSocket == 'displacementShader' or dstSocket == 'rman__displacement':
            nt.links.new(srcNode.outputs['Displacement'], dstNode.inputs['Displacement'])
        else:
            print('error connecting %s.%s to %s.%s' % (srcNode,srcSocket, dstNode, dstSocket))

##
# @brief      Check the compatibility of the loaded asset with the host app and
#             the renderman version. We pass g_validNodeTypes to help determine
#             if we have any substitution nodes available. To support
#             Katana/Blender/Houdini nodes in Maya, you would just need to
#             implement a node with the same nßame (C++ or OSL) and make it
#             available to RfM.
#
# @param      Asset  The asset we are checking out.
#
# @return     True if compatible, False otherwise.
#
def compatibilityCheck(Asset):
    global g_validNodeTypes
    # the version numbers should always contain at least 1 dot.
    # I'm going to skip the maya stuff
    prmanversion = "%d.%d.%s" % filepath_utils.get_rman_version(filepath_utils.guess_rmantree())
    compatible = Asset.IsCompatible(rendererVersion=prmanversion,
                                    validNodeTypes=g_validNodeTypes)
    if not compatible:
        str1 = 'This Asset is incompatible ! '
        str2 = 'See Console for details...'
        print(str1 + str2)
    return compatible


##
# @brief      Import an asset into maya
#
# @param      filepath  full path to a *.rma directory
#
# @return     none
#
def importAsset(filepath):
    # early exit
    if not os.path.exists(filepath):
        raise RmanAssetBlenderError("File doesn't exist: %s" % filepath)

    Asset = RmanAsset()
    Asset.load(filepath, localizeFilePaths=True)
    assetType = Asset.type()

    # compatibility check
    #
    #if not compatibilityCheck(Asset):
    #    return

    if assetType == "nodeGraph":
        mat,nt,newNodes = createNodes(Asset)
        connectNodes(Asset, nt, newNodes)
        return mat

    elif assetType == "envMap":
        scene = bpy.context.scene
        dome_lights = [ob for ob in scene.objects if ob.type == 'LIGHT' \
            and ob.data.renderman.get_light_node_name() == 'PxrDomeLight']

        selected_dome_lights = [ob for ob in dome_lights if ob.select_get()]
        env_map_path = Asset.envMapPath()

        if not selected_dome_lights:
            if not dome_lights:
                # create a new dome light              
                bpy.ops.object.rman_add_light(rman_light_name='PxrDomeLight')
                ob = bpy.context.view_layer.objects.active
                plugin_node = ob.data.renderman.get_light_node()
                plugin_node.lightColorMap = env_map_path                    

            elif len(dome_lights) == 1:
                light = dome_lights[0].data
                plugin_node = light.renderman.get_light_node()
                plugin_node.lightColorMap = env_map_path
            else:
                print('More than one dome in scene.  Not sure which to use')
        else:
            for light in selected_dome_lights:
                light = dome_lights[0].data
                plugin_node = light.renderman.get_light_node()
                plugin_node.lightColorMap = env_map_path

    else:
        raise RmanAssetBlenderError("Unknown asset type : %s" % assetType)

    return ''