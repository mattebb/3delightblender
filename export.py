# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2011 Matt Ebb
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# 
#
# ##### END MIT LICENSE BLOCK #####

import bpy
import bpy_types
import math
import os
import time
import subprocess
import mathutils
from mathutils import Matrix, Vector, Quaternion

from . import bl_info

from .util import bpy_newer_257
from .util import BlenderVersionError
from .util import rib, rib_path, rib_ob_bounds
from .util import make_frame_path
from .util import init_env
from .util import get_sequence_path
from .util import user_path
from .util import get_path_list_converted
from .util import path_list_convert

addon_version = bl_info['version']

# global dictionaries
from .shader_parameters import exclude_lamp_params

# helper functions for parameters
from .shader_parameters import shaderparameters_from_class
from .shader_parameters import path_win_to_unixy
from .shader_parameters import rna_to_shaderparameters
from .shader_parameters import get_parameters_shaderinfo
from .shader_parameters import rna_types_initialise

from .shader_parameters import shader_recompile

from .shader_parameters import shader_requires_shadowmap

from .shader_parameters import tex_source_path
from .shader_parameters import tex_optimised_path

from .nodes import export_shader_nodetree

class RPass:    
    def __init__(self, scene, objects=[], paths={}, type="", motion_blur=False):
        
        self.type = type if type != "" else "default"
        self.objects = objects
        self.archives = archive_objects(scene)
        self.paths = paths
        
        self.do_render = True
        self.options = []

        self.emit_photons = False
    
        self.resolution = []
        self.motion_blur = scene.renderman.motion_blur
        
        self.surface_shaders = True
        self.displacement_shaders = True
        self.interior_shaders = True
        self.atmosphere_shaders = True
        self.light_shaders = True    
        
        if type == 'shadowmap':
            self.interior_shaders = False
            self.atmosphere_shaders = False
            self.light_shaders = False

            # force motion blur on for shadows for the time being
            self.motion_blur = True
        elif type == 'ptc_indirect':
            self.motion_blur = False
    
    
    '''
    def print_options(self, file):
        #if self.type == 'ptc_indirect':            
        #    file.write('Option "user" "uniform string delight_renderpass_type" "bakePass" \n')            
        #file.write('Option "user" "uniform string delight_renderpass_name" "%s" \n' % self.type)
        pass
    '''



# ------------- Texture optimisation -------------

# 3Delight specific tdlmake stuff
def make_optimised_texture_3dl(tex, texture_optimiser, srcpath, optpath):
    rm = tex.renderman

    print("Optimising Texture: %s --> %s" % (tex.name, optpath))

    cmd = [texture_optimiser]

    if rm.format == 'ENV_LATLONG':
        cmd.append('-envlatl')
        
    # Wrapping
    cmd.append('-smode')
    cmd.append(rm.wrap_s)
    cmd.append('-tmode')
    cmd.append(rm.wrap_t)
    
    if rm.flip_s:
        cmd.append('-flips')
    if rm.flip_t:
        cmd.append('-flipt')
    
    # Filtering
    if rm.filter_type != 'DEFAULT':
        cmd.append('-filter')
        cmd.append(rm.filter_type)
    if rm.filter_type in ('catmull-rom', 'bessel') and rm.filter_window != 'DEFAULT':
        cmd.append('-window')
        cmd.append(rm.filter_window)

    if rm.filter_width_s != 1.0:
        cmd.append('-sfilterwidth')
        cmd.append(str(rm.filter_width_s))
    if rm.filter_width_t != 1.0:
        cmd.append('-tfilterwidth')
        cmd.append(str(rm.filter_width_t))
    
    if (rm.filter_blur != 1.0):
        cmd.append('-blur')
        cmd.append(str(rm.filter_blur))
    
    # Colour space
    if rm.input_color_space == 'GAMMA':
        cmd.append('-gamma')
        cmd.append(str(rm.input_gamma))
    else:
        cmd.append('-colorspace')
        cmd.append(rm.input_color_space)
    
    # Colour depth
    if rm.output_color_depth == 'UBYTE':
        cmd.append('-ubyte')
    elif rm.output_color_depth == 'SBYTE':
        cmd.append('-sbyte')
    elif rm.output_color_depth == 'USHORT':
        cmd.append('-ushort')
    elif rm.output_color_depth == 'SSHORT':
        cmd.append('-sshort')
    elif rm.output_color_depth == 'FLOAT':
        cmd.append('-float')
        
    if rm.output_compression == 'LZW':
        cmd.append('-lzw')
    elif rm.output_compression == 'ZIP':
        cmd.append('-zip')
    elif rm.output_compression == 'PACKBITS':
        cmd.append('-packbits')
    elif rm.output_compression == 'LOGLUV' and rm.output_color_depth == 'FLOAT':
        cmd.append('-logluv')
    elif rm.output_compression == 'UNCOMPRESSED':
        cmd.append('-c-')  
    
    # add preview
    cmd.append('-preview')
    cmd.append('256')
    
    # Filenames
    cmd.append(srcpath)
    cmd.append(optpath)
    
    proc = subprocess.Popen(cmd).wait()

def auto_optimise_textures(paths, scene):
    
    rm_textures = [tex for tex in bpy.data.textures if tex.renderman.auto_generate_texture == True]
    
    for tex in rm_textures:
        rm = tex.renderman
        srcpath = tex_source_path(tex, scene.frame_current)
        optpath = tex_optimised_path(tex, scene.frame_current)
        generate = False
        
        if not os.path.exists(srcpath):
            continue
        
        if rm.generate_if_nonexistent and not os.path.exists(optpath):
            generate = True
        elif rm.generate_if_older and os.path.getmtime(optpath) < os.path.getmtime(srcpath):
            generate = True
        
        if not generate: continue
        
        make_optimised_texture_3dl(tex, paths['texture_optimiser'], srcpath, optpath)

# ------------- Filtering -------------

def is_visible_layer(scene, ob):

    for i in range(len(scene.layers)):
        if scene.layers[i] == True and ob.layers[i] == True:
            return True
    return False

def is_renderable(scene, ob):
    return (is_visible_layer(scene, ob) and not ob.hide_render)
    # and not ob.type in ('CAMERA', 'ARMATURE', 'LATTICE'))

def renderable_objects(scene):
    return [ob for ob in scene.objects if is_renderable(scene, ob)]


# ------------- Archive Helpers -------------

# Generate an automatic path to write an archive when 'Export as Archive' is enabled
def auto_archive_path(paths, objects, create_folder=False):
    filename = objects[0].name + ".rib"
    
    if os.getenv("ARCHIVE") != None:
        archive_dir = os.getenv("ARCHIVE")
    else:
        archive_dir = os.path.join(paths['export_dir'], "archives")

    if create_folder and not os.path.exists(archive_dir):
        os.mkdir(archive_dir)

    return os.path.join(archive_dir, filename)

def archive_objects(scene):
    archive_obs = []
    
    for ob in renderable_objects(scene):
        # explicitly set
        if ob.renderman.export_archive == True:
            archive_obs.append(ob)
        
        # particle instances
        for psys in ob.particle_systems:
            rm = psys.settings.renderman
            if rm.particle_type == 'OBJECT':
                try:
                    ob = bpy.data.objects[rm.particle_instance_object]
                    archive_obs.append(ob)
                except:
                    pass
                    
        # dupli objects (TODO)

    return archive_obs


# ------------- Data Access Helpers -------------

def get_subframes(segs):
    return [i * 1.0/segs for i in range(segs+1)]

def get_ob_subframes(scene, ob):
    if ob.renderman.motion_segments_override:
        return get_subframes(ob.renderman.motion_segments)
    else:
        return get_subframes(scene.renderman.motion_segments)

def is_subd_last(ob):
    return ob.modifiers and ob.modifiers[len(ob.modifiers)-1].type == 'SUBSURF'

def is_subd_displace_last(ob):
    if len(ob.modifiers) < 2: return False
    
    return (ob.modifiers[len(ob.modifiers)-2].type == 'SUBSURF' and
        ob.modifiers[len(ob.modifiers)-1].type == 'DISPLACE')

def is_subdmesh(ob):
    return (is_subd_last(ob) or is_subd_displace_last(ob))

# XXX do this better, perhaps by hooking into modifier type data in RNA?
# Currently assumes too much is deforming when it isn't
def is_deforming(ob):
    deforming_modifiers = ['ARMATURE', 'CAST', 'CLOTH', 'CURVE', 'DISPLACE', 'HOOK', 'LATTICE', 'MESH_DEFORM',
                            'SHRINKWRAP', 'SIMPLE_DEFORM', 'SMOOTH', 'WAVE', 'SOFT_BODY', 'SURFACE']
    if ob.modifiers:        
        # special cases for auto subd/displace detection
        if len(ob.modifiers) == 1 and is_subd_last(ob):
            return False
        if len(ob.modifiers) == 2 and is_subd_displace_last(ob):
            return False
        
        for mod in ob.modifiers:
            if mod.type in deforming_modifiers:
                return True
    
    return False
    
# handle special case of fluid sim a bit differently
def is_deforming_fluid(ob):
    if ob.modifiers:
        mod = ob.modifiers[len(ob.modifiers)-1]
        if mod.type == 'FLUID_SIMULATION' and mod.settings.type == 'DOMAIN':
            return True


def psys_motion_name(ob, psys):
    return ob.name + "_" + psys.name
    


# ------------- Geometry Access -------------
def get_strands(ob, psys):
    nstrands = 0
    nvertices = []
    P = []
    
    for particle in psys.particles:
        hair = particle.hair_keys
        nvertices += [len(hair)+2]
        i=0
        
        # hair keys are stored as local offsets from the 
        # particle location (on surface)
        for key in particle.hair_keys:
            P.extend( key.co )
            
            # double up start and end points
            if i == 0 or i == len(hair)-1:
                P.extend( key.co )
            i += 1
            
    return (nvertices, P)

# only export particles that are alive, 
# or have been born since the last frame
def valid_particle(pa, cfra):
    return not (pa.birth_time > cfra or (pa.birth_time + pa.die_time) < cfra)

def get_particles(scene, ob, psys):
    P = []
    rot = []
    width = []
    
    cfra = scene.frame_current
    
    for pa in [p for p in psys.particles if valid_particle(p, cfra)]:
        
        P.extend( pa.location )
        rot.extend( pa.rotation )
        
        if pa.alive_state != 'ALIVE':
            width.append(0.0)
        else:
            width.append(pa.size)
    
    return (P, rot, width)

