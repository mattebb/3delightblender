#include "./struct.h"

#pragma annotation freq "gadgettype=floatfield"
#pragma annotation amp "gadgettype=floatfield"
#pragma annotation __category "gadgettype=stringfield"

class noise_cosh(
    float freq = 1;
    float amp = 1;
	output string __category = "";
    )
{
    varying float noiseValue;
    
    public void begin()
    {
        noiseValue = noise(P*freq)*amp;
    }
    
    public void setColor( output Pstrc shdP )
    {
        shdP->Col *= noiseValue;
    }
    
    public color getColor( point P )
    {
        return color( noiseValue );
    }
    
    public color getFloat( point P )
    {
        return noiseValue;
    }
}
