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
    Primary GI light shader: 'raytrace'

    Can be used for 'final gathering' style lighting, either with a photon map, 
    or on its own directly sampling geometry.
*/

#pragma annotation intensity "gadgettype=floatfield;label=Intensity;"
#pragma annotation samples "gadgettype=floatfield;label=Samples;"
#pragma annotation maxdist "gadgettype=floatfield;label=Max Distance;"
#pragma annotation falloffmode "gadgettype=optionmenu:Exponential:Polynomial;label=Falloff Type;hint=Method for calculating falloff from incoming light;"
#pragma annotation falloff "gadgettype=floatfield;label=Falloff;hint=Strength of falloff effect"

#pragma annotation envmap "gadgettype=inputfile;label=Environment Map;hint=Add image based lighting from this environment."
#pragma annotation envspace "gadgettype=textfield;label=Environment Space;hint=Transformation space of the environment map"

#pragma annotation __nonspecular "hide=true;"

light gi_raytrace(
	float intensity = 1.0;
	float samples = 16;
	float maxdist = 100000;

    float falloffmode = 0, falloff = 0;
    
    string envmap = "", envspace = "world";

    float __nonspecular = 1;
    )
{
	normal Nn = normalize( Ns );

	illuminate( Ps + Nn ) /* shade all surface points */
	{
		Cl = 0;

		if( intensity > 0.0 )
		{
            uniform float minsamples = samples/2;
            
            color Cenv;
            
            Cl = indirectdiffuse(Ps, Ns, samples,
                "maxdist", maxdist,
                "environmentmap", envmap,
                "environmentspace", envspace,
                "minsamples", minsamples,
                "falloffmode", falloffmode,
                "falloff", falloff,
                
                "environmentcolor", Cenv
                );
            
            Cl *= intensity;
		}
	}
}