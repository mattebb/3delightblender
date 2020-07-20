import unittest
from RenderManForBlender.rfb_unittests.test_string_expr import StringExprTest

classes = [
    StringExprTest
]

def suite():
    suite = unittest.TestSuite()

    for cls in classes:
        cls.add_tests(suite)

    return suite

def run_rfb_unittests():
    runner = unittest.TextTestRunner()
    runner.run(suite())

if __name__ == '__main__':
    run_rfb_unittests()