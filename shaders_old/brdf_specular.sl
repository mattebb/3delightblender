#include "./struct.h"
#pragma annotation ks "gadgettype=floatfield"
#pragma annotation roughness "gadgettype=floatfield"
#pragma annotation surfcolormix "gadgettype=floatslider;min=0;max=1"

class brdf_specular(
    float ks = 1;
    float roughness = 0.3;
    float surfcolormix = 0;
)
{
    public color getBrdf( Pstrc shdP )
    {
        color c = 1;
        if( surfcolormix > 0 )
            c = mix( c, c*shdP->Col, surfcolormix);
        
        return c * ks * shdP->ks * specular( shdP->Nn, shdP->V, roughness );
    }
}
