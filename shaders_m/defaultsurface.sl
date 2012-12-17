/******************************************************************************/
/*                                                                            */
/*    Copyright (c)The 3Delight Team.                                         */
/*    All Rights Reserved.                                                    */
/*                                                                            */
/******************************************************************************/

surface defaultsurface(
	float Kd=.8, Ka=.2;
	string texturename = "" )
{
	float diffuse = I.N;
	diffuse = (diffuse*diffuse) / (I.I * N.N);

	color texturecolor = ( texturename != "" ) ? texture( texturename ) : 1;

	Ci = Cs * ( Ka + Kd*diffuse ) * texturecolor;
	Oi = Os;

	Ci *= Oi;
}
