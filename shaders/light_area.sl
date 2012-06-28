// realight.sl

#include "util.h"

class
area(
       uniform float intensity = 1;
       uniform color lightcolor = 1;
       uniform float samples = 16;
       uniform float width = 1.0;
       uniform float height = 1.0;
       uniform string texturename = "";
       )
       
{

    uniform point center = point "shader" (0,0,0); // center of rectangle
    varying vector udir = vector "shader" (width,0,0); // axis of rectangle
    varying vector vdir = vector "shader" (0,height,0); // axis of rectangle
    uniform vector zdir = vector "shader" (0,0,1);   // direction of light


    public color getshadow(varying point P; varying vector L) {
        return transmission(P, P+L);
    }
    
    public float intersect(point P; vector V;)
    {
        // check for parallel
        if (V . zdir == 0) return 0;
        
        
        uniform point center = point "shader" (0,0,0); // center of rectangle
        center = transform("world", center);
        return 1;
    }
    
    
    public void light( output vector L;         // unused
                       output color Cl;         // unused
                       output color _Cl[] = { };
                       output vector _L[] = { };
                       output float _pdf[] = { };
                       )
    {
       vector rnd;
       varying point samplepos;
       varying float su, sv;
       uniform float s;
       uniform float area = width*height;

       resize(_Cl, samples);   // note use of resizable arrays
       resize(_L, samples);
       resize(_pdf, samples);

      
       for (s = 0; s < samples; s += 1) {
            su = random();
            sv = random();
            samplepos = center + ((su-0.5) * udir) + ((sv-0.5) * vdir);
            _L[s] = samplepos - Ps;
            
            varying float dist = length(_L[s]);
            float costheta_z = _L[s] . zdir;
            
            _pdf[s] = (dist*dist) / (costheta_z * area);
            
            
            if (costheta_z < 0) {
                _Cl[s] = 0.0;
            } else {
                if (texturename != "") {
                    uniform float f = sqrt(1/samples)*4;
                    Cl = texture(texturename, su, sv, su+f, sv, su+f, sv+f, su, sv+f);
                    //Cl = texture(texturename, su, sv, "width", 1);
                } else
                    Cl = lightcolor;
               
                _Cl[s] = intensity * Cl;
            }            
           
       }

       // Clear L and Cl, even though they're unused.
       L = (0,0,0);
       Cl = (0,0,0);
    }
}