#pragma annotation coneAngle "gadgettype=floatslider;min=0;max=1"
#pragma annotation shadowSamples "gadgettype=intfield"
#pragma annotation bias "gadgettype=floatfield"
#pragma annotation traceSet "gadgettype=textfield"

class raytracedShadow(
    float coneAngle = 5;
    float shadowSamples = 16;
    float bias = 0.01;
    string traceSet = "";
)
{
    public color getShadow( point srcP; point distP )
    {
		float angle = radians(coneAngle);
        color shad = transmission( srcP, distP, "samples", shadowSamples, "samplecone", angle, "bias", bias, "subset", traceSet );
        return shad;
    }
}
