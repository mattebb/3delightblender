import mathutils
from mathutils import Matrix, Vector
from .string_expr import StringExpression
from bpy.app.handlers import persistent
import bpy
import os
import re

PAD_FMT = ['%d', '%01d', '%02d', '%03d', '%04d']
__SCENE_STRING_CONVERTER__ = None
EXT_MAP = {'it': 'it', 'openexr': 'exr', 'tiff': 'tif', 'blender': 'blender'}

class SceneStringConverter(object):
    """Class maintaining an up-to-date StringExpression object.
    """

    def __init__(self):
        self.expr = None

    def expand(self, string, display=None, frame=None, token_dict = dict(), asFilePath=False):
        """Expand the <tokens> in the string.

        Args:
        - string (str): The string to be expanded.

        Kwargs:
        - display (str): The display being considered. This is necessary if your
        expression contains <aov> or <ext>
        - frame (int): An optional frame number to expand {F}, {F4}, etc.

        Returns:
        - The expanded string
        """
        if not self.expr:
            self.update()
            
        if token_dict:
            self.update_tokens(token_dict)

        if frame is not None:
            self.expr.set_frame_context(frame)

        if display:
            self.set_display(display)

        return self.expr.expand(string, asFilePath=asFilePath)

    def update(self):
        """Create a new StringExpression and configures it for the current state
        of the scene."""
        tk = None
        self.expr = StringExpression(tokens=tk)

    def set_display(self, display):
        """Sets the <aov> and <ext> tokens based on the display.

        Args:
        - display (str): the name of the display node.
        """

        if display in EXT_MAP.keys():
            self.expr.tokens['ext'] = EXT_MAP[display]

    def update_tokens(self, token_dict):
        for k,v in token_dict.items():
            self.set_token(k,v)


    def set_token(self, key, value):
        """Sets a token's value in the StringExpression object.

        Args:
        - key (str): the token's name
        - value (str): the token's value
        """
        if not self.expr:
            self.update()
        self.expr.tokens[key] = value

    def get_token(self, key):
        """Gets a token's value in the StringExpression object.

        Args:
        - key (str): the token's name
        """
        if not self.expr:
            self.update()
        value = ''
        if key in self.expr.tokens:
            value = self.expr.tokens[key]
        return value

def expand_string(string, display=None, glob_sequence=False, frame=None, token_dict=dict(), asFilePath=False):
    """expand a string containing tokens.

    Args:
    - string (str): a string that may or may not contain tokens.

    Kwargs:
    - display (str): the name of a display driver to update <ext> tokens.
    - frame (str): the frame to use for expanding
    - token_dict (dict): dictionary of token/vals that also need to be set.
    - asFilePath (bool): treat the input string as a path. Will create directories if they don't exist

    Returns:
    - The expanded string.
    """
    global __SCENE_STRING_CONVERTER__

    def _resetStringConverter():
        try:
            __SCENE_STRING_CONVERTER__.expr = None
        except:
            pass

    if not string or (not '{' in string and not '$' in string):
        return string

    if __SCENE_STRING_CONVERTER__ is None:
        __SCENE_STRING_CONVERTER__ = SceneStringConverter()

    if glob_sequence:
        string = re.sub(r'{(f\d*)}', '*', string)

    return __SCENE_STRING_CONVERTER__.expand(
        string, display=display, frame=frame, token_dict=token_dict, asFilePath=asFilePath)

def converter_validity_check():
    global __SCENE_STRING_CONVERTER__
    if __SCENE_STRING_CONVERTER__ is None:
        __SCENE_STRING_CONVERTER__ = SceneStringConverter()

def set_var(nm, val):
    # This is needed so that we can update the scripting variable state
    # before evaluating a string.
    converter_validity_check()
    __SCENE_STRING_CONVERTER__.set_token(nm, val)

def get_var(nm):
    converter_validity_check()
    return __SCENE_STRING_CONVERTER__.get_token(nm)

@persistent
def update_blender_tokens_cb(bl_scene):
    global __SCENE_STRING_CONVERTER__
    converter_validity_check()
    __SCENE_STRING_CONVERTER__.update()


def _format_time_(seconds):
    hours = seconds // (60 * 60)
    seconds %= (60 * 60)
    minutes = seconds // 60
    seconds %= 60
    return "%02i:%02i:%02i" % (hours, minutes, seconds)

def convert_val(v, type_hint=None):

    # float, int
    if type_hint == 'color':
        return list(v)[:3]

    if type(v) in (mathutils.Vector, mathutils.Color) or\
            v.__class__.__name__ == 'bpy_prop_array'\
            or v.__class__.__name__ == 'Euler':
        # BBM modified from if to elif
        return list(v)

    # matrix
    elif type(v) == mathutils.Matrix:
        return [v[0][0], v[1][0], v[2][0], v[3][0],
                v[0][1], v[1][1], v[2][1], v[3][1],
                v[0][2], v[1][2], v[2][2], v[3][2],
                v[0][3], v[1][3], v[2][3], v[3][3]]
    elif type_hint == 'int':
        return int(v)
    elif type_hint == 'float':
        return float(v)
    else:
        return v

def getattr_recursive(ptr, attrstring):
    for attr in attrstring.split("."):
        ptr = getattr(ptr, attr)

    return ptr        