"""blah"""

# pylint: disable=missing-docstring
import os
import re
import json
import glob
import time
from collections import OrderedDict
from . import (
    txm_log,
    TxManagerError,
    NW,
    IT,
    STATE_MISSING,
    STATE_EXISTS,
    STATE_IS_TEX,
    STATE_ERROR,
    STATE_REPROCESS,
    STATE_UNKNOWN,
    STATE_INPUT_MISSING,
    STATE_AS_STR,
    TEX_EXTENSIONS)
from .txparams import TxParams, TXMAKE_PRESETS
import bpy
#import ice  # pylint: disable=import-error

RULE_FILECACHE = {}
# pixel types
#PXTYPES = {
#    ice.constants.FRACTIONAL: ('int', 8),
#    ice.constants.FIXED_POINT: ('int', 16),
#    ice.constants.FLOAT: ('float', 32),
#    ice.constants.DOUBLE: ('float', 64)
#}

def _get_px_type(txfile):
    img = bpy.data.images.load(txfile)
    data_type = 'float' if img.is_float else 'int'
    data_depth = int(img.depth / img.channels)
    bpy.data.images.remove(img)
    return (data_type, data_depth)


def _load_rules():
    """Load the txmaking rules from txmanager_rules.json. This files can be
    located in:
    - $RMAN_TXMANAGER_RULES/txmanager_rules.json
    - $RMANTREE/etc/txmanager_rules.json
    RMANTREE is the fallback location and if the file

    Returns:
        OrderedDict or None -- The rules dict or None if not available
    """
    rules_path = os.environ.get('RMAN_TXMANAGER_RULES')
    if rules_path is None:
        rules_path = os.environ.get('RMANTREE')
        if rules_path is None:
            return None
        rules_path = os.path.join(rules_path, 'etc')
    rules_file = os.path.join(rules_path, 'txmanager_rules.json')
    if not os.path.exists(rules_file):
        return None
    with open(rules_file, 'r') as fhdl:
        try:
            data = json.load(fhdl, object_pairs_hook=OrderedDict)
        except ValueError as err:
            txm_log().error('Failed to parse %r: %s', rules_file, err)
            return None
    return data


def _reset_rule_filecache():
    RULE_FILECACHE.clear()


class TxItem(object):
    """Struct-like class to store output file(s) specs."""

    def __init__(self, filepath, istex=False):
        self.infile = filepath
        self.outfile = filepath if istex else filepath + '.tex'
        self.state = STATE_IS_TEX if istex else STATE_UNKNOWN
        self.input_timestamp = os.path.getmtime(filepath)
        self.file_size = 0
        self.update_file_size()

    def __eq__(self, other):
        return ((self.infile, self.outfile, self.state) ==
                (other.infile, self.outfile, self.state))

    def __ne__(self, other):
        return ((self.infile, self.outfile, self.state) !=
                (other.infile, self.outfile, self.state))

    def update_file_size(self):
        if self.state == STATE_IS_TEX:
            self.file_size = 0
            return
        try:
            self.file_size = os.path.getsize(self.outfile)
        except OSError:
            self.file_size = 0
        else:
            self.state = STATE_EXISTS


