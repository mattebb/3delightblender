#include "./struct.h"

// ANNOTATIONS gadgettypes
#pragma annotation floatfield "gadgettype=floatfield"
#pragma annotation floatslider "gadgettype=floatslider;min=0;max=1"
#pragma annotation intfield "gadgettype=intfield"
#pragma annotation intslider "gadgettype=intslider;min=0;max=100"
#pragma annotation textfield "gadgettype=textfield"
#pragma annotation inputfile "gadgettype=inputfile"
#pragma annotation optionmenu "gadgettype=optionmenu:red:green:blue"
#pragma annotation checkbox "gadgettype=checkbox"
#pragma annotation colorslider "gadgettype=colorslider"
#pragma annotation single_coshader "gadgettype=textfield"
#pragma annotation coshader_list "gadgettype=textfield"

// ANNOTATIONS groupings
#pragma annotation "grouping" "float/floatfield;"
#pragma annotation "grouping" "float/floatslider;"
#pragma annotation "grouping" "int/intfield;"
#pragma annotation "grouping" "int/intslider;"
#pragma annotation "grouping" "int/optionmenu;"
#pragma annotation "grouping" "int/checkbox;"
#pragma annotation "grouping" "color/colorslider;"
#pragma annotation "grouping" "string/intslider;"
#pragma annotation "grouping" "string/inputfile;"
#pragma annotation "grouping" "string/single_coshader;"
#pragma annotation "grouping" "string/coshader_list;"

class gadgetTypes_surface(
    float floatfield = 0.52;
    float floatslider = 0.25;
    float intfield = 53;
    float intslider = 35;
    string textfield = "defaultTestField";
    string inputfile = "defaultInputFile";
    float optionmenu = 2;
    float checkbox = 1;
    color colorslider = color(1,0.6,0.3);
    shader single_coshader = null; # single coshader
    shader coshader_list[] = {}; # coshader array
)
{
    Pstrc shdP;
    
    public void begin()
    {
        // init struct
        shdP->P = P;
        shdP->Nn = normalize(N);
        shdP->V = normalize(-I);
        shdP->Col = colorslider; // will be set in color coshader
    }
    
    public void surface(output color Ci, Oi )
    {
        if( single_coshader != null )
            single_coshader->setColor( shdP );
        
        uniform float numOfBrdfCosh = arraylength( coshader_list );
        uniform float iter = 0;
        for( iter = 0; iter < arraylength(coshader_list); iter +=1 )
        {
            if( coshader_list[iter] != null )
                Ci += coshader_list[iter]->getBrdf( shdP );
        }
        Oi = 1;
    }
}
