/*
# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2012 Matt Ebb
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
*/

#pragma annotation visibility "True"

#pragma annotation sample_light "gadgettype=checkbox;label=Sample Lights;"
#pragma annotation sample_bsdf "gadgettype=checkbox;label=Sample BSDF;"

#include "util.h"
#include "integrator.h"

class integrator(
            uniform float minsamples = 16;
            uniform float maxsamples = 32;
            uniform float diffuse_bounces = 0;
            uniform float diffuse_factor = 1.0;
            uniform float specular_bounces = 1;
            uniform float specular_factor = 1.0;
            uniform float transmission_bounces = 2;
            uniform float transmission_factor = 1.0;
            uniform float sample_light = 1;
            uniform float sample_bsdf = 1;
            uniform float indirect_sample_factor = 0.2;
    )
{
    /* to get parameters picked up */
    public void surface(output color Ci, Oi) { }

    uniform float ray_depth;
    uniform float diffuse_depth;
    uniform float specular_depth;
    uniform float transmission_depth;

    color visibility(point Pt; vector V; shader lgt;)
    {
        color Cv=0;
        uniform float stype;
        uniform float has_stype = getvar(lgt, "shadowtype", stype);

        if (has_stype == 0) stype = 0;

        if (stype == 0) {  // raytrace
            Cv = transmission(Pt, Pt+V);
        }
        else if (stype == 1) { // shadow map
            uniform string smap;
            uniform float has_smap = getvar(lgt, "shadowmap", smap);

            if (has_smap)
                Cv = color(1) - shadow(smap, Pt);
        }
        else {          // handled by lamp
            return lgt->getshadow();
        }
        return Cv;
    }

    public void begin() {
        rayinfo("depth", ray_depth);
        rayinfo("diffusedepth", diffuse_depth);
        rayinfo("speculardepth", specular_depth);
        rayinfo("shadowdepth", transmission_depth);
    }

    public void integ(output varying color Ci, Oi;
                        shadingGeo SG;
                        uniform shader shd) {

        integrate(Ci, Oi, SG, shd);
        return;
    }

}