# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 Brian Savery
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
import math
import os
from mathutils import Matrix, Vector, Quaternion

from . import bl_info

from .util import rib, rib_path, rib_ob_bounds
from .util import make_frame_path
from .util import init_env
from .util import get_sequence_path
from .util import user_path
from .util import path_list_convert
from .util import get_properties

addon_version = bl_info['version']

# helper functions for parameters
from .nodes import export_shader_nodetree, get_textures


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
    if rm.filter_type in ('catmull-rom', 'bessel') and \
            rm.filter_window != 'DEFAULT':
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
# Generate an automatic path to write an archive when 
#'Export as Archive' is enabled
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
    deforming_modifiers = ['ARMATURE', 'CAST', 'CLOTH', 'CURVE', 'DISPLACE', 
                            'HOOK', 'LATTICE', 'MESH_DEFORM', 'SHRINKWRAP', 
                            'SIMPLE_DEFORM', 'SMOOTH', 'WAVE', 'SOFT_BODY', 
                            'SURFACE']
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
    print("get_mesh: [%s]." % mesh.name)
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
        uvs.append( 1.0 - uvloop.uv.y )     
        # renderman expects UVs flipped vertically from blender

    return uvs


# requires facevertex interpolation
def get_mesh_vcol(mesh, name=""):
    vcol_layer = mesh.vertex_colors[name] if name != "" \
         else mesh.vertex_colors.active
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
            weights.extend( [g.weight for g in v.groups \
                    if g.group == vgroup.index ] )
            
    return weights


def get_primvars(ob, geo, interpolation=""):
    primvars = {}
    #if ob.type != 'MESH':
    #    return
    
    rm = ob.data.renderman

    interpolation = 'facevertex' if interpolation == '' else interpolation
    
    # default hard-coded prim vars
    if rm.export_smooth_normals and ob.renderman.primitive in \
            ('AUTO', 'POLYGON_MESH', 'SUBDIVISION_MESH'):
        N = get_mesh_vertex_N(geo)
        if N is not None:
            primvars["varying normal N"] = N
    if rm.export_default_uv:
        uvs = get_mesh_uv(geo)
        if uvs is not None:
            primvars["%s float[2] st" % interpolation] = uvs
    if rm.export_default_vcol:
        vcols = get_mesh_vcol(geo)
        if vcols is not None:
            primvars["%s color Cs" % interpolation] = rib(vcols)
    
    # custom prim vars
    for p in rm.prim_vars:
        if p.data_source == 'VERTEX_COLOR':
            vcols = get_mesh_vcol(geo, p.data_name)
            if vcols is not None:
                primvars["%s color %s" % (interpolation, p.name)] = rib(vcols)

        elif p.data_source == 'UV_TEXTURE':
            uvs = get_mesh_uv(geo, p.data_name)
            if uvs is not None:
                primvars["%s float[2] %s" % (interpolation, p.name)] = uvs

        elif p.data_source == 'VERTEX_GROUP':
            weights = get_mesh_vgroup(ob, geo, p.data_name)
            if weights is not None:
                primvars["vertex float %s" % p.name] = weights

    return primvars
    
def get_primvars_particle(file, scene, psys):
    primvars = {}
    rm = psys.settings.renderman
    cfra = scene.frame_current
    
    for p in rm.prim_vars:
        pvars = []
        
        if p.data_source in ('VELOCITY', 'ANGULAR_VELOCITY'):
            if p.data_source == 'VELOCITY':
                for pa in \
                        [p for p in psys.particles if valid_particle(p, cfra)]:
                    pvars.extend ( pa.velocity )
            elif p.data_source == 'ANGULAR_VELOCITY':
                for pa in \
                        [p for p in psys.particles if valid_particle(p, cfra)]:
                    pvars.extend ( pa.angular_velocity )

            primvars["varying float[3] %s" % p.name] = pvars

        elif p.data_source in \
                ('SIZE', 'AGE', 'BIRTH_TIME', 'DIE_TIME', 'LIFE_TIME'):
            if p.data_source == 'SIZE':
                for pa in \
                        [p for p in psys.particles if valid_particle(p, cfra)]:
                    pvars.append ( pa.size )
            elif p.data_source == 'AGE':
                for pa in \
                        [p for p in psys.particles if valid_particle(p, cfra)]:
                    pvars.append ( (cfra - pa.birth_time) / pa.lifetime )
            elif p.data_source == 'BIRTH_TIME':
                for pa in \
                        [p for p in psys.particles if valid_particle(p, cfra)]:
                    pvars.append ( pa.birth_time )
            elif p.data_source == 'DIE_TIME':
                for pa in \
                        [p for p in psys.particles if valid_particle(p, cfra)]:
                    pvars.append ( pa.die_time )
            elif p.data_source == 'LIFE_TIME':
                for pa in \
                        [p for p in psys.particles if valid_particle(p, cfra)]:
                    pvars.append ( pa.lifetime )

            primvars["varying float %s" % p.name] = pvars

    return primvars



def get_fluid_mesh(scene, ob):
    
    subframe = scene.frame_subframe
    
    fluidmod = [m for m in ob.modifiers if m.type == 'FLUID_SIMULATION'][0]
    fluidmeshverts = fluidmod.settings.fluid_mesh_vertices
    
    mesh = create_mesh(scene, ob)
    (nverts, verts, P) = get_mesh(mesh)
    bpy.data.meshes.remove(mesh)
    
    # use fluid vertex velocity vectors to reconstruct moving points
    P = [P[i] + fluidmeshverts[int(i/3)].velocity[i%3] * subframe * 0.5 for \
        i in range(len(P))]
    
    return (nverts, verts, P)
    
