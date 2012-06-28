/*

# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2011 Matt Ebb
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

    3Delight to Blender exporter
    Primary GI light shader: 'photon'

    Uses photon map directly for primary indirect lighting
*/

#pragma annotation intensity "gadgettype=floatfield;label=Intensity;"
#pragma annotation estimator "gadgettype=floatfield;label=Estimator;"

#pragma annotation envmap "gadgettype=inputfile;label=Environment Map;hint=Add image based lighting from this environment."
#pragma annotation envspace "gadgettype=textfield;label=Environment Space;hint=Transformation space of the environment map"
#pragma annotation env_samples "gadgettype=floatfield;label=Environment Samples;hint=Samples to take from environment map when casting environment photons;"

#pragma annotation __nonspecular "hide=true;"

light gi_photon(
	float intensity = 1.0;
    float estimator = 500;
    
    float env_samples = 32;
    
    string envmap = "", envspace = "world";

    float __nonspecular = 1;
    )
{
    uniform string raytype="";
    rayinfo( "type", raytype );
    
    if( raytype == "light" )
	{
        
        uniform string gather_cat = concat("environment:", envmap);
        vector envdir = 0;
    	color Cenv = 0;
        float solidangle = 0;
        
		gather(
			gather_cat, 0, 0, 0, env_samples,
			"environment:color", Cenv,
			"environment:direction", envdir,
			"environment:solidangle", solidangle )
		{
			envdir = vtransform( envspace, "current", envdir );

			/* Convert from solid angle to angle */
			solar( -envdir, acos( 1-solidangle/(2*PI) ))
			{
				Cl = intensity * (Cenv / (4*PI));
			}
		}
	}
    else
    {
    	normal Nn = normalize( Ns );
    
    	illuminate( Ps + Nn ) /* shade all surface points */
    	{
    		Cl = 0;
    
    		if( intensity > 0.0 )
    		{
                uniform string pmapname;
                attribute("photon:globalmap", pmapname);
                
                Cl = photonmap(pmapname, Ps, Ns,
                    "estimator", estimator,
                    "lookuptype", "irradiance",
                    "mindepth", 0
                    );
    
                Cl *= intensity;
    		}
    	}
    }
}