class TxFile(object):
    """A class representing one or more texture file(s).

    detects:
        /path/to/my_udim_texture._MAPID_.tif     > prman token
        /path/to/my_udim_texture.<udim>.tif      > prman UDIM token
        /path/to/my_udim_texture.<UDIM>.tif      > prman/maya UDIM token
        /path/to/my_zbrush_texture_u<u>_v<v>.tif > maya ZBRUSH token (0 based)
        /path/to/my_mudbox_texture_u<U>_v<V>.tif > maya MUDBOX token (1 based)
        /path/to/my_sequence.0034.tif            > frame number
        /path/to/my_udim_texture.%(UDIM)d.tif    > houdini UDIM token
        /path/to/my_sequence.$F.tif              > houdini frame number
        /path/to/my_sequence.`some_expr`.tif     > houdini expression

    Note: The Zbrush and Mudbox tokens MUST start with an underscore.

    Attributes:
        - params (TxParams): holds this file's txmake settings.
        - input_image (str): The original path passed to the constructor.
        - output_texture (str): The path to the texture, including unresolved tokens.
        - tex_dict (dict): map a resolved image path to a TxItem.
        - dirty (bool): False if any of the textures is not available.
        - num_dirty_files (int): The number of textures left to create. 0 when dirty is False.
    """

    tokenExpr = re.compile(r'(_MAPID_|{(udim|UDIM|[F|f][1-4]*)}|_u<[uU]>_v<[vV]>|`.+`|\$(F[1-4]*)|\${[A-Z]+})|\%\(UDIM\)d')
    uvTokenExpr = re.compile(r'_u<[uU]>_v<[vV]>|\%\(UDIM\)d')
    atlasExpr = re.compile(r'(_MAPID_|<(udim|UDIM)>|_u<[uU]>_v<[vV]>|\%\(UDIM\)d)')
    rules = _load_rules()

    def __init__(self, input_image, tex_ext_list=TEX_EXTENSIONS,
                 fallback_path='',
                 fallback_always=False,
                 host_token_resolver_func=None):
        self.log = txm_log()
        self.params = TxParams()
        self.input_image = input_image
        self.is_rtxplugin = 'rtxplugin:' in input_image
        self.output_texture = input_image + '.tex'
        self.tex_dict = {}
        self.dirty = True
        self.num_dirty_files = 0
        self.done_callback = None
        self.state = STATE_MISSING
        self.tex_ext_list = tex_ext_list
        self.org_path = os.path.dirname(self.input_image)
        self.fallback_path = fallback_path
        self.fallback_always = fallback_always
        self.use_fallback_path = False
        self.is_texture_atlas = False
        self.host_token_resolver_func = host_token_resolver_func
        self.error_msg = ''
        self.fileinfo = ''
        self.file_size = 0

        # check if input is a texture atlas
        if re.search(self.atlasExpr, self.output_texture) is not None:
            self.is_texture_atlas = True

        # check if input texture has 'u<u>_v<v>' in it
        # this is what the Maya file node give us when using zbrush uv tile modes
        # RenderMan expects _MAPID_, so substitute
        self.output_texture = re.sub(self.uvTokenExpr, '_MAPID_', self.output_texture)

        if self.is_rtxplugin:
            self.output_texture = self.output_texture[:-4]
            self.dirty = False
            self.state = STATE_EXISTS
            return

        if not self._check_if_input_exists():
            return

        self.build_texture_dict()

        if self._check_source_is_tex():
            return

        if self.fallback_path:
            if self.fallback_always:
                # user has requested we always use the fallback path
                # re-path textures
                self.repath_outputs(new_path=self.fallback_path)
            else:
                 # if we have a fallback path, let's check for textures, there
                self._check_fallback_path()

        # check the existence of the texture and update the state.
        self.check_dirty()

    def _check_if_input_exists(self):
        """Check if the input image exists on disk.

        Returns:
        - True if image exists, False otherwise
        """
        globpat = re.sub(self.tokenExpr, '*', self.input_image)
        if globpat != self.input_image:
            if self.host_token_resolver_func:
                globpat = self.host_token_resolver_func(globpat)
            any_exists = False
            self.log.debug('GLOBALPAT: %s', globpat)
            for fpath in glob.glob(globpat):
                if os.path.exists(fpath):
                    any_exists = True
            if not any_exists:
                self.state = STATE_INPUT_MISSING
                self.dirty = False
                return False
        else:
            resolved_path = self.input_image
            if self.host_token_resolver_func:
                resolved_path = self.host_token_resolver_func(resolved_path)
            if not os.path.exists(resolved_path):
                self.state = STATE_INPUT_MISSING
                self.dirty = False
                return False
        return True

    def _check_fallback_path(self):
        """Check if the fallback path has the textures. If so,
        switch to using that. If there are .tex files in both places,
        use the path that has the most in it."""

        org_path_files = []
        fallback_path_files = []

        for item in list(self.tex_dict.values()):

            if not os.path.isfile(item.outfile):
                fallback_outfile = os.path.join(self.fallback_path,
                                                os.path.basename(item.outfile))

                if os.path.isfile(fallback_outfile):
                    item.state = STATE_EXISTS
                    fallback_path_files.append(fallback_outfile)
            else:
                item.state = STATE_EXISTS
                org_path_files.append(item.outfile)

        if len(fallback_path_files) > len(org_path_files):
            self.repath_outputs(new_path=self.fallback_path)
            self.log.debug('Textures exist in fallback path. Switching...')

    def _check_source_is_tex(self):
        """Check if the source image is already a texture file and sets internal
        states accordingly.

        Returns:
        - True if it is a texture, False otherwise.
        """
        splitext = os.path.splitext(self.input_image)
        # check if this is already a .tex
        # os.path.splitext always returns a tuple of size 2.
        ext = splitext[1]
        if ext in self.tex_ext_list:
            self.dirty = False
            globpat = re.sub(self.tokenExpr, '*', self.input_image)
            if globpat != self.input_image:
                if self.host_token_resolver_func:
                    globpat = self.host_token_resolver_func(globpat)
                for fpath in glob.glob(globpat):
                    self.state = STATE_IS_TEX if os.path.exists(fpath) else STATE_ERROR
            else:
                resolved_path = self.input_image
                if self.host_token_resolver_func:
                    resolved_path = self.host_token_resolver_func(resolved_path)
                self.state = STATE_IS_TEX if os.path.exists(resolved_path) else STATE_ERROR
            self.output_texture = self.input_image
            # RenderMan expects _MAPID_, so substitute
            self.output_texture = re.sub(self.uvTokenExpr, '_MAPID_', self.output_texture)
            return True
        return False

    def __str__(self):
        """
        Return a string representation for debugging.
        """
        sstr = '%s =================================\n' % (__name__)
        sstr += '|_ input_image: %r\n' % (self.input_image)
        i = 0
        for fpath, item in self.tex_dict.items():
            sstr += ('|_ #%0d: %r\n    |_ %r\n    |_ %s\n' %
                     (i, fpath, item.outfile, STATE_AS_STR[item.state]))
            i += 1
        sstr += '|_ dirty = %s\n' % self.dirty
        sstr += '|_ num_dirty_files = %s\n' % self.num_dirty_files
        sstr += str(self.params)
        return sstr

    def tooltip(self):
        """
        Return a html representation for the UI.
        """
        html = '%s<div><b>image</b>: "%s"</div>' % (NW, self.input_image)
        html += '<div><b>texture(s)</b>:</div>'
        for item in list(self.tex_dict.values()):
            html += ('%s&#8226; %s : %s</div>' %
                     (IT, item.outfile, STATE_AS_STR[item.state]))
        html += '<div><b>fileinfo</b>: %s</div>' % self.fileinfo
        html += '<div><b>dirty</b>: %s</div>' % self.dirty
        html += ('%s&#8226; num_dirty_files = %s</div></div>' %
                 (IT, self.num_dirty_files))
        html += self.params.tooltip()
        return html

    def tooltip_text(self):
        """
        Return a regular text version of tooltip
        """
        html = 'Image: "%s"\n' % (self.input_image)
        html += 'Texture(s):\n'
        for item in list(self.tex_dict.values()):
            html += ('   * %s : %s\n' %
                     (item.outfile, STATE_AS_STR[item.state]))
        #html += 'Fileinfo: %s' % self.fileinfo
        html += 'Dirty: %s\n' % self.dirty
        html += ('num_dirty_files = %s' %
                 (self.num_dirty_files))
        #html += self.params.tooltip()
        return html        

    def build_texture_dict(self):
        """Resolve special tokens in input_image like _MAPID_, <udim>, <f4>
        to get a list of input images and build the tex_dict.

        Arguments:
            - input_image {str} -- input image

        Returns:
            - dict -- dict of resolved TxItems
        """
        self.tex_dict = {}
        globpat = re.sub(self.tokenExpr, '*', self.input_image)
        ext = os.path.splitext(self.input_image)[1]
        is_tex = ext in self.tex_ext_list
        if globpat != self.input_image:
            if self.host_token_resolver_func:
                globpat = self.host_token_resolver_func(globpat)
            for fpath in glob.glob(globpat):
                self.tex_dict[fpath] = TxItem(fpath, istex=is_tex)
        else:
            resolved_path = self.input_image
            if self.host_token_resolver_func:
                resolved_path = self.host_token_resolver_func(resolved_path)
            self.tex_dict[resolved_path] = TxItem(resolved_path, istex=is_tex)
        self.update_file_size()

    def source_is_tex(self):
        """
        Return True is the source file is already a texture.
        """
        return self.state == STATE_IS_TEX

    def num_textures(self):
        """
        Returns the number of textures generated by this input_image.
        WARNING: This will not work if the input is a texture.
        """
        return len(self.tex_dict)

    def set_item_state(self, item, state):
        if state in [STATE_EXISTS, STATE_IS_TEX]:
            self.num_dirty_files -= 1
        elif state in [STATE_MISSING, STATE_ERROR, STATE_REPROCESS]:
            self.num_dirty_files += 1
        else:
            # ignore STATE_IN_QUEUE, STATE_PROCESSING
            pass

        item.state = state
        self.state = max(self.state, item.state)

        if self.num_dirty_files <= 0:
            self.num_dirty_files = 0
            self.dirty = False
            self.state = STATE_EXISTS
        else:
            self.dirty = True

    def set_file_state(self, infile, state):
        self.set_item_state(self.tex_dict[infile], state)

    def get_output_texture(self):
        """
        Return the path (un-resolved tokens included)
        to the texture file(s).
        """
        return self.output_texture

    def get_params(self):
        return self.params

    def set_params(self, params):
        self.params = params
        # FIXME update output images with new hash

    def is_dirty(self):
        """
        Returns True if:
        - the texture is missing.
        - the last conversion has failed.
        - the user has requested reprocessing with different settings.

        WARNING: there is no file checking: it just looks at the state attribute.
        """
        return self.dirty

    def check_dirty(self, force_check=False):
        """
        Check the file's state and returns True if it needs to be sent to the
        txmake queue.
        1. If the file is already a tex, is queued or being converted, we just
        return False.
        2. If the last conversion failed or reprocessing was requested by the
        user, return True.
        3. If the corresponding tex file doesn't exists, return True.
        4. At this point, we know the tex(s) exists and we make sure the source
        file(s) is/are not more recent than the tex(s).

        Arguments:
            - force_check {bool} -- ignore the dirty member var and force a check
                                    of input files

        """

        # only check if it hasn't been marked clean, like a *.tex source file.
        if (not force_check) and (not self.dirty):
            self.log.debug('not dirty: skipping... %r', self.input_image)
            return False

        # reset
        self.dirty = False
        self.num_dirty_files = 0

        # if this is a rtxplugin invocation, make sure we keep it valid.
        if self.is_rtxplugin:
            return self.dirty

        # re-check if the input image is missing
        if not self._check_if_input_exists():
            return False
        else:
            # input image exists now, check if tex_dict
            # is empty. If it is, build it now.
            if not self.tex_dict:
                self.build_texture_dict()

        # if the source is already a *.tex, we should check if the timestamp
        # has changed since this TxFile was created.
        if self.source_is_tex():
            for in_img, item in self.tex_dict.items():
                tstp = item.input_timestamp
                in_img_time = os.path.getmtime(in_img)
                if in_img_time > tstp:
                    self.dirty = True
                    item.input_timestamp = tstp
                    item.state = STATE_MISSING
                    self.log.debug('dirty ! timestamp for %r has changed  (%s > %s)',
                                   in_img, in_img_time, tstp)
        else:
            for in_img, item in self.tex_dict.items():

                if item.state == STATE_REPROCESS:
                    self.dirty = True
                    self.state = STATE_REPROCESS
                    self.num_dirty_files += 1
                    self.log.debug("dirty: reprocess %r", in_img)
                    continue

                if not os.path.isfile(item.outfile):
                    item.state = STATE_MISSING
                    self.state = STATE_MISSING
                    self.dirty = True
                    self.num_dirty_files += 1
                    self.log.debug("dirty: doesn't exist %r", in_img)
                    continue
                else:
                    item.state = STATE_EXISTS
                    self.log.debug("clean: exist %r", in_img)

                in_img_time = os.path.getmtime(in_img)
                out_img_time = os.path.getmtime(item.outfile)
                now_time = time.time()

                if in_img_time > out_img_time:
                    item.state = STATE_MISSING
                    self.state = STATE_MISSING
                    self.dirty = True
                    self.num_dirty_files += 1
                    self.log.debug('dirty ! %r is newer  (%s > %s)',
                                   in_img, in_img_time, out_img_time)

                elif (out_img_time > now_time) and (in_img_time <= now_time):
                    # if the outfile is from the future, but the
                    # in_img is not, mark as dirty
                    item.state = STATE_MISSING
                    self.state = STATE_MISSING
                    self.dirty = True
                    self.num_dirty_files += 1
                    self.log.debug('dirty ! %r is from the future, but input '
                                   'file is not!  (%s > %s)',
                                   out_img_time, out_img_time, now_time)

            # we're not dirty, mark TxFile state as exists
            if self.dirty is False:
                self.state = STATE_EXISTS

        self.log.debug('%r -> dirty (%s)', os.path.basename(self.input_image),
                       self.dirty)
        return self.dirty

    def repath_outputs(self, new_path):
        """
        Move all output files to a new directory.
        Only paths are modified, existing files are not affected.
        """
        self.use_fallback_path = True
        self.fallback_path = new_path

        # re-path output textures
        for item in list(self.tex_dict.values()):
            item.outfile = os.path.join(new_path,
                                        os.path.basename(item.outfile))
        # repath the general output path.
        self.output_texture = os.path.join(new_path,
                                           os.path.basename(self.output_texture))

    def re_process(self):
        """
        Tag the file to be reprocessed with txmake.
        Only the state attribute changes, the file lists are unmodified.
        """
        for item in list(self.tex_dict.values()):
            if not item.state == STATE_IS_TEX and not self.is_rtxplugin:
                item.state = STATE_REPROCESS
        self.dirty = True
        self.state = STATE_REPROCESS
        self.num_dirty_files = self.num_textures()

    def __eq__(self, other):
        # we don't compare the params anymore. The first discovered instance of
        # an image wins until one day we find a better solution.
        return ((self.input_image, self.tex_dict, self.dirty) ==
                (other.input_image, other.tex_dict, other.dirty))

    def __ne__(self, other):
        return ((self.input_image, self.tex_dict, self.dirty) !=
                (other.input_image, other.tex_dict, other.dirty))

    def __hash__(self):
        return id(self)

    def as_dict(self):
        txfile = dict()
        try:
            vardict = vars(self)
            for key, val in vardict.items():
                if key == 'params':
                    txfile[key] = self.params.get_params_as_dict()
                else:
                    txfile[key] = val
        except:
            raise TxManagerError('Unable to convert TxFile to a dictionary.')

        return txfile

    def set_from_dict(self, vardict):
        for key, val in vardict.items():
            if key == 'params':
                self.params.set_params_from_dict(val)
            else:
                try:
                    setattr(self, key, val)
                except AttributeError:
                    # warn but don't raise an error.
                    self.log.error('%s is not an attribute of TxFile ! vardict = %r',
                                   key, vardict)

    def set_done_callback(self, func, node_ids):
        """Setup the callbacks that will be executed by the host application to
        send an edit to the renderer. This method will build an array of
        closures.

        Args:
        - func (function pointer): The function passed by the host app on
                manager initialisation.
        - node_ids (list): all ids using this txfile.
        """
        self.log.debug('done_callback = %r -> %s', func, node_ids)
        self.done_callback = []
        for nid in node_ids:
            #self.done_callback.append(func(nid, self))
            self.done_callback.append((func, nid, self))

    def emit_done_callback(self, force=False):
        """Notify the DCC host this texture is available. We will only notify
        if the texture exists. In the case of texture atlases, all files need
        to be converted.

        Args:
        - force (bool): Force notification irrespective of current state.
        """
        if self.done_callback:
            if force or self.state == STATE_EXISTS:
                #for func in self.done_callback:
                for func,nid,txfile in self.done_callback:
                    try:
                        #func()
                        func(nid,txfile)
                    except Exception as err:
                        self.log.warning('done_callback FAILED = %r',
                                         str(err))
                        # pass
                self.log.debug('EMIT: done_callback = %r (reset)',
                               self.done_callback)
            else:
                self.log.debug('SKIP:  force=%s  state=%s',
                               force, STATE_AS_STR[self.state])
        else:
            self.log.debug('IGNORE: done_callback = %r', self.done_callback)

    def delete_texture_files(self):
        """Delete all texture files associated with that instance and set the
        state to 're-process'.
        """
        if self.dirty or self.state == STATE_IS_TEX or self.is_rtxplugin:
            return

        for item in list(self.tex_dict.values()):
            tex = item.outfile
            try:
                os.remove(tex)
            except OSError:
                self.log.error(' |_ Failed to remove: %r', tex)
            else:
                self.log.info(' |_ Deleted: %r', tex)
        self.re_process()

    def apply_preset(self, ntype, category):
        if self.state == STATE_IS_TEX:
            return
        if self.rules is None or int(os.environ.get('TXMGR_IGNORE_RULES', 0)):
            self.log.debug('Using hard-codes rules ! -> %s', self.rules)
            # Use named presets
            if ntype == 'PxrDomeLight':
                self.params.set_params_from_dict(TXMAKE_PRESETS['env'])
            elif ntype == 'imagePlane':
                self.params.set_params_from_dict(TXMAKE_PRESETS['imageplane'])
            else:
                self.params.set_params_from_dict(TXMAKE_PRESETS['texture'])
        else:
            # we have a rules dict: compute the required param combination.
            if not self.tex_dict:
                self.log.debug('Empty self.tex_dict ! -> %s', self.input_image)
                return
            test_file = self.tex_dict[list(self.tex_dict.keys())[0]].infile
            try:
                return RULE_FILECACHE[test_file]
            except KeyError:
                # build the dict used to evaluate the rule expressions.
                var_dict = {'node_type': ntype,
                            'classification': category,
                            'img_atlas': self.is_texture_atlas}
                var_dict['img_name'], var_dict['img_ext'] = os.path.splitext(
                    os.path.basename(test_file))
                # load test_file headers
                #img = ice.Load(test_file)
                (var_dict['img_type'],
                 var_dict['img_depth']) = _get_px_type(test_file) #PXTYPES[img.ComponentType()]
                self.fileinfo = ('%s %s ("%s"' %
                                 (var_dict['img_type'], var_dict['img_depth'],
                                  test_file))
                # close test_file
                #ice._registry.Remove(img)   # FIXME: pending fix to ice lib
                #del img
                # evaluate rules
                for category, c_dict in self.rules.items():
                    if category in var_dict['classification']:
                        args = c_dict['args']
                        rules = c_dict.get('rules', {})
                        for rule, r_dict in rules.items():
                            if eval(rule % var_dict) is True:
                                if r_dict.get('DO_NOT_CONVERT', False):
                                    self.state = STATE_IS_TEX
                                    self.output_texture = self.input_image
                                    return
                                args.update(r_dict.get('args', {}))
                        RULE_FILECACHE[test_file] = args
                        self.params.set_params_from_dict(args)
                self.log.debug('computed rules ! -> %s', var_dict)
            else:
                self.log.debug('looked-up rules ! -> %s', args)

    def update_file_size(self):
        self.file_size = 0
        for txitem in list(self.tex_dict.values()):
            if txitem.state != STATE_EXISTS:
                continue
            self.file_size += txitem.file_size