def get_subd_creases(mesh):
    creases = []
    
    # only do creases 1 edge at a time for now, 
    #detecting chains might be tricky..
    for e in mesh.edges:
        if e.crease > 0.0:
            creases.append( (e.vertices[0], e.vertices[1], 
                                e.crease*e.crease * 10) ) 
            # squared, to match blender appareance better 
            #: range 0 - 10 (infinitely sharp)
    return creases

def create_mesh(scene, ob, matrix=None):
    # 2 special cases to ignore:
    # subsurf last or subsurf 2nd last +displace last
    
    #if is_subd_last(ob):
    #    ob.modifiers[len(ob.modifiers)-1].show_render = False
    #elif is_subd_displace_last(ob):
    #    ob.modifiers[len(ob.modifiers)-2].show_render = False
    #    ob.modifiers[len(ob.modifiers)-1].show_render = False
    
    mesh = ob.to_mesh(scene, True, 'RENDER', calc_tessface=True, calc_undeformed=True)    
    if matrix != None:
        mesh.transform(matrix)

    return mesh
 

def export_light(rpass, scene, ri, ob):
    lamp = ob.data
    rm = lamp.renderman

    m = ob.parent.matrix_world * ob.matrix_local if ob.parent \
        else ob.matrix_world

    loc = m.to_translation()
    lvec = loc - (m.to_quaternion() * Vector((0,0,1)))

    params = []
    
    ri.AttributeBegin()
    ri.TransformBegin()
    ri.Transform(rib(m))
    ri.ShadingRate(rm.shadingrate)

    def point():
        ri.Sphere(.1, -.1, .1, 360)

    def geometry(type):
        ri.Geometry(type)

    def spot():
        ri.Disk(0, 0.5, 360)

    shapes = {
            "POINT":("sphere", point),
            "SUN":("disk", lambda: geometry('distantlight')),
            "SPOT":("spot", spot),
            "AREA":("rect", lambda: geometry('rectlight')),
            "HEMI":("env", lambda: geometry('envsphere'))
        }

    name = "PxrAreaLight"
    handle = lamp.name
    params = {ri.HANDLEID: lamp.name, "float exposure":[lamp.energy]}
    
    if lamp.type == "HEMI":
        name = "PxrEnvMapLight"  
        params["color envtint"] = rib(lamp.color)
    else:
        params["color lightcolor"] = rib(lamp.color)
        params["string shape"] = [shapes[lamp.type][0]]
    
    if rm.nodetree != '':
        export_shader_nodetree(ri, lamp, handle=handle)
    else:
        ri.AreaLightSource(name, params)
    shapes[lamp.type][1]()
    
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
    
  #   if rm.nodetree != '':
  #       print('export nodetree ')
  #       export_shader_nodetree(file, scene, lamp, output_node='OutputLightShaderNode', handle=ob.name)
  #       params = []

  #   # parameter list
  #   for sp in params:
  #       # special exceptions since they're not an actual properties on lamp datablock
  #       if sp.name == 'from':
  #           value = rib(loc)
  #       elif sp.name == 'to': 
  #           value = rib(lvec)


  #       elif sp.meta == 'shadow_map_path':
  #           if shader_requires_shadowmap(scene, rm, 'light'):
  #               path = rib_path(shadowmap_path(scene, ob))
  #               print(path)
  #               file.write('        "string %s" "%s" \n' % (sp.name, path))

  #           ''' XXX old shaders

        
  #       elif sp.name == 'coneangle':
  #           if hasattr(lamp, "spot_size"):
  #               coneangle = lamp.spot_size / 2.0
  #               value = rib(coneangle)
  #           else:
  #               value = rib(45)
        
  #       elif sp.name in ('shadowmap', 'shadowname', 'shadowmapname'):
  #           if rm.shadow_method == 'SHADOW_MAP':
  #               shadowmapname = rib_path(shadowmap_path(scene, ob))
  #               file.write('        "string %s" "%s" \n' % (sp.name, shadowmapname))
  #           elif rm.shadow_method == 'RAYTRACED':
  #               file.write('        "string %s" ["raytrace"] \n' % sp.name)
            
  #           continue
  #           '''
  #       # more exceptions, use blender's built in equivalent parameters (eg. spot size)
  #       elif sp.name in exclude_lamp_params.keys():
  #           value = rib(getattr(lamp, exclude_lamp_params[sp.name]))
        
  #       # otherwise use the stored raw shader parameters
  #       else:
  #           value = rib(sp.value)

        # # BBM addition begin
  #       if sp.is_array:
  #           file.write('        "%s %s[%d]" %s\n' % (sp.data_type, sp.name, len(sp.value), rib(sp.value,is_cosh_array=True)))
  #       else:
        # # BBM addition end
  #           file.write('        "%s %s" %s\n' % (sp.data_type, sp.name, value))

    ri.TransformEnd()
    ri.AttributeEnd()
    
    ri.Illuminate(handle, rm.illuminates_by_default)

    
def export_material(ri, rpass, scene, mat):

    rm = mat.renderman

    if rm.nodetree != '':
        #ri.write('        Color %s\n' % rib(mat.diffuse_color))
        #ri.write('        Opacity %s\n' % rib([mat.alpha for i in range(3)]))
            
        #if rm.displacementbound > 0.0:
            #ri.write('        Attribute "displacementbound" "sphere" %f \n' % rm.displacementbound)
        ri.Attribute('displacementbound', {'sphere':rm.displacementbound})
        export_shader_nodetree(ri, mat)
    else:
        #export_shader(file, scene, rpass, mat, 'shader') # BBM addition
        export_shader(ri, scene, rpass, mat, 'surface')
        export_shader(ri, scene, rpass, mat, 'displacement')
        export_shader(ri, scene, rpass, mat, 'interior')
    
    
