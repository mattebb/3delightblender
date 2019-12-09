# pylint: disable=invalid-name
import re
import time
import os
import datetime
from collections import OrderedDict
from ..rfb_logger import rfb_log
from . import prefs_utils
import bpy

COUNTERS = None


def time_this(f):
    """Function that can be used as a decorator to time any method."""
    def timed(*args, **kw):
        global COUNTERS
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()
        elapsed = (te - ts) * 1000.0
        if COUNTERS is None:
            print('  _ %0.3f ms: %r args:[%r, %r]' % (elapsed, f.__name__,
                                                      args, kw))
        else:
            if not f.__name__ in COUNTERS:
                COUNTERS[f.__name__] = (1, elapsed)
            else:
                COUNTERS[f.__name__] = (COUNTERS[f.__name__][0] + 1,
                                        COUNTERS[f.__name__][1] + elapsed)
        return result

    return timed


STD_TOKENS = OrderedDict()
STD_TOKENS['ws'] = '<ws>:\tpath to current project'
STD_TOKENS['pwd'] = '<pwd>:\tpath to current directory'
STD_TOKENS['file'] = '<file>:\tscene file name'
STD_TOKENS['scene'] = '<scene>:\tscene name'
STD_TOKENS['camera'] = '<camera>:\trender camera'
STD_TOKENS['aov'] = '<aov>:\tAOV display name'
STD_TOKENS['aovdir'] = '''<aovdir>:\tAOV directory name (without '_variance' if denoised)'''
STD_TOKENS['ext'] = '<ext>:\timage file extension'
STD_TOKENS['layer'] = '<layer>:\trender layer name'
STD_TOKENS['shape'] = '<shape>:\tshort shape name'
STD_TOKENS['shapepath'] = '<shapepath>:\tlong shape name'
STD_TOKENS['frame'] = '<frame>:\tdecimal frame number'
STD_TOKENS['f'] = '<f>:\tframe number'
STD_TOKENS['f2'] = '<f2>:\tzero-padded frame number'
STD_TOKENS['f3'] = '<f3>:\tzero-padded frame number'
STD_TOKENS['f4'] = '<f4>:\tzero-padded frame number'
STD_TOKENS['jobid'] = '<jobid>:\tunique job identifier'
STD_TOKENS['date'] = '<date>:\tcurrent date'
STD_TOKENS['time'] = '<time>:\tcurrent time'
STD_TOKENS['version'] = '<version>:\tscene version number'
STD_TOKENS['take'] = '<take>:\tscene take number'
STD_TOKENS['assetlib'] = '<assetlib>:\tpath to the standard RenderManAssetLibrary'
STD_TOKENS['imagedir'] = '<imagedir>:\timages output path defined in rmanGlobals'
STD_TOKENS['integrator'] = '<integrator>:\tcurrent integrator'


# split the token into 3 groups:
#   1 - the main token
#   2 - the token formatting string
#   3 - an environment variable
#
# Examples:
#   '<shape.fogColor>'  ->  ('shape.fogColor', None, None)
#   '<shape.fogColor:%g %g %g>'  ->  ('shape.fogColor', ':%g %g %g', None)
#   '$RMANTREE/bin' ->  (None, None, '$RMANTREE')
#
PARSING_EXPR = re.compile(r'{([\w\:]*[\w\.]+)(\?[\w\d\._-]+)*'  # token
                          r'(:[^}]+)*}|'                        # formatter
                          r'\$\{?([A-Z0-9_]{3,})\}?')           # env var


