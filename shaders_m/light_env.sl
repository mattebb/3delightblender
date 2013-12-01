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
light_env(
    uniform float intensity = 1;
    uniform color lightcolor = 1;
    uniform string texturename = "";
    uniform float nu=512;
    uniform float nv=256;
    )

{
    public constant float isdelta = 0;
    public constant float shadowtype = SHADOW_RAYTRACE;

    uniform float pdfv[] = 0;
    uniform float cdfv[] = 0;

    uniform float pdfu[] = 0;
    uniform float cdfu[] = 0;

    uniform float sinvals[] = 0;
    uniform point pts[];

    uniform point center = point "shader" (0,0,0);
    uniform vector udir = vector "shader" (1,0,0);
    uniform vector vdir = vector "shader" (0,1,0);
    uniform vector zdir = vector "shader" (0,0,-1);   // direction of light

    void makecol(output float col[]; float sinvals[]; float u;){
        float j;
        float s, t;
        float ds = 1/nu;
        float dt = 1/nv;

        for (j=0; j<nv; j+=1) {
            s = u * ds;
            t = j * dt;
            col[j] = sinvals[j] * lum( texture(texturename, s,t, s+ds,t, s+ds,t+dt, s,t+dt) );
        }
    }

    void precompute1d(float f[]; float n, u; output float pdf[], cdf[]; output float colsum; ) {
        float i;
        float sum=0;
        float ofsp = u*nv;      // offset into pdf array, (for v, stored column by column)
        float ofsc = u*(nv+1);  // offset into cdf array, (for v, stored column by column)

        // sum
        for (i=0; i<n; i+=1) {
            sum += f[i];
        }

        // pdf
        for (i=0; i<n; i+=1) {
            pdf[ofsp+i] = f[i] / sum;
        }

        // accumulate cdf
        cdf[ofsc + 0] = 0;
        for (i=1; i<n; i+=1) {
            cdf[ofsc + i] = cdf[ofsc + i-1] + pdf[ofsp + i-1];
        }
        cdf[ofsc + n] = 1;

        colsum = sum;
    }

    float lsearch(float ar[]; float ofs; float n; float x;)
    {
        float i;
        for (i=0; i<n-1; i+=1) {
            if (ar[ofs + i + 1] > x)
            break;
        }
        return i;
    }
    
    // binary search
    float search(float ar[]; float ofs; float n; float x;)
    {
        float low = ofs + 0;
        float high = ofs + n;
        float m;

        while ( low <= high ){
            m = floor((low+high)/2);

            if (ar[m] > x) {
                high = m-1;
            }
            else if (ar[m] < x) {
                if (ar[m+1] > x)
                return m - ofs;

                low = m+1;
            }
            else
            return m - ofs;
        }
        return -1;
    }

    void sample1d(float pdf[], cdf[]; float iu, n; float rnd; output float x, p;)
    {
        float i, w;
        float ofsp = iu*n;
        float ofsc = iu*(n+1);
        
        // find intersection of random number with CDF
        i = search(cdf, ofsc, n, rnd);

        // linear interpolation weight
        w = (cdf[ofsc + i+1] - rnd) / (cdf[ofsc+ i+1] - cdf[ofsc + i]);

        // find interpolated position along array
        //x = (1-w)*i + w*(i+1); // from paper... doesn't seem right?
        x = (i + (1-w)) / n;

        // return found pdf
        p = pdf[ofsp + i];
    }

    public void construct() {

        /* only do importance precalculation if there's an environment map */
        if (texturename == "") return;

        uniform float i;
        uniform float colsum[nu];
        uniform float sum;

        resize(pdfv, nu*nv);
        resize(cdfv, nu*(nv+1));
        resize(pdfu, nu);
        resize(cdfu, nu+1);
        
        // precompute values of sin theta
        resize(sinvals, nv);
        for (i=0; i<nv; i+=1) {        
            sinvals[i] = sin(PI * (i+0.5)/nv);
        }

        for (i=0; i<nu; i+=1) {
            uniform float col[nv];
            makecol(col, sinvals, i);
            precompute1d(col, nv, i, pdfv, cdfv, colsum[i]);
        }
        precompute1d(colsum, nu, 0, pdfu, cdfu, sum);
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
            _pdf[i] = 1/(2*PI);
            _L[i] = wi[i] * SCENE_BOUNDS;
            _Li[i] = Le(P, _L[i]);
        }
    }
    
    public void lightddd( output vector L;         // unused
                       output color Cl;         // unused
                       varying normal Ns;
                       output color _Li[];
                       output vector _L[];
                       output float _pdf[];
                       uniform float nsamples;
                       )
    {
        vector rnd;
        varying point samplepos;
        varying float r1, r2;
        uniform float s;
        
        resize(_Li, nsamples);
        resize(_L, nsamples);
        resize(_pdf, nsamples);

        color Le;
        color black=0;

        // if no environment map, use cosine weighted sampling
        if (texturename == "") {
            for (s = 0; s < nsamples; s += 1) {
                r1 = random();
                r2 = random();

                vector l = warp_hemicosine(r1, r2);                
                // cosine weighted full sphere sampling
                //if (random() < 0.5)
                //    l[2] *= -1 ;

                _L[s] = align_ortho(l, Ns, dPdu );
                _pdf[s] = (_L[s] . Ns) / PI;    //(2*PI)
                _L[s] *= SCENE_BOUNDS;

                _Li[s] = lightcolor * intensity;
            }

        // else use importance sampling
        } else {
            for (s = 0; s < nsamples; s += 1) {
                r1 = random();
                r2 = random();

                float su=0, sv=0;
                float pu=0, pv=0;
                float vi;

                sample1d(pdfu, cdfu, 0,  nu, r1, su, pu);
                sample1d(pdfv, cdfv, floor(su*(nu-1)), nv, r2, sv, pv);

                if (sv == 0 || sv == 1)
                    _pdf[s] = 0;
                else
                    _pdf[s] = (pu * pv) * (nu*nv / (2*PI*PI* sinvals[sv*nv]));

                float phi = su*2*PI;
                float theta = sv*PI;
                vector l = spherical_to_cartesian(sin(theta), cos(theta), phi);
                
                _L[s] = align_ortho(l, -zdir, vdir ) * SCENE_BOUNDS;

                _Li[s] = texture(texturename, su,sv,su,sv,su,sv,su,sv);

            }
        }
        
       // Clear L and Cl, even though they're unused.
       L = (0,0,0);
       Cl = (0,0,0);
   }

   public void light( output vector L;
                       output color Cl;
                       )
    {
        vector rnd;
        varying point samplepos;
        varying float r1, r2;
        uniform float s;
        color Le;
        color black=0;

        L = vector(random(), random(), random());
        float vis = trace(P, L);
        Cl = 1.0 * vis;
   }
}