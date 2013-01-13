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

// realight.sl

#include "util.h"

#define SHAPE_RECT  0
#define SHAPE_DISC  1

#pragma annotation shape "gadgettype=optionmenu:Rectangle:Disc;label=Shape;hint=Area light shape"

class
light_area(
        uniform float intensity = 1;
        uniform color lightcolor = 1;
        uniform float width = 1.0;
        uniform float height = 1.0;
        uniform string texturename = "";
        uniform float shape = 0;
       )
       
{

    public constant float isdelta = 0;
    public constant float shadowtype = SHADOW_RAYTRACE;
    
    constant float zero = 0;
    constant color black = 0;

    uniform point center = point "shader" (0,0,0); // center of rectangle
    uniform vector udir = vector "shader" (width*0.5,0,0); // axis of rectangle
    uniform vector vdir = vector "shader" (0,height*0.5,0); // axis of rectangle
    uniform vector zdir = vector "shader" (0,0,-1);   // direction of light
    uniform float area;

    public void construct() {
        if (shape == SHAPE_RECT)         area = width*height;
        else if (shape == SHAPE_DISC)    area = PI*width*0.5*height*0.5;
    }

    float intersect(point P; vector V;)
    {
        // transform ray into local space of light (shader space)
        varying point Pl = transform("current", "shader", P);
        varying vector Vl = transform("current", "shader", V);
        
        // check to see if ray is parallel or behind the light
        if (Vl[2] <= 0)
           return zero;
        
        varying float thit = -Pl[2] / Vl[2];
        if (thit < 0) return zero;
        
        varying point ph = Pl + Vl * thit;
        
        if (shape == SHAPE_RECT) {
            // check to see if inside area quad
            if ((abs(ph[0]) > width*0.5) || (abs(ph[1]) > height*0.5))
                return zero;
            
        } else if (shape == SHAPE_DISC) {
            // check to see if inside area disc
            float x = ph[0]/(width*0.5);
            float y = ph[1]/(height*0.5);
            
            if ( x*x + y*y > 1 )
                return zero;    
        }
        
        return thit;
    }
    
    color Le(point P; vector L;) {
        color Le = black;
        
        if (length(L) < 0.001)
            return black;
        
        if (texturename == "") {
             Le = lightcolor*intensity;
             return Le;
        }

        point Pl = P + L;
        
        point uv = transform("current", "shader", Pl);
        float su = ((uv[0] / width)+1)*0.5;
        float sv = ((uv[1] / height)+1)*0.5;
        
        Le = texture(texturename); //, su, sv, su, sv, su, sv, su, sv);
        Le *= intensity;
        return Le;
    }
    
    float pdf(point P; vector V; output vector L;)
    {
        varying float thit = intersect(P, V);
                
        if (thit < 0)
            return 0;
        
        L = V*thit;       
        
        // convert to solid angle
        varying float distsq = lengthsq(L);
        varying float costheta = -zdir . normalize(L);
        varying float pdf = distsq / (costheta*area);
        
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
              
       resize(_Li, nsamples);   // note use of resizable arrays
       resize(_L, nsamples);
       resize(_pdf, nsamples);

       for (s = 0; s < nsamples; s += 1) {
            su = random();
            sv = random();
            
            if (shape == SHAPE_RECT) {
                samplepos = center + (((su*2)-1) * udir) + (((sv*2)-1) * vdir);
            } else if (shape == SHAPE_DISC) {
                varying vector S = warp_disc(su, sv);   // in [-1,1]
                su = S[0];
                sv = S[1];
                samplepos = center + (su * udir) + (sv * vdir);
            }

            _L[s] = samplepos - P;     // vector P -> light
            
            
            varying float distsq = lengthsq(_L[s]);
            varying float costheta_z = normalize(_L[s]) . -zdir;
            
            if (costheta_z <= 0) {
                _Li[s] = 0;
                _pdf[s] = 0;
                return;
            }
            _pdf[s] = distsq / (abs(costheta_z)*area);

            
            if (texturename != "")
                _Li[s] = texture(texturename, su, sv, su, sv, su, sv, su, sv);
            else
                _Li[s] = lightcolor;
            _Li[s] *= intensity;           
       }
       
       // Clear L and Cl, even though they're unused.
       L = (0,0,0);
       Cl = (0,0,0);
    }
}