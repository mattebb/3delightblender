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

// light_env.sl

#include "util.h"

class
light_env_cosine(
        uniform float intensity = 1;
        uniform color lightcolor = 1;
        uniform float samples = 16;
        uniform string texturename = "";
       )
       
{

    uniform point center = point "shader" (0,0,0);
    uniform vector udir = vector "shader" (1,0,0);
    uniform vector vdir = vector "shader" (0,1,0);
    uniform vector zdir = vector "shader" (0,0,-1);   // direction of light
    uniform float area;

    public void construct() {
    }

    public color Le(point P; vector L;) {
        color Le;
        vector Lw = transform("current", "world", normalize(L));
        float u, v;
                
        cartesian_to_spherical( Lw, u, v);
        
        u = u/(2*PI);
        v = 0.5*(v/(PI/2));
        
        if (texturename != "")
            Le = texture(texturename, u, v, u, v, u, v, u, v);
        else
            Le = lightcolor;

        return Le*intensity;
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
            
            //_pdf[i] = pdf(P, wi[i], _L[i]);
            _pdf[i] = 1/(2*PI);
            
            _L[i] = wi[i] * 100000;

            _Li[i] = Le(P, _L[i]);
        }
    }
    
    public void light( output vector L;         // unused
                       output color Cl;         // unused
                       varying normal Ns;
                       output color _Li[];
                       output vector _L[];
                       output float _pdf[];
                       output uniform float nsamp = 0;
                       )
    {
       vector rnd;
       varying point samplepos;
       varying float u, v;
       uniform float s;
       uniform float nsamples;
       
       if (nsamp <= 0)
            nsamples = 32;
       else
            nsamples = nsamp;

       resize(_Li, nsamples);
       resize(_L, nsamples);
       resize(_pdf, nsamples);

       color Le;
       color black=0;
       
       for (s = 0; s < nsamples; s += 1) {
            u = random();
            v = random();
            
            /* the obvious thing would be to sample the 
             * entire hemi/sphere in world space.  
             * Since it will sample the entire sphere anyway though,
             * we can get a better distribution by sampling 
             * with a cosine weighting against the normal,
             * to account for the geometric term, as long as its 
             * taken into consideration in the pdf as well. (pbrt)
             */
             
            vector l = warp_hemicosine(u, v);
            /* full sphere sampling ? no btdfs yet
             * if (random() < 0.5)
             *    l[2] *= -1 ; //cosine weighted full sphere sampling
             */
            _L[s] = align_ortho(l, Ns, dPdu );
            
            _pdf[s] = (_L[s] . Ns) / (2*PI);
            _Li[s] = Le(P, _L[s]);
            
            // XXX: set to huge for ray intersections.. must be a better way?
            _L[s] *= 999999999;            

       }
       nsamp = nsamples;
       
       // Clear L and Cl, even though they're unused.
       L = (0,0,0);
       Cl = (0,0,0);
    }
}