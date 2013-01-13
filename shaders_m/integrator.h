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

// integrator.h

#ifndef integrator_h
#define integrator_h

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

void integrate(output varying color Ci, Oi;
                        shadingGeo SG;
                        uniform shader shd) {

    shader IS = getshader("inte");

    uniform float minsamples = IS->minsamples;
    uniform float maxsamples = IS->maxsamples;
    uniform float diffuse_bounces = IS->diffuse_bounces;
    uniform float diffuse_factor = IS->diffuse_factor;
    uniform float specular_bounces = IS->specular_bounces;
    uniform float specular_factor = IS->specular_factor;
    uniform float transmission_bounces = IS->transmission_bounces;
    uniform float transmission_factor = IS->transmission_factor;
    uniform float sample_light = IS->sample_light;
    uniform float sample_bsdf = IS->sample_bsdf;
    uniform float indirect_sample_factor = IS->indirect_sample_factor;

    uniform float ray_depth;
    uniform float diffuse_depth;
    uniform float specular_depth;
    uniform float transmission_depth;

    rayinfo("depth", ray_depth);
    rayinfo("diffusedepth", diffuse_depth);
    rayinfo("speculardepth", specular_depth);
    rayinfo("shadowdepth", transmission_depth);
 
    Oi = 1.0;
    varying normal Ns = SG->Ns;
    varying point P = SG->P;
    varying vector I = SG->I;
    varying float i=0, s=0;

    shader lights[] = getlights();
    uniform float nlights = arraylength(lights);

    uniform color black = color(0,0,0);

    varying vector L;   // unused
    varying color Cl;   // unused
    
    varying vector wo = -I;
    
    // for sampling light        
    varying vector _l_L[]; // P -> light sampled vector
    varying float _l_pdf[]; // light sampled pdf
    varying color _l_Li[];  // light sampled value

    varying color _l_bsdf_f[];  // corresponding bsdf value
    varying float _l_bsdf_pdf[];    // corresponding bsdf pdf

    // for sampling bsdf
    varying vector _b_wi[];    // P -> light bsdf sampled outgoing direction
    varying float _b_pdf[];    // bsdf sampled pdf
    varying color _b_f[];      // bsdf sampled value
    
    varying vector _b_L[];     // corresponding P -> light sampled vector
    varying color _b_Li[];     // corresponding light value
    varying float _b_Lpdf[];   // corresponding light pdf

    varying color _l_vis[];     // visibility
    varying color _b_vis[];     // visibility

    

    varying float area = area(transform("raster", P), "dicing");
               
    uniform float mis_sample_light = sample_light;
    uniform float mis_sample_bsdf = sample_bsdf;
    if (shd->type == "DIFFUSE")
        mis_sample_bsdf = 0;
    else if (shd->type == "SPECULAR")
        mis_sample_light = 0;

    varying float max_samples = clamp((maxsamples*area), minsamples, maxsamples);
    //uniform float max_samples = maxsamples;

    if (ray_depth > 0 )
        max_samples = indirect_sample_factor / ray_depth;

    varying float samples[max_samples];

    varying color CLi;
    varying color Cdirect=0;

    // Sample the light
    for (i = 0; i < nlights; i += 1) {
        CLi = color(0);

        if (mis_sample_light == 1 ) {
            lights[i]->light(L, Cl, Ns, _l_Li, _l_L, _l_pdf, maxsamples);
            shd->eval_bsdf(Ns, wo, _l_L, maxsamples, _l_bsdf_f, _l_bsdf_pdf);
        }
        if (mis_sample_bsdf == 1 ) {
            shd->sample_bsdf(Ns, wo, maxsamples, _b_wi, _b_f, _b_pdf);
            lights[i]->eval_light(P, _b_wi, maxsamples, _b_L, _b_Li, _b_Lpdf);
        }
        
        varying float samples_taken = 0;
        varying point Pt;
        
        for (s = 0; s < max_samples; s += 1) {
            varying color Csamp = color(0,0,0);
            extern float du;
            extern float dv;

            // Jitter across micropolygon area for anti-aliasing
            Pt = P + (float random()-0.5)*Du(P)*du + (float random()-0.5)*Dv(P)*dv;

            if (0) { //mis_sample_light == 1) {
                // MIS: sampling light
                if (_l_Li[s] != black && _l_bsdf_f[s] != black && _l_pdf[s] > 0) {
                
                    varying color Li = _l_Li[s];// * visibility(Pt, _l_L[s], lights[i]);
                    varying float dot_i = abs(normalize(_l_L[s]) . Ns);
                    varying float weight;
                    uniform float isdelta = lights[i]->isdelta;
                    
                    if (isdelta == 1)
                        weight = 1;
                    if (mis_sample_light == 1 && mis_sample_bsdf == 0)
                        weight = 1;
                    else
                        weight = power(1, _l_pdf[s], 1, _l_bsdf_pdf[s]);
                    weight = 1;

                    Csamp += _l_bsdf_f[s];// * Li * dot_i * weight / _l_pdf[s];
                    
                }
            }
            
            if (mis_sample_bsdf == 1) {
            
                // MIS: sampling BSDF
                if (lights[i]->isdelta != 1 && _b_f[s] != black && _b_pdf[s] > 0) {
                    if (_b_Lpdf[s] > 0) {
                        varying color Li = _b_Li[s];// * visibility(Pt, _b_L[s], lights[i]);
                        varying float dot_i = abs(normalize(_b_L[s]) . Ns);
                        varying float weight = power(1, _b_pdf[s], 1, _b_Lpdf[s]);
                        if (mis_sample_light == 0 && mis_sample_bsdf == 1)
                            weight = 1;
                        weight = 1;
                        
                        Csamp += _b_f[s];// * Li * dot_i * weight / _b_pdf[s]; 
                    }
                }
            }

            CLi += Csamp;
            samples_taken += 1;
        }

        Cdirect += CLi / samples_taken;

    }

    uniform float trace_indirect=0;
    if (shd->type == "diffuse" && diffuse_depth < diffuse_bounces)
        trace_indirect = 1;
    else if (shd->type == "specular" && specular_depth < specular_bounces)
        trace_indirect = 1;
    else if (shd->type == "transmission" && transmission_depth < transmission_bounces)
        trace_indirect = 1;

    varying color Cindirect=0;
    if (trace_indirect){
        //varying color 
        CLi = 0;
        //uniform float indirect_samples = max_samples * indirect_sample_factor;
        shd->sample_bsdf(Ns, wo, maxsamples, _b_wi, _b_f, _b_pdf);

        for (s = 0; s < max_samples; s += 1) {
            if (_b_f[s] != black && _b_pdf[s] > 0) {
                varying color Li = trace(P, _b_wi[s], "raytype", shd->type);
                
                varying float dot_i = abs(normalize(_b_wi[s]) . Ns);
                CLi += _b_f[s] * Li * dot_i / _b_pdf[s];
            }
        }
        Cindirect += CLi / max_samples;
    }

    // Set Ci and Oi
    Ci = Cdirect + Cindirect;    
    Oi = 1;
}

#endif