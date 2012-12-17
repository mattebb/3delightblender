//  atmosphere shader for point-based baking of micropolygon area (for occlusion) and Ci (for color bleeding)  

volume vol_ptcbake(
    string ptc_file = "default.ptc";
    string ptc_coordsys = "world";)
    
{

    normal Nn = normalize(N);

    bake3d( ptc_file, "", P, Nn,
            "coordsystem", ptc_coordsys,
            "_radiosity", Ci,
            "interpolate", 1 );

    Ci = Ci * Cs;
}