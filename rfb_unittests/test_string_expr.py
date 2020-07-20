import unittest
import bpy
from ..rman_utils import string_utils

class StringExprTest(unittest.TestCase):

    @classmethod
    def add_tests(self, suite):
        suite.addTest(StringExprTest('test_get_var'))
        suite.addTest(StringExprTest('test_set_var'))
        suite.addTest(StringExprTest('test_expand_string'))

    # test getvar 
    def test_get_var(self):
        self.assertEqual(string_utils.get_var('scene'), bpy.context.scene.name)

    # test set_var
    def test_set_var(self):
        string_utils.set_var('OUT', '/var/tmp')
        self.assertEqual(string_utils.get_var('OUT'), '/var/tmp')

    # test string expansion
    def test_expand_string(self):
        s = '{OUT}/{unittest}/{scene}.{f4}.{ext}'
        compare = f'/var/tmp/StringExprTest/{bpy.context.scene.name}.0001.exr'
        string_utils.set_var('OUT', '/var/tmp')
        string_utils.set_var('unittest', 'StringExprTest')
        expanded_str = string_utils.expand_string(s, display='openexr', frame=1)
        self.assertEqual(expanded_str, compare)