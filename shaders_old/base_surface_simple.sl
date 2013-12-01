#include "./struct.h"

//#pragma annotation brdf_coshader_name "shader_input=True"

class base_surface_simple(
    color baseColor = 1;
    shader color_coshader = null;
    
    color baseOpacity = 1;
    shader opac_coshader = null;
    
    string bump_coshader_cat = "_bump";
    string disp_coshader_cat = "_disp";
    
    shader brdf_coshader = null;
    float kenv = 1;
    float kd = 1;
    float ks = 1;
)
{
    Pstrc shdP;
    
    public void begin()
    {
        // init struct
        shdP->P = P;
        shdP->Nn = normalize(N);
        shdP->V = normalize(-I);
        shdP->Col = baseColor; // will be set in color coshader
        shdP->kenv = kenv;
        shdP->kd = kd;
        shdP->ks = ks;
    }
    
    public void displacement( output point P; output normal N )
    {
        shader disp_cosh[] = getshaders( "category", disp_coshader_cat );
        float dispAmount = 0;
        uniform float iter = 0;
        for( iter = 0; iter < arraylength(disp_cosh); iter += 1 )
        {
            dispAmount *= disp_cosh[iter]->getFloat( P );
        }
        P = P + ( shdP->Nn * dispAmount );
        normal dispN = calculatenormal( P );
        shdP->P = P;
        shdP->Nn = normalize(dispN);
    }
    
    public void opacity( output color Oi )
    {
        color c = baseOpacity;
        if( opac_coshader != null )
            c *= opac_coshader->getColor( P );
        Oi = c;
    }
    
    public void surface(output color Ci, Oi )
    {
        uniform float iter = 0;

        
        
        // color
        if( color_coshader != null )
            color_coshader->setColor( shdP );
        /*
        // bump
        shader bump_cosh[] = getshaders( "category", bump_coshader_cat );
        float bumpAmount = 0;
        for( iter = 0; iter < arraylength(bump_cosh); iter += 1 )
        {
            bumpAmount *= bump_cosh[iter]->getFloat( P );
        }
        point bmpP = P + ( shdP->Nn * bumpAmount );
        normal bumpN = calculatenormal( bmpP );
        shdP->Nn = normalize(bumpN);
        */
        // brdf
        //shader brdf_coshader = getshader( brdf_coshader_name );
        Ci += brdf_coshader->getBrdf( shdP );
        Ci += 0.1*diffuse(normalize(N));
        Ci *= 1.0; //Oi;
    }
}
