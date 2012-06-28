
#include "util.h"

//
// Surface shader class definition
//
class brdf_glossy (

                  string texturename = "";
                  float Kd = 0.5;
                  float roughness=0.5;)
{
    
    float exp = (2 / (roughness*roughness)) - 2;


    public float D(normal N; vector wh;)
    {
        float costhetah = abs(N . wh);
        float D = (exp+2) * (1/(2*M_PI)) * pow( max(0, costhetah), exp);
        return D;
    }
    
    public float G(normal N; vector wi; vector wo; vector wh)
    {
        float ndotwh = normalize(wh) . N;
        float ndotwo = normalize(wo) . N;
        float ndotwi = normalize(wi) . N;
        float wodotwh = abs(normalize(wo) . normalize(wh));
        float g = min(1, min((2*ndotwh*ndotwo / wodotwh),
                             (2*ndotwh*ndotwi / wodotwh)));
        return g;

    }
    
    public float pdf(normal N; vector wi; vector wo)
    {
        vector won = normalize(wo);
        vector win = normalize(wi);
        vector wh = normalize( won + win );
        float costheta = abs(N . wh);
        
        float pdf = ((exp + 1) * pow(costheta, exp)) /
                    (2 * M_PI * 4 * (wo . wh));
        return pdf;
    }
    
    public float schlick(float costheta) {
        float Rs = 1;    
        float fr = Rs + pow(1-costheta, 5) * (1 - Rs);
        return fr;
    }

    public color f(normal N; vector wi; vector wo)
    {
        vector won = normalize(wo);
        vector win = normalize(wi);
        
        float costhetaO = abs(won . N);
        float costhetaI = abs(win . N);
        
        vector wh = normalize( won + win );
        
        float costhetah = win . wh;
        
        float F = schlick(costhetah);
        float geo = G(N, wi, wo, wh);

        color f = Cs * D(N, wh) * geo * F / (4 * costhetaO * costhetaI);
        return f;
    }

    public void eval_bsdf(normal N; vector I; vector _L[];
                        uniform float nsamp;
                        output color f[];
                        output float pdf[];
                        )
    {
        float i;
        vector wo=normalize(I);
        
        resize(f, nsamp);
        resize(pdf, nsamp);
        
        
        for (i = 0; i < nsamp; i += 1) {
            vector wi = normalize(_L[i]);
            if (wi . N < 0) {
                f[i] = color(0,0,0);
                pdf[i] = 0;
                continue;
            }
            
            f[i] = f(N, wi, wo);
            pdf[i] = pdf(N, wi, wo);
        }
    }
    
    // XXX: Hmmmmmmm
    public void sample_bsdf(normal N; vector wo; uniform float nsamp;
                            output vector wi[];
                            output color f[];
                            output float pdf[];
                            )
    {    
        float s1, s2, i;
        float costheta;
        
        resize(wi, nsamp);
        resize(f, nsamp);
        resize(pdf, nsamp);
        
        vector won = normalize(wo);
        
        for (i = 0; i < nsamp; i += 1) {
            s1 = random();
            s2 = random();
            
            float costheta = pow(s1, 1.0/(exp+1));
            float sintheta = sqrt(max(0, 1-(costheta*costheta)));
            float phi = s2 * 2 * M_PI;
            
            vector H = spherical_to_cartesian(sintheta, costheta, phi);
            
            H = normalize(align_ortho(H, N, dPdu ));
            
            if (won . H < 0) H = -H;
            
            wi[i] = normalize(reflect(-won, H));
            
            if (wi[i] . N < 0) {
                f[i] = color(0,0,0);
                pdf[i] = 0;
                continue;
            }
            
            pdf[i] = pdf(N, wi[i], won);
            f[i] = f(N, wi[i], won);
        }
    }
    
    public void surface(output color Ci, Oi) {
        
        shader int = getshader("inte");
        uniform string shadername = "brdf_glossy";
        int->integrate(Ci, Oi, shadername);


        
        // Set Ci and Oi
        Ci *= Os;
        Oi = Os;
    }
}