def export_motion_begin(ri, scene, ob):
    ri.MotionBegin(get_ob_subframes(scene, ob))

def export_strands(ri, rpass, scene, ob, motion):

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
            export_motion_begin(ri, scene, ob)
            samples = motion['deformation'][pname]
        else:
            samples = [get_strands(ob, psys)]
        
        for nverts, P in samples:
            
            ri.Basis("catmull-rom", 1, "catmull-rom", 1)
            ri.Curves("cubic", nverts, "nonperiodic", 
                        {"P": rib(P), "constantwidth": rm.width})

        if motion_blur:
            ri.MotionEnd()

def geometry_source_rib(ri, scene, ob):
    rm = ob.renderman
    anim = rm.archive_anim_settings
    blender_frame = scene.frame_current
    
    if rm.geometry_source == 'ARCHIVE':
        archive_path = \
            rib_path(get_sequence_path(rm.path_archive, blender_frame, anim))
        ri.ReadArchive(archive_path)
        
    else:
        if rm.procedural_bounds == 'MANUAL':
            min = rm.procedural_bounds_min
            max = rm.procedural_bounds_max
            bounds = [min[0], max[0], min[1], max[1], min[2], max[2]]
        else:
            bounds = rib_ob_bounds(ob.bound_box)
        
        if rm.geometry_source == 'DELAYED_LOAD_ARCHIVE':
            archive_path = rib_path(get_sequence_path(rm.path_archive, 
                                                        blender_frame, anim))
            ri.Procedural("DelayedReadArchive", archive_path, rib(bounds))
        
        elif rm.geometry_source == 'PROCEDURAL_RUN_PROGRAM':
            path_runprogram = rib_path(rm.path_runprogram)
            ri.Procedural("RunProgram", [path_runprogram, 
                                            rm.path_runprogram_args], 
                                        rib(bounds))
        
        elif rm.geometry_source == 'DYNAMIC_LOAD_DSO':
            path_dso = rib_path(rm.path_dso)
            ri.Procedural("DynamicLoad", [path_dso, rm.path_dso_initial_data], 
                                        rib(bounds))


def export_particle_instances(ri, rpass, scene, ob, psys, motion):
    rm = psys.settings.renderman
    pname = psys_motion_name(ob, psys)
    
    # Precalculate archive path for object instances
    try:
        instance_ob = bpy.data.objects[rm.particle_instance_object]
    except:
        return
    
    
    
    motion_blur = pname in motion['deformation']
    cfra = scene.frame_current

    for i in range(len( [ p for p in psys.particles \
                                    if valid_particle(p, cfra) ] )):
        
        if motion_blur:
            export_motion_begin(ri, scene, ob)
            samples = motion['deformation'][pname]
        else:
            samples = [get_particles(scene, ob, psys)]
        
        for P, rot, width in samples:

            loc = Vector((P[i*3+0], P[i*3+1], P[i*3+2]))
            rot = Quaternion((rot[i*4+0], rot[i*4+1], rot[i*4+2], rot[i*4+3]))
            mtx = Matrix.Translation(loc) * rot.to_matrix().to_4x4() \
                    * Matrix.Scale(width[i], 4)
            
            ri.Transform(rib(mtx))
        
        if motion_blur:
            ri.MotionEnd()

        if instance_ob.renderman.geometry_source == 'BLENDER_SCENE_DATA':
            archive_path = rib_path(auto_archive_path(rpass.paths, 
                                                        [instance_ob]))
            ri.ReadArchive(archive_path)
        else:
            geometry_source_rib(ri, scene, instance_ob)
        


def export_particle_points(ri, scene, ob, psys, motion):
    rm = psys.settings.renderman
    pname = psys_motion_name(ob, psys)
    
    motion_blur = pname in motion['deformation']
    
    if motion_blur:
        export_motion_begin(ri, scene, ob)
        samples = motion['deformation'][pname]
    else:
        samples = [get_particles(scene, ob, psys)]
    
    for P, rot, width in samples:
        params = get_primvars_particle(scene, psys)
        params[ri.P] =  rib(P)
        params["uniform string type"] = rm.particle_type
        if rm.constant_width:
            params["constantwidth"] = rm.width
        elif rm.export_default_size:
            params["varying float width"] = width
        ri.Points(params)
    
    if motion_blur:
        ri.MotionEnd()

def export_particles(ri, rpass, scene, ob, motion):

    for psys in ob.particle_systems:
        rm = psys.settings.renderman
        pname = psys_motion_name(ob, psys)
        
        if psys.settings.type != 'EMITTER':
            continue
    
        ri.AttributeBegin()
        ri.Attribute("identifier", {"name": pname})
        
        # use 'material_id' index to decide which material
        if ob.data.materials:
            if ob.data.materials[rm.material_id-1] != None:
                mat = ob.data.materials[rm.material_id-1]
                export_material(ri, rpass, scene, mat)
        
        # Write object instances or points
        if rm.particle_type == 'OBJECT':
            export_particle_instances(ri, rpass, scene, ob, psys, motion)
        else:
            export_particle_points(ri, scene, ob, psys, motion)
        
        
        ri.AttributeEnd()
    
def export_comment(ri, comment):
    ri.ArchiveRecord('comment', comment)