class StringExpression(object):

    # @time_this
    def __init__(self, tokens=None):
        self.tokens = {}
        self.update_blend_tokens()  
        self.tokens['pwd'] = ''
        ts = datetime.datetime.fromtimestamp(time.time())
        self.tokens['jobid'] = ts.strftime('%y%m%d%H%M%S')
        self.tokens['date'] = ts.strftime('%y_%m_%d')
        self.tokens['time'] = ts.strftime('%H-%M-%S')
        self.tokens['layer'] = '' 
        self.tokens['renderlayer'] = self.tokens['layer']
        self.tokens['ext'] = 'exr'
        self.tokens['aov'] = '' 
        self.tokens['aovdir'] = 'beauty'
        self.tokens['version'] = '001'
        self.tokens['take'] = '01'  
        self.tokens['file'] = self.tokens['blend']
        self.tokens['ws'] = self.tokens['OUT']


        for k, v in self.tokens.items():
            # print '%s = %s' % (k, repr(v))
            # suppress any trailing slash or anti-slash for consistency.
            if v and v[-1] in ['/', os.sep]:
                self.tokens[k] = v[:-1]

        if tokens is not None:
            for k, v in tokens.items():
                tokens[k] = self.expand(v)
            self.tokens.update(tokens)

    def update_blend_tokens(self):
        unsaved = True if not bpy.data.filepath else False
        if unsaved:
            self.tokens['blend'] = 'UNTITLED'
        else:
            self.tokens['blend'] = os.path.splitext(os.path.split(bpy.data.filepath)[1])[0]     

        self.tokens['OUT'] = self.expand(prefs_utils.get_addon_prefs().env_vars.out)
        self.tokens['scene'] = bpy.context.scene.name 
        self.set_frame_context(bpy.context.scene.frame_current)

    # @time_this
    def set_frame_context(self, frame):
        """Set the scene frame for the next subst() call."""
        self.tokens['frame'] = str(frame)
        iframe = int(frame)
        self.tokens['f'] = str(iframe)
        self.tokens['f2'] = '{:0>2d}'.format(iframe)
        self.tokens['f3'] = '{:0>3d}'.format(iframe)
        self.tokens['f4'] = '{:0>4d}'.format(iframe)
        self.tokens['F'] = str(iframe)
        self.tokens['F2'] = '{:0>2d}'.format(iframe)
        self.tokens['F3'] = '{:0>3d}'.format(iframe)
        self.tokens['F4'] = '{:0>4d}'.format(iframe)        

    # @time_this
    def expand(self, expr, objTokens={}, asFilePath=False):
        """handle the '<token>' format"""

        # early exit: around 0.003ms
        if '{' not in expr and '$' not in expr:
            return expr

        toks = dict(self.tokens)
        toks.update(objTokens)
        # print toks
        pos = 0
        result = ''
        for m in re.finditer(PARSING_EXPR, expr):
            # print 'GROUPS: %s' % str(m.groups())
            if m.group(1):
                # Token case
                tok = m.group(1)
                tok_val = None
                # print '  |__ TOKEN: %02d-%02d: %s' % (m.start(), m.end(), tok)
                try:
                    tok_val = toks[tok]
                    # result += expr[pos:m.start()] + toks[tok]
                except KeyError:
                    try:
                        # forced lower-case version if first attempts failed.
                        tok_val = toks[tok.lower()]
                    except KeyError:
                        # the token REALLY doesn't exist...
                        try:
                            # if it contains 'shape.' it may be a getAttr for an
                            # attribute on the current shape.
                            tok = tok.replace('shape.', '%s.' % toks['shape'])
                        except KeyError:
                            pass
                        try:
                            # if it contains 'shapepath.' it may be a getAttr for an
                            # attribute on the current shape.
                            tok = tok.replace('shapepath.', '%s.' % toks['shapepath'])
                        except KeyError:
                            pass
                        try:
                            # could be a getAttr node.attr ?
                            tok_val = '' #mc.getAttr(tok)
                        except ValueError as err:
                            # the node or attribute desn't exist.
                            if m.group(2):
                                # a default value has been provided
                                tok_val = m.group(2)[1:]
                            else:
                                # the node or/and attribute doesn't exist, pass
                                # un-substituted: that's better for debugging.
                                rfb_log().debug('%s  (maya plug = %r)', err, tok)
                                tok_val = m.group(0)
                        except TypeError as err:
                            # invalid plug string, just append it. Tokens like
                            # <udim> will be substituted by the renderer.
                            tok_val = m.group(0)
                            rfb_log().debug('%s  (maya plug = %r)', err, tok)
                            # print '   un-processed token: %s' % m.group(0)
                        else:
                            pass 
                            # getAttr(tok) succeeded: store the result
                            """
                            if mc.getAttr(tok, mi=True) is None:
                                if mc.getAttr(tok, type=True) == 'float3':
                                    # maya returns [(x, x, x)] and we just want (x, x, x)
                                    tok_val = tok_val[0]
                            else:
                                rfb_log().warning('Array attribute lookups are '
                                                  'not supported ! (%s)', tok)
                                continue
                            """
                # optional formating
                if m.group(3):
                    if isinstance(tok_val, basestring) and tok_val:
                        try:
                            tok_val = eval(tok_val)
                        except (NameError, SyntaxError, TypeError) as err:
                            rfb_log().debug('Eval failed: %s  -> %r', err, tok_val)
                            result += expr[pos:m.start()] +  tok_val
                        else:
                            result += expr[pos:m.start()] +  m.group(3)[1:] % tok_val
                    else:
                        result += expr[pos:m.start()] +  m.group(3)[1:] % tok_val
                else:
                    result += '%s%s' % (expr[pos:m.start()], tok_val)
            else:
                # Environment variable case
                tok = m.group(4)
                # print '  |__ ENV VAR: %02d-%02d: %s' % (m.start(), m.end(), tok)
                try:
                    result += expr[pos: m.start()] + os.environ[tok]
                except KeyError:
                    result += expr[pos: m.start()] + m.group(0)

            pos = m.end()
        # append the end of the string. If no match (despite the presence of
        # a < or $), sets result to the original expression.
        result += expr[pos:]

        
        if asFilePath:
            # If this is meant to be a file path, substitute : with _
            # Can not have ':' after the drive descriptor on windows. Allow
            # for a leading space before the drive letter
            result = re.sub(r'((?<!^[A-Z])(?<!^[ ][A-Z]))\:', '_', result)
            result = result.replace(' ', '_')

            dirname = os.path.dirname(result)
            if not os.path.exists(dirname):
                os.makedirs(dirname, exist_ok=True)
    
        return result


def fixup_file_name(inputNm):
    result = inputNm
    # replace repeated underscores with one underscore
    # these come about if a var like <layer> is empty
    result = re.sub(r'_+', '_', result)
    # eg.  test_.0001.exr -> test.0001.exr
    result = re.sub(r'_\.', '.', result)
    # strip underscore if it's at end of string
    result = result.rstrip('_')
    return result