# Mesh data access
def get_mesh(mesh):
    nverts = []
    verts = []
    P = []
    
    for v in mesh.vertices:
        P.extend( v.co )
  
    for p in mesh.polygons:
        nverts.append( p.loop_total )
        verts.extend( p.vertices )
        
    return (nverts, verts, P)

def get_mesh_vertex_N(mesh):
    N = []
    
    for v in mesh.vertices:
        N.extend( v.normal )
    
    return N

# requires facevertex interpolation
def get_mesh_uv(mesh, name=""):
    uvs = []

    if name == "":
        uv_loop_layer = mesh.uv_layers.active
    else:
        # assuming uv loop layers and uv textures share identical indices
        idx = mesh.uv_textures.keys().index(name)
        uv_loop_layer = mesh.uv_layers[idx]
    
    if uv_loop_layer == None:
        return None
    
    for uvloop in uv_loop_layer.data:
        uvs.append( uvloop.uv.x )
        uvs.append( 1.0 - uvloop.uv.y )     # renderman expects UVs flipped vertically from blender

    return uvs


# requires facevertex interpolation
def get_mesh_vcol(mesh, name=""):
    vcol_layer = mesh.vertex_colors[name] if name != "" else mesh.vertex_colors.active
    cols = []
    
    if vcol_layer == None:
        return None
    
    for vcloop in vcol_layer.data:
        cols.extend( vcloop.color )
    
    return cols

# requires per-vertex interpolation
def get_mesh_vgroup(ob, mesh, name=""):
    vgroup = ob.vertex_groups[name] if name != "" else ob.vertex_groups.active
    weights = []
    
    if vgroup == None:
        return None

    for v in mesh.vertices:
        if len(v.groups) == 0:
            weights.append(0.0)
        else:
            weights.extend( [g.weight for g in v.groups if g.group == vgroup.index ] )
            
    return weights


def export_primvars(file, ob, geo, interpolation=""):
    if ob.type != 'MESH':
        return

    rm = ob.data.renderman
    
    interpolation = 'facevertex' if interpolation == '' else interpolation
    
    # default hard-coded prim vars
    if rm.export_smooth_normals and ob.renderman.primitive in ('AUTO', 'POLYGON_MESH', 'SUBDIVISION_MESH'):
        N = get_mesh_vertex_N(geo)
        if N is not None:
            file.write('            "varying normal N" %s \n' % rib(N) )
    if rm.export_default_uv:
        uvs = get_mesh_uv(geo)
        if uvs is not None:
            file.write('            "%s float[2] st" %s \n' % (interpolation, rib(uvs)) )
    if rm.export_default_vcol:
        vcols = get_mesh_vcol(geo)
        if vcols is not None:
            file.write('            "%s color Cs" %s \n' % (interpolation, rib(vcols)) )
    
    # custom prim vars
    for p in rm.prim_vars:
        if p.data_source == 'VERTEX_COLOR':
            vcols = get_mesh_vcol(geo, p.data_name)
            if vcols is not None:
                file.write('            "%s color %s" %s \n' % (interpolation, p.name, rib(vcols)) )

        elif p.data_source == 'UV_TEXTURE':
            uvs = get_mesh_uv(geo, p.data_name)
            if uvs is not None:
                file.write('            "%s float[2] %s" %s \n' % (interpolation, p.name, rib(uvs)) )

        elif p.data_source == 'VERTEX_GROUP':
            weights = get_mesh_vgroup(ob, geo, p.data_name)
            if weights is not None:
                file.write('            "vertex float %s" %s \n' % (p.name, rib(weights)) )
    
def export_primvars_particle(file, scene, psys):
    rm = psys.settings.renderman
    cfra = scene.frame_current
    
    for p in rm.prim_vars:
        vars = []
        
        if p.data_source in ('VELOCITY', 'ANGULAR_VELOCITY'):
            if p.data_source == 'VELOCITY':
                for pa in [p for p in psys.particles if valid_particle(p, cfra)]:
                    vars.extend ( pa.velocity )
            elif p.data_source == 'ANGULAR_VELOCITY':
                for pa in [p for p in psys.particles if valid_particle(p, cfra)]:
                    vars.extend ( pa.angular_velocity )

            file.write('            "varying float[3] %s" %s \n' % (p.name, rib(vars)) )

        elif p.data_source in ('SIZE', 'AGE', 'BIRTH_TIME', 'DIE_TIME', 'LIFE_TIME'):
            if p.data_source == 'SIZE':
                for pa in [p for p in psys.particles if valid_particle(p, cfra)]:
                    vars.append ( pa.size )
            elif p.data_source == 'AGE':
                for pa in [p for p in psys.particles if valid_particle(p, cfra)]:
                    vars.append ( (cfra - pa.birth_time) / pa.lifetime )
            elif p.data_source == 'BIRTH_TIME':
                for pa in [p for p in psys.particles if valid_particle(p, cfra)]:
                    vars.append ( pa.birth_time )
            elif p.data_source == 'DIE_TIME':
                for pa in [p for p in psys.particles if valid_particle(p, cfra)]:
                    vars.append ( pa.die_time )
            elif p.data_source == 'LIFE_TIME':
                for pa in [p for p in psys.particles if valid_particle(p, cfra)]:
                    vars.append ( pa.lifetime )

            file.write('            "varying float %s" %s \n' % (p.name, rib(vars)) )


def get_fluid_mesh(scene, ob):
    
    subframe = scene.frame_subframe
    
    fluidmod = [m for m in ob.modifiers if m.type == 'FLUID_SIMULATION'][0]
    fluidmeshverts = fluidmod.settings.fluid_mesh_vertices
    
    mesh = create_mesh(scene, ob)
    (nverts, verts, P) = get_mesh(mesh)
    bpy.data.meshes.remove(mesh)
    
    # use fluid vertex velocity vectors to reconstruct moving points
    P = [P[i] + fluidmeshverts[int(i/3)].velocity[i%3] * subframe * 0.5 for i in range(len(P))]
    
    return (nverts, verts, P)
    
def get_subd_creases(mesh):
    creases = []
    
    # only do creases 1 edge at a time for now, detecting chains might be tricky..
    for e in mesh.edges:
        if e.crease > 0.0:
            creases.append( (e.vertices[0], e.vertices[1], e.crease*e.crease * 10) ) # squared, to match blender appareance better : range 0 - 10 (infinitely sharp)
    return creases

def create_mesh(scene, ob, matrix=None):
    # 2 special cases to ignore:
    # subsurf last or subsurf 2nd last +displace last
    
    #if is_subd_last(ob):
    #    ob.modifiers[len(ob.modifiers)-1].show_render = False
    #elif is_subd_displace_last(ob):
    #    ob.modifiers[len(ob.modifiers)-2].show_render = False
    #    ob.modifiers[len(ob.modifiers)-1].show_render = False
    
    mesh = ob.to_mesh(scene, True, 'RENDER')    
    
    if matrix != None:
        mesh.transform(matrix)

    return mesh






# RIB Exporting functions

def shadowmap_path(scene, ob):
    if ob.type != 'LAMP': return ''
    rm = ob.data.renderman
    path = user_path(rm.path_shadow_map, scene=scene, ob=ob)
    
    if rm.shadow_transparent:
        path += '.dsm'
    else:
        path += '.tdl'
    return path
    

def export_light(rpass, scene, file, ob):
    lamp = ob.data
    rm = lamp.renderman

    m = ob.parent.matrix_world * ob.matrix_local if ob.parent else ob.matrix_world

    loc = m.to_translation()
    lvec = loc - (m.to_quaternion() * mathutils.Vector((0,0,1)))
    
    params = []
    
    file.write('    AttributeBegin\n')
    file.write('    TransformBegin\n')
    file.write('            Transform %s\n' % rib(m))
    
    
    if rm.emit_photons and lamp.type in ('SPOT', 'POINT', 'SUN'):
        file.write('        Attribute "light" "string emitphotons" [ "on" ]\n' )
	
	# BBM addition begin
	# export light coshaders
    '''
    file.write('\n        ## Light Co-shaders\n')
    for cosh_item in rm.coshaders.items():
        coshader_handle = cosh_item[0]
        coshader_name = cosh_item[1].shader_shaders.active
        file.write('        Shader "%s" \n            "%s"\n' % (coshader_name, coshader_handle) )
        parameterlist = rna_to_shaderparameters(scene, cosh_item[1], 'shader')
        for sp in parameterlist:
            if sp.is_array:
                file.write('            "%s %s[%d]" %s\n' % (sp.data_type, sp.name, len(sp.value), rib(sp.value,is_cosh_array=True)))
            else:
                file.write('            "%s %s" %s\n' % (sp.data_type, sp.name, rib(sp.value)))
	
    file.write('\n        ## Light shader\n')
    '''
    # BBM addition end
	
    '''
    # user defined light shader
    if rm.nodetree == '' and rm.light_shaders.active != '':
        file.write('        LightSource "%s" ' % rm.light_shaders.active)
        
        params = rna_to_shaderparameters(scene, rm, 'light')

    # automatic shaders per blender lamp type
    elif lamp.type == 'POINT':
        file.write('        LightSource "pointlight" \n')
        name, params = get_parameters_shaderinfo(rpass.paths['shader'], 'pointlight', 'light')
        
    elif lamp.type == 'SPOT':
        if rm.shadow_method == 'SHADOW_MAP':
            file.write('        LightSource "shadowspot" \n')
            name, params = get_parameters_shaderinfo(rpass.paths['shader'], 'shadowspot', 'light')
        
        else:
            file.write('        LightSource "spotlight" \n')
            name, params = get_parameters_shaderinfo(rpass.paths['shader'], 'spotlight', 'light')
            
    elif lamp.type == 'SUN':
        file.write('        LightSource "h_distantshadow" \n')
        name, params = get_parameters_shaderinfo(rpass.paths['shader'], 'h_distantshadow', 'light')
        
    elif lamp.type == 'HEMI':
        file.write('        LightSource "ambientlight" \n')
        name, params = get_parameters_shaderinfo(rpass.paths['shader'], 'ambientlight', 'light')
        
    # file.write('            "%s" \n' % ob.name) # handle
    '''
    
    if rm.nodetree != '':
        print('export nodetree ')
        export_shader_nodetree(file, scene, lamp, output_node='OutputLightShaderNode', handle=ob.name)
        params = []

    # parameter list
    for sp in params:
        # special exceptions since they're not an actual properties on lamp datablock
        if sp.name == 'from':
            value = rib(loc)
        elif sp.name == 'to': 
            value = rib(lvec)


        elif sp.meta == 'shadow_map_path':
            if shader_requires_shadowmap(scene, rm, 'light'):
                path = rib_path(shadowmap_path(scene, ob))
                print(path)
                file.write('        "string %s" "%s" \n' % (sp.name, path))

            ''' XXX old shaders

        
        elif sp.name == 'coneangle':
            if hasattr(lamp, "spot_size"):
                coneangle = lamp.spot_size / 2.0
                value = rib(coneangle)
            else:
                value = rib(45)
        
        elif sp.name in ('shadowmap', 'shadowname', 'shadowmapname'):
            if rm.shadow_method == 'SHADOW_MAP':
                shadowmapname = rib_path(shadowmap_path(scene, ob))
                file.write('        "string %s" "%s" \n' % (sp.name, shadowmapname))
            elif rm.shadow_method == 'RAYTRACED':
                file.write('        "string %s" ["raytrace"] \n' % sp.name)
            
            continue
            '''
        # more exceptions, use blender's built in equivalent parameters (eg. spot size)
        elif sp.name in exclude_lamp_params.keys():
            value = rib(getattr(lamp, exclude_lamp_params[sp.name]))
        
        # otherwise use the stored raw shader parameters
        else:
            value = rib(sp.value)

		# BBM addition begin
        if sp.is_array:
            file.write('        "%s %s[%d]" %s\n' % (sp.data_type, sp.name, len(sp.value), rib(sp.value,is_cosh_array=True)))
        else:
		# BBM addition end
            file.write('        "%s %s" %s\n' % (sp.data_type, sp.name, value))

    file.write('    TransformEnd\n')
    file.write('    AttributeEnd\n')
    
    file.write('    Illuminate "%s" %d \n' % (ob.name, rm.illuminates_by_default))
    file.write('    \n')