def get_texture_list(scene):
    #if not rpass.light_shaders: return
    SUPPORTED_MATERIAL_TYPES = ['MESH','CURVE','FONT']
    textures = []
    for o in renderable_objects(scene):
        if o.type == 'CAMERA':
            continue
        elif o.type == 'LAMP':
            if o.data.renderman.nodetree != '':
                textures = textures + get_textures(o.data)
        elif o.type in SUPPORTED_MATERIAL_TYPES:
            for mat in [mat for mat in o.data.materials if mat != None]:
                textures = textures + get_textures(mat)
        else:
            print ("get_texture_list: unsupported object type [%s]." % o.type)
    return textures

def get_texture_list_preview(scene):
    #if not rpass.light_shaders: return
    textures = []
    return get_textures(find_preview_material(scene))


def export_scene_lights(ri, rpass, scene):
    #if not rpass.light_shaders: return

    export_comment(ri,'Lights')
    
    for ob in [o for o in rpass.objects if o.type == 'LAMP']:
        export_light(rpass, scene, ri, ob)
    
'''def export_shader_init(ri, rpass, mat):
    rm = mat.renderman

    if rpass.emit_photons:
        file.write('        Attribute "photon" "string shadingmodel" "%s" \n' % rm.photon_shadingmodel)
'''

def export_shader(ri, scene, rpass, idblock, shader_type):
    rm = idblock.renderman
    export_comment(ri, shader_type) # BBM addition
    
    '''
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
    '''

    if shader_type == 'surface':
        mat = idblock
        
        #if rm.surface_shaders.active == '' or not rpass.surface_shaders: return
        
        name = mat.name
        params = {"color baseColor": rib(mat.diffuse_color),
                "float specular": mat.specular_intensity}

        if mat.emit:
            params["color emitColor"] = rib(mat.diffuse_color)
        if mat.subsurface_scattering.use:
            params["float subsurface"] = mat.subsurface_scattering.scale
            params["color subsurfaceColor"] = \
                rib(mat.subsurface_scattering.color)
        if mat.raytrace_mirror.use:
            params["float metallic"] = mat.raytrace_mirror.reflect_factor
        ri.Bxdf("PxrDisney", mat.name, params)
        

        #file.write('        Color %s\n' % rib(mat.diffuse_color))
        #file.write('        Opacity %s\n' % rib([mat.alpha for i in range(3)]))
        #file.write('        Surface "%s" \n' % mat.name)
      
    '''  
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

    '''

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
            width.append( bp.radius * 0.01 )
        
        #basis = ["bezier", 3, "bezier", 3]
        basis = ["BezierBasis", 3, "BezierBasis", 3]
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

def export_curve(ri, scene, ob, motion):
    if ob.type == 'CURVE':
        curve  = ob.data

        motion_blur = ob.name in motion['deformation']
        
        if motion_blur:
            export_motion_begin(ri, scene, ob)
            samples = motion['deformation'][ob.name]
        else:
            samples = [get_curve(curve)]
        
        for spline_samples in samples:
            for P, width, npt, basis, period in spline_samples:
                ri.Basis(basis[0], basis[1], basis[2], basis[3])
                ri.Curves("cubic", [npt], period, {"P": rib(P), "width": width})
      
        if motion_blur:
            ri.MotionEnd()
    else:
        print ("export_curve: recieved a non-supported object type of [%s]." % ob.type)

def export_subdivision_mesh(ri, scene, ob, motion):
    mesh = create_mesh(scene, ob)
    
    motion_blur = ob.name in motion['deformation']
    
    if motion_blur:
        export_motion_begin(ri, scene, ob)
        samples = motion['deformation'][ob.name]
    else:
        samples = [get_mesh(mesh)]
    
    creases = get_subd_creases(mesh)
    
    for nverts, verts, P in samples:
        tags = []
        nargs = []
        intargs = []
        floatargs = []

        if len(creases) > 0:
            for c in creases:
                tags.append( '"crease"' )
                nargs.extend( [2, 1] )
                intargs.extend( [c[0], c[1]] )
                floatargs.append( c[2] )

        tags.append('interpolateboundary')
        nargs.extend( [0, 0] )
        
        primvars = get_primvars(ob, mesh, "facevertex")
        primvars[ri.P] = P

        ri.SubdivisionMesh("catmull-clark", nverts, verts, tags, nargs, intargs,
            floatargs, primvars)
    
    if motion_blur:
        ri.MotionEnd()
            
    bpy.data.meshes.remove(mesh)

def export_polygon_mesh(ri, scene, ob, motion):
    mesh = create_mesh(scene, ob)
    
    motion_blur = ob.name in motion['deformation']
    
    if motion_blur:
        export_motion_begin(ri, scene, ob)
        samples = motion['deformation'][ob.name]
    else:
        samples = [get_mesh(mesh)]
        
    for nverts, verts, P in samples:
        primvars = get_primvars(ob, mesh, "facevarying")
        print(primvars)
        primvars['P'] = P
        ri.PointsPolygons(nverts, verts, primvars)
        
    if motion_blur:
        ri.MotionEnd()
            
    bpy.data.meshes.remove(mesh)

def export_points(ri, scene, ob, motion):
    rm = ob.renderman
    
    mesh = create_mesh(scene, ob)
    
    motion_blur = ob.name in motion['deformation']
    
    if motion_blur:
        export_motion_begin(ri,scene, ob)
        samples = motion['deformation'][ob.name]
    else:
        samples = [get_mesh(mesh)]
        
    for nverts, verts, P in samples:
        params = {
            ri.P: rib(P),
            "uniform string type": rm.primitive_point_type,
            "constantwidth": rm.primitive_point_width
        }
        ri.Points(params)
            
    if motion_blur:
        ri.MotionEnd()
            
    bpy.data.meshes.remove(mesh)


