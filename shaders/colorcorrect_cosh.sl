#include "./struct.h"
#pragma annotation saturation "gadgettype=floatslider;min=0;max=1"
#pragma annotation tint "gadgettype=colorslider"
#pragma annotation gamma "gadgettype=floatslider;min=0;max=1"

class colorcorrect_cosh(
    float saturation = 1;
    color tint = 1;
    float gamma = 1;
    )
{
    public void setColor( output Pstrc shdP )
    {
        color c = shdP->Col;
        if( saturation != 1 )
        {
            c = ctransform("RGB","HSV", c);
            c[1] *= saturation;
            c = ctransform("HSV","RGB", c);
        }
        c *= tint;
        if( gamma != 1 )
        {
            float g = max( gamma, 0.0001 );
            c[0] = pow( c[0], 1/g );
            c[1] = pow( c[1], 1/g );
            c[2] = pow( c[2], 1/g );
        }
        shdP->Col = c;
    }
}
