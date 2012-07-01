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

#pragma annotation visibility "False"

#include "util.h"

class integrator(
    float minsamples = 16;
    float maxsamples = 32;
    float diffuse_bounces = 0;
    )
{
    /* to get parameters picked up */
    public void surface(output color Ci, Oi) { }


    color visibility(point Pt; vector V; float shadowtype; string shadowmap;)
    {
        color Cv;
        if (shadowtype == 0) {  // raytrace
            Cv = transmission(Pt, Pt+V);
        }
        else if (shadowtype == 1) { // shadow map
            Cv = color(1) - shadow(shadowmap, Pt);
        }
        return Cv;
    }

    public void begin() {


    }

    public void integrate(output color Ci, Oi;
                        uniform string shadername) {
 
        varying normal Ns = shadingnormal(N);
        vector In = normalize(I);
        vector Ln;

        varying color Cdirect=0, tr=0;
        uniform float i, s;

        shader lights[] = getlights();
        uniform float nlights = arraylength(lights);

        uniform float ray_depth;
        rayinfo( "depth", ray_depth );

        color black = color(0,0,0);
        color bsdf_f;
        float bsdf_pdf;

        vector L;   // unused
        color Cl;   // unused
        color CLi;
        Ci=0;
        vector wi;
        varying vector wo = -I;
        

        // for sampling light        
        vector _l_L[]; // P -> light sampled vector
        float _l_pdf[]; // light sampled pdf
        color _l_Li[];  // light sampled value

        color _l_bsdf_f[];  // corresponding bsdf value
        float _l_bsdf_pdf[];    // corresponding bsdf pdf

        // for sampling bsdf
        vector _bl_wi[];    // P -> light bsdf sampled outgoing direction
        float _bl_pdf[];    // bsdf sampled pdf
        color _bl_f[];      // bsdf sampled value
        
        vector _bl_L[];     // corresponding P -> light sampled vector
        color _bl_Li[];     // corresponding light value
        float _bl_Lpdf[];   // corresponding light pdf

        color _l_vis[];     // visibility
        color _bl_vis[];     // visibility

        shader shd = getshader(shadername);

        if (ray_depth > 2)
            return;

        varying float area = area(transform("raster", P), "dicing");

#if 1
                   
        float sample_lamp = 1;
        float sample_brdf = 1;

        uniform float nsamples=maxsamples;
        varying float max_samples = clamp((nsamples*area), minsamples, nsamples);

        varying float samples[max_samples];

        // Sample the light
        for (i = 0; i < nlights; i += 1) {
            CLi = 0;
            
            if (ray_depth > 0 )
                max_samples = nsamples = 1;

            if (sample_lamp ==1 ) {
            lights[i]->light(L, Cl, Ns, _l_Li, _l_L, _l_pdf, "nsamp", nsamples);
            shd->eval_bsdf(Ns, wo, _l_L, nsamples, _l_bsdf_f, _l_bsdf_pdf);
            //lights[i]->visibility(P, _l_L, _l_pdf, _l_Li, nsamples, _l_vis);
            }

            if (sample_brdf ==1 ) {
            shd->sample_bsdf(Ns, wo, nsamples, _bl_wi, _bl_f, _bl_pdf);
            lights[i]->eval_light(P, _bl_wi, nsamples, _bl_L, _bl_Li, _bl_Lpdf);
            //lights[i]->visibility(P, _bl_L, _bl_pdf, _bl_Li, nsamples, _bl_vis);
            }

            uniform string smap = lights[i]->smap;
            uniform float stype = lights[i]->stype;
            //if (ray_depth > 0)
            //    stype = 1;

            varying point Pt = P;
            varying float samples_taken = 0;

            for (s = 0; s < max_samples; s += 1) {
                color Csamp=0;

                // Jitter across micropolygon area for anti-aliasing
                Pt = P + (float random()-0.5)*Du(P)*du + (float random()-0.5)*Dv(P)*dv;

                if (sample_lamp == 1) {
                
                // MIS: sampling light
                if (_l_Li[s] != black && _l_pdf[s] > 0) {
                
                    if (_l_bsdf_f[s] != black) {
                        //varying color Li = _l_Li[s] * transmission(Pt, Pt + _l_L[s]);
                        varying color Li = _l_Li[s] * visibility(Pt, _l_L[s],stype,smap);
                        //varying color Li = _l_Li[s] * lights[i]->vis(Pt, _l_L[s]);
                        //varying color Li = _l_Li[s] * _l_vis[s];
                        
                        float dot_i = normalize(_l_L[s]) . Ns;
                        
                        varying float weight;
                        if (sample_lamp == 1 && sample_brdf == 0)
                            weight = 1;
                        if (lights[i]->isdelta == 1)
                            weight = 1;
                        else
                            weight = power(1, _l_pdf[s], 1, _l_bsdf_pdf[s]);
                        
                        Csamp += _l_bsdf_f[s] * Li * dot_i * weight / _l_pdf[s];
                    }
                }
                }
                
                if (sample_brdf == 1) {
                
                // MIS: sampling BSDF
                if (lights[i]->isdelta != 1 && _bl_f[s] != black && _bl_pdf[s] > 0) {
                    if (_bl_Lpdf[s] > 0) {
                        varying color Li = _bl_Li[s] * transmission(Pt, Pt + _bl_L[s]);
                        //varying color Li = _l_Li[s] * visibility(Pt, _l_L[s],stype,smap);
                        //varying color Li = _l_Li[s] * lights[i]->vis(Pt, _bl_L[s]);
                        //varying color Li = _bl_Li[s] * _bl_vis[s];

                        float dot_i = normalize(_bl_L[s]) . Ns;
                        varying float weight = power(1, _bl_pdf[s], 1, _bl_Lpdf[s]);
                        
                        if (sample_lamp == 0 && sample_brdf == 1)
                            weight = 1;
                        
                        Csamp += _bl_f[s] * Li * dot_i * weight / _bl_pdf[s]; 
                    }
                }
                }

                

                samples_taken += 1;

                CLi += Csamp;

                #if 0
                samples[s] = lum(Csamp);
                varying float j;
                varying float Lavg=0;
                for (j=0; j<s; j+=1) {
                    Lavg += samples[j];
                }
                Lavg /= s;
                varying float breakloop= 0;
                varying float maxContrast=0.0001;
                for (j=0; j<s; j+=1) {
                    if (abs(samples[s] - Lavg) / Lavg < maxContrast) {
                        breakloop = 1;
                        break;
                    }
                }
                if (breakloop) break;
                #endif

                #if 0
                // adaptive sampling
                if (samples_taken > max_samples/2) {
                    color mean =  CLi / samples_taken;
                    color var = (CLisq / samples_taken) - mean*mean;
                    if (lum(var) < 0.0001) break;
                    Cvar += var;
                }
                #endif


            }
            Ci += CLi / samples_taken;
            //Ci = (samples_taken/max_samples);
            //Ci = mix(Ci, ctransform("HSV", "RGB", color((s/max_samples)*0.5,1,1)) , 0.1);
        }



        if (ray_depth < diffuse_bounces) {
            CLi = 0;
            
            shd->sample_bsdf(Ns, wo, nsamples, _bl_wi, _bl_f, _bl_pdf);

            for (s = 0; s < nsamples; s += 1) {
                if (_bl_f[s] != black && _bl_pdf[s] > 0) {
                    color Li = trace(P, _bl_wi[s]);
                    
                    float dot_i = normalize(_bl_wi[s]) . Ns;
                    CLi += _bl_f[s] * Li * dot_i / _bl_pdf[s];
                }
            }
            Ci += CLi / nsamples;
        }
                
        // Set Ci and Oi
        Ci *= Os;
        Oi = Os;
        
        
#endif
    }

}