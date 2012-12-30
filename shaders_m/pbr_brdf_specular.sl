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


class pbr_brdf_specular (
                    )
{

    public constant string type = "specular";
    
    public void sample_bsdf(normal N; vector wo; uniform float nsamp;
                            output vector wi[];
                            output color f[];
                            output float pdf[];
                            )
    {    
        float i;
        resize(wi, nsamp);
        resize(f, nsamp);
        resize(pdf, nsamp);
        vector won = normalize(wo);
        
        for (i = 0; i < nsamp; i += 1) {
            wi[i] = normalize(reflect(-won, N));
            
            // XXX include fresnel stuff here?
            f[i] = color(1,1,1);    
            pdf[i] = 1;
        }
    }
    
    public void eval_bsdf(normal Ns; vector I; vector _L[];
                        uniform float nsamp;
                        output color _f[];
                        output float _pdf[];
                        )
    {
        float i;
        resize(_f, nsamp);
        resize(_pdf, nsamp);
        
        for (i = 0; i < nsamp; i += 1) {
            _f[i] = color(0,0,0);
            _pdf[i] = 0;
        }
    }


    public void surface(output color Ci, Oi)
    {
        shader int = getshader("inte");
        uniform string shadername = "brdf_specular";
        int->integrate(Ci, Oi, shadername);

        //Ci = color(1,0,0);

        // Set Ci and Oi
        Ci *= Os;
        Oi = Os;
        
    }
}
