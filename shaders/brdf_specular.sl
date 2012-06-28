
#include "util.h"

//
// Surface shader class definition
//
class brdf_specular (
                    )
{

    public constant string type = "SPECULAR";
    
    public void sample_bsdf(normal N; vector wo; uniform float nsamp;
                            output vector wi[];
                            output color f[];
                            output float pdf[];
                            )
    {    
        float i;
        resize(wi, nsamp);
        resize(f, nsamp);
        resize(pdf, nsamp);
        vector won = normalize(wo);
        
        for (i = 0; i < nsamp; i += 1) {
            wi[i] = normalize(reflect(-won, N));
            
            // XXX include fresnel stuff here?
            f[i] = color(1,1,1);    
            pdf[i] = 1;
        }
    }
    
    public void eval_bsdf(normal Ns; vector I; vector _L[];
                        uniform float nsamp;
                        output color _f[];
                        output float _pdf[];
                        )
    {
        float i;
        resize(_f, nsamp);
        resize(_pdf, nsamp);
        
        for (i = 0; i < nsamp; i += 1) {
            _f[i] = color(0,0,0);
            _pdf[i] = 0;
        }
    }


    public void surface(output color Ci, Oi)
    {
        shader int = getshader("inte");
        uniform string shadername = "brdf_specular";
        int->integrate(Ci, Oi, shadername);

        //Ci = color(1,0,0);

        // Set Ci and Oi
        Ci *= Os;
        Oi = Os;
        
    }
}
