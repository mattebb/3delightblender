#include "./struct.h"


// ANNOTATIONS 
#pragma annotation tint "gadgettype=colorslider"
#pragma annotation surfcolormix "gadgettype=floatslider;min=0;max=1"
#pragma annotation Kenv "gadgettype=floatfield"
#pragma annotation Kocc "gadgettype=floatslider;min=0;max=1"
#pragma annotation envmap "gadgettype=textfield"
#pragma annotation envmap "gadgettype=textfield"
#pragma annotation samples "gadgettype=intfield"
#pragma annotation maxdist "gadgettype=floatfield"
#pragma annotation bias "gadgettype=floatfield"


// ripped off of envlight2.sl

class brdf_env(
    color tint = 1;
    float surfcolormix = 0;
    float Kenv = 1;
    float Kocc = 1;
    string envmap = "";
    string envspace = "world";
	float samples = 64; 
	float maxdist = 1e10;
	float bias = -1;
)
{
    public color getBrdf( Pstrc shdP )
    {    
        // init
        normal shading_normal = shdP->Nn;
        point Ps = shdP->P;
        uniform string gather_cat = concat("environment:", envmap);
		uniform float t1 = 0.025 * sqrt(samples);
		uniform float t2 = 0.05 * sqrt(samples);
        vector raydir = 0;
        color envcolor = 0;
        vector envdir = 0;
        float solidangle = 0;
        color c = 0;

		gather(
			gather_cat, point(0), vector(0), 0, samples,
			"environment:color", envcolor,
			"ray:direction", raydir,
			"environment:direction", envdir,
			"environment:solidangle", solidangle )
		{
			raydir = vtransform( envspace, "current", raydir );
			envdir = vtransform( envspace, "current", envdir );

			float atten = max( shading_normal . normalize(envdir), 0 );

			float kocc = 1 - smoothstep( t1, t2, solidangle );
			kocc *= Kocc;

			color trs = 1;
			if( kocc > 0 && atten > 0 )
			{
				trs = transmission( Ps, Ps + raydir * maxdist, "bias", bias );
				trs = 1 - kocc * (1 - trs);
			}

			c += envcolor * trs * atten * tint / (4*PI);
		}
        if( surfcolormix > 0 )
            c = mix( c, c*shdP->Col, surfcolormix );
		
        return c * Kenv * shdP->kenv;
    }
}
