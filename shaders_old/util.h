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

// util.h

#ifndef util_h
#define util_h

#define SHADOW_RAYTRACE     0
#define SHADOW_MAP          1

#define SCENE_BOUNDS    999999

struct shadingGeo{
    varying point P = 0;
    varying normal Ns = 0;
    varying color Cs = 0;
    varying vector dPdu = 0;
    varying vector dPdv = 0;
    varying vector I = 0;
}


// Compute normalized shading normal with appropriate orientation.
// We ensure that the normal faces forward if Sides is 2 or if the
// shader evaluation is caused by a ray hit.
//
normal
shadingnormal(normal N)
{
    extern vector I;
    normal Ns = normalize(N);
    /*
    uniform float sides = 2;
    uniform float raydepth;
    attribute("Sides", sides);
    rayinfo("depth", raydepth);
    if (sides == 2 || raydepth > 0)
        Ns = faceforward(Ns, I, Ns);
    */
    return Ns;
}


#define INIT_SG() {             \
    SG->P = P;                  \
    SG->Ns = shadingnormal(N);  \
    SG->I = I;                  \
    SG->dPdu = dPdu;            \
    SG->dPdv = dPdv;            \
    SG->Cs = Cs;                \
}

void sample2d_stratified(float nsamples; output float s1[], s2[];)
{
    // Compute the number of strata in r and phi directions.
    // For optimal stratification, there should be three to four
    // times as many phi strata as r strata.
    rstrata = floor(0.5 * sqrt(samples));
    phistrata = floor(samples / rstrata);
    stratifiedsamples = rstrata * phistrata;
    remainingsamples = samples - stratifiedsamples;

    // Generate fully stratified directions
    for (rs = 0; rs < rstrata; rs += 1) {
	for (ps = 0; ps < phistrata; ps += 1) {
            // Pick a point within stratum (rs,ps) on the unit disk
	    rnd = (rs + random()) / rstrata;
            r = sqrt(rnd);
	    rnd = (ps + random()) / phistrata;
            phi = 2 * 3.141592 * rnd;

            // Project point onto unit hemisphere
            S[0] = r * cos(phi);
            S[1] = r * sin(phi);
            S[2] = sqrt(1 - r*r);

  	    // Convert to a direction on the hemisphere defined by the normal
            S = S[0] * udir + S[1] * vdir + S[2] * ndir;
            Cindir += trace(P, S)  * clamp(ndir . normalize(S), 0, 1);
  
	}
    }

}

#if 0
void halton_sample(double *ht_invprimes, double *ht_nums, double *v)
{
	// incremental halton sequence generator, from:
	// "Instant Radiosity", Keller A.
	unsigned int i;
	
	for (i = 0; i < 2; i++)
	{
		double r = fabs((1.0 - ht_nums[i]) - 1e-10);
		
		if (ht_invprimes[i] >= r)
		{
			double lasth;
			double h = ht_invprimes[i];
			
			do {
				lasth = h;
				h *= ht_invprimes[i];
			} while (h >= r);
			
			ht_nums[i] += ((lasth + h) - 1.0);
		}
		else
			ht_nums[i] += ht_invprimes[i];
		
		v[i] = (float)ht_nums[i];
	}
}
#endif


float lum(color C)
{
    return 0.2126*C[0] + 0.7152*C[1] + 0.0722*C[2];
}

float lengthsq(vector V)
{
    return V[0]*V[0] + V[1]*V[1] + V[2]*V[2];
}

float power(float nf; float fPdf; float ng; float gPdf)
{
    float f = nf * fPdf;
    float g = ng * gPdf;
    float result = (f*f) / (f*f + g*g);
    return result;
}

vector warp_hemicosine(float s1; float s2)
{
    float phi = s1*2*PI;
    float sqr = sqrt(s2);
    vector S;
    
	S[0] = cos(phi) * sqr;
	S[1] = sin(phi) * sqr;
	S[2] = sqrt(max(0.0, 1.0-S[0]*S[0] - S[1]*S[1]));
    
    return S;
}

vector warp_hemi(float s1; float s2)
{
    float phi = 2 * PI * s1;	
	float sqr = sqrt( max(0, (1 - s2*s2)) );
    vector S;
	
	S[0] = cos(phi) * sqr;
	S[1] = sin(phi) * sqr;
	S[2] = s2;

    return S;
}

vector warp_disc(float s1; float s2)
{
    float phi = 2 * PI * s1;	
	float sqr = sqrt( s2 );
    vector S;
	
	S[0] = cos(phi) * sqr;
	S[1] = sin(phi) * sqr;
	S[2] = 0;

    return S;
}

vector warp_cone(float s1; float s2; float costhetamax; vector udir; vector vdir; vector zdir;)
{
    float costheta = mix(costhetamax, 1, s1);
    float sintheta = sqrt(1 - costheta*costheta);
    float phi = 2 * PI * s2;    
    vector S = cos(phi) * sintheta * udir + sin(phi) * sintheta * vdir +
        costheta * zdir;
    return S;
}

/*
Vector UniformSampleCone(float u1, float u2, float costhetamax,
        const Vector &x, const Vector &y, const Vector &z) {
    float costheta = Lerp(u1, costhetamax, 1.f);
    float sintheta = sqrtf(1.f - costheta*costheta);
    float phi = u2 * 2.f * M_PI;
    return cosf(phi) * sintheta * x + sinf(phi) * sintheta * y +
        costheta * z;
}
*/


vector spherical_to_cartesian(float sintheta; float costheta; float phi;)
{
    vector V = vector(sintheta*cos(phi), sintheta*sin(phi), costheta);
    return V;
}

//assumes normalised vec
void cartesian_to_spherical(vector vec; output float phi; output float theta;)
{
    theta = acos(vec[2]);
    float p = atan(vec[0], vec[1]);
    if (p < 0)
        phi = p + 2*PI;
    else
        phi = p;
}

void cartesian_to_spherical_uv(vector vec; output float u; output float v;)
{
    v = (acos(vec[2]) * 0.5) + 0.5;

    float p = atan(vec[1], vec[0]) * (0.5/PI);    // range [-0.5,0.5]
    if (p < 0)
        u = p + 0.5;
    else
        u = p;
}

vector align_ortho(vector v; normal N; vector u)
{
    vector ndir = vector(N), udir = normalize(u), vdir;
    vector v_out;
    
    udir = udir - (N.udir) * N; // project udir onto plane perp. to normal
    normalize(udir);
    vdir = N ^ udir;
    
    v_out = v[0] * udir + v[1] * vdir + v[2] * ndir;
    return v_out;
}


#endif