def export_sss_bake(file, rpass, mat):
    rm = mat.renderman
    
    if not rm.sss_do_bake: return
    
    group = mat.name if rm.sss_group == "" else rm.sss_group
    
    file.write('        \n')
    file.write('        Attribute "visibility" "string subsurface" "%s" \n\n' % group)
    
    file.write('        Attribute "subsurface" \n')
    file.write('            "color meanfreepath" %s \n' % rib(rm.sss_meanfreepath))
    if rm.sss_use_reflectance:
        file.write('            "color reflectance" %s \n' % rib(rm.sss_reflectance))
    file.write('            "refractionindex" %s \n' % rm.sss_ior)
    file.write('            "shadingrate" %s \n' % rm.sss_shadingrate)
    file.write('            "scale" %s \n' % rm.sss_scale)
    file.write('        \n')
    
def export_material(file, rpass, scene, mat):

    export_sss_bake(file, rpass, mat)
    
    export_shader_init(file, rpass, mat)
    
    rm = mat.renderman

    if rm.nodetree != '':
        file.write('        Color %s\n' % rib(mat.diffuse_color))
        file.write('        Opacity %s\n' % rib([mat.alpha for i in range(3)]))
            
        if rm.displacementbound > 0.0:
            file.write('        Attribute "displacementbound" "sphere" %f \n' % rm.displacementbound)
        
        export_shader_nodetree(file, scene, mat)
    else:
        #export_shader(file, scene, rpass, mat, 'shader') # BBM addition
        export_shader(file, scene, rpass, mat, 'surface')
        export_shader(file, scene, rpass, mat, 'displacement')
        export_shader(file, scene, rpass, mat, 'interior')
    
    '''
    # allow overriding with global world atmosphere shader
    if mat.renderman.inherit_world_atmosphere:
        export_shader(file, scene, rpass, scene.world, 'atmosphere')
    else:
        export_shader(file, scene, rpass, mat, 'atmosphere')
    ''' 
    #file.write('        Shader "brdf_specular" "brdf_specular" \n')
    #file.write('        Shader "btdf_specular" "btdf_specular" \n')


def export_strands(file, rpass, scene, ob, motion):

    for psys in ob.particle_systems:
        pname = psys_motion_name(ob, psys)    
        rm = psys.settings.renderman

        if psys.settings.type != 'HAIR':
            continue
        
        # use 'material_id' index to decide which material
        if ob.data.materials and len(ob.data.materials) > 0:
            if ob.data.materials[rm.material_id-1] != None:
                mat = ob.data.materials[rm.material_id-1]
                export_material(file, rpass, scene, mat)
        
        motion_blur = pname in motion['deformation']
            
        if motion_blur:
            file.write('        MotionBegin %s\n' % rib(get_ob_subframes(scene, ob)))
            samples = motion['deformation'][pname]
        else:
            samples = [get_strands(ob, psys)]
        
        for nverts, P in samples:
        
            file.write('    Basis "catmull-rom" 1 "catmull-rom" 1\n')
            file.write('    Curves "cubic" \n')
            file.write('        %s \n' % rib(nverts))
            file.write('        "nonperiodic" \n')
            file.write('        "P" %s \n' % rib(P))
            file.write('        "constantwidth" [ %f ] \n' % rm.width)

        if motion_blur:
            file.write('        MotionEnd\n')

def geometry_source_rib(scene, ob):
    rm = ob.renderman
    anim = rm.archive_anim_settings
    blender_frame = scene.frame_current
    rib = ""
    
    if rm.geometry_source == 'ARCHIVE':
        archive_path = rib_path(get_sequence_path(rm.path_archive, blender_frame, anim))
        rib = '        ReadArchive "%s"\n' % archive_path
        
    else:
        if rm.procedural_bounds == 'MANUAL':
            min = rm.procedural_bounds_min
            max = rm.procedural_bounds_max
            bounds = [min[0], max[0], min[1], max[1], min[2], max[2]]
        else:
            bounds = rib_ob_bounds(ob.bound_box)
        
        if rm.geometry_source == 'DELAYED_LOAD_ARCHIVE':
            archive_path = rib_path(get_sequence_path(rm.path_archive, blender_frame, anim))
            rib = '        Procedural "DelayedReadArchive" ["%s"] %s\n' \
                                    % (archive_path, rib(bounds))
        
        elif rm.geometry_source == 'PROCEDURAL_RUN_PROGRAM':
            path_runprogram = rib_path(rm.path_runprogram)
            rib = '        Procedural "RunProgram" ["%s" "%s"] %s\n' \
                                    % (path_runprogram, rm.path_runprogram_args, rib(bounds))
        
        elif rm.geometry_source == 'DYNAMIC_LOAD_DSO':
            path_dso = rib_path(rm.path_dso)
            rib = '        Procedural "DynamicLoad" ["%s" "%s"] %s\n' \
                                    % (path_dso, rm.path_dso_initial_data, rib(bounds))

    return rib

def export_particle_instances(file, rpass, scene, ob, psys, motion):
    rm = psys.settings.renderman
    pname = psys_motion_name(ob, psys)
    
    # Precalculate archive path for object instances
    try:
        instance_ob = bpy.data.objects[rm.particle_instance_object]
    except:
        return
    
    if instance_ob.renderman.geometry_source == 'BLENDER_SCENE_DATA':
        archive_path = rib_path(auto_archive_path(rpass.paths, [instance_ob]))
        instance_geometry_rib = '            ReadArchive "%s"\n' % archive_path
    else:
        instance_geometry_rib = geometry_source_rib(scene, instance_ob)
    
    motion_blur = pname in motion['deformation']
    cfra = scene.frame_current

    for i in range(len( [ p for p in psys.particles if valid_particle(p, cfra) ] )):
        
        if motion_blur:
            file.write('        MotionBegin %s\n' % rib(get_ob_subframes(scene, ob)))
            samples = motion['deformation'][pname]
        else:
            samples = [get_particles(scene, ob, psys)]
        
        for P, rot, width in samples:

            loc = Vector((P[i*3+0], P[i*3+1], P[i*3+2]))
            rot = Quaternion((rot[i*4+0], rot[i*4+1], rot[i*4+2], rot[i*4+3]))
            mtx = Matrix.Translation(loc) * rot.to_matrix().to_4x4() * Matrix.Scale(width[i], 4)
            
            file.write('                Transform %s \n' % rib(mtx))
        
        if motion_blur:
            file.write('            MotionEnd\n')

        file.write( instance_geometry_rib )
        


def export_particle_points(file, scene, ob, psys, motion):
    rm = psys.settings.renderman
    pname = psys_motion_name(ob, psys)
    
    motion_blur = pname in motion['deformation']
    
    if motion_blur:
        file.write('        MotionBegin %s\n' % rib(get_ob_subframes(scene, ob)))
        samples = motion['deformation'][pname]
    else:
        samples = [get_particles(scene, ob, psys)]
    
    for P, rot, width in samples:
        
        file.write('        Points \n')
        file.write('            "P" %s \n' % rib(P))
        file.write('            "uniform string type" [ "%s" ] \n' % rm.particle_type)
        if rm.constant_width:
            file.write('            "constantwidth" [%f] \n' % rm.width)
        elif rm.export_default_size:
            file.write('            "varying float width" %s \n' % rib(width))

        export_primvars_particle(file, scene, psys)

    if motion_blur:
        file.write('        MotionEnd\n')

def export_particles(file, rpass, scene, ob, motion):

    for psys in ob.particle_systems:
        rm = psys.settings.renderman
        pname = psys_motion_name(ob, psys)
        
        if psys.settings.type != 'EMITTER':
            continue
    
        file.write('    AttributeBegin\n')
        file.write('        Attribute "identifier" "name" [ "%s" ]\n' % pname)
        
        # use 'material_id' index to decide which material
        if ob.data.materials:
            if ob.data.materials[rm.material_id-1] != None:
                mat = ob.data.materials[rm.material_id-1]
                export_material(file, rpass, scene, mat)
        
        # Write object instances or points
        if rm.particle_type == 'OBJECT':
            export_particle_instances(file, rpass, scene, ob, psys, motion)
        else:
            export_particle_points(file, scene, ob, psys, motion)
        
        
        file.write('AttributeEnd\n\n')
        
def export_scene_lights(file, rpass, scene):
    if not rpass.light_shaders: return

    file.write('    ## Lights \n\n')
    
    for ob in [o for o in rpass.objects if o.type == 'LAMP']:
        export_light(rpass, scene, file, ob)

    file.write('    \n')


