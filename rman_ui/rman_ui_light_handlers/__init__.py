import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from ...rman_utils import transform_utils
from .barn_light_filter_draw_helper import BarnLightFilterDrawHelper
from mathutils import Vector, Matrix
import mathutils
import math

_DRAW_HANDLER_ = None
_BARN_LIGHT_DRAW_HELPER_ = None
_PI0_5_ = 1.570796327

s_rmanLightLogo = dict()
s_rmanLightLogo['box'] = [
    (-0.5,0.5,0.0),
    (-0.5,-0.5,0.0),
    (0.5,-0.5,0.0),
    (0.5,0.5, 0.0)
]

s_rmanLightLogo['point'] = [
    (0.1739199623,0.2189011082,0.0),
    (0.2370826019,0.2241208805,0.0),
    (0.2889232079,0.180194478,0.0),
    (0.2945193948,0.1124769769,0.0),
    (0.2505929922,0.06063637093,0.0),
    (0.1828754911,0.05504018402,0.0),
    (0.1310348852,0.09896658655,0.0),
    (0.1254386983,0.1666840877,0.0)
]

s_rmanLightLogo['bouncing_r'] = [    
    (0.10014534,0.163975795,0.0),
    (0.02377454715,0.2079409584,0.0),
    (-0.0409057802,0.162414633,0.0),
    (-0.09261710117,-0.03967857045,0.0),
    (-0.1033546419,-0.3941421577,0.0),
    (-0.1714205988,-0.3935548906,0.0),
    (-0.1743695606,-0.2185861014,0.0),
    (-0.1934162612,-0.001801638764,0.0),
    (-0.2387964527,0.228222199,0.0),
    (-0.2945193948,0.388358659,0.0),
    (-0.2800665961,0.3941421577,0.0),
    (-0.1944135703,0.2262313617,0.0),
    (-0.1480375743,0.08022936015,0.0),
    (-0.09632135301,0.2812304287,0.0),
    (0.03260773708,0.3415349284,0.0),
    (0.1794274591,0.2497892755,0.0),
    (0.10014534,0.163975795,0.0)
]

s_rmanLightLogo['arrow'] = [
    (0.03316599252,-6.536167e-18,0.0294362),
    (0.03316599252,-7.856030e-17,0.3538041),
    (0.06810822842,-7.856030e-17,0.3538041),
    (0,-1.11022302e-16,0.5),
    (-0.0681082284,-7.85603e-17,0.353804),
    (-0.0331659925,-7.85603e-17,0.353804),
    (-0.0331659925,-6.53616e-18,0.029436)
]

s_rmanLightLogo['R_outside'] = [
    [0.265400, -0.291600, 0.000000],
    [0.065400, -0.291600, 0.000000],
    [0.065400, -0.125000, 0.000000],
    [0.025800, -0.125000, 0.000000],
    [0.024100, -0.125000, 0.000000],
    [-0.084800, -0.291600, 0.000000],
    [-0.305400, -0.291600, 0.000000],
    [-0.170600, -0.093300, 0.000000],
    [-0.217900, -0.062800, 0.000000],
    [-0.254000, -0.023300, 0.000000],
    [-0.276900, 0.025800, 0.000000],
    [-0.284500, 0.085000, 0.000000],
    [-0.284500, 0.086700, 0.000000],
    [-0.281200, 0.128700, 0.000000],
    [-0.271200, 0.164900, 0.000000],
    [-0.254500, 0.196600, 0.000000],
    [-0.231000, 0.224900, 0.000000],
    [-0.195200, 0.252600, 0.000000],
    [-0.149600, 0.273700, 0.000000],
    [-0.092000, 0.287100, 0.000000],
    [-0.020300, 0.291600, 0.000000],
    [0.265400, 0.291600, 0.000000],
    [0.265400, -0.291600, 0.000000]

]

s_rmanLightLogo['R_inside'] = [
    [0.065400, 0.019100, 0.000000],
    [0.065400, 0.133300, 0.000000],
    [-0.014600, 0.133300, 0.000000],
    [-0.043500, 0.129800, 0.000000],
    [-0.065700, 0.119500, 0.000000],
    [-0.079800, 0.102100, 0.000000],
    [-0.084500, 0.077400, 0.000000],
    [-0.084500, 0.075700, 0.000000],
    [-0.079800, 0.052000, 0.000000],
    [-0.065700, 0.034100, 0.000000],
    [-0.043300, 0.022800, 0.000000],
    [-0.013800, 0.019100, 0.000000],
    [0.065400, 0.019100, 0.000000]
]

