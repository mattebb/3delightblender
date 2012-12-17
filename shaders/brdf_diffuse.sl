#include "./struct.h"
#pragma annotation kd "gadgettype=floatfield"

class brdf_diffuse(
    float kd = 1;
)
{
    public color getBrdf( Pstrc shdP )
    {
        return kd * shdP->Col * shdP->kd * diffuse( shdP->Nn );
    }
}
