
#include "util.h"

//
// Surface shader class definition
//
class brdf_diffuse (

                  string texturename = "";
                  float Kd = 0.5;)
{
    public constant string type = "DIFFUSE";
    
    public color f(varying normal Ns; varying vector wi;)
    {
        color f = Cs/PI;
        return f;
    }

    public float pdf(normal Ns; vector wi; vector wo;)
    {
        return (wi . Ns)/PI;
    }

    public void sample_bsdf(normal N; vector wo; uniform float nsamp;
                            output vector wi[];
                            output color f[];
                            output float pdf[];
                            )
    {    
        float s1, s2, i=0;
        float costheta;
        
        resize(wi, nsamp);
        resize(f, nsamp);
        resize(pdf, nsamp);
        
        for (i = 0; i < nsamp; i += 1) {
            s1 = random();
            s2 = random();
        
            wi[i] = warp_hemicosine(s1, s2);
            wi[i] = align_ortho(wi[i], N, dPdu );
            
            f[i] = f(N, wi[i]);
            pdf[i] = pdf(N, wi[i], I);
        }
    }
    
    public void eval_bsdf(normal Ns; vector I; vector _L[];
                        uniform float nsamp;
                        output color _f[];
                        output float _pdf[];
                        )
    {
        float i;
        vector wo=vector(0,0,0);
        resize(_f, nsamp);
        resize(_pdf, nsamp);
        
        
        for (i = 0; i < nsamp; i += 1) {
            vector wi = normalize(_L[i]);

            if (wi . Ns < 0) {
                _f[i] = color(0,0,0);
                _pdf[i] = 0;
                continue;
            }
            _f[i] = f(Ns, wi);
            _pdf[i] = pdf(Ns, wi, wo);
        }
    }


    public void surface(output color Ci, Oi)
    {
        shader int = getshader("inte");
        uniform string shadername = "brdf_diffuse";
        int->integrate(Ci, Oi, shadername);

        //Ci = color(1,0,0);

        // Set Ci and Oi
        Ci *= Os;
        Oi = Os;
        
    }
}