s_envday = dict()
s_envday['west_rr_shape'] = [  
    [-1.9994, 0, -0.1652], [-2.0337, 0, 0.0939],
    [-2.0376, 0, 0.1154], [-2.0458, 0, 0.1159],
    [-2.046, 0, 0.0952], [-2.0688, 0, -0.2033],
    [-2.1958, 0, -0.203], [-2.1458, 0, 0.1705],
    [-2.1408, 0, 0.1874], [-2.1281, 0, 0.2],
    [-2.1116, 0, 0.2059], [-2.0941, 0, 0.2078],
    [-1.9891, 0, 0.2073], [-1.9719, 0, 0.2039],
    [-1.9573, 0, 0.1938], [-1.9483, 0, 0.1786],
    [-1.9447, 0, 0.1613], [-1.9146, 0, -0.1149],
    [-1.9049, 0, -0.1127], [-1.8721, 0, 0.1759],
    [-1.8652, 0, 0.1921], [-1.8507, 0, 0.2021],
    [-1.8339, 0, 0.2072], [-1.7112, 0, 0.207],
    [-1.6943, 0, 0.2024], [-1.6816, 0, 0.1901],
    [-1.6744, 0, 0.1742], [-1.6234, 0, -0.2037],
    [-1.751, 0, -0.2035], [-1.7748, 0, 0.1153],
    [-1.7812, 0, 0.1166], [-1.7861, 0, 0.1043],
    [-1.8188, 0, -0.1565], [-1.8218, 0, -0.1738],
    [-1.83, 0, -0.1894], [-1.8447, 0, -0.1995],
    [-1.8618, 0, -0.2034], [-1.9493, 0, -0.2037],
    [-1.967, 0, -0.2024], [-1.9824, 0, -0.1956],
    [-1.9943, 0, -0.1825]
]
s_envday['east_rr_shape'] = [              
    [1.8037, 0, 0.1094], [1.9542, 0, 0.1094],
    [1.9604, 0, 0.2004], [1.9175, 0, 0.2043],
    [1.8448, 0, 0.2069], [1.7493, 0, 0.2082],
    [1.7375, 0, 0.2079], [1.7258, 0, 0.2066],
    [1.7144, 0, 0.204], [1.7033, 0, 0.2],
    [1.6928, 0, 0.1947], [1.6831, 0, 0.188],
    [1.6743, 0, 0.1802], [1.6669, 0, 0.171],
    [1.6607, 0, 0.1611], [1.6559, 0, 0.1503],
    [1.6527, 0, 0.139], [1.6508, 0, 0.1274],
    [1.6502, 0, 0.1156], [1.6502, 0, -0.1122],
    [1.6505, 0, -0.1239], [1.6521, 0, -0.1356],
    [1.6551, 0, -0.147], [1.6597, 0, -0.1578],
    [1.6657, 0, -0.168], [1.6731, 0, -0.1771],
    [1.6816, 0, -0.1852], [1.6911, 0, -0.1922],
    [1.7014, 0, -0.1978], [1.7124, 0, -0.2021],
    [1.7238, 0, -0.205], [1.7354, 0, -0.2066],
    [1.7472, 0, -0.207], [1.8528, 0, -0.2058],
    [1.9177, 0, -0.2028], [1.9602, 0, -0.1993],
    [1.9541, 0, -0.1082], [1.8006, 0, -0.1084],
    [1.7892, 0, -0.1054], [1.7809, 0, -0.0968],
    [1.7789, 0, -0.0851], [1.7793, 0, -0.0471],
    [1.9329, 0, -0.0469], [1.933, 0, 0.0388],
    [1.7793, 0, 0.0384], [1.779, 0, 0.0895],
    [1.7825, 0, 0.1002], [1.792, 0, 0.1083]
]
s_envday['south_rr_shape'] = [
    [0.1585, 0, 1.654],   [0.1251, 0, 1.6444],
    [0.0918, 0, 1.6383],  [0.053, 0, 1.6345],
    [0.0091, 0, 1.6331],  [-0.0346, 0, 1.6347],
    [-0.0712, 0, 1.6397], [-0.1002, 0, 1.6475],
    [-0.1221, 0, 1.6587], [-0.142, 0, 1.6791],
    [-0.1537, 0, 1.7034], [-0.1579, 0, 1.7244],
    [-0.1599, 0, 1.7458], [-0.1593, 0, 1.7672],
    [-0.1566, 0, 1.7884], [-0.1499, 0, 1.8088],
    [-0.1392, 0, 1.8273], [-0.1249, 0, 1.8433],
    [-0.1079, 0, 1.8563], [-0.0894, 0, 1.8675],
    [-0.0707, 0, 1.8765], [-0.0139, 0, 1.9013],
    [0.0258, 0, 1.9185],  [0.041, 0, 1.9287],
    [0.0411, 0, 1.939],   [0.0366, 0, 1.9485],
    [0.0253, 0, 1.9525],  [-0.1485, 0, 1.95],
    [-0.1566, 0, 2.0398], [-0.1297, 0, 2.0462],
    [-0.0876, 0, 2.0538], [-0.0451, 0, 2.0585],
    [-0.0024, 0, 2.0603], [0.0403, 0, 2.0591],
    [0.0827, 0, 2.0534],  [0.1231, 0, 2.0397],
    [0.1537, 0, 2.0102],  [0.168, 0, 1.97],
    [0.1706, 0, 1.9273],  [0.1631, 0, 1.8852],
    [0.1404, 0, 1.8491],  [0.106, 0, 1.8236],
    [0.0875, 0, 1.8137],  [-0.0136, 0, 1.7711],
    [-0.0244, 0, 1.7643], [-0.0309, 0, 1.7558],
    [-0.031, 0, 1.7462],  [-0.0261, 0, 1.7393],
    [-0.0124, 0, 1.7353], [0.1505, 0, 1.7366]
]
s_envday['north_rr_shape'] = [ 
    [-0.144, 0, -2.034],   [-0.1584, 0, -2.0323],
    [-0.1719, 0, -2.0256], [-0.1804, 0, -2.0136],
    [-0.1848, 0, -1.9996], [-0.185, 0, -1.9849],
    [-0.185, 0, -1.6235],  [-0.0661, 0, -1.6236],
    [-0.0663, 0, -1.8158], [-0.0672, 0, -1.8303],
    [-0.0702, 0, -1.8594], [-0.0721, 0, -1.8739],
    [-0.0654, 0, -1.8569], [-0.048, 0, -1.8169],
    [-0.0415, 0, -1.8038], [0.0554, 0, -1.65],
    [0.0641, 0, -1.638],   [0.0747, 0, -1.6286],
    [0.0869, 0, -1.6244],  [0.0978, 0, -1.6235],
    [0.1541, 0, -1.6238],  [0.1677, 0, -1.6263],
    [0.1811, 0, -1.6341],  [0.1896, 0, -1.6477],
    [0.1926, 0, -1.6633],  [0.1927, 0, -1.6662],
    [0.1927, 0, -2.0339],  [0.0743, 0, -2.0341],
    [0.0743, 0, -1.8646],  [0.0759, 0, -1.8354],
    [0.0786, 0, -1.8062],  [0.0803, 0, -1.7917],
    [0.0735, 0, -1.8051],  [0.0605, 0, -1.8312],
    [0.0473, 0, -1.8573],  [0.0422, 0, -1.8659],
    [-0.0534, 0, -2.0154], [-0.0632, 0, -2.0261],
    [-0.0741, 0, -2.0322], [-0.0909, 0, -2.034]
]
s_envday['inner_circle_rr_shape'] = [ 
    [0, 0, -1],            [-0.1961, 0, -0.9819],
    [-0.3822, 0, -0.9202], [-0.5587, 0, -0.8291],
    [-0.7071, 0, -0.707],  [-0.8308, 0, -0.5588],
    [-0.9228, 0, -0.3822], [-0.9811, 0, -0.1961],
    [-1.0001, 0, 0],       [-0.9811, 0, 0.1961],
    [-0.9228, 0, 0.3822],  [-0.8361, 0, 0.5486],
    [-0.7071, 0, 0.7071],  [-0.5587, 0, 0.8311],
    [-0.3822, 0, 0.9228],  [-0.1961, 0, 0.9811],
    [0, 0, 1.0001],        [0.1961, 0, 0.981],
    [0.3822, 0, 0.9228],   [0.5587, 0, 0.8309],
    [0.7071, 0, 0.7071],   [0.8282, 0, 0.5587],
    [0.9228, 0, 0.3822],   [0.9811, 0, 0.1961],
    [1.0001, 0, 0],        [0.9811, 0, -0.1961],
    [0.9228, 0, -0.3822],  [0.831, 0, -0.5587],
    [0.7071, 0, -0.7071],  [0.5587, 0, -0.8308],
    [0.3822, 0, -0.9228],  [0.1961, 0, -0.981]
]