def export_sphere(ri, scene, ob, motion):
    rm = ob.renderman
    ri.Sphere(rm.primitive_radius, rm.primitive_zmin, rm.primitive_zmax, 
            rm.primitive_sweepangle)
        
def export_cylinder(ri, scene, ob, motion):
    rm = ob.renderman
    ri.Cylinder(rm.primitive_radius, rm.primitive_zmin, rm.primitive_zmax, 
            rm.primitive_sweepangle)
        
def export_cone(ri, scene, ob, motion):
    rm = ob.renderman
    ri.Cone(rm.primitive_height, rm.primitive_radius, rm.primitive_sweepangle)

def export_disk(ri, scene, ob, motion):
    rm = ob.renderman
    ri.Disk(rm.primitive_height, rm.primitive_radius, rm.primitive_sweepangle)

def export_torus(ri, scene, ob, motion):
    rm = ob.renderman
    ri.Torus(rm.primitive_majorradius, rm.primitive_minorradius, 
            rm.primitive_phimin, rm.primitive_phimax, rm.primitive_sweepangle)

def is_dupli(ob):
    return ob.type == 'EMPTY' and ob.dupli_type != 'NONE'

def export_geometry_data(ri, rpass, scene, ob, motion, force_prim=''):

    # handle duplis
    if is_dupli(ob):
        ob.dupli_list_create(scene)
        
        dupobs = [(dob.object, dob.matrix) for dob in ob.dupli_list]
        
        for dupob, dupob_mat in dupobs:
            if is_renderable(scene, dupob):
                export_object(ri, rpass, scene, dupob, motion)
        
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
            export_material(ri, rpass, scene, mat)
            break
    
    if prim == 'SPHERE':
        export_sphere(ri, scene, ob, motion)
    elif prim == 'CYLINDER':
        export_cylinder(ri, scene, ob, motion)
    elif prim == 'CONE':
        export_cone(ri, scene, ob, motion)
    elif prim == 'DISK':
        export_disk(ri, scene, ob, motion)
    elif prim == 'TORUS':
        export_torus(ri, scene, ob, motion)
    
    # curve only
    elif prim == 'CURVE' or prim == 'FONT':
        # If this curve is extruded or beveled it can produce faces from a to_mesh call.
        l = ob.data.extrude + ob.data.bevel_depth
        if l > 0:
            export_polygon_mesh(ri, scene, ob, motion)
        else:
            export_curve(ri, scene, ob, motion) 

        #print ("export_geometry_data: exporting [%s] as [%s]." % (ob.name,ob.type))
        #export_curve(ri, scene, ob, motion)
 
    # mesh only
    elif prim == 'POLYGON_MESH':
        export_polygon_mesh(ri, scene, ob, motion)
    elif prim == 'SUBDIVISION_MESH':
        export_subdivision_mesh(ri, scene, ob, motion)
    elif prim == 'POINTS':
        export_points(ri, scene, ob, motion)
  
def export_geometry(ri, rpass, scene, ob, motion):
    rm = ob.renderman
    
    if rm.geometry_source == 'BLENDER_SCENE_DATA':
        if ob in rpass.archives:
            archive_path = rib_path(auto_archive_path(rpass.paths, [ob]))        
            if os.path.exists(archive_path):
                ri.ReadArchive(archive_path)
        else:
            export_geometry_data(ri, rpass, scene, ob, motion)

    else:    
        ri.write(geometry_source_rib(scene, ob))


def export_object(ri, rpass, scene, ob, motion):
    rm = ob.renderman

    if ob.type in ('LAMP', 'CAMERA'): return
    
    if ob.parent:
        mat = ob.parent.matrix_world * ob.matrix_local
    else:
        mat = ob.matrix_world

    ri.AttributeBegin()
    ri.Attribute("identifier", {"name": ob.name})

    # Shading
    if rm.shadingrate_override:
        ri.ShadingRate(rm.shadingrate)

    # Transformation
    if ob.name in motion['transformation']:
        export_motion_begin(ri,scene, ob)
        
        for sample in motion['transformation'][ob.name]:
            ri.Transform(rib(sample))
            
        ri.MotionEnd()
    else:
        ri.Transform(rib(mat))

    export_geometry(ri, rpass, scene, ob, motion)
    export_strands(ri, rpass, scene, ob, motion)
    
    ri.AttributeEnd()
    
    # Particles live in worldspace, export as separate object
    export_particles(ri, rpass, scene, ob, motion)

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
            motion['deformation'][pname].insert(0, 
                                            get_particles(scene, ob, psys));
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
    
    if not scene.renderman.motion_blur:
        return motion

    # get a de-duplicated set of all possible numbers of motion segments 
    # from renderable objects in the scene, and global scene settings
    all_segs = [ob.renderman.motion_segments for ob in scene.objects \
                                if ob.renderman.motion_segments_override]
    all_segs.append(scene.renderman.motion_segments)
    all_segs = set(all_segs)
    
    # the aim here is to do only a minimal number of scene updates, 
    # so we process objects in batches of equal numbers of segments
    # and update the scene only once for each of those unique fractional 
    #frames per segment set
    for segs in all_segs:

        if segs == scene.renderman.motion_segments:
            motion_obs = [ob for ob in scene.objects \
                                if not ob.renderman.motion_segments_override]
        else:
            motion_obs = [ob for ob in scene.objects \
                                if ob.renderman.motion_segments == segs]

        # prepare list of frames/sub-frames in advance, 
        #ordered from future to present,
        # to prevent too many scene updates 
        #(since loop ends on current frame/subframe)
        for sub in get_subframes(segs):
            scene.frame_set(origframe, 1.0-sub)
            
            for ob in motion_obs:
                export_motion_ob(scene, motion, ob)
                        
    return motion