def export_shader_init(file, rpass, mat):
    rm = mat.renderman

    if rpass.emit_photons:
        file.write('        Attribute "photon" "string shadingmodel" "%s" \n' % rm.photon_shadingmodel)

def export_shader(file, scene, rpass, idblock, shader_type):
    rm = idblock.renderman
    file.write('\n        # %s\n' % shader_type ) # BBM addition
	
    parameterlist = rna_to_shaderparameters(scene, rm, shader_type)

    for sp in parameterlist:
        print('sp.meta[\'data_type\'] %s ' % sp.meta['data_type'])
        if sp.meta['data_type'] == 'shader':
            if sp.value == 'null':
                continue
            if sp.is_array:
                collection = sp.value 
                for item in collection:
                    file.write('        Shader "%s" "%s"\n' % (item.value, idblock.name+'_'+sp.name) )
            else:
                file.write('        Shader "%s" "%s"\n' % (sp.value, sp.value)) #idblock.name+'_'+sp.name) )

    if shader_type == 'surface':
        mat = idblock
        
        if rm.surface_shaders.active == '' or not rpass.surface_shaders: return
        
        file.write('        Color %s\n' % rib(mat.diffuse_color))
        file.write('        Opacity %s\n' % rib([mat.alpha for i in range(3)]))
        file.write('        Surface "%s" \n' % rm.surface_shaders.active)
        
    elif shader_type == 'displacement':
        if rm.displacement_shaders.active == '' or not rpass.displacement_shaders: return
        
        if rm.displacementbound > 0.0:
            file.write('        Attribute "displacementbound" "sphere" %f \n' % rm.displacementbound)
        file.write('        Displacement "%s" \n' % rm.displacement_shaders.active)
            
    elif shader_type == 'interior':
        if rm.interior_shaders.active == '' or not rpass.interior_shaders: return
        
        file.write('        Interior "%s" \n' % rm.interior_shaders.active)
    
    elif shader_type == 'atmosphere':

        if rpass.type == 'ptc_indirect':

            # use a relative path to pointcloud_dir to work around windows paths issue -
            # bake3d() doesn't seem to like baking windows absolute paths
            relpath = os.path.relpath( rpass.paths["gi_ptc_bake_path"], start=rpass.paths["export_dir"] )            
            file.write('        # ptc_file is exported as relative path to export directory \n')
            file.write('        # to work around a problem with windows absolute paths in bake3d() \n')
            file.write('        Atmosphere "vol_ptcbake" \n')
            file.write('            "string ptc_file" "%s" \n' % relpath)
        
        if rm.atmosphere_shaders.active == '' or not rpass.atmosphere_shaders: return
        file.write('        Atmosphere "%s" \n' % rm.atmosphere_shaders.active)
    

    '''
    # BBM addition begin
    elif shader_type == 'shader':
        for cosh_item in rm.coshaders.items():
            coshader_handle = cosh_item[0]
            coshader_name = cosh_item[1].shader_shaders.active
            file.write('        Shader "%s" "%s"\n' % (coshader_name, coshader_handle) )
            parameterlist = rna_to_shaderparameters(scene, cosh_item[1], shader_type)
            print('--', sp.value, sp.pyname)
            for sp in parameterlist:
                if sp.is_coshader and sp.value == '' or sp.value == 'null':
                    sp.value = 'null'
                else:
                    if sp.is_array:
                        file.write('            "%s %s[%d]" %s\n' % (sp.data_type, sp.name, len(sp.value), rib(sp.value,is_cosh_array=True)))
                    else:
                        file.write('            "%s %s" %s\n' % (sp.data_type, sp.name, rib(sp.value)))
        return
	# BBM addition end
    '''

    # parameter list
    for sp in parameterlist:
		# BBM addition begin
        if sp.value == 'null':
            continue

        if sp.is_array:
            file.write('            "%s %s[%d]" %s\n' % (sp.data_type, sp.name, len(sp.value), rib(sp.value,is_cosh_array=True)))
        else:
		# BBM addition end
            file.write('            "%s %s" %s\n' % (sp.data_type, sp.name, rib(sp.value)))

    # BBM removed begin
    #if type == 'surface':
    #    file.write('        Shader "%s" "%s" \n' % (rm.surface_shaders.active, rm.surface_shaders.active))
    #    for sp in parameterlist:
    #        file.write('            "%s %s" %s\n' % (sp.data_type, sp.name, rib(sp.value)))
	# BBM removed end

def detect_primitive(ob):
    rm = ob.renderman
    
    if rm.primitive == 'AUTO':
        if ob.type == 'MESH':
            if is_subdmesh(ob):
                return 'SUBDIVISION_MESH'
            else:
                return 'POLYGON_MESH'
        elif ob.type == 'CURVE':
            return 'CURVE'
        elif ob.type in ('SURFACE', 'META', 'FONT'):
            return 'POLYGON_MESH'
        else:
            return 'NONE'
    else:
        return rm.primitive

def get_curve(curve):
    splines = []
    
    for spline in curve.splines:
        P = []
        width = []
        npt = len(spline.bezier_points)*3
        
        for bp in spline.bezier_points:
            P.extend( bp.handle_left )
            P.extend( bp.co )
            P.extend( bp.handle_right )
            width.append( bp.radius )
        
        basis = '"bezier" 3 "bezier" 3'
        if spline.use_cyclic_u:
            period = 'periodic'
            # wrap the initial handle around to the end, to begin on the CV
            P = P[3:] + P[:3]
        else:
            period = 'nonperiodic'
            # remove the two unused handles
            npt -= 2
            P = P[3:-3]

        splines.append( (P, width, npt, basis, period) )

    return splines

def export_curve(file, scene, ob, motion):
    if ob.type != 'CURVE':
        return
    curve  = ob.data

    motion_blur = ob.name in motion['deformation']
    
    if motion_blur:
        file.write('        MotionBegin %s\n' % rib(get_ob_subframes(scene, ob)))
        samples = motion['deformation'][ob.name]
    else:
        samples = [get_curve(curve)]
    
    for spline_samples in samples:
        for P, width, npt, basis, period in spline_samples:

            file.write('        Basis %s\n' % basis)
            file.write('        Curves "cubic" \n')
            file.write('            [ %s ] \n' % rib(npt))
            file.write('            "%s" \n' % period)
            file.write('            "P" %s \n' % rib(P))
            file.write('            "width" %s \n' % rib(width))
            #file.write('        "constantwidth" [ %f ] \n' % 0.2)
            
    if motion_blur:
        file.write('        MotionEnd\n')

def export_subdivision_mesh(file, scene, ob, motion):
    mesh = create_mesh(scene, ob)
    
    motion_blur = ob.name in motion['deformation']
    
    if motion_blur:
        file.write('        MotionBegin %s\n' % rib(get_ob_subframes(scene, ob)))
        samples = motion['deformation'][ob.name]
    else:
        samples = [get_mesh(mesh)]
    
    creases = get_subd_creases(mesh)
    
    for nverts, verts, P in samples:
        tags = []
        nargs = []
        intargs = []
        floatargs = []

        file.write('        SubdivisionMesh "catmull-clark" \n')
        file.write('            %s\n' % rib(nverts))
        file.write('            %s\n' % rib(verts))
        if len(creases) > 0:
            for c in creases:
                tags.append( '"crease"' )
                nargs.extend( [2, 1] )
                intargs.extend( [c[0], c[1]] )
                floatargs.append( c[2] )

        tags.append('"interpolateboundary"')
        nargs.extend( [0, 0] )
        
        file.write('            %s %s %s %s \n' % (rib(tags), rib(nargs), rib(intargs), rib(floatargs)) )
                
        file.write('            "P" %s\n' % rib(P))
        export_primvars(file, ob, mesh, "facevertex")
        

    if motion_blur:
        file.write('        MotionEnd\n')
            
    bpy.data.meshes.remove(mesh)

def export_polygon_mesh(file, scene, ob, motion):
    mesh = create_mesh(scene, ob)
    
    motion_blur = ob.name in motion['deformation']
    
    if motion_blur:
        file.write('        MotionBegin %s\n' % rib(get_ob_subframes(scene, ob)))
        samples = motion['deformation'][ob.name]
    else:
        samples = [get_mesh(mesh)]
        
    for nverts, verts, P in samples:

        file.write('        PointsPolygons \n')
        file.write('            %s\n' % rib(nverts))
        file.write('            %s\n' % rib(verts))
        file.write('            "P" %s\n' % rib(P))
        export_primvars(file, ob, mesh, "facevarying")
        
    if motion_blur:
        file.write('        MotionEnd\n')
            
    bpy.data.meshes.remove(mesh)

def export_points(file, scene, ob, motion):
    rm = ob.renderman
    
    mesh = create_mesh(scene, ob)
    
    motion_blur = ob.name in motion['deformation']
    
    if motion_blur:
        file.write('        MotionBegin %s\n' % rib(get_ob_subframes(scene, ob)))
        samples = motion['deformation'][ob.name]
    else:
        samples = [get_mesh(mesh)]
        
    for nverts, verts, P in samples:

        file.write('        Points \n')
        file.write('            "P" %s\n' % rib(P))
        file.write('            "uniform string type" [ "%s" ] \n' % rm.primitive_point_type)
        file.write('            "constantwidth" [ %f ] \n' % rm.primitive_point_width)
            
    if motion_blur:
        file.write('        MotionEnd\n')
            
    bpy.data.meshes.remove(mesh)


def export_sphere(file, scene, ob, motion):
    rm = ob.renderman
    file.write('        Sphere %f %f %f %f \n' %
        (rm.primitive_radius, rm.primitive_zmin, rm.primitive_zmax, rm.primitive_sweepangle))
        
def export_cylinder(file, scene, ob, motion):
    rm = ob.renderman
    file.write('        Cylinder %f %f %f %f \n' %
        (rm.primitive_radius, rm.primitive_zmin, rm.primitive_zmax, rm.primitive_sweepangle))
        
def export_cone(file, scene, ob, motion):
    rm = ob.renderman
    file.write('        Cone %f %f %f \n' %
        (rm.primitive_height, rm.primitive_radius, rm.primitive_sweepangle))

def export_disk(file, scene, ob, motion):
    rm = ob.renderman
    file.write('        Disk %f %f %f \n' %
        (rm.primitive_height, rm.primitive_radius, rm.primitive_sweepangle))

