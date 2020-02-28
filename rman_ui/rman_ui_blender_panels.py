import bpy

def get_panels():
    exclude_panels = {
        'DATA_PT_area',
        'DATA_PT_camera_dof',
        'DATA_PT_falloff_curve',
        'DATA_PT_light',
        'DATA_PT_preview',
        'DATA_PT_shadow',
        'DATA_PT_sunsky',
        'MATERIAL_PT_diffuse',
        'MATERIAL_PT_flare',
        'MATERIAL_PT_halo',
        'MATERIAL_PT_mirror',
        'MATERIAL_PT_options',
        'MATERIAL_PT_pipeline',
        'MATERIAL_PT_preview',
        'MATERIAL_PT_shading',
        'MATERIAL_PT_shadow',
        'MATERIAL_PT_specular',
        'MATERIAL_PT_sss',
        'MATERIAL_PT_strand',
        'MATERIAL_PT_transp',
        'MATERIAL_PT_volume_density',
        'MATERIAL_PT_volume_integration',
        'MATERIAL_PT_volume_lighting',
        'MATERIAL_PT_volume_options',
        'MATERIAL_PT_volume_shading',
        'MATERIAL_PT_volume_transp',
        'RENDERLAYER_PT_layer_options',
        'RENDERLAYER_PT_layer_passes',
        'RENDERLAYER_PT_views',
        'RENDER_PT_antialiasing',
        'RENDER_PT_bake',
        'RENDER_PT_performance',
        'RENDER_PT_freestyle',
        'RENDER_PT_shading',
        'RENDER_PT_render',
        'RENDER_PT_stamp',
        'RENDER_PT_simplify',
        'RENDER_PT_color_management',
        'TEXTURE_PT_context_texture',
        'WORLD_PT_ambient_occlusion',
        'WORLD_PT_environment_lighting',
        'WORLD_PT_gather',
        'WORLD_PT_indirect_lighting',
        'WORLD_PT_mist',
        'WORLD_PT_preview',
        'WORLD_PT_world',
        'NODE_DATA_PT_light',
        'NODE_DATA_PT_spot',
    }

    panels = []
    for t in bpy.types.Panel.__subclasses__():
        if hasattr(t, 'COMPAT_ENGINES') and 'BLENDER_RENDER' in t.COMPAT_ENGINES:
            if t.__name__ not in exclude_panels:
                panels.append(t)

    return panels

def register():
    # This module is here to tell Blender which builtin panels we are
    # compatible with
    for panel in get_panels():
        panel.COMPAT_ENGINES.add('PRMAN_RENDER')


def unregister():

    for panel in get_panels():
        panel.COMPAT_ENGINES.remove('PRMAN_RENDER')