def export_objects(ri, rpass, scene, motion):

    export_comment(ri, "Objects")

    # export the objects to RIB recursively
    for ob in rpass.objects:
        print ("export_objects: Exporting [%s]." % ob.name)
        export_object(ri, rpass, scene, ob, motion)

#TODO take in an ri object and write out archive
def export_archive(scene, objects, filepath="", archive_motion=True, 
                    animated=True, frame_start=1, frame_end=3):

    #init_env(scene)
    paths = initialise_paths(scene)    
    rpass = RPass(scene, objects, paths)
    
    if frame_start == frame_end:
        animated = False
    
    if filepath == "":
        filepath = auto_archive_path(paths, objects, create_folder=True)
    
    for frame in range(frame_start, frame_end+1):
        scene.frame_set(frame)
        
        motion = export_motion(rpass, scene) \
                    if archive_motion else empty_motion()
        ribpath = anim_archive_path(filepath, frame) if animated else filepath

        
        file = open(ribpath, "w")
        export_header(file)
        
        for ob in rpass.objects:
            export_geometry_data(file, rpass, scene, ob, motion)
    
        file.close()
    
    return file.name

#takes a list of bpy.types.properties and converts to params for rib
def property_group_to_params(prop_group):
    params = {}

    type_map = {
        "FloatProperty": 'float',
        "IntProperty": 'int',
        "StringProperty": 'string',
        "EnumProperty": 'string',
        "BoolProperty": 'bool',
    }

    for (key, value) in prop_group.bl_rna.properties.items(): 
        # This is somewhat ugly, but works best!!
            if key not in ['rna_type', 'name']:
                val = prop_group.get(key)
                if val:
                    param_type = "%s %s" % (type(val).__name__, key)
                    params[param_type] = val
    
    return params

def export_integrator(ri, rpass, scene):
    rm = scene.renderman

    integrator_settings = getattr(rm, "%s_settings" % rm.integrator)
    params = property_group_to_params(integrator_settings)
    
    ri.Integrator(rm.integrator, "integrator", params)

    
  #   for sp in shaderparameters_from_class(rm.integrator2):
  #       file.write('            "%s %s" %s\n' % (sp.data_type, sp.name, rib(sp.value)))
    
  #   parameterlist = rna_to_shaderparameters(scene, rm.integrator, 'surface')
  #   for sp in parameterlist:
        # # BBM addition begin
  #       if sp.is_array:
  #           file.write('            "%s %s[%d]" %s\n' % (sp.data_type, sp.name, len(sp.value), rib(sp.value,is_cosh_array=True)))
  #       else:
        # # BBM addition end
  #           file.write('            "%s %s" %s\n' % (sp.data_type, sp.name, rib(sp.value)))
    

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


def export_render_settings(ri, rpass, scene, preview=False):
    rm = scene.renderman
    r = scene.render
    
    '''file.write('Option "render" "integer nthreads" %d\n' % rm.threads)
    file.write('Option "trace" "integer maxdepth" [%d]\n' % rm.max_trace_depth)
    file.write('Attribute "trace" "integer maxspeculardepth" [%d]\n' % rm.max_specular_depth)
    file.write('Attribute "trace" "integer maxdiffusedepth" [%d]\n' % rm.max_diffuse_depth)
    file.write('Option "limits" "integer eyesplits" %d\n' % rm.max_eye_splits)
    file.write('Option "trace" "float approximation" %f\n' % rm.trace_approximation)
    if rm.use_statistics:
        file.write('Option "statistics" "endofframe" %d "filename" "/tmp/stats.txt" \n' % rm.statistics_level    )
    
    
    '''

    depths = {'int maxdiffusedepth': rm.max_diffuse_depth,
            'int maxspeculardepth': rm.max_specular_depth,
            'int displacements': 1}
    if preview:
        depths = {'int maxdiffusedepth': rm.preview_max_diffuse_depth,
            'int maxspeculardepth': rm.preview_max_specular_depth}

    rpass.resolution = render_get_resolution(r)
    ri.Format(rpass.resolution[0], rpass.resolution[1], 1.0)
    #ri.PixelSamples(rm.pixelsamples_x, rm.pixelsamples_y)
    ri.PixelFilter(rm.pixelfilter, rm.pixelfilter_x, rm.pixelfilter_y)
    ri.ShadingRate(rm.shadingrate )
    ri.Attribute("trace", depths)


def export_camera_matrix(ri, scene, ob, motion):
    motion_blur = ob.name in motion['transformation']
    
    if motion_blur:
        export_motion_begin(ri, scene, ob)
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

            ri.Transform(rib(m))

    if motion_blur:
        ri.MotionEnd()

def export_camera(ri, scene, motion):
    
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
        ri.DepthOfField(rm.fstop, 1.0, dof_distance)
        
    if scene.renderman.motion_blur:
        ri.Shutter(rm.shutter_open, rm.shutter_close)
        #ri.Option "shutter" "efficiency" [ %f %f ] \n' % (rm.shutter_efficiency_open, rm.shutter_efficiency_close))

    ri.Clipping(cam.clip_start, cam.clip_end)
    
    if cam.type == 'PERSP':
        lens= cam.lens
        
        sensor = cam.sensor_height \
            if cam.sensor_fit == 'VERTICAL' else cam.sensor_width

        fov= 360.0*math.atan((sensor*0.5)/lens/aspectratio)/math.pi

        ri.Projection("perspective", {"fov": fov})
    else:
        lens= cam.ortho_scale
        xaspect= xaspect*lens/(aspectratio*2.0)
        yaspect= yaspect*lens/(aspectratio*2.0)
        ri.Projection("orthographic")

    ri.ScreenWindow(-xaspect, xaspect, -yaspect, yaspect)

    export_camera_matrix(ri, scene, ob, motion)
    