def export_torus(file, scene, ob, motion):
    rm = ob.renderman
    file.write('        Torus %f %f %f %f %f \n' %
        (rm.primitive_majorradius, rm.primitive_minorradius, rm.primitive_phimin, rm.primitive_phimax, rm.primitive_sweepangle))

def is_dupli(ob):
    return ob.type == 'EMPTY' and ob.dupli_type != 'NONE'

def export_geometry_data(file, rpass, scene, ob, motion, force_prim=''):

    # handle duplis
    if is_dupli(ob):
        ob.dupli_list_create(scene)
        
        dupobs = [(dob.object, dob.matrix) for dob in ob.dupli_list]
        
        for dupob, dupob_mat in dupobs:
            if is_renderable(scene, dupob):
                export_object(file, rpass, scene, dupob, motion)
        
        ob.dupli_list_clear()
        return
        
    if force_prim == '':
        prim = detect_primitive(ob)
    else:
        prim = force_prim
    
    if prim == 'NONE':
        return

    if ob.data and ob.data.materials:
        for mat in [mat for mat in ob.data.materials if mat != None]:
            export_material(file, rpass, scene, mat)
            break
    
    if prim == 'SPHERE':
        export_sphere(file, scene, ob, motion)
    elif prim == 'CYLINDER':
        export_cylinder(file, scene, ob, motion)
    elif prim == 'CONE':
        export_cone(file, scene, ob, motion)
    elif prim == 'DISK':
        export_disk(file, scene, ob, motion)
    elif prim == 'TORUS':
        export_torus(file, scene, ob, motion)
    
    # curve only
    elif prim == 'CURVE':
        export_curve(file, scene, ob, motion) 
        
    # mesh only
    elif prim == 'POLYGON_MESH':
        export_polygon_mesh(file, scene, ob, motion)
    elif prim == 'SUBDIVISION_MESH':
        export_subdivision_mesh(file, scene, ob, motion)
    elif prim == 'POINTS':
        export_points(file, scene, ob, motion)
  
def export_geometry(file, rpass, scene, ob, motion):
    rm = ob.renderman
    
    if rm.geometry_source == 'BLENDER_SCENE_DATA':
        if ob in rpass.archives:
            archive_path = rib_path(auto_archive_path(rpass.paths, [ob]))        
            if os.path.exists(archive_path):
                file.write('        ReadArchive "%s"\n' % archive_path)
        else:
            export_geometry_data(file, rpass, scene, ob, motion)

    else:    
        file.write(geometry_source_rib(scene, ob))


def export_object(file, rpass, scene, ob, motion):
    rm = ob.renderman

    if ob.type in ('LAMP', 'CAMERA'): return
    
    if ob.parent:
        mat = ob.parent.matrix_world * ob.matrix_local
    else:
        mat = ob.matrix_world

    file.write('    AttributeBegin\n')
    file.write('        Attribute "identifier" "name" [ "%s" ]\n' % ob.name)

    # Shading
    if rm.shadingrate_override:
        file.write('        ShadingRate %f\n' % rm.shadingrate)
    file.write('        GeometricApproximation "motionfactor"  %d \n' % int(rm.geometric_approx_motion))
    file.write('        GeometricApproximation "focusfactor"  %d \n' % int(rm.geometric_approx_focus))
        
    file.write('        ShadingInterpolation "%s"\n' % rm.shadinginterpolation)
    
    file.write('        Matte  %d \n' % int(rm.matte))
    
    file.write('        Attribute "visibility" \n')
    file.write('            "integer camera" [ %d ]\n' % int(rm.visibility_camera))
    file.write('            "integer diffuse" [ %d ]\n' % int(rm.visibility_trace_diffuse))
    file.write('            "integer specular" [ %d ]\n' % int(rm.visibility_trace_specular))
    file.write('            "integer photon" [ %d ]\n' % int(rm.visibility_photons))
    file.write('            "integer transmission" [ %d ]\n' % int(rm.visibility_trace_transmission))
    
    file.write('        Attribute "shade" "string diffusehitmode" [ "%s" ] \n' % rm.trace_diffuse_hitmode)
    file.write('        Attribute "shade" "string specularhitmode" [ "%s" ] \n' % rm.trace_specular_hitmode)
    file.write('        Attribute "shade" "string transmissionhitmode" [ "%s" ] \n' % rm.trace_transmission_hitmode)
    
    file.write('        Attribute "trace" "displacements" [ %d ] \n' % int(rm.trace_displacements))
    file.write('        Attribute "trace" "samplemotion" [ %d ] \n' % int(rm.trace_samplemotion))

    if rm.export_coordsys:
        file.write('        CoordinateSystem "%s" \n' % ob.name)
    
	# Light Linking
    if rpass.light_shaders:
        file.write('\n        # Light Linking\n')
        for light in rm.light_linking:
            light_name = light.light
            if is_renderable(scene, scene.objects[light_name]):
                if light.illuminate.split(' ')[-1] == 'ON':
                    file.write('        Illuminate "%s" 1 \n' % light_name)
                elif light.illuminate.split(' ')[-1] == 'OFF':
                    file.write('        Illuminate "%s" 0 \n' % light_name)

    # Trace Sets
    file.write('\n        # Trace Sets\n')
    for set in rm.trace_set:
        set_name = set.group
        set_mode = '+'
        if set.mode.startswith('exclude'):
            set_mode = '-'
        file.write('        Attribute "grouping" "string membership" ["%s%s"] \n' % (set_mode,set_name))
	
    # Transformation
    if ob.name in motion['transformation']:
        file.write('\n        MotionBegin %s\n' % rib(get_ob_subframes(scene, ob)))
        
        for sample in motion['transformation'][ob.name]:
            file.write('            Transform %s\n' % rib(sample))
            
        file.write('        MotionEnd\n')
    else:
        file.write('        Transform %s\n' % rib(mat))

    export_geometry(file, rpass, scene, ob, motion)
    export_strands(file, rpass, scene, ob, motion)
    
    file.write('    AttributeEnd\n\n')
    
    # Particles live in worldspace, export as separate object
    export_particles(file, rpass, scene, ob, motion)

def empty_motion():
    motion = {}
    motion['transformation'] = {}
    motion['deformation'] = {}
    return motion

def export_motion_ob(scene, motion, ob):

    prim = detect_primitive(ob)

    # object transformation animation
    if ob.animation_data != None or ob.constraints:
        if ob.name not in motion['transformation'].keys():
            motion['transformation'][ob.name] = []
        
        if ob.parent:
            mat = ob.parent.matrix_world * ob.matrix_local
        else:
            mat = ob.matrix_world
        
        motion['transformation'][ob.name].insert(0, mat.copy())

    # recursive dupli sub-objects
    if is_dupli(ob):
        ob.dupli_list_create(scene)

        dupobs = [(dob.object, dob.matrix) for dob in ob.dupli_list]
        for dupob, dupob_mat in dupobs:
            if not dupob.hide_render:
                export_motion_ob(scene, motion, dupob)
        ob.dupli_list_clear()

    # particles
    for psys in ob.particle_systems:
        pname = psys_motion_name(ob, psys)
        
        if pname not in motion['deformation'].keys():
            motion['deformation'][pname] = []
        
        if psys.settings.type == 'EMITTER':
            motion['deformation'][pname].insert(0, get_particles(scene, ob, psys));
        if psys.settings.type == 'HAIR':
            motion['deformation'][pname].insert(0, get_strands(ob, psys));

    if prim in ('POLYGON_MESH', 'SUBDIVISION_MESH', 'POINTS'):
        # fluid sim deformation - special case
        if is_deforming_fluid(ob):
            if ob.name not in motion['deformation'].keys():
                motion['deformation'][ob.name] = []
            
            motion['deformation'][ob.name].insert(0, get_fluid_mesh(scene, ob))          
        
        # deformation animation
        if is_deforming(ob):
            if ob.name not in motion['deformation'].keys():
                motion['deformation'][ob.name] = []
            
            mesh = create_mesh(scene, ob)
            motion['deformation'][ob.name].insert(0, get_mesh(mesh))
            bpy.data.meshes.remove(mesh)

    # not working yet, needs access to post-deform-modifier curve data
    elif prim == 'CURVE':
        if is_deforming(ob):
            if ob.name not in motion['deformation'].keys():
                motion['deformation'][ob.name] = []
            
            motion['deformation'][ob.name].insert(0, get_curve(ob.data))

# Collect and store motion blur transformation data in a pre-process.
# More efficient, and avoids too many frame updates in blender.
def export_motion(rpass, scene):
    motion = empty_motion()
    origframe = scene.frame_current
    
    if not rpass.motion_blur:
        return motion

    # get a de-duplicated set of all possible numbers of motion segments 
    # from renderable objects in the scene, and global scene settings
    all_segs = [ob.renderman.motion_segments for ob in rpass.objects if ob.renderman.motion_segments_override]
    all_segs.append(scene.renderman.motion_segments)
    all_segs = set(all_segs)
    
    # the aim here is to do only a minimal number of scene updates, 
    # so we process objects in batches of equal numbers of segments
    # and update the scene only once for each of those unique fractional frames per segment set
    for segs in all_segs:

        if segs == scene.renderman.motion_segments:
            motion_obs = [ob for ob in rpass.objects if not ob.renderman.motion_segments_override]
        else:
            motion_obs = [ob for ob in rpass.objects if ob.renderman.motion_segments == segs]

        # prepare list of frames/sub-frames in advance, ordered from future to present,
        # to prevent too many scene updates (since loop ends on current frame/subframe)
        for sub in get_subframes(segs):
            scene.frame_set(origframe, 1.0-sub)
            
            for ob in motion_obs:
                export_motion_ob(scene, motion, ob)
                        
    return motion


def export_objects(file, rpass, scene, motion):

    file.write('    ## Objects \n\n')

    # export the objects to RIB recursively
    for ob in rpass.objects:
        export_object(file, rpass, scene, ob, motion)


def export_archive(scene, objects, filepath="", archive_motion=True, animated=True, frame_start=1, frame_end=3):

    init_env(scene)
    paths = initialise_paths(scene)    
    rpass = RPass(scene, objects, paths)
    
    if frame_start == frame_end:
        animated = False
    
    if filepath == "":
        filepath = auto_archive_path(paths, objects, create_folder=True)
    
    for frame in range(frame_start, frame_end+1):
        scene.frame_set(frame)
        
        motion = export_motion(rpass, scene) if archive_motion else empty_motion()
        ribpath = anim_archive_path(filepath, frame) if animated else filepath

        
        file = open(ribpath, "w")
        export_header(file)
        
        for ob in rpass.objects:
            export_geometry_data(file, rpass, scene, ob, motion)
    
        file.close()
    
    return file.name


