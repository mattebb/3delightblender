
#pragma annotation light_color "gadgettype=colorslider"
#pragma annotation light_intensity "gadgettype=floatfield"
#pragma annotation is_directional "gadgettype=checkbox"
#pragma annotation diff_contribution "gadgettype=floatslider;min=0;max=1"
#pragma annotation spec_contribution "gadgettype=floatslider;min=0;max=1"
#pragma annotation shadow_coshaders "gadgettype=textfield"

class spotLight(
    color light_color = 1;
    float light_intensity = 1;
    float is_directional = 0;
    float cone_angle = 20;
    float penumbra_angle = 15;
    float falloff_power = 0;
    float diff_contribution = 1;
    float spec_contribution = 1;
    shader shadow_coshaders[] = null;
   )
{
    constant float illumAngle, cosoutside, cosinside;
    constant point P_light;
    constant vector light_dir;
    
    public void construct()
    {
        illumAngle = radians( cone_angle/2 + penumbra_angle );
        cosoutside = cos( illumAngle );
        cosinside = cos( radians( cone_angle/2 )  );
        P_light = point "shader" (0,0,0);
        light_dir = vector "shader" (0,0,-1);
    }
    
    public void light( output vector L; output color Cl )
	{
        // light vector
        float atten = 1;
		L = light_dir;
        if( is_directional == 0 )
        {
            L = normalize( Ps - P_light );
        
            // light angle attenuation
            float cosangle = L.light_dir;
            atten = smoothstep( cosoutside, cosinside, cosangle );

            // distance attenuation
            float distance = distance( P_light, Ps );
            atten /= pow( distance, falloff_power );
        }
        
        // shadows
        color shad = 1;
        uniform float iter = 0;
        for( iter = 0; iter < arraylength( shadow_coshaders ); iter += 1 )
            if( shadow_coshaders[iter] != null )
                shad = min( shad, shadow_coshaders[iter]->getShadow( Ps, P_light ) );
        
		Cl = light_color * light_intensity * atten * shad;
	}
}