def export_camera_render_preview(ri, scene):
    r = scene.render

    xaspect, yaspect, aspectratio = render_get_aspect(r)

    ri.Clipping(0.100000, 100.000000)
    ri.Projection("perspective", {"fov": 28.841546})
    ri.ScreenWindow(-xaspect, xaspect, -yaspect, yaspect)

    ri.Transform([0.685881, -0.317370, -0.654862, 0.000000, 
                0.727634, 0.312469, 0.610666, 0.000000, 
                -0.010817, 0.895343, -0.445245, 0.000000, 
                0.040019, -0.661400, 6.220541, 1.000000])           


def export_searchpaths(ri, paths):
    ri.Option("searchpath", {"string shader": ["%s" % \
        ':'.join(path_list_convert(paths['shader'], to_unix=True))]})
    ri.Option("searchpath", {"string texture": ["%s" % \
        ':'.join(path_list_convert(paths['texture'], to_unix=True))]})
    
    #ri.Option("searchpath", {"string procedural": ["%s" % \
    #    ':'.join(path_list_convert(paths['procedural'], to_unix=True))]})
    #ri.Option("searchpath", {"string archive": ["%s" % \
    #    ':'.join(path_list_convert(paths['archive'], to_unix=True))]})

def export_header(ri):
    export_comment(ri, 'Generated by PRMan for Blender, v%s.%s.%s \n' % \
            (addon_version[0], addon_version[1], addon_version[2]))

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
                if not object.name in objects_materials.keys(): 
                    objects_materials[object] = []
                objects_materials[object].append(mat)

    # find objects that are likely to be the preview objects
    preview_objects = [o for o in objects_materials.keys() \
                        if o.name.startswith('preview')]
    if len(preview_objects) < 1:
        return

    # find the materials attached to the likely preview object
    likely_materials = objects_materials[preview_objects[0]]
    if len(likely_materials) < 1:
        return

    return likely_materials[0]
    
# --------------- End Hopefully temporary --------------- #

def preview_model(ri,mat):
    if mat.preview_render_type == 'SPHERE':
        ri.Sphere(1, -1, 1, 360)
    elif mat.preview_render_type == 'FLAT': #FLAT PLANE
        #ri.Scale(0.75, 0.75, 0.75)
        ri.Translate(0.0, 0.0, 0.01)
        ri.PointsPolygons([4,], 
            [0, 1, 2, 3],
            {ri.P: [0, -1, -1,  0, 1, -1,  0, 1, 1,  0, -1, 1]})
    else: # CUBE
        ri.Scale(0.75, 0.75, 0.75)
        ri.Translate(0.0,0.0,0.01)
        ri.PointsPolygons([4, 4, 4, 4, 4, 4, ],
            [0, 1, 2, 3, 4, 7, 6, 5, 0, 4, 5, 1,
             1, 5, 6, 2, 2, 6, 7, 3, 4, 0, 3, 7],
            {ri.P: [1, 1, -1, 1, -1, -1, -1, -1, -1, -1, 1, -1, 
                    1, 1, 1, 1, -1, 1, -1, -1, 1, -1, 1, 1]})

    
    

def export_display(ri, rpass, scene):
    rm = scene.renderman
    
    active_layer = scene.render.layers.active
    aovs = [
        #(name, do?, declare type/name, source)
        ("z", active_layer.use_pass_z, None, None),
        ("N", active_layer.use_pass_normal, None, None),
        ("dPdtime", active_layer.use_pass_vector, None, None),
        ("u,v", active_layer.use_pass_uv, None, None),
        ("id", active_layer.use_pass_uv, "float", None),
        #("lpe:shadows", active_layer.use_pass_shadow, "color", None),
        #("reflection", active_layer.use_pass_shadow, "float id"),
        ("lpe:diffuse", active_layer.use_pass_diffuse_direct, "color", None),
        #("lpe:diffusedirect", active_layer.use_pass_diffuse_direct, "color", None),
        ("lpe:indirectdiffuse", active_layer.use_pass_diffuse_indirect, 
            "color", None),
        ("albedo", active_layer.use_pass_diffuse_color, "color", 
            "color lpe:nothruput;noinfinitecheck;noclamp;unoccluded;overwrite;C(U2L)|O"),
        ("lpe:specular", active_layer.use_pass_specular, "color", None),
        #("lpe:diffuse", active_layer.use_pass_diffuse_direct, "color", None),
        ("lpe:indirectspecular", active_layer.use_pass_glossy_indirect, 
            "color", None),
        #specular COLOR???("lpe:indirectdiffuse", active_layer.use_pass_diffuse_indirect, "color", None),
        ("lpe:subsurface", active_layer.use_pass_subsurface_indirect, 
            "color", None),
        ("lpe:refraction", active_layer.use_pass_refraction, "color", None),
        ("lpe:emission", active_layer.use_pass_emit, "color", None),
        #("lpe:ambient occlusion", active_layer.use_pass_emit, "color", None),
        
    ]

    #declare display channels
    for aov, doit, declare_type, source in aovs:
        if doit and declare_type:
            params = {}
            if source:
                params['string source'] = source
            ri.DisplayChannel('%s %s' % (declare_type, aov), params)

    dspy_driver = "tiff"
    main_display = os.path.basename(rpass.paths['render_output'])
    if rm.display_driver != 'blender':
        dspy_driver = rm.display_driver
        main_display = user_path(rm.path_display_driver_image, 
                scene=scene)
        
    image_base, ext = main_display.rsplit('.', 1)
    if dspy_driver == "openexr":
        ext = 'exr'
    ri.Display(image_base + '.' + ext, dspy_driver, "rgba", 
                {"quantize": [0, 0, 0, 0]})

    #now do aovs
    for aov, doit, declare, source in aovs:
        if doit:
            ri.Display('+' + image_base + '.%s.' % aov + ext, dspy_driver, aov, 
                {"quantize": [0, 0, 0, 0]})


