
#pragma annotation ptc_coordsystem "hide=true;"

#pragma annotation ptc_file "gadgettype=inputfile;label=Point Cloud File;hint=Point cloud file to read (usually should be the same as the ptc file being baked)"

#pragma annotation indirect_intensity "gadgettype=floatfield;label=Indirect Intensity;hint=Brightness multiplier for indirect light"
#pragma annotation indirect_occlusion "gadgettype=floatslider;label=Indirect Occlusion;hint=Amount of ambient occlusion to multiply with the indirect light"
#pragma annotation envmap "gadgettype=inputfile;label=Environment Map;hint=Add image based lighting from this environment (does not contribute to indirect light)"
#pragma annotation env_color "label=Environment Color;hint=Use this color for environment lighting, if not using an environment map (does not contribute to indirect light)"
#pragma annotation env_intensity "gadgettype=floatfield;label=Environment Intensity;hint=Brightness multiplier for environment light"
#pragma annotation env_occlusion "gadgettype=floatslider;label=Environment Occlusion;hint=Amount of ambient occlusion to multiply with the environment light"

#pragma annotation falloffmode "gadgettype=optionmenu:Exponential:Polynomial;label=Falloff Type;hint=Method for calculating falloff from incoming light;"
#pragma annotation falloff "gadgettype=floatfield;label=Falloff;hint=Strength of falloff effect"


#pragma annotation hitsides "gadgettype=optionmenu:Front:Back:Both;label=Hit Sides;hint=Specifies which side(s) of the point cloud’s samples will produce occlusion"
#pragma annotation clamp "gadgettype=checkbox;label=Clamp;hint=Reduce the excessive occlusion caused by the point-based algorithm, at the cost of speed."
#pragma annotation sortbleeding "gadgettype=checkbox;label=Sort Bleeding;hint=When 'Clamp' is enabled, force the color bleeding computations to take the ordering of surfaces into account."

#pragma annotation coneangle "gadgettype=floatfield;label=Cone Angle;hint=The solid angle in degrees around the normal considered for the point cloud lookup. Default (90) covers the entire hemisphere."
#pragma annotation maxdist "gadgettype=floatfield;label=Max Distance;hint=Only consider points closer than this distance for indirect lighting"
#pragma annotation maxsolidangle "gadgettype=floatfield;label=Max Solid Angle;hint=Controls quality vs speed - a good range of values is 0.01 to 0.5."
#pragma annotation bias "gadgettype=floatfield;label=Bias;hint=Self intersection bias"

light
gi_pointcloud(
    float indirect_intensity = 1;
    float indirect_occlusion = 0;
    
    string envmap = "";
    color env_color = 0.5;
    float env_intensity = 1;
    float env_occlusion = 1;
    

    float falloff = 0;
    float falloffmode = 0;
    
    string hitsides = "front";
    float clamp = 1;
    float sortbleeding = 1;

    float coneangle = 90; //entire hemisphere
    float maxdist = 1000;
    float maxsolidangle = .1;   
    float bias = 0;

    string ptc_coordsystem = "world";
    string ptc_file = "$PTC/{scene}.ptc";

)
{
    color radiance;
    color Cenv = color(0,0,0);
    
    uniform string ptcRenderPath = "";
    uniform string ptcBakePath = "";
    
    uniform float rendering = 0;
    uniform float baking = 0;
    baking = option("user:delight_gi_ptc_bake_path", ptcBakePath);
    // rendering = option("user:delight_gi_ptc_render_path", ptcRenderPath);
    
    if (baking == 1) {
        if (envmap == "") Cenv = env_color;
        else Cenv = indirectdiffuse(envmap, Ns);
        
        Cl = Cenv * env_intensity;
    } else {
        float occ;
        float indir_occ_factor;
        float env_occ_factor;
        
        illuminate( Ps + Ns ) {
        
            radiance = indirectdiffuse(Ps, Ns, 0,
                                         "pointbased", 1,
                                          "filename", ptc_file,
                                          "hitsides", hitsides,
                                          "coneangle", radians(coneangle),
                                          "clamp", clamp,
                                          "sortbleeding", sortbleeding,
                                          "maxdist", maxdist,
                                          "falloff", falloff,
                                          "falloffmode", falloffmode,
                                          "samplebase", 1,
                                          "bias", bias,
                                          "coordsystem", ptc_coordsystem,
                                          "maxsolidangle", maxsolidangle,
                                          "environmentmap", envmap,
                                          "environmentcolor", Cenv,
                                          "occlusion", occ);
        }
        
        indir_occ_factor = mix(1.0, (1.0-occ), indirect_occlusion);
        env_occ_factor = mix(1.0, (1.0-occ), env_occlusion);
        
        // subtract out environment contribution, to add it in later
        color indirect_light = (radiance - Cenv) * indirect_intensity * indir_occ_factor;

        if (envmap == "") Cenv = env_color;
        color env_light = Cenv * env_intensity * env_occ_factor;
        
        // indirect + environment
        Cl = indirect_light + env_light;
    }
}