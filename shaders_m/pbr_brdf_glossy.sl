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

//
// Surface shader class definition
//
class pbr_brdf_glossy (
                  uniform string texturename = "";
                  uniform float Kd = 0.5;
                  uniform float roughness=0.5;
                  )
{
    public constant string type = "specular";

    float exp = (2 / (roughness*roughness)) - 2;


    public float D(normal N; vector wh;)
    {
        float costhetah = abs(N . wh);
        float D = (exp+2) * (1/(2*PI)) * pow( max(0, costhetah), exp);
        return D;
    }
    
    /* expects all vector inputs normalised */
    public float G(normal N; vector wi; vector wo; vector wh)
    {
        float ndotwh = wh . N;
        float ndotwo = wo . N;
        float ndotwi = wi . N;
        float wodotwh = abs(wo . wh);
        float g = min(1, min((2*ndotwh*ndotwo / wodotwh),
                             (2*ndotwh*ndotwi / wodotwh)));
        return g;

    }
    
    public float pdf(normal N; vector wi; vector wo)
    {
        vector won = normalize(wo);
        vector win = normalize(wi);
        vector wh = normalize( won + win );
        float costheta = abs(N . wh);
        
        float pdf = ((exp + 1) * pow(costheta, exp)) /
                    (2 * PI * 4 * (wo . wh));
        return pdf;
    }
    
    public float schlick(float costheta) {
        float Rs = 1;    
        float fr = Rs + pow(1-costheta, 5) * (1 - Rs);
        return fr;
    }

    public color f(normal N; vector wi; vector wo)
    {
        vector won = normalize(wo);
        vector win = normalize(wi);
        vector wh = normalize( won + win );

        float costhetaO = abs(won . N);
        float costhetaI = abs(win . N);
        
        float costhetah = win . wh;
        
        float F = schlick(costhetah);
        float geo = G(N, win, won, wh);

        color f = Cs * D(N, wh) * geo * F / (4 * costhetaO * costhetaI);
        return f;
    }

    public void eval_bsdf(normal N; vector I; vector _L[];
                        uniform float nsamp;
                        output color f[];
                        output float pdf[];
                        )
    {
        float i;
        vector wo=normalize(I);
        
        resize(f, nsamp);
        resize(pdf, nsamp);
        
        
        for (i = 0; i < nsamp; i += 1) {
            vector wi = normalize(_L[i]);
            if (wi . N < 0) {
                f[i] = color(0,0,0);
                pdf[i] = 0;
                continue;
            }
            
            f[i] = f(N, wi, wo);
            pdf[i] = pdf(N, wi, wo);
        }
    }
    
    // XXX: Hmmmmmmm
    public void sample_bsdf(normal N; vector wo; uniform float nsamp;
                            output vector wi[];
                            output color f[];
                            output float pdf[];
                            )
    {    
        float s1, s2, i;
        float costheta;
        
        resize(wi, nsamp);
        resize(f, nsamp);
        resize(pdf, nsamp);
        
        vector won = normalize(wo);
        
        for (i = 0; i < nsamp; i += 1) {
            s1 = random();
            s2 = random();
            
            float costheta = pow(s1, 1.0/(exp+1));
            float sintheta = sqrt(max(0, 1-(costheta*costheta)));
            float phi = s2 * 2 * PI;
            
            vector H = spherical_to_cartesian(sintheta, costheta, phi);
            
            H = normalize(align_ortho(H, N, dPdu ));
            
            if (won . H < 0) H = -H;
            
            wi[i] = normalize(reflect(-won, H));
            
            if (wi[i] . N < 0) {
                f[i] = color(0,0,0);
                pdf[i] = 0;
                continue;
            }
            
            pdf[i] = pdf(N, wi[i], won);
            f[i] = f(N, wi[i], won);
        }
    }
    
    public void surface(output color Ci, Oi) {
        
        shader int = getshader("inte");
        uniform string shadername = "brdf_glossy";
        int->integrate(Ci, Oi, shadername);


        
        // Set Ci and Oi
        Ci *= Os;
        Oi = Os;
    }
}