def export_hider(ri, rpass, scene, preview=False):
    rm = scene.renderman
    
    '''if rm.hider == 'hidden':
        file.write('Hider "hidden" \n')
        file.write('    "string depthfilter" "%s" \n' % rm.hidden_depthfilter)
        file.write('    "integer jitter" [%d] \n' % rm.hidden_jitter)
        file.write('    "integer samplemotion" [%d] \n' % rm.hidden_samplemotion)
        file.write('    "integer extrememotiondof" [%d] \n' % rm.hidden_extrememotiondof)
        file.write('    "integer maxvpdepth" [%d] \n' % rm.hidden_maxvpdepth)
        if rm.hidden_depthfilter == 'midpoint':
            file.write('"float midpointratio" [%f] \n' % rm.hidden_midpointratio)'''
    pv = rm.pixel_variance
    hider_params = {'string integrationmode': 'path', 
                    'int maxsamples': rm.max_samples,
                    'int minsamples': rm.min_samples,
                    'int incremental': 1}

    if preview:
        hider_params['int maxsamples'] = rm.preview_max_samples
        hider_params['int minsamples'] = rm.preview_min_samples
        pv = rm.preview_pixel_variance

    ri.PixelVariance(pv)
    
    if rm.hider == 'raytrace':
        ri.Hider(rm.hider, hider_params)
  



def write_rib(rpass, scene, ri):
    #info_callback('Generating RIB')
    
    # precalculate motion blur data
    rpass.motion_blur = None
    rpass.objects = renderable_objects(scene)
    rpass.archives = []

    motion = export_motion(rpass, scene)
    
    ri.Begin(rpass.paths['rib_output'])
    
    export_header(ri)
    export_searchpaths(ri, rpass.paths)
    
    export_display(ri, rpass, scene)
    export_hider(ri, rpass, scene)
    export_integrator(ri, rpass, scene)
    
    #export_inline_rib(ri, rpass, scene)
    
    scene.frame_set(scene.frame_current)
    ri.FrameBegin(scene.frame_current)
    
    export_camera(ri, scene, motion)
    export_render_settings(ri, rpass, scene)
    #export_global_illumination_settings(ri, rpass, scene)
    
    ri.WorldBegin()

    #export_global_illumination_lights(ri, rpass, scene)
    #export_world_coshaders(ri, rpass, scene) # BBM addition
    export_scene_lights(ri, rpass, scene)

    #default bxdf
    ri.Bxdf("PxrDisney", "default")
    export_objects(ri, rpass, scene, motion)
    
    ri.WorldEnd()

    ri.FrameEnd()
    ri.End()

def write_preview_rib(rpass, scene, ri):

    previewdir = os.path.join(rpass.paths['export_dir'], "preview")
    preview_rib_data_path = \
        rib_path(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                'preview', "preview_scene.rib"))
    
    rpass.paths['rib_output'] = os.path.join(previewdir, "preview.rib")
    rpass.paths['render_output'] = os.path.join(previewdir, "preview.tif")
    rpass.paths['export_dir'] = os.path.dirname(rpass.paths['rib_output'])
    
    if not os.path.exists(previewdir):
        os.mkdir(previewdir)
    
    #print('writing rib to ' + rpass.paths['rib_output'])
    
    ri.Begin(rpass.paths['rib_output'])
    
    export_header(ri)
    export_searchpaths(ri, rpass.paths)
    
    # temporary tiff display to be read back into blender render result
    ri.FrameBegin(1)
    ri.Display(os.path.basename(rpass.paths['render_output']), "tiff", "rgb",
                                {ri.DISPLAYQUANTIZE: [0, 0, 0, 0]})
    

    export_hider(ri, rpass, scene, preview=True)
    export_integrator(ri, rpass, scene)
    

    export_camera_render_preview(ri, scene)
    export_render_settings(ri, rpass, scene, preview=True)

    ri.WorldBegin()
    
    # preview scene: walls, lights
    ri.ReadArchive(preview_rib_data_path)
    
    # preview model and material
    ri.AttributeBegin()
    ri.Attribute("identifier", {"name":[ "Preview" ]})
    ri.Translate(0,0,0.75)
    # file.write('        Attribute "visibility" \n \
    #         "integer camera" [ 1 ] \n \
    #         "integer trace" [ 1 ] \n \
    #         "integer photon" [ 1 ] \n \
    #         "string transmission" ["opaque"] \n ')
    # file.write('        Attribute "trace" "displacements" [1] \n')
    
    mat = find_preview_material(scene)
    export_material(ri, rpass, scene, mat)
    preview_model(ri,mat)
    ri.AttributeEnd()
    
    ri.WorldEnd()
    ri.FrameEnd()
    ri.End()
    

def anim_archive_path(filepath, frame):
    if filepath.find("#") != -1:
        ribpath = make_frame_path(filepath, fr)
    else:
        ribpath = os.path.splitext(filepath)[0] + "." + str(frame).zfill(4) + \
                    os.path.splitext(filepath)[1]
    return ribpath


def write_auto_archives(paths, scene, info_callback):
    for ob in archive_objects(scene):
        export_archive(scene, [ob], archive_motion=True, 
                frame_start=scene.frame_current, frame_end=scene.frame_current)
    