def export_integrator(file, rpass, scene):
    rm = scene.world.renderman

    '''
    file.write('        Shader "integrator" "inte" \n')

    
    for sp in shaderparameters_from_class(rm.integrator2):
        file.write('            "%s %s" %s\n' % (sp.data_type, sp.name, rib(sp.value)))
    '''

    '''
    parameterlist = rna_to_shaderparameters(scene, rm.integrator, 'surface')
    for sp in parameterlist:
		# BBM addition begin
        if sp.is_array:
            file.write('            "%s %s[%d]" %s\n' % (sp.data_type, sp.name, len(sp.value), rib(sp.value,is_cosh_array=True)))
        else:
		# BBM addition end
            file.write('            "%s %s" %s\n' % (sp.data_type, sp.name, rib(sp.value)))
    '''

# BBM addition begin
def export_world_coshaders(file, rpass, scene):
    rm = scene.world.renderman

    file.write('    ## World Co-shaders\n')
    for cosh_item in rm.coshaders.items():
        coshader_handle = cosh_item[0]
        coshader_name = cosh_item[1].shader_shaders.active
        file.write('    Shader "%s" "%s"\n' % (coshader_name, coshader_handle) )
        parameterlist = rna_to_shaderparameters(scene, cosh_item[1], 'shader')
        for sp in parameterlist:
            if sp.is_array:
                file.write('        "%s %s[%d]" %s\n' % (sp.data_type, sp.name, len(sp.value), rib(sp.value,is_cosh_array=True)))
            else:
                file.write('        "%s %s" %s\n' % (sp.data_type, sp.name, rib(sp.value)))
				
# BBM addition end

def export_global_illumination_lights(file, rpass, scene):
    rm = scene.world.renderman
    
    #if scene.renderman.recompile_shaders:
        #shader_recompile(scene, rm.gi_primary.light_shaders.active)
        #shader_recompile(scene, rm.gi_secondary.light_shaders.active)
    
    if not rm.global_illumination: return
    
    file.write('    ## GI lights \n\n')
    
    file.write('    AttributeBegin\n')
    file.write('    Attribute "light" "emitphotons" [ "%s" ] \n' % ('on' if rm.gi_primary.light_shaders.active == 'gi_photon' else 'off'))
    file.write('    LightSource "%s" "indirectambient" \n' % rm.gi_primary.light_shaders.active)
    
    parameterlist = rna_to_shaderparameters(scene, rm.gi_primary, 'light')
   
    # parameter list
    for sp in parameterlist:
		# BBM addition begin
        if sp.is_array:
            file.write('            "%s %s[%d]" %s\n' % (sp.data_type, sp.name, len(sp.value), rib(sp.value,is_cosh_array=True)))
        else:
		# BBM addition end
            file.write('            "%s %s" %s\n' % (sp.data_type, sp.name, rib(sp.value)))
        
    file.write('    AttributeEnd\n')
    file.write('    Illuminate "indirectambient" 1 \n');
    file.write('\n');

def export_global_illumination_settings(file, rpass, scene):
    rm = scene.world.renderman
    gi_primary = rm.gi_primary
    gi_secondary = rm.gi_secondary
    
    if not rm.global_illumination: return
    
    file.write('Option "user" "string gi_primary" [ "%s" ] \n' % gi_primary.light_shaders.active)
    file.write('Option "user" "string gi_secondary" [ "%s" ] \n' % gi_secondary.light_shaders.active)

    if gi_primary.light_shaders.active == 'gi_pointcloud':
        if rpass.type == 'ptc_indirect':
            file.write('Option "user" "string delight_gi_ptc_bake_path" [ "%s" ] \n' % rib_path(rpass.paths["gi_ptc_bake_path"]))
            
    if gi_secondary.light_shaders.active == 'gi_photon' or \
        gi_primary.light_shaders.active == 'gi_photon':

        # XXX todo, figure out decisions for photon emission
        
        file.write('Option "photon" "integer emit" [ %d ] \n' % gi_secondary.photon_count)
        
        file.write('Attribute "photon" \n')
        file.write('    "string globalmap" [ "%s" ] \n' %  gi_secondary.photon_map_global)
        file.write('    "string causticmap" [ "%s" ] \n' %  gi_secondary.photon_map_caustic)
        
    file.write('\n\n')


def render_get_resolution(r):
    xres= int(r.resolution_x*r.resolution_percentage*0.01)
    yres= int(r.resolution_y*r.resolution_percentage*0.01)
    return xres, yres


def render_get_aspect(r, camera=None):
    xres, yres = render_get_resolution(r)
    
    xratio= xres*r.pixel_aspect_x/200.0
    yratio= yres*r.pixel_aspect_y/200.0

    if camera == None or camera.type != 'PERSP':
        fit = 'AUTO'
    else:
        fit = camera.sensor_fit
    
    if fit == 'HORIZONTAL' or fit == 'AUTO' and xratio > yratio:
        aspectratio= xratio/yratio
        xaspect= aspectratio
        yaspect= 1.0
    elif fit == 'VERTICAL' or fit == 'AUTO' and yratio > xratio:
        aspectratio= yratio/xratio;
        xaspect= 1.0;
        yaspect= aspectratio;
    else:
        aspectratio = xaspect = yaspect = 1.0
        
    return xaspect, yaspect, aspectratio


def export_render_settings(file, rpass, scene):
    rm = scene.renderman
    r = scene.render
    
    file.write('Option "render" "integer nthreads" %d\n' % rm.threads)
    file.write('Option "trace" "integer maxdepth" [%d]\n' % rm.max_trace_depth)
    file.write('Attribute "trace" "integer maxspeculardepth" [%d]\n' % rm.max_specular_depth)
    file.write('Attribute "trace" "integer maxdiffusedepth" [%d]\n' % rm.max_diffuse_depth)
    file.write('Option "limits" "integer eyesplits" %d\n' % rm.max_eye_splits)
    file.write('Option "trace" "float approximation" %f\n' % rm.trace_approximation)
    if rm.use_statistics:
        file.write('Option "statistics" "endofframe" %d "filename" "/tmp/stats.txt" \n' % rm.statistics_level    )
    
    rpass.resolution = render_get_resolution(r)

    file.write('Format %d %d %f\n' % (rpass.resolution[0], rpass.resolution[1], 1.0))
    file.write('PixelSamples %d %d \n' % (rm.pixelsamples_x, rm.pixelsamples_y))
    file.write('PixelFilter "%s" %d %d \n' % (rm.pixelfilter, rm.pixelfilter_x, rm.pixelfilter_y))
    file.write('ShadingRate %f \n' % rm.shadingrate )
    file.write('\n')

def export_render_settings_preview(file, rpass, scene):
    r = scene.render
    rpass.resolution = render_get_resolution(r)
    
    file.write('Format %d %d %f\n' % (rpass.resolution[0], rpass.resolution[1], 1.0))
    file.write('PixelSamples 2 2 \n')
    file.write('PixelFilter "sinc" 2 2 \n')

def export_camera_matrix(file, scene, ob, motion):
    motion_blur = ob.name in motion['transformation']
    
    if motion_blur:
        file.write('        MotionBegin %s\n' % rib(get_ob_subframes(scene, ob)))
        samples = motion['transformation'][ob.name]
    else:
        samples = [ob.matrix_world]
        
    for sample in samples:
            mat = sample
            loc = sample.translation
            rot = sample.to_euler()
            
            s = Matrix(([1,0,0,0],[0,1,0,0],[0,0,-1,0],[0,0,0,1]))
            r = Matrix.Rotation(-rot[0], 4, 'X')
            r *= Matrix.Rotation(-rot[1], 4, 'Y')
            r *= Matrix.Rotation(-rot[2], 4, 'Z')
            l = Matrix.Translation(-loc)
            m = s * r * l

            file.write('Transform %s\n' % rib(m))

    if motion_blur:
        file.write('        MotionEnd\n')

def export_camera(file, scene, motion):
    
    if not scene.camera or scene.camera.type != 'CAMERA':
        return
        
    r = scene.render
    ob = scene.camera    
    cam = ob.data
    rm = scene.renderman
    
    xaspect, yaspect, aspectratio = render_get_aspect(r, cam)
    
    if rm.depth_of_field:
        if cam.dof_object:
            dof_distance = (ob.location - cam.dof_object.location).length
        else:
            dof_distance = cam.dof_distance
        file.write('DepthOfField %f 1.0 %f\n' % (rm.fstop, dof_distance))
        
    if scene.renderman.motion_blur:
        file.write('Shutter %f %f\n' % (rm.shutter_open, rm.shutter_close))
        file.write('Option "shutter" "efficiency" [ %f %f ] \n' % (rm.shutter_efficiency_open, rm.shutter_efficiency_close))

    file.write('Clipping %f %f\n' % (cam.clip_start, cam.clip_end))
    
    if cam.type == 'PERSP':
        lens= cam.lens
        
        sensor = cam.sensor_height if cam.sensor_fit == 'VERTICAL' else cam.sensor_width

        fov= 360.0*math.atan((sensor*0.5)/lens/aspectratio)/math.pi

        file.write('Projection "perspective" "fov" %f\n' % fov)
    else:
        lens= cam.ortho_scale
        xaspect= xaspect*lens/(aspectratio*2.0)
        yaspect= yaspect*lens/(aspectratio*2.0)
        file.write('Projection "orthographic"\n')

    file.write('ScreenWindow %f %f %f %f\n' % (-xaspect, xaspect, -yaspect, yaspect))

    export_camera_matrix(file, scene, ob, motion)
    file.write('\n')

def export_camera_render_preview(file, scene):
    r = scene.render

    xaspect, yaspect, aspectratio = render_get_aspect(r)

    file.write('Clipping 0.100000 100.000000 \n')
    file.write('Projection "perspective" "fov" 28.841546 \n')
    file.write('ScreenWindow %f %f %f %f\n' % (-xaspect, xaspect, -yaspect, yaspect))

    file.write('Transform [ 0.685881 -0.317370 -0.654862 0.000000 0.727634 0.312469 0.610666 0.000000 -0.010817 0.895343 -0.445245 0.000000 0.040019 -0.661400 6.220541 1.000000 ] \n')
    

