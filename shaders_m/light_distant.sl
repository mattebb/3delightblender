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

#include "util.h"

#pragma annotation shadow_ortho_scale "meta=distant_scale;label=Ortho Scale;hint=Scale of parallel shadow map boundary"
#pragma annotation shadowmap "meta=shadow_map_path;label=Shadow Map Path;hide=True;"
#pragma annotation shadowtype "meta=use_shadow_map;label=Shadow Type;"

class
light_distant(
        uniform float intensity = 1;
        uniform color lightcolor = 1;
        uniform float angle = 0.5;
        uniform float shadowtype = 0;
        uniform string shadowmap = "";
        uniform float shadow_ortho_scale = 10.0;
       )
       
{
    public constant float isdelta = 1;
    public constant float stype=shadowtype;
    public constant string smap=shadowmap;

    constant point center = point "shader" (0,0,0); // center
    constant vector udir = vector "shader" (1,0,0); // axis of rectangle
    constant vector vdir = vector "shader" (0,1,0); // axis of rectangle
    constant vector zdir = vector "shader" (0,0,1);   // direction of light
    
    constant float angle_rad = radians(angle);
    
    color Le(point P; vector L;) {

        color Le = lightcolor*intensity;
        
        return Le;
    }
    
    float pdf(point P; vector V; output vector L;)
    {
        float pdf=0;
        return pdf;
        
    }
    
    public void eval_light(point P; vector wi[];
                                uniform float nsamp;
                                output vector _L[];
                                output color _Li[];
                                output float _pdf[];
                                )
    {
        float i;
        resize(_L, nsamp);
        resize(_Li, nsamp);
        resize(_pdf, nsamp);
        
        for (i = 0; i < nsamp; i += 1) {
            _pdf[i] = pdf(P, wi[i], _L[i]);
            
            if (_pdf[i] > 0)
                _Li[i] = Le(P, _L[i]);
        }
    }
    
    public void light( output vector L;         // unused
                       output color Cl;         // unused
                       varying normal Ns;
                       output color _Li[];
                       output vector _L[];
                       output float _pdf[];
                       uniform float nsamples;
                       )
    {
       varying point samplepos;
       varying float su, sv;
       uniform float s;
       
       resize(_Li, nsamples);
       resize(_L, nsamples);
       resize(_pdf, nsamples);

       for (s = 0; s < nsamples; s += 1) {
          if (angle > 0) {
            su = random();
            sv = random();

            varying float cosangle = cos(angle_rad);
            _L[s] = warp_cone(su, sv, cosangle, udir, vdir, zdir) * SCENE_BOUNDS;
          } else {
            _L[s] = SCENE_BOUNDS * zdir;
          }

          _pdf[s] = 1.0;
          _Li[s] = Le(P, _L[s]);           
       }
       
       L = vector(0,0,0);
       Cl = color(0,0,0);
    }
}