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
#include "integrator.h"


class pbr_brdf_diffuse (
                  shader shdColor = null;
                  float Kd = 0.5;
                  )
{
    public constant string type = "diffuse";
    shadingGeo SG;
    varying color surfColor = 1;

    public void begin()
    {
        INIT_SG();

        if( shdColor != null )
            surfColor = shdColor->getColor(P);
    }
    
    public color f(varying normal Ns; varying vector wi;)
    {
        color f = (Cs * surfColor)/PI;
        return f;
    }

    public float pdf(normal Ns; vector wi; vector wo;)
    {
        return (wi . Ns)/PI;
    }

    public void sample_bsdf(normal Ns; vector wo; uniform float nsamp;
                            output vector wi[];
                            output color f[];
                            output float pdf[];
                            )
    {    
        float s1, s2, i=0;
        float costheta;
        
        resize(wi, nsamp);
        resize(f, nsamp);
        resize(pdf, nsamp);
        
        for (i = 0; i < nsamp; i += 1) {
            s1 = random();
            s2 = random();
        
            vector v = warp_hemicosine(s1, s2);
            v = align_ortho(normalize(v), Ns, SG->dPdu );

            wi[i] = v;
            f[i] = f(Ns, wi[i]);
            pdf[i] = pdf(Ns, wi[i], I);
        }
    }
    
    public void eval_bsdf(normal Ns; vector I; vector _L[];
                        uniform float nsamp;
                        output color _f[];
                        output float _pdf[];
                        )
    {
        float i;
        vector wo=vector(0,0,0);
        resize(_f, nsamp);
        resize(_pdf, nsamp);
        
        
        for (i = 0; i < nsamp; i += 1) {
            vector wi = normalize(_L[i]);

            if (wi . Ns < 0) {
                _f[i] = color(0,0,0);
                _pdf[i] = 0;
                continue;
            }
            _f[i] = f(Ns, wi);
            _pdf[i] = pdf(Ns, wi, wo);
        }
    }

    public void surface(output color Ci, Oi)
    {
        varying color cc, oo;
        //uniform shader inte = getshader("inte");
        //inte->zintegrate(cc, oo, SG, this);

        integrate(cc, oo, SG, this);

        Ci = cc;
        Oi = oo;
    }
}