def export_camera_shadowmap(file, scene, ob, motion):
    lamp = ob.data
    rm = lamp.renderman
    srm = scene.renderman
    
    file.write('Format %d %d %f\n' % (int(rm.shadow_map_resolution), int(rm.shadow_map_resolution), 1.0))
    
    if rm.shadow_transparent:
        file.write('PixelSamples %d %d \n' % 
                    (rm.pixelsamples_x, rm.pixelsamples_y))
        file.write('PixelFilter "box" 1 1 \n')

    file.write('ShadingRate %f \n' % rm.shadingrate )
    file.write('\n') 
    
    if rm.light_shaders.active != '':
        params = rna_to_shaderparameters(scene, rm, 'light')
        for sp in params:
            if sp.meta == 'distant_scale':
                xaspect = yaspect = sp.value / 2.0
                file.write('Projection "orthographic"\n')
                file.write('ScreenWindow %f %f %f %f\n' % (-xaspect, xaspect, -yaspect, yaspect))
                
    '''
    if lamp.type == 'SPOT':
        file.write('Clipping %f %f\n' % (lamp.shadow_buffer_clip_start, lamp.shadow_buffer_clip_end))
        file.write('Projection "perspective" "fov" %f\n' % (lamp.spot_size*(180.0/math.pi)))
    elif lamp.type == 'SUN':
        file.write('Clipping %f %f\n' % (1, lamp.distance))
        lens= lamp.renderman.ortho_scale
        xaspect= lens/2.0
        yaspect= lens/2.0
        file.write('Projection "orthographic"\n')    
        file.write('ScreenWindow %f %f %f %f\n' % (-xaspect, xaspect, -yaspect, yaspect))
    '''
    if scene.renderman.motion_blur:
        file.write('Shutter %f %f\n' % (srm.shutter_open, srm.shutter_close))
        file.write('Option "shutter" "efficiency" [ %f %f ] \n' % 
            (srm.shutter_efficiency_open, srm.shutter_efficiency_close))    
    
    export_camera_matrix(file, scene, ob, motion)
    
    file.write('\n')
            

def export_searchpaths(file, paths):
    file.write('Option "searchpath" "string shader" "%s"\n' % ':'.join(path_list_convert(paths['shader'], to_unix=True)))
    file.write('Option "searchpath" "string texture" "%s"\n' % ':'.join(path_list_convert(paths['texture'], to_unix=True)))
    file.write('Option "searchpath" "string procedural" "%s"\n' % ':'.join(path_list_convert(paths['procedural'], to_unix=True)))
    file.write('Option "searchpath" "string archive" "%s"\n' % ':'.join(path_list_convert(paths['archive'], to_unix=True)))
    file.write('\n')

def export_header(file):
    file.write('# Generated by 3Delight exporter for Blender, v%s.%s.%s \n' % (addon_version[0], addon_version[1], addon_version[2]))
    file.write('# By Matt Ebb - matt (at) mattebb (dot) com\n\n')

def ptc_generate_required(scene):
    rm = scene.world.renderman
    if not rm.global_illumination: return False
    if not rm.gi_primary.light_shaders.active == 'gi_pointcloud': return False
    if not rm.gi_secondary.ptc_generate_auto: return False
    return True

def shadowmap_generate_required(scene, ob):
    if ob.type != 'LAMP': return False
    
    rm = ob.data.renderman

    if shader_requires_shadowmap(scene, rm, 'light'):
        return True
    
    '''
    if not ob.data.type in ('SPOT', 'SUN'): return False
    if not rm.shadow_method == 'SHADOW_MAP': return False
    if not rm.shadow_map_generate_auto: return False
    '''
    return False


def make_ptc_indirect(paths, scene, info_callback):
    if not ptc_generate_required(scene):
        return
    
    info_callback('Creating Point Clouds')
    
    rm = scene.world.renderman
    
    rpass = RPass(scene, renderable_objects(scene), paths, "ptc_indirect")
    
    # prepare paths for point cloud and rib output
    paths['gi_ptc_bake_path'] = user_path(rm.gi_secondary.ptc_path, scene=scene)
    ptc_rib = os.path.splitext(paths['gi_ptc_bake_path'])[0] + '.rib'
    
    paths['pointcloud_dir'] = os.path.dirname(paths['gi_ptc_bake_path'])
    if not os.path.exists(paths['pointcloud_dir']):
        os.mkdir(paths['pointcloud_dir'])

    file = open(ptc_rib, "w")
    
    motion = empty_motion()
    
    export_header(file)
    export_searchpaths(file, paths)
    export_inline_rib(file, rpass, scene)
    
    scene.frame_set(scene.frame_current)
    file.write('FrameBegin %d\n\n' % scene.frame_current)
    
    export_camera(file, scene, motion)
    export_render_settings(file, rpass, scene)
    export_global_illumination_settings(file, rpass, scene)

    # uses ptc_write_vol atmosphere shader on all surfaces 
    # to bake shading to a point cloud
    
    # ptc related attributes
    file.write('Attribute "cull" "hidden" [0] \n')
    file.write('Attribute "cull" "backfacing" [0] \n')
    file.write('Attribute "dice" "rasterorient" [0] \n')
    file.write('PixelSamples 1 1 \n')
    file.write('PixelFilter "box" 1 1 \n')
    file.write('ShadingRate %f \n' % rm.gi_secondary.ptc_shadingrate)

    file.write('WorldBegin\n\n')
    
    export_global_illumination_lights(file, rpass, scene)
    export_scene_lights(file, rpass, scene)    
    export_objects(file, rpass, scene, motion)
    
    file.write('WorldEnd\n\n')
    file.write('FrameEnd\n\n')
    
    file.close()
    
    # render and bake the pointcloud
    # set cwd to pointcloud_dir to work around windows paths issue -
    # bake3d() doesn't seem to like baking windows absolute paths, so we use relative
    proc = subprocess.Popen([rpass.paths['rman_binary'], ptc_rib], cwd=rpass.paths['export_dir']).wait()

def make_shadowmaps(paths, scene, info_callback):

    info_callback('Creating Shadow maps')

    render_objects = [o for o in renderable_objects(scene) if o.renderman.visibility_shadowmaps]
    
    rpass = RPass(scene, render_objects, paths, "shadowmap")    
    
    shadow_lamps = [ob for ob in rpass.objects if shadowmap_generate_required(scene, ob) ]
    
    for ob in shadow_lamps:
        rm = ob.data.renderman
        
        # prepare paths for shadow map and rib output
        paths['shadow_map'] = shadowmap_path(scene, ob)
        paths['shadowmap_dir'] = os.path.dirname(paths['shadow_map'])        
        if not os.path.exists(rpass.paths['shadowmap_dir']):
            os.mkdir(rpass.paths['shadowmap_dir'])
        
        shadow_rib = os.path.splitext(paths['shadow_map'])[0] + '.rib'
        file = open(shadow_rib, "w")
        
        export_header(file)
        export_searchpaths(file, rpass.paths)
        
        if rm.shadow_transparent:
            file.write('Display "%s" "dsm" "rgbaz" \n\n' % rib_path( paths['shadow_map'], escape_slashes=True ))
        else:
            file.write('Display "%s" "shadowmap" "z" \n\n' % rib_path( paths['shadow_map'], escape_slashes=True ))
        

        export_inline_rib(file, rpass, scene, lamp=ob.data)
        
        scene.frame_set(scene.frame_current)
        file.write('FrameBegin %d\n\n' % scene.frame_current)
        
        motion = export_motion(rpass, scene) 
        
        export_camera_shadowmap(file, scene, ob, motion)
        
        file.write('WorldBegin\n\n')
        
        export_objects(file, rpass, scene, motion)
        
        file.write('WorldEnd\n\n')
        file.write('FrameEnd\n\n')
        
        file.close()
        
        # render the shadow map
        proc = subprocess.Popen([rpass.paths['rman_binary'], shadow_rib]).wait()


def find_preview_material(scene):
    for o in renderable_objects(scene):
        if o.type not in ('MESH', 'EMPTY'):
            continue
        if len(o.data.materials) > 0:
            mat = o.data.materials[0]
            if mat != None and mat.name == 'preview':
                return mat

# --------------- Hopefully temporary --------------- #

def get_instance_materials(ob):
	obmats = []
	# Grab materials attached to object instances ...
	if hasattr(ob, 'material_slots'):
		for ms in ob.material_slots:
			obmats.append(ms.material)
	# ... and to the object's mesh data
	if hasattr(ob.data, 'materials'):
		for m in ob.data.materials:
			obmats.append(m)
	return obmats

def find_preview_material(scene):
    # taken from mitsuba exporter
    objects_materials = {}

    for object in renderable_objects(scene):
        for mat in get_instance_materials(object):
            if mat is not None:
                if not object.name in objects_materials.keys(): objects_materials[object] = []
                objects_materials[object].append(mat)

    # find objects that are likely to be the preview objects
    preview_objects = [o for o in objects_materials.keys() if o.name.startswith('preview')]
    if len(preview_objects) < 1:
        return

    # find the materials attached to the likely preview object
    likely_materials = objects_materials[preview_objects[0]]
    if len(likely_materials) < 1:
        return

    return likely_materials[0]
    
# --------------- End Hopefully temporary --------------- #

def preview_model(mat):
    if mat.preview_render_type == 'SPHERE':
        return '        Sphere 1 -1 1 360 \n'
    else: # CUBE
        return '        Scale 0.75 0.75 0.75 \n \
        Translate 0.0 0.0 0.01 \n \
        PointsPolygons \n \
        [ 4 4 4 4 4 4 ] \n \
        [ 0 1 2 3 4 7 6 5 0 4 5 1 1 5 6 2 2 6 7 3 4 0 3 7 ] \n \
        "P" [ 1 1 -1  1 -1 -1  -1 -1 -1  -1 1 -1  1 1 1  1 -1 1  -1 -1 1  -1 1 1 ] \n'
        