s_envday['outer_circle_rr_shape'] = [ 
    [0, 0, -1],            [-0.1961, 0, -0.9815],
    [-0.3822, 0, -0.9202], [-0.5587, 0, -0.8288],
    [-0.7071, 0, -0.707],  [-0.8282, 0, -0.5588],
    [-0.9228, 0, -0.3822], [-0.981, 0, -0.1961],
    [-1.0001, 0, 0],       [-0.981, 0, 0.1961],
    [-0.9228, 0, 0.3822],  [-0.8308, 0, 0.5538],
    [-0.7071, 0, 0.7071],  [-0.5587, 0, 0.8302],
    [-0.3822, 0, 0.9228],  [-0.1961, 0, 0.9811],
    [0, 0, 1.0001],        [0.1961, 0, 0.981],
    [0.3822, 0, 0.9228],   [0.5587, 0, 0.8279],
    [0.7071, 0, 0.7071],   [0.8308, 0, 0.5587],
    [0.9228, 0, 0.3822],   [0.981, 0, 0.1961],
    [1.0001, 0, 0],        [0.981, 0, -0.1961],
    [0.9228, 0, -0.3822],  [0.8308, 0, -0.5587],
    [0.7071, 0, -0.7071],  [0.5587, 0, -0.8308],
    [0.3822, 0, -0.9228],  [0.1961, 0, -0.9784]
]
s_envday['compass_shape'] = [             
    [0, 0, -0.9746], [-0.2163, 0, -0.0012],
    [0, 0, 0.9721], [0.2162, 0, -0.0012],
    [0, 0, -0.9746]
]

s_envday['east_arrow_shape'] = [ 
    [1.2978, 0, -0.2175], [1.2978, 0, 0.215],
    [1.5141, 0, -0.0012], [1.2978, 0, -0.2175]
]
s_envday['south_arrow_shape'] = [ 
    [-0.2163, 0, 1.2965], [0.2162, 0, 1.2965],
    [0, 0, 1.5128], [-0.2163, 0, 1.2965]
]
s_envday['west_arrow_shape'] = [ 
    [-1.2979, 0, -0.2175], [-1.2979, 0, 0.215],
    [-1.5142, 0, -0.0012], [-1.2979, 0, -0.2175]
]
s_envday['north_arrow_shape'] = [ 
    [-0.2163, 0, -1.2991], [0.2162, 0, -1.2991],
    [0, 0, -1.5154],       [-0.2163, 0, -1.2991]
]

s_diskLight = [
    [0.490300, 0.097500, 0.000000],
    [0.461900, 0.191300, 0.000000],
    [0.415700, 0.277700, 0.000000],
    [0.353500, 0.353500, 0.000000],
    [0.277700, 0.415700, 0.000000],
    [0.191300, 0.461900, 0.000000],
    [0.097500, 0.490300, 0.000000],
    [0.000000, 0.499900, 0.000000],
    [-0.097500, 0.490300, 0.000000],
    [-0.191300, 0.461900, 0.000000],
    [-0.277700, 0.415700, 0.000000],
    [-0.353500, 0.353500, 0.000000],
    [-0.415700, 0.277700, 0.000000],
    [-0.461900, 0.191300, 0.000000],
    [-0.490300, 0.097500, 0.000000],
    [-0.499900, 0.000000, 0.000000],
    [-0.490300, -0.097500, 0.000000],
    [-0.461900, -0.191300, 0.000000],
    [-0.415700, -0.277700, 0.000000],
    [-0.353500, -0.353500, 0.000000],
    [-0.277700, -0.415700, 0.000000],
    [-0.191300, -0.461900, 0.000000],
    [-0.097500, -0.490300, 0.000000],
    [0.000000, -0.499900, 0.000000],
    [0.097500, -0.490300, 0.000000],
    [0.191300, -0.461900, 0.000000],
    [0.277700, -0.415700, 0.000000],
    [0.353500, -0.353500, 0.000000],
    [0.415700, -0.277700, 0.000000],
    [0.461900, -0.191300, 0.000000],
    [0.490300, -0.097500, 0.000000],
    [0.500000, 0.000000, 0.000000],
    [0.490300, 0.097500, 0.000000]
]

s_distantLight = dict()
s_distantLight['arrow1'] =  [
    (0.03316599252,-6.536167e-18,0.0294362),
    (0.03316599252,-7.856030e-17,0.5),
    (0.06810822842,-7.856030e-17,0.5),
    (0,-1.11022302e-16, 1.0),
    (-0.0681082284,-7.85603e-17,0.5),
    (-0.0331659925,-7.85603e-17,0.5),
    (-0.0331659925,-6.53616e-18,0.029436)
]

s_distantLight['arrow2'] =  [
    (0.03316599252,-0.5,0.0294362),
    (0.03316599252,-0.5,0.5),
    (0.06810822842,-0.5,0.5),
    (0,-0.5, 1.0),
    (-0.0681082284,-0.5,0.5),
    (-0.0331659925,-0.5,0.5),
    (-0.0331659925,-0.5,0.029436)
]

s_distantLight['arrow3'] =  [
    (0.03316599252,0.5,0.0294362),
    (0.03316599252,0.5,0.5),
    (0.06810822842,0.5,0.5),
    (0,0.5, 1.0),
    (-0.0681082284,0.5,0.5),
    (-0.0331659925,0.5,0.5),
    (-0.0331659925,0.5,0.029436)
]

s_portalRays = [
    (-1, 0,  0),
    (-2, 0,  0),
    (-1, 0,  0),
    (-1, 0, -1),    
    (-2, 0, -2),
    (-1, 0, -1),
    ( 0, 0, -1),
    ( 0, 0, -2),    
    ( 0, 0, -1),
    ( 1, 0, -1),
    ( 2, 0, -2),
    ( 1, 0, -1),    
    ( 1, 0,  0),
    ( 2, 0,  0),
    ( 1, 0,  0),
    ( 1, 0,  1),    
    ( 2, 0,  2),
    ( 1, 0,  1),
    ( 0, 0,  1),
    ( 0, 0,  2),    
    ( 0, 0,  1),
    (-1, 0,  1),
    (-2, 0,  2),
    (-1, 0,  1),    
    (-1, 0,  0)
]

