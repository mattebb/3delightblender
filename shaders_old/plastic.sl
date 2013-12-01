/******************************************************************************/
/*                                                                            */
/*    Copyright (c)The 3Delight Team.                                         */
/*    All Rights Reserved.                                                    */
/*                                                                            */
/******************************************************************************/

surface 
plastic(
	float Ks = .5;
	float Kd = .5;
	float Ka = 1;
	float roughness = .1;
	color specularcolor = 1; )
{
	normal Nf =  faceforward( normalize(N), I );
	vector V  = - normalize( I );

	Oi = Os;
	Ci = ( Cs * (Ka * ambient() + Kd * diffuse(Nf)) + 
		specularcolor * Ks * specular(Nf, V, roughness) );

	Ci *= Oi;
}