def write_preview_rib(rpass, scene):

    previewdir = os.path.join(rpass.paths['blender_exporter'], "preview")
    preview_rib_data_path = rib_path(os.path.join(previewdir, "preview_scene.rib"))
    
    rpass.paths['rib_output'] = os.path.join(previewdir, "preview.rib")
    rpass.paths['render_output'] = os.path.join(previewdir, "preview.tif")
    rpass.paths['export_dir'] = os.path.dirname(rpass.paths['rib_output'])
    
    if not os.path.exists(rpass.paths['export_dir']):
        os.mkdir(rpass.paths['export_dir'])
    
    file = open(rpass.paths['rib_output'], "w")
    
    export_header(file)
    export_searchpaths(file, rpass.paths)
    
    # temporary tiff display to be read back into blender render result
    file.write('Display "%s" "tiff" "rgba" "quantize" [0 0 0 0] \n\n' % os.path.basename(rpass.paths['render_output']))
    
    file.write('FrameBegin 1 \n\n')
    
    export_camera_render_preview(file, scene)
    export_render_settings_preview(file, rpass, scene)

    file.write('WorldBegin\n\n')
    
    # preview scene: walls, lights
    file.write('        ReadArchive "%s" \n\n' % preview_rib_data_path)
    
    # preview model and material
    file.write('    AttributeBegin\n')
    file.write('    Attribute "identifier" "name" [ "Preview" ] \n')
    file.write('        Translate 0 0 0.75 \n')
    file.write('        Attribute "visibility" \n \
            "integer camera" [ 1 ] \n \
            "integer trace" [ 1 ] \n \
            "integer photon" [ 1 ] \n \
            "string transmission" ["opaque"] \n ')
    file.write('        Attribute "trace" "displacements" [1] \n')
    
    mat = find_preview_material(scene)
    export_material(file, rpass, scene, mat)
    file.write( preview_model(mat)  )
    file.write('    AttributeEnd\n')
    
    file.write('WorldEnd\n\n')
    file.write('FrameEnd\n\n')

def export_display(file, rpass, scene):
    rm = scene.renderman
    
    if rm.display_driver == 'AUTO':
        # temporary tiff display to be read back into blender render result
        file.write('Display "%s" "tiff" "rgba" "quantize" [0 0 0 0] \n\n' % os.path.basename(rpass.paths['render_output']))
    elif rm.display_driver == 'idisplay':
        rpass.options.append('-id')
    elif rm.display_driver == 'tiff':
        file.write('Display "%s" "tiff" "rgba" "quantize" [0 0 0 0] \n\n' % rib_path(user_path(rm.path_display_driver_image, scene=scene)))

def export_hider(file, rpass, scene):
    rm = scene.renderman
    
    if rm.hider == 'hidden':
        file.write('Hider "hidden" \n')
        file.write('    "string depthfilter" "%s" \n' % rm.hidden_depthfilter)
        file.write('    "integer jitter" [%d] \n' % rm.hidden_jitter)
        file.write('    "integer samplemotion" [%d] \n' % rm.hidden_samplemotion)
        file.write('    "integer extrememotiondof" [%d] \n' % rm.hidden_extrememotiondof)
        file.write('    "integer maxvpdepth" [%d] \n' % rm.hidden_maxvpdepth)
        if rm.hidden_depthfilter == 'midpoint':
            file.write('"float midpointratio" [%f] \n' % rm.hidden_midpointratio)
        
    elif rm.hider == 'raytrace':
        file.write('Hider "raytrace" \n')
        file.write('    "int progressive" [%d] \n' % rm.raytrace_progressive)
	
	
def export_inline_rib(file, rpass, scene, lamp=None ):
    rm = scene.renderman
	
    if lamp != None and rpass.type == 'shadowmap':
        rm = lamp.renderman
        txts = rm.shd_inlinerib_texts
    elif rpass.type == 'ptc_indirect':
        txts = rm.bak_inlinerib_texts
    else:
        txts = rm.bty_inlinerib_texts

    file.write( '\n# Inline RIB \n' )

    for txt in txts:
        textblock = bpy.data.texts[txt.name]
        for l in textblock.lines:
            file.write( '%s \n' % l.body )    

    file.write( '\n' )

def write_rib(rpass, scene, info_callback):
    info_callback('Generating RIB')
    
    # precalculate motion blur data
    motion = export_motion(rpass, scene)
    
    file = open(rpass.paths['rib_output'], "w")
    
    export_header(file)
    export_searchpaths(file, rpass.paths)
    
    export_display(file, rpass, scene)
    export_hider(file, rpass, scene)
    export_inline_rib(file, rpass, scene)
    
    scene.frame_set(scene.frame_current)
    file.write('FrameBegin %d\n\n' % scene.frame_current)
    
    export_camera(file, scene, motion)
    export_render_settings(file, rpass, scene)
    #export_global_illumination_settings(file, rpass, scene)
    
    file.write('WorldBegin\n\n')

    #export_global_illumination_lights(file, rpass, scene)
    #export_world_coshaders(file, rpass, scene) # BBM addition
    export_integrator(file, rpass, scene)
    export_scene_lights(file, rpass, scene)
    export_objects(file, rpass, scene, motion)
    
    file.write('WorldEnd\n\n')

    file.write('FrameEnd\n\n')

def initialise_paths(scene):
    paths = {}
    paths['rman_binary'] = scene.renderman.path_renderer
    paths['texture_optimiser'] = scene.renderman.path_texture_optimiser
    
    paths['blender_exporter'] = os.path.dirname(os.path.realpath(__file__))
   
    paths['rib_output'] = user_path(scene.renderman.path_rib_output, scene=scene)
    paths['export_dir'] = os.path.dirname(paths['rib_output'])
    
    if not os.path.exists(paths['export_dir']):
        os.mkdir(paths['export_dir'])
    
    paths['render_output'] = os.path.join(paths['export_dir'], 'buffer.tif')
    
    paths['shader'] = get_path_list_converted(scene.renderman, 'shader')
    paths['texture'] = get_path_list_converted(scene.renderman, 'texture')
    paths['procedural'] = get_path_list_converted(scene.renderman, 'procedural')
    paths['archive'] = get_path_list_converted(scene.renderman, 'archive')
    
    return paths

def anim_archive_path(filepath, frame):
    if filepath.find("#") != -1:
        ribpath = make_frame_path(filepath, fr)
    else:
        ribpath = os.path.splitext(filepath)[0] + "." + str(frame).zfill(4) + os.path.splitext(filepath)[1]
    return ribpath

'''
def export_ptc(scene, objects, filepath=""):
    
    paths = initialise_paths(scene)    
    rpass = RPass(scene, objects, paths)
    motion = empty_motion()
    
    file = open(filepath, "w")
    
    export_header(file)
    
    file.write('WorldBegin\n\n')
    
    export_geometry_data(file, rpass, scene, ob, motion, force_prim='POINTS')
    
    file.write('WorldEnd\n\n')
    
    file.close()
'''    

def write_auto_archives(paths, scene, info_callback):
    for ob in archive_objects(scene):
        export_archive(scene, [ob], archive_motion=True, frame_start=scene.frame_current, frame_end=scene.frame_current)
    

def available_licenses():
    output = subprocess.check_output(["licutils", "serverlicenses"]).decode().split('\n')
        
    if len(output) < 1:
        return false
    
    total = int(output[5].rpartition(':')[2])
    used = int(output[6].rpartition(':')[2])
    print("total licenses %d , used licenses: %d" % (total, used))
    return (total - used)
    








def init(engine):
    pass

def free(engine):
    if hasattr(engine, "rpass"):
        del engine.rpass
    
def update_preview(engine, data, scene):
    
    init_env(data.scenes[0])
    
    # XXX use this bpy.data.scenes[0] hack to take paths from 
    # the first scene, rather than the preview scene.
    # Not reliable, need to be fixed properly!
    engine.rpass = RPass(scene, renderable_objects(scene), initialise_paths(data.scenes[0]))
    
    auto_optimise_textures(engine.rpass.paths, scene)
    
    # preview render update function is still blocked
    # rna_types_initialise(scene)

    write_preview_rib(engine.rpass, scene)


def update_scene(engine, data, scene):
    
    init_env(scene)
    
    engine.rpass = RPass(scene, renderable_objects(scene), initialise_paths(scene))

    def info_callback(txt):
        engine.update_stats("", "3Delight: " + txt)
    
    auto_optimise_textures(engine.rpass.paths, scene)

    rna_types_initialise(scene)

    write_auto_archives(engine.rpass.paths, scene, info_callback)

    make_ptc_indirect(engine.rpass.paths, scene, info_callback)
    make_shadowmaps(engine.rpass.paths, scene, info_callback)
    
    write_rib(engine.rpass, scene, info_callback)

    engine.rpass.do_render = True if scene.renderman.output_action == 'EXPORT_RENDER' else False


# hopefully temporary
def update(engine, data, scene):
    if engine.is_preview:
        update_preview(engine, data, scene)
    else:
        update_scene(engine, data, scene)

# hopefully temporary
def render(engine):
    if engine.is_preview:
        render_preview(engine)
    else:
        render_scene(engine)


def render_scene(engine):
    if engine.rpass.do_render:
        render_rib(engine)
    
def render_preview(engine):
    pass
    #render_rib(engine)


def render_rib(engine):
    DELAY = 0.1

    try:
        os.remove(engine.rpass.paths['render_output']) # so as not to load the old file
    except:
        pass
    
    render_output = engine.rpass.paths['render_output']
    
#XXX    engine.rpass.options.append('-q')
    #engine.rpass.options.append('-Progress')
    
    cmd = [engine.rpass.paths['rman_binary']] + engine.rpass.options + [engine.rpass.paths['rib_output']]
    
    cdir = os.path.dirname(engine.rpass.paths['rib_output'])
    process = subprocess.Popen(cmd, cwd=cdir, stdout=subprocess.PIPE)


    # Wait for the file to be created
    while not os.path.exists(render_output):
        if engine.test_break():
            try:
                process.kill()
            except:
                pass
            break

        if process.poll() != None:
            engine.update_stats("", "3Delight: Failed")
            break

        time.sleep(DELAY)
    
    if os.path.exists(render_output):
        engine.update_stats("", "3Delight: Rendering")
    
        prev_size = -1
    
        def update_image():
            result = engine.begin_result(0, 0, engine.rpass.resolution[0], engine.rpass.resolution[1])
            lay = result.layers[0]
            # possible the image wont load early on.
            try:
                lay.load_from_file(render_output)
            except:
                pass
            engine.end_result(result)


        # Update while rendering
        while True:    
            if process.poll() is not None:
                update_image()
                break
    
            # user exit
            if engine.test_break():
                try:
                    process.kill()
                except:
                    pass
                break
    
            # check if the file updated
            new_size = os.path.getsize(render_output)
    
            if new_size != prev_size:
                update_image()
                prev_size = new_size
    
            time.sleep(DELAY)


def register():
    pass
     #bpy.utils.register_module(__name__)

def unregister():
    pass
     #bpy.utils.unregister_module(__name__)