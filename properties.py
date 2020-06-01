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

import bpy
import os
import sys
import time

from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty, BoolVectorProperty

import traceback

from .rman_utils import filepath_utils
from .rfb_logger import rfb_log
from . import rman_render
from . import rman_bl_nodes
from .rman_bl_nodes import rman_bl_nodes_props
from . import rman_bl_nodes

# Blender data
# --------------------------

class RendermanPath(bpy.types.PropertyGroup):
    name: StringProperty(
        name="", subtype='DIR_PATH')


class RendermanInlineRIB(bpy.types.PropertyGroup):
    name: StringProperty(name="Text Block")

class Tab_CollectionGroup(bpy.types.PropertyGroup):

    #################
    #       Tab     #
    #################

    bpy.types.Scene.rm_ipr = BoolProperty(
        name="IPR settings",
        description="Show some useful setting for the Interactive Rendering",
        default=False)

    bpy.types.Scene.rm_render = BoolProperty(
        name="Render settings",
        description="Show some useful setting for the Rendering",
        default=False)

    bpy.types.Scene.rm_render_external = BoolProperty(
        name="Render settings",
        description="Show some useful setting for external rendering",
        default=False)

    bpy.types.Scene.rm_help = BoolProperty(
        name="Help",
        description="Show some links about RenderMan and the documentation",
        default=False)

    bpy.types.Scene.rm_env = BoolProperty(
        name="Envlight",
        description="Show some settings about the selected Env light",
        default=False)

    bpy.types.Scene.rm_area = BoolProperty(
        name="AreaLight",
        description="Show some settings about the selected Area Light",
        default=False)

    bpy.types.Scene.rm_daylight = BoolProperty(
        name="DayLight",
        description="Show some settings about the selected Day Light",
        default=False)

    bpy.types.Scene.prm_cam = BoolProperty(
        name="Renderman Camera",
        description="Show some settings about the camera",
        default=False)


initial_aov_channels = [("a", "alpha", ""),
                        ("id", "id", "Returns the integer assigned via the 'identifier' attribute as the pixel value"),
                        ("z", "z_depth", "Depth from the camera in world space"),
                        ("zback", "z_back",
                         "Depth at the back of volumetric objects in world space"),
                        ("P", "P", "Position of the point hit by the incident ray"),
                        ("PRadius", "PRadius",
                         "Cross-sectional size of the ray at the hit point"),
                        ("cpuTime", "cpuTime", "The time taken to render a pixel"),
                        ("sampleCount", "sampleCount",
                         "The number of samples taken for the resulting pixel"),
                        ("Nn", "Nn", "Normalized shading normal"),
                        ("Ngn", "Ngn", "Normalized geometric normal"),
                        ("Tn", "Tn", "Normalized shading tangent"),
                        ("Vn", "Vn", "Normalized view vector (reverse of ray direction)"),
                        ("VLen", "VLen", "Distance to hit point along the ray"),
                        ("curvature", "curvature", "Local surface curvature"),
                        ("incidentRaySpread", "incidentRaySpread",
                         "Rate of spread of incident ray"),
                        ("mpSize", "mpSize",
                         "Size of the micropolygon that the ray hit"),
                        ("u", "u", "The parametric coordinates on the primitive"),
                        ("v", "v", "The parametric coordinates on the primitive"),
                        ("w", "w", "The parametric coordinates on the primitive"),
                        ("du", "du", "Derivatives of u, v, and w to adjacent micropolygons"),
                        ("dv", "dv", "Derivatives of u, v, and w to adjacent micropolygons"),
                        ("dw", "dw", "Derivatives of u, v, and w to adjacent micropolygons"),
                        ("dPdu", "dPdu", "Direction of maximal change in u, v, and w"),
                        ("dPdv", "dPdv", "Direction of maximal change in u, v, and w"),
                        ("dPdw", "dPdw", "Direction of maximal change in u, v, and w"),
                        ("dufp", "dufp",
                         "Multiplier to dPdu, dPdv, dPdw for ray differentials"),
                        ("dvfp", "dvfp",
                         "Multiplier to dPdu, dPdv, dPdw for ray differentials"),
                        ("dwfp", "dwfp",
                         "Multiplier to dPdu, dPdv, dPdw for ray differentials"),
                        ("time", "time", "Time sample of the ray"),
                        ("dPdtime", "dPdtime", "Motion vector"),
                        ("id", "id", "Returns the integer assigned via the identifier attribute as the pixel value"),
                        ("outsideIOR", "outsideIOR",
                         "Index of refraction outside this surface"),
                        ("__Pworld", "Pworld", "P in world-space"),
                        ("__Nworld", "Nworld", "Nn in world-space"),
                        ("__depth", "depth", "Multi-purpose AOV\nr : depth from camera in world-space\ng : height in world-space\nb : geometric facing ratio : abs(Nn.V)"),
                        ("__st", "st", "Texture coords"),
                        ("__Pref", "Pref", "Reference Position primvar (if available)"),
                        ("__Nref", "Nref", "Reference Normal primvar (if available)"),
                        ("__WPref", "WPref",
                         "Reference World Position primvar (if available)"),
                        ("__WNref", "WNref", "Reference World Normal primvar (if available)")]

# collection of property group classes that need to be registered on
# module startup
classes = [RendermanPath,
           RendermanInlineRIB,
    
           #RendermanParticlePrimVar,
           
           
           #RendermanParticleSettings,    
           
           
           Tab_CollectionGroup
           ]

def register():

    # dynamically find integrators from args
    # register_integrator_settings(RendermanSceneSettings)
    # dynamically find camera from args
    # register_camera_settings()

    for cls in classes:
        bpy.utils.register_class(cls)

    #bpy.types.ParticleSettings.renderman = PointerProperty(
    #    type=RendermanParticleSettings, name="Renderman Particle Settings")
        

def unregister():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass

    #bpy.utils.unregister_class(RmanObjectSettings)
    #FIXME bpy.utils.unregister_module(__name__)
