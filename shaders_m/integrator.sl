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

    public void integrate(output color Ci, Oi;
                        uniform shader shd) {
 
        
        varying normal Ns = shadingnormal(N);
        uniform float i, s;

        shader lights[] = getlights();
        uniform float nlights = arraylength(lights);

        color black = color(0,0,0);

        vector L;   // unused
        color Cl;   // unused
        Ci=0;

        //Ci = shd->mycolor();
        //Ci = myc;
        //Oi = 1;
        //return;


        varying vector wo = -I;
        
        // for sampling light        
        varying vector _l_L[]; // P -> light sampled vector
        varying float _l_pdf[]; // light sampled pdf
        varying color _l_Li[];  // light sampled value

        varying color _l_bsdf_f[];  // corresponding bsdf value
        varying float _l_bsdf_pdf[];    // corresponding bsdf pdf

        // for sampling bsdf
        varying vector _bl_wi[];    // P -> light bsdf sampled outgoing direction
        varying float _bl_pdf[];    // bsdf sampled pdf
        varying color _bl_f[];      // bsdf sampled value
        
        varying vector _bl_L[];     // corresponding P -> light sampled vector
        varying color _bl_Li[];     // corresponding light value
        varying float _bl_Lpdf[];   // corresponding light pdf

        varying color _l_vis[];     // visibility
        varying color _bl_vis[];     // visibility

        

        varying float area = area(transform("raster", P), "dicing");
                   
        float mis_sample_light = sample_light;
        float mis_sample_bsdf = sample_bsdf;
        if (shd->type == "DIFFUSE")
            mis_sample_bsdf = 0;
        else if (shd->type == "SPECULAR")
            mis_sample_light = 0;

        //varying float max_samples = clamp((maxsamples*area), minsamples, maxsamples);
        uniform float max_samples = maxsamples;

        if (ray_depth > 0 )
            max_samples = 2; //indirect_sample_factor / ray_depth;

        varying float samples[max_samples];

        // Sample the light
        for (i = 0; i < nlights; i += 1) {
            color CLi = 0;
            
            if (mis_sample_light == 1 ) {
                lights[i]->light(L, Cl, Ns, _l_Li, _l_L, _l_pdf, "nsamp", max_samples);
                shd->eval_bsdf(Ns, wo, _l_L, max_samples, _l_bsdf_f, _l_bsdf_pdf);
            }
            if (mis_sample_bsdf == 1 ) {
                shd->sample_bsdf(Ns, wo, max_samples, _bl_wi, _bl_f, _bl_pdf);
                lights[i]->eval_light(P, _bl_wi, max_samples, _bl_L, _bl_Li, _bl_Lpdf);
            }

            varying float samples_taken = 0;
            varying point Pt;

            for (s = 0; s < max_samples; s += 1) {
                varying color Csamp=0;

                // Jitter across micropolygon area for anti-aliasing
                Pt = P + (float random()-0.5)*Du(P)*du + (float random()-0.5)*Dv(P)*dv;

                if (mis_sample_light == 1) {
                
                    // MIS: sampling light
                    if (_l_Li[s] != black && _l_pdf[s] > 0) {
                    
                        if (_l_bsdf_f[s] != black) {
                            varying color Li = _l_Li[s] * visibility(Pt, _l_L[s], lights[i]);
                            
                            float dot_i = abs(normalize(_l_L[s]) . Ns);
                            
                            varying float weight;
                            uniform float isdelta = lights[i]->isdelta;
                            
                            if (isdelta == 1)
                                weight = 1;
                            if (mis_sample_light == 1 && mis_sample_bsdf == 0)
                                weight = 1;
                            else
                                weight = power(1, _l_pdf[s], 1, _l_bsdf_pdf[s]);
                            
                            Csamp += _l_bsdf_f[s] * Li * dot_i * weight / _l_pdf[s];
                        }
                    }
                }
                
                if (mis_sample_bsdf == 1) {
                
                    // MIS: sampling BSDF
                    if (lights[i]->isdelta != 1 && _bl_f[s] != black && _bl_pdf[s] > 0) {
                        if (_bl_Lpdf[s] > 0) {
                            varying color Li = _l_Li[s] * visibility(Pt, _l_L[s], lights[i]);
                            
                            float dot_i = abs(normalize(_bl_L[s]) . Ns);

                            varying float weight = power(1, _bl_pdf[s], 1, _bl_Lpdf[s]);
                            
                            if (mis_sample_light == 0 && mis_sample_bsdf == 1)
                                weight = 1;
                            
                            Csamp += _bl_f[s] * Li * dot_i * weight / _bl_pdf[s]; 
                        }
                    }
                }

                samples_taken += 1;
                CLi += Csamp;
            }
            Ci += CLi / samples_taken;
        }

        /*

        uniform float trace_indirect=0;
        if (shd->type == "diffuse" && diffuse_depth < diffuse_bounces)
            trace_indirect = 1;
        else if (shd->type == "specular" && specular_depth < specular_bounces)
            trace_indirect = 1;
        else if (shd->type == "transmission" && transmission_depth < transmission_bounces)
            trace_indirect = 1;

        if (trace_indirect){
            color CLi = 0;
            
            shd->sample_bsdf(Ns, wo, max_samples, _bl_wi, _bl_f, _bl_pdf);

            for (s = 0; s < max_samples; s += 1) {
                if (_bl_f[s] != black && _bl_pdf[s] > 0) {
                    color Li = trace(P, _bl_wi[s], "raytype", shd->type);
                    
                    float dot_i = abs(normalize(_bl_wi[s]) . Ns);
                    CLi += _bl_f[s] * Li * dot_i / _bl_pdf[s];
                }
            }
            Ci += CLi / max_samples;
        }
        */

        // Set Ci and Oi
        Ci *= Os;
        Oi = Os;
    }

}