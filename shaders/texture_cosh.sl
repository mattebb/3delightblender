#include "./struct.h"
#pragma annotation inputfile "gadgettype=inputfile"
#pragma annotation colorcorrect "gadgettype=textfield"
#pragma annotation __category "gadgettype=stringfield"

class texture_cosh(
    string inputfile = "";
    shader colorcorrect = null;
	output string __category = "";
    )
{
    public void setColor( output Pstrc shdP )
    {
        shdP->Col *= texture( inputfile );
        if( colorcorrect != null )
            colorcorrect->setColor( shdP );
    }
    
    public color getColor( point P )
    {
        return color texture( inputfile );
    }
    
    public float getFloat( point P )
    {
        return float texture( inputfile );
    }
}