s_cylinderLight = dict()
s_cylinderLight['vtx'] = [
    [-0.5, -0.4045, -0.2938],
    [-0.5, -0.1545, -0.4755],
    [-0.5, 0.1545, -0.4755],
    [-0.5, 0.4045, -0.2938],
    [-0.5, 0.5, 0],
    [-0.5, 0.4045, 0.2938],
    [-0.5, 0.1545, 0.4755],
    [-0.5, -0.1545, 0.4755],
    [-0.5, -0.4045, 0.2938],
    [-0.5, -0.5, 0],
    [-0.5, -0.4045, -0.2938],

    [0.5, -0.4045, -0.2938],
    [0.5, -0.1545, -0.4755],
    [0.5, 0.1545, -0.4755],
    [0.5, 0.4045, -0.2938],
    [0.5, 0.5, 0],
    [0.5, 0.4045, 0.2938],
    [0.5, 0.1545, 0.4755],
    [0.5, -0.1545, 0.4755],
    [0.5, -0.4045, 0.2938],
    [0.5, -0.5, 0],
    [0.5, -0.4045, -0.2938]
]

s_cylinderLight['indices'] = [
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (4, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (8, 9),
    (9, 10),
    (11, 12),
    (12, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (16, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (20, 21),
    (0, 11),
    (2, 13),
    (4, 15),
    (6, 17),
    (8, 19)
]


_SHADER_ = None
if not bpy.app.background:
    _SHADER_ = gpu.shader.from_builtin('3D_UNIFORM_COLOR')

def _get_indices(l):
    indices = []
    for i in range(0, len(l)):
        if i == len(l)-1:
            indices.append((i, 0))
        else:
            indices.append((i, i+1)) 

    return indices   

def _get_sun_direction(ob):
    light = ob.data
    rm = light.renderman.get_light_node()

    m = Matrix.Identity(4)     
    m = m @ Matrix.Rotation(math.radians(90.0), 4, 'X')

    month = float(rm.month)
    day = float(rm.day)
    year = float(rm.year)
    hour = float(rm.hour)
    zone = rm.zone
    latitude = rm.latitude
    longitude = rm.longitude

    sunDirection = Vector([rm.sunDirection[0], rm.sunDirection[1], rm.sunDirection[2]])
    
    if month == 0.0:
        return sunDirection

    if month == 1.0:
        dayNumber = day
    elif month == 2.0:
        dayNumber = day + 31.0
    else:
        year_mod = 0.0
        if math.fmod(year, 4.0) != 0.0:
            year_mod = 0.0
        elif math.fmod(year, 100.0) != 0.0:
            year_mod = 1.0
        elif math.fmod(year, 400.0) != 0.0:
            year_mod = 0.0
        else:
            year_mod = 1.0

        dayNumber = math.floor(30.6 * month - 91.4) + day + 59.0 + year_mod

    dayAngle = 2.0 * math.pi * float(dayNumber - 81.0 + (hour - zone) / 24.0) / 365.0
    timeCorrection = 4.0 * (longitude - 15.0 * zone) + 9.87 * math.sin(2.0 * dayAngle) - 7.53 * math.cos(1.0 * dayAngle) - 1.50 * math.sin(1.0 * dayAngle)
    hourAngle = math.radians(15.0) * (hour + timeCorrection / 60.0 - 12.0)
    declination = math.asin(math.sin(math.radians(23.45)) * math.sin(dayAngle))
    elevation = math.asin(math.sin(declination) * math.sin(math.radians(latitude)) + math.cos(declination) * math.cos(math.radians(latitude)) * math.cos(hourAngle))
    azimuth = math.acos((math.sin(declination) * math.cos(math.radians(latitude)) - math.cos(declination) * math.sin(math.radians(latitude)) * math.cos(hourAngle)) / math.cos(elevation))
    if hourAngle > 0.0:
        azimuth = 2.0 * math.pi - azimuth
    sunDirection[0] = math.cos(elevation) * math.sin(azimuth)
    sunDirection[1] = max(math.sin(elevation), 0)
    sunDirection[2] = math.cos(elevation) * math.cos(azimuth)
    
    return m @ sunDirection

def make_sphere(m):
    lats = 12
    longs = 20
    radius = 0.5
    v = []
    
    i = 0
    j = 0
    for j in range(0, longs+1):
        lng = 2 * math.pi * float (j / longs)
        x = math.cos(lng)
        y = math.sin(lng)
            
        for i in range(0, lats+1):
            lat0 = math.pi * (-0.5 + float(i/ lats))
            z0  = math.sin(lat0) * radius
            zr0 = math.cos(lat0) * radius
        
            v.append( m @ Vector((x*zr0, y*zr0, z0)))

        for i in range(0, lats+1):
            lat0 = math.pi * (-0.5 + float(i / lats))
            z0  = math.sin(lat0) * radius
            zr0 =  math.cos(lat0) * radius
         
            v.append( m @ Vector((-x*zr0, -y*zr0, z0)))

    for i in range(0, lats+1):
        lat0 = math.pi * (-0.5 + float(i / lats))
        z0  = math.sin(lat0) * radius
        zr0 = math.cos(lat0) * radius
        
        for j in range(0, longs+1):
            lng = 2 * math.pi * (float(j / longs))
            x = math.cos(lng)
            y = math.sin(lng)
            
            v.append( m @ Vector((x*zr0, y*zr0, z0)))

    return v

def draw_rect_light(ob):
    _SHADER_.bind()

    if ob in bpy.context.selected_objects:
        _SHADER_.uniform_float("color", (1,1,1,1))

    m = Matrix(ob.matrix_world)        
    m = m @ Matrix.Rotation(math.radians(180.0), 4, 'Y')
    m = m @ Matrix.Rotation(math.radians(90.0), 4, 'Z')

    box = []
    for pt in s_rmanLightLogo['box']:
        box.append( m @ Vector(pt))

    box_indices = _get_indices(s_rmanLightLogo['box'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": box}, indices=box_indices)    
    batch.draw(_SHADER_)

    arrow = []
    for pt in s_rmanLightLogo['arrow']:
        arrow.append( m @ Vector(pt))  

    arrow_indices = _get_indices(s_rmanLightLogo['arrow'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": arrow}, indices=arrow_indices)    
    batch.draw(_SHADER_)

    R_outside = []
    for pt in s_rmanLightLogo['R_outside']:
        R_outside.append( m @ Vector(pt))

    R_outside_indices = _get_indices(s_rmanLightLogo['R_outside'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": R_outside}, indices=R_outside_indices)    
    batch.draw(_SHADER_)
  
    R_inside = []
    for pt in s_rmanLightLogo['R_inside']:
        R_inside.append( m @ Vector(pt))

    R_inside_indices = _get_indices(s_rmanLightLogo['R_inside'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": R_inside}, indices=R_inside_indices)    
    batch.draw(_SHADER_)    

def draw_sphere_light(ob):
    
    _SHADER_.bind()

    if ob in bpy.context.selected_objects:
        _SHADER_.uniform_float("color", (1,1,1,1))

    m = Matrix(ob.matrix_world)        
    m = m @ Matrix.Rotation(math.radians(180.0), 4, 'Y')
    m = m @ Matrix.Rotation(math.radians(90.0), 4, 'Z')

    R_outside = []
    for pt in s_rmanLightLogo['R_outside']:
        R_outside.append( m @ Vector(pt))

    R_outside_indices = _get_indices(s_rmanLightLogo['R_outside'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": R_outside}, indices=R_outside_indices)    
    batch.draw(_SHADER_)
  
    R_inside = []
    for pt in s_rmanLightLogo['R_inside']:
        R_inside.append( m @ Vector(pt))

    R_inside_indices = _get_indices(s_rmanLightLogo['R_inside'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": R_inside}, indices=R_inside_indices)    
    batch.draw(_SHADER_)    

    sphere = make_sphere(m)
    sphere_indices = []
    for i in range(0, len(sphere)):
        if i == len(sphere)-1:
            sphere_indices.append((i, 0))
        else:
            sphere_indices.append((i, i+1))     

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": sphere}, indices=sphere_indices)    
    batch.draw(_SHADER_)    

def draw_envday_light(ob): 

    _SHADER_.bind()

    if ob in bpy.context.selected_objects:
        _SHADER_.uniform_float("color", (1,1,1,1))

    loc, rot, sca = Matrix(ob.matrix_world).decompose()
    axis,angle = rot.to_axis_angle()
    scale = max(sca) # take the max axis
    m = Matrix.Rotation(angle, 4, axis)
    m = m @ Matrix.Scale(scale, 4)
    m = m @ Matrix.Translation(loc)
    ob_matrix = m
    
    m = Matrix(ob_matrix)
    m = m @ Matrix.Rotation(math.radians(90.0), 4, 'X')

    west_rr_shape = []
    for pt in s_envday['west_rr_shape']:
        west_rr_shape.append( m @ Vector(pt))

    west_rr_indices = _get_indices(s_envday['west_rr_shape'])

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": west_rr_shape}, indices=west_rr_indices)    
    batch.draw(_SHADER_)

    east_rr_shape = []
    for pt in s_envday['east_rr_shape']:
        east_rr_shape.append( m @ Vector(pt)) 

    east_rr_indices = _get_indices(s_envday['east_rr_shape'])

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": east_rr_shape}, indices=east_rr_indices)    
    batch.draw(_SHADER_)   

    south_rr_shape = []
    for pt in s_envday['south_rr_shape']:
        south_rr_shape.append( m @ Vector(pt))

    south_rr_indices = _get_indices(s_envday['south_rr_shape'])

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": south_rr_shape}, indices=south_rr_indices)    
    batch.draw(_SHADER_)  

    north_rr_shape = []
    for pt in s_envday['north_rr_shape']:
        north_rr_shape.append( m @ Vector(pt) )

    north_rr_indices = _get_indices(s_envday['north_rr_shape'])

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": north_rr_shape}, indices=north_rr_indices)    
    batch.draw(_SHADER_)             

    inner_circle_rr_shape = []
    for pt in s_envday['inner_circle_rr_shape']:
        inner_circle_rr_shape.append( m @ Vector(pt) )

    inner_circle_rr_shape_indices = _get_indices(s_envday['inner_circle_rr_shape'])

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": inner_circle_rr_shape}, indices=inner_circle_rr_shape_indices)    
    batch.draw(_SHADER_)   

    outer_circle_rr_shape = []
    for pt in s_envday['outer_circle_rr_shape']:
        outer_circle_rr_shape.append( m @ Vector(pt) )

    outer_circle_rr_shape_indices = _get_indices(s_envday['outer_circle_rr_shape'])

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": outer_circle_rr_shape}, indices=outer_circle_rr_shape_indices)    
    batch.draw(_SHADER_)  

    compass_shape = []
    for pt in s_envday['compass_shape']:
        compass_shape.append( m @ Vector(pt))

    compass_shape_indices = _get_indices(s_envday['compass_shape'])

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": compass_shape}, indices=compass_shape_indices)    
    batch.draw(_SHADER_)    

    east_arrow_shape = []
    for pt in s_envday['east_arrow_shape']:
        east_arrow_shape.append( m @ Vector(pt))

    east_arrow_shape_indices = _get_indices(s_envday['east_arrow_shape'])

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": east_arrow_shape}, indices=east_arrow_shape_indices)    
    batch.draw(_SHADER_)      

    west_arrow_shape = []
    for pt in s_envday['west_arrow_shape']:
        west_arrow_shape.append( m @ Vector(pt) )

    west_arrow_shape_indices = _get_indices(s_envday['west_arrow_shape'])

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": west_arrow_shape}, indices=west_arrow_shape_indices)    
    batch.draw(_SHADER_)         

    north_arrow_shape = []
    for pt in s_envday['north_arrow_shape']:
        north_arrow_shape.append( m @ Vector(pt))

    north_arrow_shape_indices = _get_indices(s_envday['north_arrow_shape'])

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": north_arrow_shape}, indices=north_arrow_shape_indices)    
    batch.draw(_SHADER_)         

    south_arrow_shape = []
    for pt in s_envday['south_arrow_shape']:
        south_arrow_shape.append( m @ Vector(pt))

    south_arrow_shape_indices = _get_indices(s_envday['south_arrow_shape'])

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": south_arrow_shape}, indices=south_arrow_shape_indices)    
    batch.draw(_SHADER_)     

    sunDirection = _get_sun_direction(ob)
    sunDirection = Matrix(ob_matrix) @ Vector(sunDirection)
    origin = Matrix(ob_matrix) @ Vector([0,0,0])
    sunDirection_pts = [ origin, sunDirection]
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": sunDirection_pts}, indices=[(0,1)])    
    batch.draw(_SHADER_) 

    # draw a sphere to represent the sun
    v = sunDirection - origin
    translate = Matrix.Translation(v)
    sphere = make_sphere(ob_matrix @ Matrix.Scale(0.25, 4))
    sphere_indices = []
    for i in range(0, len(sphere)):
        if i == len(sphere)-1:
            sphere_indices.append((i, 0))
        else:
            sphere_indices.append((i, i+1))    

    sphere_shape = []
    for pt in sphere:
        sphere_shape.append( translate @ Vector(pt) )
 

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": sphere_shape}, indices=sphere_indices)    
    batch.draw(_SHADER_)  


def draw_disk_light(ob): 
                 

    _SHADER_.bind()

    if ob in bpy.context.selected_objects:
        _SHADER_.uniform_float("color", (1,1,1,1))

    m = Matrix(ob.matrix_world)        
    m = m @ Matrix.Rotation(math.radians(180.0), 4, 'Y')
    m = m @ Matrix.Rotation(math.radians(90.0), 4, 'Z')

    disk = []
    for pt in s_diskLight:
        disk.append( m @ Vector(pt))

    disk_indices = _get_indices(s_diskLight)
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": disk}, indices=disk_indices)    
    batch.draw(_SHADER_)

    arrow = []
    for pt in s_rmanLightLogo['arrow']:
        arrow.append( m @ Vector(pt)) 

    arrow_indices = _get_indices(s_rmanLightLogo['arrow'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": arrow}, indices=arrow_indices)    
    batch.draw(_SHADER_)

    R_outside = []
    for pt in s_rmanLightLogo['R_outside']:
        R_outside.append( m @ Vector(pt)) 

    R_outside_indices = _get_indices(s_rmanLightLogo['R_outside'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": R_outside}, indices=R_outside_indices)    
    batch.draw(_SHADER_)
  
    R_inside = []
    for pt in s_rmanLightLogo['R_inside']:
        R_inside.append( m @ Vector(pt))

    R_inside_indices = _get_indices(s_rmanLightLogo['R_inside'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": R_inside}, indices=R_inside_indices)    
    batch.draw(_SHADER_)  

def draw_dist_light(ob):      
    

    _SHADER_.bind()

    if ob in bpy.context.selected_objects:
        _SHADER_.uniform_float("color", (1,1,1,1))

    m = Matrix(ob.matrix_world)        
    m = m @ Matrix.Rotation(math.radians(180.0), 4, 'Y')
    m = m @ Matrix.Rotation(math.radians(90.0), 4, 'Z')     

    disk = []
    for pt in s_diskLight:
        disk.append( m @ Vector(pt) )

    disk_indices = _get_indices(s_diskLight)
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": disk}, indices=disk_indices)    
    batch.draw(_SHADER_)    

    arrow1 = []
    for pt in s_distantLight['arrow1']:
        arrow1.append( m @ Vector(pt) )

    arrow1_indices = _get_indices(s_distantLight['arrow1'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": arrow1}, indices=arrow1_indices)    
    batch.draw(_SHADER_)    

    arrow2 = []
    for pt in s_distantLight['arrow2']:
        arrow2.append( m @ Vector(pt)) 

    arrow2_indices = _get_indices(s_distantLight['arrow2'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": arrow2}, indices=arrow2_indices)    
    batch.draw(_SHADER_) 

    arrow3 = []
    for pt in s_distantLight['arrow3']:
        arrow3.append( m @ Vector(pt) )

    arrow3_indices = _get_indices(s_distantLight['arrow3'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": arrow3}, indices=arrow3_indices)    
    batch.draw(_SHADER_)         

    R_outside = []
    for pt in s_rmanLightLogo['R_outside']:
        R_outside.append( m @ Vector(pt) )

    R_outside_indices = _get_indices(s_rmanLightLogo['R_outside'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": R_outside}, indices=R_outside_indices)    
    batch.draw(_SHADER_)
  
    R_inside = []
    for pt in s_rmanLightLogo['R_inside']:
        R_inside.append( m @ Vector(pt) ) 

    R_inside_indices = _get_indices(s_rmanLightLogo['R_inside'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": R_inside}, indices=R_inside_indices)    
    batch.draw(_SHADER_)             

def draw_portal_light(ob):
    _SHADER_.bind()

    if ob in bpy.context.selected_objects:
        _SHADER_.uniform_float("color", (1,1,1,1))

    m = Matrix(ob.matrix_world)        
    m = m @ Matrix.Rotation(math.radians(180.0), 4, 'Y')
    m = m @ Matrix.Rotation(math.radians(90.0), 4, 'Z')

    R_outside = []
    for pt in s_rmanLightLogo['R_outside']:
        R_outside.append( m @ Vector(pt) )

    R_outside_indices = _get_indices(s_rmanLightLogo['R_outside'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": R_outside}, indices=R_outside_indices)    
    batch.draw(_SHADER_)
  
    R_inside = []
    for pt in s_rmanLightLogo['R_inside']:
        R_inside.append( m @ Vector(pt))

    R_inside_indices = _get_indices(s_rmanLightLogo['R_inside'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": R_inside}, indices=R_inside_indices)    
    batch.draw(_SHADER_)                 

    m = Matrix(ob.matrix_world)
    m = m @ Matrix.Rotation(math.radians(90.0), 4, 'X')
    m = m @ Matrix.Scale(0.5, 4)
    rays = []
    for pt in s_portalRays:
        rays.append( m @ Vector(pt) )

    rays_indices = _get_indices(s_portalRays)
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": rays}, indices=rays_indices)    
    batch.draw(_SHADER_)         

def draw_dome_light(ob):
    
    
    _SHADER_.bind()

    if ob in bpy.context.selected_objects:
        _SHADER_.uniform_float("color", (1,1,1,1))

    loc, rot, sca = Matrix(ob.matrix_world).decompose()
    axis,angle = rot.to_axis_angle()
    m = Matrix.Rotation(angle, 4, axis)
    m = m @ Matrix.Scale(100, 4)

    R_outside = []
    for pt in s_rmanLightLogo['R_outside']:
        R_outside.append( m @ Vector(pt))

    R_outside_indices = _get_indices(s_rmanLightLogo['R_outside'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": R_outside}, indices=R_outside_indices)    
    batch.draw(_SHADER_)
  
    R_inside = []
    for pt in s_rmanLightLogo['R_inside']:
        R_inside.append( m @ Vector(pt) )

    R_inside_indices = _get_indices(s_rmanLightLogo['R_inside'])
    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": R_inside}, indices=R_inside_indices)    
    batch.draw(_SHADER_)    

    sphere = make_sphere(m)
    sphere_indices = []
    for i in range(0, len(sphere)):
        if i == len(sphere)-1:
            sphere_indices.append((i, 0))
        else:
            sphere_indices.append((i, i+1))     

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": sphere}, indices=sphere_indices)    
    batch.draw(_SHADER_)        

def draw_cylinder_light(ob):

    _SHADER_.bind()

    if ob in bpy.context.selected_objects:
        _SHADER_.uniform_float("color", (1,1,1,1))

    m = Matrix(ob.matrix_world)

    cylinder = []
    for pt in s_cylinderLight['vtx']:
        cylinder.append( m @ Vector(pt)) 

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": cylinder}, indices=s_cylinderLight['indices'])    
    batch.draw(_SHADER_)  


def draw_arc(a, b, numSteps, quadrant, xOffset, yOffset, pts):
    stepAngle = float(_PI0_5_ / numSteps)
    for i in range(0, numSteps):

        angle = stepAngle*i + quadrant*_PI0_5_
        x = a * math.cos(angle)
        y = b * math.sin(angle)
        
        pts.append(Vector([x+xOffset, y+yOffset, 0.0]))
        #pts.append(Vector([x+xOffset, 0.0, y+yOffset]))

def draw_rounded_rectangles( left, right,
                            top,  bottom,
                            radius,
                            leftEdge,  rightEdge,
                            topEdge,  bottomEdge,
                            zOffset1,  zOffset2, 
                            m):

    pts = []
    a = radius+rightEdge
    b = radius+topEdge
    draw_arc(a, b, 10, 0, right, top, pts)
    a = radius+leftEdge
    b = radius+topEdge
    draw_arc(a, b, 10, 1, -left, top, pts)
    a = radius+leftEdge
    b = radius+bottomEdge
    draw_arc(a, b, 10, 2, -left, -bottom, pts)
    
    a = radius+rightEdge
    b = radius+bottomEdge
    draw_arc(a, b, 10, 3, right, -bottom, pts)

    translate = m #Matrix.Translation( Vector([0,0, zOffset1])) @ m
    shape_pts = []
    for pt in pts:
        shape_pts.append( translate @ Vector(pt)) 
    shape_pts_indices = _get_indices(shape_pts)

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": shape_pts}, indices=shape_pts_indices)    
    batch.draw(_SHADER_)  

    shape_pts = []
    translate = m #Matrix.Translation( Vector([0,0, zOffset2])) @ m
    for pt in pts:
        shape_pts.append( translate @ Vector(pt) )
    shape_pts_indices = _get_indices(shape_pts)

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": shape_pts}, indices=shape_pts_indices)    
    batch.draw(_SHADER_)   

def draw_rod(leftEdge, rightEdge, topEdge,  bottomEdge,
            frontEdge,  backEdge,  scale, width,  radius, 
            left,  right,  top,  bottom,  front, back, world_mat):

    leftEdge *= scale
    rightEdge *= scale
    topEdge *= scale
    backEdge *= scale
    frontEdge *= scale
    bottomEdge *= scale
    
    m = world_mat
    
    # front and back
    draw_rounded_rectangles(left, right, top, bottom, radius,
                          leftEdge, rightEdge,
                          topEdge, bottomEdge, front, -back, m)

 
    m = world_mat @ Matrix.Rotation(math.radians(-90.0), 4, 'X')
 
    
    # top and bottom
    
    draw_rounded_rectangles(left, right, back, front, radius,
                          leftEdge, rightEdge,
                          backEdge, frontEdge, top, -bottom, m)
 
    m = world_mat  @ Matrix.Rotation(math.radians(90.0), 4, 'Y')
    
    
    # left and right
    draw_rounded_rectangles(front, back, top, bottom, radius,
                          frontEdge, backEdge,
                          topEdge, bottomEdge, -left, right, m)

def draw_rod_light_filter(ob):
    _SHADER_.bind()

    if ob in bpy.context.selected_objects:
        _SHADER_.uniform_float("color", (1,1,1,1))

    m = Matrix(ob.matrix_world)     
    m = m @ Matrix.Rotation(math.radians(90.0), 4, 'X')
    m = m @ Matrix.Rotation(math.radians(90.0), 4, 'Y')
    
    #m = m @ Matrix.Rotation(math.radians(180.0), 4, 'Y')
    #m = m @ Matrix.Rotation(math.radians(90.0), 4, 'Z')

    light = ob.data
    rm = light.renderman.get_light_node()

    edge = rm.edge
    width = rm.width
    depth = rm.depth
    height = rm.height
    radius = rm.radius

    left_edge = edge
    right_edge = edge
    top_edge = edge
    bottom_edge = edge
    front_edge = edge
    back_edge = edge

    left = 0.0
    right = 0.0
    top = 0.0
    bottom = 0.0
    front = 0.0
    back = 0.0

    scale_width = 1.0
    scale_height = 1.0
    scale_depth = 1.0

    rod_scale = 0.0

    if light.renderman.get_light_node_name() == 'PxrRodLightFilter':
        left_edge *= rm.leftEdge
        right_edge *= rm.rightEdge
        top_edge *= rm.topEdge
        bottom_edge *= rm.bottomEdge
        front_edge *= rm.frontEdge
        back_edge *= rm.backEdge
        scale_width *= rm.scaleWidth
        scale_height *= rm.scaleHeight
        scale_depth *= rm.scaleDepth
        left = rm.left
        right = rm.right
        top = rm.top
        bottom = rm.bottom
        front = rm.front
        back = rm.back

    left += scale_width * width
    right += scale_width * width
    top += scale_height * height
    bottom += scale_height * height
    front += scale_depth * depth
    back += scale_depth * depth

    draw_rod(left_edge, right_edge,
            top_edge, bottom_edge,
            front_edge, back_edge, rod_scale,
            width, radius,
            left, right, top, bottom, front,
            back, m)
        
    if edge > 0.0:
            
        # draw outside box
        rod_scale = 1.0
        draw_rod(left_edge, right_edge,
            top_edge, bottom_edge,
            front_edge, back_edge, rod_scale,
            width, radius,
            left, right, top, bottom, front,
            back, m)           

def draw_ramp_light_filter(ob):
    _SHADER_.bind()

    if ob in bpy.context.selected_objects:
        _SHADER_.uniform_float("color", (1,1,1,1))

    light = ob.data
    rm = light.renderman.get_light_node()
    rampType = int(rm.rampType)

    begin = float(rm.beginDist)
    end = float(rm.endDist)    

    # distToLight
    if rampType in (0,2):
        _SHADER_.bind()

        if ob in bpy.context.selected_objects:
            _SHADER_.uniform_float("color", (1,1,1,1))

        m = Matrix(ob.matrix_world)        
        m = m @ Matrix.Rotation(math.radians(180.0), 4, 'Y')
        m = m @ Matrix.Rotation(math.radians(90.0), 4, 'Z')

        # begin
        begin_m = m @ Matrix.Scale(begin, 4)      

        disk = []
        for pt in s_diskLight:
            disk.append( begin_m @ Vector(pt) ) 

        disk_indices = _get_indices(s_diskLight)
        batch = batch_for_shader(_SHADER_, 'LINES', {"pos": disk}, indices=disk_indices)    
        batch.draw(_SHADER_)

        m2 = begin_m @ Matrix.Rotation(math.radians(90.0), 4, 'Y')
        disk = []
        for pt in s_diskLight:
            disk.append( m2 @ Vector(pt)) 

        disk_indices = _get_indices(s_diskLight)
        batch = batch_for_shader(_SHADER_, 'LINES', {"pos": disk}, indices=disk_indices)    
        batch.draw(_SHADER_)

        m3 = begin_m @ Matrix.Rotation(math.radians(90.0), 4, 'X')
        disk = []
        for pt in s_diskLight:
            disk.append( m3 @ Vector(pt))

        disk_indices = _get_indices(s_diskLight)
        batch = batch_for_shader(_SHADER_, 'LINES', {"pos": disk}, indices=disk_indices)    
        batch.draw(_SHADER_)   

        # end
        end_m = m @ Matrix.Scale(end, 4)      

        disk = []
        for pt in s_diskLight:
            disk.append( end_m @ Vector(pt)) 

        disk_indices = _get_indices(s_diskLight)
        batch = batch_for_shader(_SHADER_, 'LINES', {"pos": disk}, indices=disk_indices)    
        batch.draw(_SHADER_)

        m2 = end_m @ Matrix.Rotation(math.radians(90.0), 4, 'Y')
        disk = []
        for pt in s_diskLight:
            disk.append( m2 @ Vector(pt))

        disk_indices = _get_indices(s_diskLight)
        batch = batch_for_shader(_SHADER_, 'LINES', {"pos": disk}, indices=disk_indices)    
        batch.draw(_SHADER_)

        m3 = end_m @ Matrix.Rotation(math.radians(90.0), 4, 'X')
        disk = []
        for pt in s_diskLight:
            disk.append( m3 @ Vector(pt))

        disk_indices = _get_indices(s_diskLight)
        batch = batch_for_shader(_SHADER_, 'LINES', {"pos": disk}, indices=disk_indices)    
        batch.draw(_SHADER_)        


    # linear
    elif rampType == 1:        

        m = Matrix(ob.matrix_world)        
        m = m @ Matrix.Rotation(math.radians(180.0), 4, 'Y')
        m = m @ Matrix.Rotation(math.radians(90.0), 4, 'Z')

        box = []
        for pt in s_rmanLightLogo['box']:
            box.append( m @ Vector(pt)) 
        n = mathutils.geometry.normal(box)
        n.normalize()
        box1 = []
        for i,pt in enumerate(box):
            if begin > 0.0:
                box1.append(pt + (begin * n))
            else:
                box1.append(pt)

        box_indices = _get_indices(s_rmanLightLogo['box'])
        batch = batch_for_shader(_SHADER_, 'LINES', {"pos": box1}, indices=box_indices)    
        batch.draw(_SHADER_)

        box2 = []
        for pt in box:
            box2.append( pt + (end * n) )

        batch = batch_for_shader(_SHADER_, 'LINES', {"pos": box2}, indices=box_indices)    
        batch.draw(_SHADER_)        

    # radial
    elif rampType == 3:
        _SHADER_.bind()

        if ob in bpy.context.selected_objects:
            _SHADER_.uniform_float("color", (1,1,1,1))

        m = Matrix(ob.matrix_world)        
        m = m @ Matrix.Rotation(math.radians(180.0), 4, 'Y')
        m = m @ Matrix.Rotation(math.radians(90.0), 4, 'Z')

        if begin > 0.0:
            m1 = m @ Matrix.Scale(begin, 4)      

            disk = []
            for pt in s_diskLight:
                disk.append( m1 @ Vector(pt) )

            disk_indices = _get_indices(s_diskLight)
            batch = batch_for_shader(_SHADER_, 'LINES', {"pos": disk}, indices=disk_indices)    
            batch.draw(_SHADER_)


        m2 = m @ Matrix.Scale(end, 4)      

        disk = []
        for pt in s_diskLight:
            disk.append( m2 @ Vector(pt)) 

        disk_indices = _get_indices(s_diskLight)
        batch = batch_for_shader(_SHADER_, 'LINES', {"pos": disk}, indices=disk_indices)    
        batch.draw(_SHADER_)

    else:
        pass

def draw_barn_light_filter(ob):
    global _BARN_LIGHT_DRAW_HELPER_

    _SHADER_.bind()

    m = Matrix(ob.matrix_world) 
    m = m @ Matrix.Rotation(math.radians(180.0), 4, 'Y')
    #m = m @ Matrix.Rotation(math.radians(90.0), 4, 'Z')

    if ob in bpy.context.selected_objects:
        _SHADER_.uniform_float("color", (1,1,1,1))

    if not _BARN_LIGHT_DRAW_HELPER_:
        _BARN_LIGHT_DRAW_HELPER_ = BarnLightFilterDrawHelper()
    _BARN_LIGHT_DRAW_HELPER_.update_input_params(ob)
    vtx_buffer = _BARN_LIGHT_DRAW_HELPER_.vtx_buffer()

    pts = []
    for pt in vtx_buffer:
        pts.append( m @ Vector(pt))

    indices = _BARN_LIGHT_DRAW_HELPER_.idx_buffer(len(pt), 0, 0)
    # blender wants a list of lists
    indices = [indices[i:i+2] for i in range(0, len(indices), 2)]

    batch = batch_for_shader(_SHADER_, 'LINES', {"pos": pts}, indices=indices)    
    batch.draw(_SHADER_)     

def draw():

    if bpy.context.engine != 'PRMAN_RENDER':
        return

    for ob in [x for x in bpy.data.objects if x.type == 'LIGHT']:
        if not ob.data.renderman:
            continue
        rm = ob.data.renderman
        light_shader = rm.get_light_node()
        if not light_shader:
            continue

        light_shader_name = rm.get_light_node_name()
        if light_shader_name == '':
            return

        if light_shader_name == 'PxrSphereLight': 
            draw_sphere_light(ob)
        elif light_shader_name == 'PxrEnvDayLight': 
            draw_envday_light(ob)
        elif light_shader_name == 'PxrDiskLight': 
            draw_disk_light(ob)
        elif light_shader_name == 'PxrDistantLight': 
            draw_dist_light(ob)       
        elif light_shader_name == 'PxrPortalLight': 
            draw_portal_light(ob)      
        elif light_shader_name == 'PxrDomeLight': 
            draw_dome_light(ob)        
        elif light_shader_name == 'PxrCylinderLight':
            draw_cylinder_light(ob)     
        elif light_shader_name in ['PxrGoboLightFilter', 'PxrCookieLightFilter']:
             draw_rect_light(ob)             
        elif light_shader_name in ['PxrRodLightFilter', 'PxrBlockerLightFilter']:
            draw_rod_light_filter(ob)
        elif light_shader_name == 'PxrRampLightFilter':
            draw_ramp_light_filter(ob)
        elif light_shader_name == 'PxrBarnLightFilter':
            # get all lights that the barn is attached to
            draw_barn_light_filter(ob)
        else: 
            draw_rect_light(ob) 

def register():
    global _DRAW_HANDLER_
    _DRAW_HANDLER_ = bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def unregister():
    global _DRAW_HANDLER_
    if _DRAW_HANDLER_:
        bpy.types.SpaceView3D.draw_handler_remove(_DRAW_HANDLER_, 'WINDOW')
