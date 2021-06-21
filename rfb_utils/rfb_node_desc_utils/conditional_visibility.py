"""Analyse conditional visibility arguments and build a string that can be
evaluated by python.

description

Example:
    build_condvis_expr(pdesc)

Attributes:
    COND_VIS_OPS (dict): map condvis keywords to python operators
"""

COND_VIS_OPS = {
    'equalTo': '==',
    'notEqualTo': '!=',
    'greaterThan': '>',
    'greaterThanOrEqualTo': '>=',
    'lessThan': '<',
    'lessThanOrEqualTo': '<=',
    'regex': '~=',
    'in': 'in'
}


def _safe_eval(strval):
    val = strval
    try:
        val = eval(strval)      # pylint: disable=eval-used
    except BaseException:
        val = strval
    else:
        if isinstance(val, type):
            # catch case where 'int' (or any other python type)
            # was evaled and we got a python type object.
            val = strval
    return val

def _is_alpha_string(s):
    hasAlpha = False
    for c in s:
        if (c.isalpha() or c.isspace()):
            hasAlpha = True
            break
    return hasAlpha    


def _condvis_expr(pdict, prefix, trigger_params, expr=''):
    """Recursively build a python expression based on node attributes.

    Args:
    - pdesc (NodeDescParam): parameter being processed
    - prefix (str): prefix being processed
    - trigger_params (set): set of parameter names on which the expression depends.

    Kwargs:
    - expr (str): The work-in-progress string. DO NOT SET on the initial call.

    Returns:
    - The python expression
    """
    fmt = '%s%%s' % prefix
    if fmt % 'Left' in pdict:
        opr = pdict[fmt % 'Op']
        left_side = pdict[fmt % 'Left']
        lexpr = _condvis_expr(pdict, left_side, trigger_params, expr=expr)
        right_side = pdict[fmt % 'Right']
        rexpr = _condvis_expr(pdict, right_side, trigger_params, expr=expr)
        expr += '%s %s %s' % (lexpr, opr, rexpr)
    else:
        attr = pdict[fmt % 'Path'].split('/')[-1]
        opr = COND_VIS_OPS[pdict[fmt % 'Op']]
        val = _safe_eval(pdict[fmt % 'Value'])

        if val == 'NoneType':
            expr = ('getattr(node, "%s") %s None' %
                    (attr, opr)) 
        elif opr == 'in':
            val = val.split(",")
            expr = ('str(getattr(node, "%s")) %s %s' %
                    (attr, opr,
                    str(val)))                      
        elif isinstance(val, int):
            # always cast to int
            # when dealing with EnumProperties, the values are always strings
            expr = ('int(getattr(node, "%s")) %s int(%s)' %
                    (attr, opr,
                        val)) 
                               
        elif isinstance(val, float):
            expr = ('float(getattr(node, "%s")) %s float(%s)' %
                    (attr, opr,
                        val))  

        elif isinstance(val, str):
            expr = ('getattr(node, "%s") %s "%s"' %
                    (attr, opr,
                        val))                                                             

        elif _is_alpha_string(val) or val.isalpha() or val == '' or val in VALID_TYPES:
            expr = ('getattr(node, "%s") %s "%s"' %
                    (attr, opr,
                        val))                                            
        else:
            expr = ('float(getattr(node, "%s")) %s float(%s)' %
                    (attr, opr,
                        val))


        if attr not in trigger_params:
            trigger_params.append(attr)
    return expr


def build_condvis_expr(pdict, trigger_params):
    if 'conditionalVisOp' in pdict:
        pdict['expr'] = _condvis_expr(pdict, 'conditionalVis', trigger_params)
    if 'conditionalLockOp' in pdict:
        pdict['lock_expr'] = 'not (%s)' % _condvis_expr(pdict, 'conditionalLock', trigger_params)


# TESTS -----------------------------------------------------------------------

def _test():
    test1 = {
        'conditionalVisOp': "and",
        'conditionalVisLeft': "conditionalVis1",
        'conditionalVisRight': "conditionalVis2",
        'conditionalVis2Op': "and",
        'conditionalVis2Left': "conditionalVis3",
        'conditionalVis2Right': "conditionalVis4",
        'conditionalVis1Path': "../type",
        'conditionalVis1Op': "notEqualTo",
        'conditionalVis1Value': "int",
        'conditionalVis3Path': "../type",
        'conditionalVis3Op': "notEqualTo",
        'conditionalVis3Value': "float",
        'conditionalVis4Path': "../type",
        'conditionalVis4Op': "notEqualTo",
        'conditionalVis4Value': "color"
    }
    test2 = {
        'conditionalVisOp': "and",
        'conditionalVisLeft': "myLeft",
        'conditionalVisRight': "myRight",
        'myLeftPath': "../enableEdgeFalloff",
        'myLeftOp': "greaterThan",
        'myLeftValue': "0",
        'myRightOp': "equalTo",
        'myRightPath': "../falloffType",
        'myRightValue': "0",
        'conditionalLockOp': 'equalTo',
        'conditionalLockPath': './fromEnv',
        'conditionalLockValue': '-1',
    }

    trigger_params = []
    build_condvis_expr(test1, trigger_params)
    print('BLENDER: %r' % test1['expr'])
    print('      |_ %s' % trigger_params)

    trigger_params = []
    build_condvis_expr(test2, trigger_params)
    print('BLENDER: %r' % test2['expr'])
    print('BLENDER: %r' % test2['lock_expr'])
    print('      |_ %s' % trigger_params)


# _test()
