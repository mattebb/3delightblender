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
import math, mathutils
import os
import time
from mathutils import Matrix, Vector, Quaternion

from . import bl_info

from .util import rib, rib_path, rib_ob_bounds
from .util import make_frame_path
from .util import init_env
from .util import get_sequence_path
from .util import user_path
from .util import path_list_convert, get_real_path
from .util import get_properties, check_if_archive_dirty
from .util import debug
from .util import find_it_path

addon_version = bl_info['version']

# helper functions for parameters
from .nodes import export_shader_nodetree, get_textures

# ------------- Atom's helper functions -------------
GLOBAL_ZERO_PADDING = 5
SUPPORTED_INSTANCE_TYPES = ['MESH','CURVE','FONT']			# Objects that can be exported as a polymesh via Blender to_mesh() method. ['MESH','CURVE','FONT']
SUPPORTED_DUPLI_TYPES = ['FACES', 'VERTS', 'GROUP']			# Supported dupli types.
MATERIAL_TYPES = ['MESH', 'CURVE','FONT']					# These object types can have materials.
EXCLUDED_OBJECT_TYPES = ['LAMP', 'CAMERA', 'ARMATURE']		# Objects without to_mesh() conversion capabilities.
VOLUMETRIC_LIGHT_TYPES = ['SPOT','AREA','POINT']			# Only these light types affect volumes.
MATERIAL_PREFIX = "mat_"
TEXTURE_PREFIX = "tex_"
MESH_PREFIX = "me_"
CURVE_PREFIX = "cu_"
GROUP_PREFIX = "group_"
MESHLIGHT_PREFIX = "meshlight_"
PSYS_PREFIX = "psys_"
DUPLI_PREFIX = "dupli_"
DUPLI_SOURCE_PREFIX = "dup_src_"

def rounded_tuple(tup):
    return tuple(round(value,4) for value in tup) 
def returnNameForNumber(passedInteger):
    temp_number = str(passedInteger)
    post_fix = temp_number.zfill(GLOBAL_ZERO_PADDING)
    return post_fix
def returnMatrixForObject(passedOb):
    if passedOb.parent:
        mtx = passedOb.parent.matrix_world * passedOb.matrix_local
    else:
        mtx = passedOb.matrix_world
    return mtx
def uniquifyList(seq, idfun=None): 
    #http://www.peterbe.com/plog/uniqifiers-benchmark
    # f5 order preserving
   if idfun is None:
       def idfun(x): return x
   seen = {}
   result = []
   for item in seq:
       marker = idfun(item)
       if marker in seen: continue
       seen[marker] = 1
       result.append(item)
   return result
def printList(passedList):
    for item in passedList:
        debug ("info",item)
def exportObjectInstance(ri, rpass, scene, ob, mtx = None, dupli_name = None, instance_handle = None):
    if mtx:
        ri.AttributeBegin()
        ri.Attribute("identifier", {"name": dupli_name})
        ri.TransformBegin()
        ri.Transform(rib(mtx))
        if hasattr(ob.data, 'materials'):
            #only output the material if not the same as master
            if ob.data and ob.data.materials and ob.data.materials[0]:
                export_material_archive(ri, ob.data.materials[0].name)
        ri.ObjectInstance(instance_handle)
        ri.TransformEnd()
        ri.AttributeEnd()
def exportObjectArchive(ri, rpass, scene, ob, archive_filename, motion, mtx = None, 
        object_name = None, instance_handle = None, matNum = 0, material=None, bounds=None):
    ri.AttributeBegin()
    ri.Attribute("identifier", {"name": instance_handle})
    if ob.renderman.do_holdout:
            ri.Attribute("identifier", {"string lpegroup": ob.renderman.lpe_group})
    if ob.name in motion['transformation']:
        export_motion_begin(ri,scene, ob)
        
        for sample in motion['transformation'][ob.name]:
            ri.Transform(rib(sample))
            
        ri.MotionEnd()
    elif mtx:
        ri.Transform(rib(mtx))

    if hasattr(ob.data, 'materials'):
        if material:
            export_material_archive(ri, material.name)
        elif ob.data and ob.data.materials:
            if ob.data.materials[matNum]:
                export_material_archive(ri, ob.data.materials[matNum].name)
    #just get the relative path
    params = {"float[6] bound": rib_ob_bounds(ob.bound_box),
                 "string filename": os.path.relpath(archive_filename, rpass.paths['archive'])}
    if bounds:
        params["float[6] bound"] = bounds
    ri.Procedural2(ri.Proc2DelayedReadArchive, ri.SimpleBound, params)
    ri.AttributeEnd()
def removeMeshFromMemory (passedName):
    # Extra test because this can crash Blender if not done correctly.
    result = False
    mesh = bpy.data.meshes.get(passedName)
    if mesh != None:
        if mesh.users == 0:
            try:
                mesh.user_clear()
                can_continue = True
            except:
                can_continue = False
            
            if can_continue == True:
                try:
                    bpy.data.meshes.remove(mesh)
                    result = True
                except:
                    result = False
            else:
                # Unable to clear users, something is holding a reference to it.
                # Can't risk removing. Favor leaving it in memory instead of risking a crash.
                result = False
    else:
        # We could not fetch it, it does not exist in memory, essentially removed.
        result = True
    return result
def removeObjectFromMemory (passedName):
    # Extra test because this can crash Blender if not done correctly.
    result = False
    ob = bpy.data.objects.get(passedName)
    if ob != None:
        if ob.users == 0:
            try:
                ob.user_clear()
                can_continue = True
            except:
                can_continue = False
            
            if can_continue == True:
                try:
                    bpy.data.objects.remove(ob)
                    result = True
                except:
                    result = False
            else:
                # Unable to clear users, something is holding a reference to it.
                # Can't risk removing. Favor leaving it in memory instead of risking a crash.
                result = False
    else:
        # We could not fetch it, it does not exist in memory, essentially removed.
        result = True
    return result 
def returnNewMeshFromFaces(passedNewName, passedMesh, passedMaterialIndex = -1):
    # Take the passed mesh and make a new mesh that is made up of only with the vertices that the faces require.
    # You can optionaly include only faces for a specific material index.
    # (i.e. remove unused vertices.)
    me_result = None    
    if passedMesh != None:
        #to_console("returnNewMeshFromFaces: create a mesh made up of faces with material " + str(passedMaterialIndex))
        #Get the material based upon the passedMaterialIndex.
        if passedMaterialIndex == -1:
            # Default to the first one.
            mat = passedMesh.materials[0]
        else:
            # User specified another material.
            mat = passedMesh.materials[passedMaterialIndex]
        if mat != None:
            vert_list = []
            face_list =[]
            c = 0
            for face in passedMesh.polygons:
                can_proceed = False
                if passedMaterialIndex == -1: can_proceed = True
                if face.material_index == passedMaterialIndex: can_proceed = True
                if can_proceed == True:
                    x = []
                    for vert in face.vertices:
                        vertex = passedMesh.vertices[vert]
                        vert_list.append(rounded_tuple(vertex.co.to_tuple()))
                        x.append(c)
                        c =c + 1
                    face_list.append(x)
            
            if len(face_list) > 0:
                me_result = bpy.data.meshes.new(passedNewName)       # Create a new blank mesh.
                try:
                    me_result.from_pydata(vert_list,[],face_list)    # Give this empty mesh a list of verts and faces to call it's own.
                    me_result.update(calc_edges=True)
                    me_result.materials.append(mat)
                except:
                    me_result = None
    return me_result

def hasFaces(ob):
    l = 0
    if ob:
        if ob.type == 'CURVE' or ob.type == 'FONT':
            # If this curve is extruded or beveled it can produce faces from a to_mesh call.
            l = ob.data.extrude + ob.data.bevel_depth
        else:
            try:
                l = len(ob.data.polygons)
            except:
                l = 0
        if l == 0:
            # No faces. Perhaps it has edges that are using a modifier to define a surface.
            if len(ob.modifiers) > 0:
                try:
                    l = len(ob.data.vertices)
                except:
                    l = 0
    return l

# ------------- Texture optimisation -------------

# 3Delight specific tdlmake stuff
def make_optimised_texture_3dl(tex, texture_optimiser, srcpath, optpath):
    rm = tex.renderman

    debug("info","Optimising Texture: %s --> %s" % (tex.name, optpath))

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

def get_strands(ri, scene,ob, psys):
    tip_width = psys.settings.renderman.tip_width
    base_width = psys.settings.renderman.base_width
    conwidth = psys.settings.renderman.constant_width
    steps = 2 ** psys.settings.render_step 
    if conwidth:
        widthString = "constantwidth"
        hair_width = psys.settings.renderman.width
        debug("info",widthString, hair_width)
    else:
        widthString = "vertex float width"
        hair_width = []
        
    psys.set_resolution(scene, ob, 'RENDER')
    
    num_parents = len(psys.particles)
    num_children = len(psys.child_particles)
    total_hair_count = num_parents + num_children
    thicknessflag = 0
    width_offset = psys.settings.renderman.width_offset
    
    wmatx = ob.matrix_world.to_4x4().inverted()
    
    points = []
    
    vertsArray = []
    nverts = 0
    for pindex in range(total_hair_count):
        vertsInStrand = 0
        #walk through each strand
        for step in range(0, steps + 1):
            pt = psys.co_hair(object=ob, particle_no=pindex, step=step)
            
            if not pt.length_squared == 0:
                pt = wmatx * pt
                points.extend(pt)
                #double the first point
                if vertsInStrand == 0:
                    points.extend(pt)
                    vertsInStrand += 1
                vertsInStrand += 1
            else:
                #this strand ends prematurely
                break
            
        if vertsInStrand > 0:
            #for varying width make the width array
            if not conwidth:
                decr = (base_width - tip_width)/(vertsInStrand - 1)
                hair_width.extend([base_width] + [(base_width - decr * i) for i in range(vertsInStrand-1)] + [tip_width])

            #add the last point again
            points.extend(points[-3:])
            vertsInStrand += 1

            vertsArray.append(vertsInStrand)
            nverts += vertsInStrand
        #debug("info","Exporting ",total_hair_count , "Strands and ", nverts ," Vertices")
        #debug("info", "WIDTH:",widthString, hair_width)
        #debug("info", "VERTARRAY:",vertsArray)

        #if we get more than 100000 vertices, export ri.Curve and reset.  This is to avoid a maxint on the array length
        if nverts > 100000 and nverts == len(points)/3:
            ri.Basis("CatmullRomBasis", 1, "CatmullRomBasis", 1)
            ri.Attribute("dice", {"int roundcurve": 1, "int hair": 1})
            ri.Curves("cubic", vertsArray, "nonperiodic", {"P": rib(points), widthString: hair_width})
            nverts = 0
            points = []
            vertsArray = []
            if not conwidth:
                hair_width = []
        
    if nverts != 0 and nverts == len(points)/3:
        ri.Basis("CatmullRomBasis", 1, "CatmullRomBasis", 1)
        ri.Attribute("dice", {"int roundcurve": 1, "int hair": 1})
        ri.Curves("cubic", vertsArray, "nonperiodic", {"P": rib(points), widthString: hair_width})
    else:
        debug("error", "Strands from, ", ob.name, "could not be exported!")
        
    psys.set_resolution(scene, ob, 'PREVIEW')

# only export particles that are alive, 
# or have been born since the last frame
def valid_particle(pa, cfra):
    return not (pa.birth_time > cfra or (pa.birth_time + pa.die_time) < cfra)

def get_particle_bounds(particles, cfra):
    xs = []
    ys = []
    zs = []
    for p in particles:
        if valid_particle(p, cfra):
            xs.append(p.location[0])
            ys.append(p.location[1])
            zs.append(p.location[2])
    return [min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)]

def get_particles(scene, ob, psys):
    P = []
    rot = []
    width = []
    
    cfra = scene.frame_current
    psys.set_resolution(scene, ob, 'RENDER')
    for pa in [p for p in psys.particles if valid_particle(p, cfra)]:
        P.extend( pa.location )
        rot.extend( pa.rotation )
        
        if pa.alive_state != 'ALIVE':
            width.append(0.0)
        else:
            width.append(pa.size)
    psys.set_resolution(scene, ob, 'PREVIEW')
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

    interpolation = 'facevarying' if interpolation == '' else interpolation
    
    # default hard-coded prim vars
    if rm.export_smooth_normals and ob.renderman.primitive in \
            ('AUTO', 'POLYGON_MESH', 'SUBDIVISION_MESH'):
        N = get_mesh_vertex_N(geo)
        if N and len(N) > 0:
            primvars["varying normal N"] = N
    if rm.export_default_uv:
        uvs = get_mesh_uv(geo)
        if uvs and len(uvs) > 0:
            primvars["%s float[2] st" % interpolation] = uvs
    if rm.export_default_vcol:
        vcols = get_mesh_vcol(geo)
        if vcols and len(vcols) > 0:
            primvars["%s color Cs" % interpolation] = rib(vcols)
    
    # custom prim vars
    for p in rm.prim_vars:
        if p.data_source == 'VERTEX_COLOR':
            vcols = get_mesh_vcol(geo, p.data_name)
            if vcols and len(vcols) > 0:
                primvars["%s color %s" % (interpolation, p.name)] = rib(vcols)

        elif p.data_source == 'UV_TEXTURE':
            uvs = get_mesh_uv(geo, p.data_name)
            if uvs and len(uvs) > 0:
                primvars["%s float[2] %s" % (interpolation, p.name)] = uvs

        elif p.data_source == 'VERTEX_GROUP':
            weights = get_mesh_vgroup(ob, geo, p.data_name)
            if weights and len(weights) > 0:
                primvars["vertex float %s" % p.name] = weights

    return primvars
    
def get_primvars_particle(scene, psys):
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
 
def export_transform(ri, ob, flip_x=False):
    m = ob.parent.matrix_world * ob.matrix_local if ob.parent \
        else ob.matrix_world
    if flip_x:
        m = m.copy()
        m[0] *= -1.0
    ri.Transform(rib(m))

def export_light_source(ri, lamp, shape):
    name = "PxrAreaLight"
    params = {ri.HANDLEID: lamp.name, "float exposure":[lamp.energy], "__instanceid": lamp.name}
    if lamp.type == "HEMI":
        name = "PxrEnvMapLight"  
        params["color envtint"] = rib(lamp.color)
    else:
        params["color lightcolor"] = rib(lamp.color)
        params["string shape"] = shape
    ri.AreaLightSource(name, params)

def export_light_shaders(ri, lamp, do_geometry=True):
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

    handle = lamp.name
    rm = lamp.renderman
    #need this for rerendering
    ri.Attribute('identifier', {'string name': handle})
    #do the shader
    if rm.nodetree != '':
        export_shader_nodetree(ri, lamp, handle)
    else:
        export_light_source(ri, lamp, shapes[lamp.type][0])
    
    #now the geometry
    if do_geometry:
        shapes[lamp.type][1]()

def export_light(rpass, scene, ri, ob):
    lamp = ob.data
    rm = lamp.renderman
    params = []
    
    ri.AttributeBegin()
    ri.TransformBegin()
    export_transform(ri, ob, lamp.type == 'HEMI' or lamp.type == 'SUN')
    ri.ShadingRate(rm.shadingrate)

    export_light_shaders(ri, lamp)
    
    ri.TransformEnd()
    ri.AttributeEnd()
    
    ri.Illuminate(lamp.name, rm.illuminates_by_default)

    
def export_material(ri, rpass, scene, mat, handle=None):

    rm = mat.renderman

    if rm.nodetree != '':
        #ri.write('        Color %s\n' % rib(mat.diffuse_color))
        #ri.write('        Opacity %s\n' % rib([mat.alpha for i in range(3)]))
            
        #if rm.displacementbound > 0.0:
            #ri.write('        Attribute "displacementbound" "sphere" %f \n' % rm.displacementbound)
        #ri.Attribute('displacementbound', {'sphere':rm.displacementbound})
        export_shader_nodetree(ri, mat, handle, disp_bound=rm.displacementbound )
    else:
        #export_shader(file, scene, rpass, mat, 'shader') # BBM addition
        export_shader(ri, scene, rpass, mat, 'surface')
        export_shader(ri, scene, rpass, mat, 'displacement')
        export_shader(ri, scene, rpass, mat, 'interior')

def export_material_archive(ri, mat_name):
    ri.ReadArchive('material.'+mat_name)
    
    
def export_motion_begin(ri, scene, ob):
    ri.MotionBegin(get_ob_subframes(scene, ob))

def export_strands(ri, rpass, scene, ob, motion):
    for psys in ob.particle_systems:
        pname = psys_motion_name(ob, psys)    
        rm = psys.settings.renderman
        
        if psys.settings.type != 'HAIR':
            continue
        
        # use 'material_id' index to decide which material
        #if ob.data.materials and len(ob.data.materials) > 0:
            #if ob.data.materials[rm.material_id-1] != None:
                #mat = ob.data.materials[rm.material_id-1]
                #debug("info", "Material is %s" , mat)
                #export_material(ri, rpass, scene, mat)
        
        motion_blur = pname in motion['deformation']
            
        if motion_blur:
            export_motion_begin(ri, scene, ob)
            samples = motion['deformation'][pname]
        else:
            get_strands(ri, scene,ob, psys)
        
        #for nverts, P in samples:
            
            #ri.Basis("catmull-rom", 1, "catmull-rom", 1)
            #ri.Curves("cubic", nverts, "nonperiodic", 
                        #{"P": rib(P), "constantwidth": rm.width})

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


def export_particle_instances(ri, scene, ob, psys, motion):
    rm = psys.settings.renderman
    pname = psys_motion_name(ob, psys)
    
    # Precalculate archive path for object instances
    try:
        instance_ob = bpy.data.objects[rm.particle_instance_object]
    except:
        return

    instance_handle = ri.ObjectBegin()
    export_geometry(ri, scene, instance_ob, motion)
    if len(instance_ob.data.materials) > 0:
        export_material_archive(ri, instance_ob.data.materials[0].name)
    ri.ObjectEnd()

    if rm.use_object_material and len(instance_ob.data.materials) > 0:
        export_material_archive(ri, instance_ob.data.materials[0].name)
    
    motion_blur = pname in motion['deformation']
    cfra = scene.frame_current
    width = rm.width 

    for i in range(len( [ p for p in psys.particles \
                                    if valid_particle(p, cfra) ] )):
        
        ri.AttributeBegin()
        
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

        ri.ObjectInstance(instance_handle)
        ri.AttributeEnd()



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


#only for emitter types for now 
def export_particles(ri, rpass, scene, ob, motion, psys):

    rm = psys.settings.renderman
    pname = psys_motion_name(ob, psys)
    
    ri.AttributeBegin()
    ri.Attribute("identifier", {"name": pname})
    
    # use 'material_id' index to decide which material
    #if ob.data.materials:
    #    if ob.data.materials[rm.material_id-1] != None:
    #        mat = ob.data.materials[rm.material_id-1]
    #        export_material(ri, rpass, scene, mat)
    
    # Write object instances or points
    if rm.particle_type == 'OBJECT':
        export_particle_instances(ri, scene, ob, psys, motion)
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
        if o.type == 'CAMERA' or o.type == 'EMPTY':
            continue
        elif o.type == 'LAMP':
            if o.data.renderman.nodetree != '':
                textures = textures + get_textures(o.data)
        elif o.type in SUPPORTED_MATERIAL_TYPES:
            for mat in [mat for mat in o.data.materials if mat != None]:
                textures = textures + get_textures(mat)
        else:
            debug ("error","get_texture_list: unsupported object type [%s]." % o.type)
    return textures

def get_texture_list_preview(scene):
    #if not rpass.light_shaders: return
    textures = []
    return get_textures(find_preview_material(scene))


def export_scene_lights(ri, rpass, scene):
    #if not rpass.light_shaders: return

    export_comment(ri,'##Lights')
    
    for ob in [o for o in rpass.objects if o.type == 'LAMP']:
        export_light(rpass, scene, ri, ob)
    
'''def export_shader_init(ri, rpass, mat):
    rm = mat.renderman

    if rpass.emit_photons:
        file.write('        Attribute "photon" "string shadingmodel" "%s" \n' % rm.photon_shadingmodel)
'''

def export_default_bxdf(ri, name):
    #default bxdf a nice grey plastic
    ri.Bxdf("PxrDisney", "default", {'color baseColor': [0.18, 0.18, 0.18], 'string __instanceid': name})

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
                "float specular": mat.specular_intensity, 'string __instanceid': idblock.name}

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

def is_smoke(ob):
    for mod in ob.modifiers:
        if mod.type == "SMOKE" and mod.domain_settings:
            return True
    return False 

def detect_primitive(ob):
    rm = ob.renderman
    
    if rm.primitive == 'AUTO':
        if ob.type == 'MESH':
            if is_subdmesh(ob):
                return 'SUBDIVISION_MESH'
            elif is_smoke(ob):
                return 'SMOKE'
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
        debug ("error","export_curve: recieved a non-supported object type of [%s]." % ob.type)

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
        
        primvars = get_primvars(ob, mesh, "facevarying")
        primvars[ri.P] = P
        try:
            ri.SubdivisionMesh("catmull-clark", nverts, verts, tags, nargs, intargs,
                floatargs, primvars)
        except:
            #usually here we have stray vertices on the mesh. So just cull them!
            P = P[:3*max(verts)+3]
            primvars[ri.P] = P
            debug("warning","Stray vertices on mesh %s.  They were removed" % ob.name)
            ri.SubdivisionMesh("catmull-clark", nverts, verts, tags, nargs, intargs,
                floatargs, primvars)
    
    if motion_blur:
        ri.MotionEnd()
            
    bpy.data.meshes.remove(mesh)

def export_polygon_mesh(ri, scene, ob, motion):
    debug("info","export_polygon_mesh [%s]" % ob.name)
    mesh = create_mesh(scene, ob)
    
    motion_blur = ob.name in motion['deformation']
    
    if motion_blur:
        export_motion_begin(ri, scene, ob)
        samples = motion['deformation'][ob.name]
    else:
        samples = [get_mesh(mesh)]
        
    for nverts, verts, P in samples:
        primvars = get_primvars(ob, mesh, "facevarying")
        primvars['P'] = P
        try:
            ri.PointsPolygons(nverts, verts, primvars)
            is_error = False
        except:
            # Activate the texture space for the offending object so it stands out in the viewport.
            ob.show_texture_space = True
            debug("error", "Cannont export mesh: ", ob.name , " check mesh for vertices that are not forming a face.")
            is_error = True
    if is_error == False:
        if motion_blur:
            ri.MotionEnd()
    bpy.data.meshes.remove(mesh)

def export_simple_polygon_mesh(ri, name, mesh):
    debug("info","export_polygon_mesh [%s]" % name)
    
    samples = [get_mesh(mesh)]
        
    for nverts, verts, P in samples:
        primvars = {'P': P}
        try:
            ri.PointsPolygons(nverts, verts, primvars)
            is_error = False
        except:
            # Activate the texture space for the offending object so it stands out in the viewport.
            debug("error", "Cannont export mesh: ", name , " check mesh for vertices that are not forming a face.")
            is_error = True
    


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

#make an ri Volume from the smoke modifier
def export_smoke(ri, scene, ob, motion):
    smoke_modifier = None
    for mod in ob.modifiers:
        if mod.type == "SMOKE":
            smoke_modifier = mod
            break
    smoke_data = smoke_modifier.domain_settings
    #the original object has the modifier too.
    if not smoke_data:
        return
    
    params = {
        "varying float density": smoke_data.density_grid,
        "varying float flame": smoke_data.flame_grid,
    }
    ri.Volume("box", [-1,1,-1,1,-1,1], rib(smoke_data.domain_resolution), params)


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
    
def is_dupli_source(ob):
    # Is this object the source mesh for other duplis?
    result = False
    if ob.parent and ob.parent.dupli_type in SUPPORTED_DUPLI_TYPES: result = True	
    return result
    
def export_geometry_data(ri, scene, ob, motion, force_prim=''):
    if force_prim == '':
        prim = detect_primitive(ob)
    else:
        prim = force_prim
    
    if prim == 'NONE':
        return

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
    

    elif prim == 'SMOKE':
        export_smoke(ri, scene, ob, motion)
    
    # curve only
    elif prim == 'CURVE' or prim == 'FONT':
        # If this curve is extruded or beveled it can produce faces from a to_mesh call.
        l = ob.data.extrude + ob.data.bevel_depth
        if l > 0:
            export_polygon_mesh(ri, scene, ob, motion)
        else:
            export_curve(ri, scene, ob, motion) 
 
    # mesh only
    elif prim == 'POLYGON_MESH':
        export_polygon_mesh(ri, scene, ob, motion)
    elif prim == 'SUBDIVISION_MESH':
        export_subdivision_mesh(ri, scene, ob, motion)
    elif prim == 'POINTS':
        export_points(ri, scene, ob, motion)
  
def export_geometry(ri, scene, ob, motion):
    rm = ob.renderman
    
    if rm.geometry_source == 'BLENDER_SCENE_DATA':
        export_geometry_data(ri, scene, ob, motion)

    else:
        pass
        #ri.write(geometry_source_rib(scene, ob))


def export_object(ri, rpass, scene, ob, motion, mtx = None, dupli_name = None):
    rm = ob.renderman

    if ob.type in ('LAMP', 'CAMERA'): return

    if mtx != None:
        mat = mtx
    else:
        if ob.parent:
            mat = ob.parent.matrix_world * ob.matrix_local
        else:
            mat = ob.matrix_world

    ri.AttributeBegin()
    if dupli_name != None:
        ri.Attribute("identifier", {"name": dupli_name})
    else:
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

    export_geometry(ri, scene, ob, motion)
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
            motion['deformation'][pname].insert(0, get_strands(ri, scene, ob, psys));

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

#return the filename for a readarchive that this object will be written into 
#relative to archive directory if True
def get_archive_filename(scene, obj, motion, psys=None):
    if psys:
        pname = psys_motion_name(obj, psys)  
        if pname in motion['deformation']:
            return user_path(scene.renderman.path_object_archive_animated,
                    scene).replace('{object}', '%s.%s.%s' % (obj.name, psys.name, psys.settings.type))
        return user_path(scene.renderman.path_object_archive_static,
                    scene).replace('{object}', '%s.%s.%s' % (obj.name, psys.name, psys.settings.type))
    elif obj.name in motion['deformation']:
        return user_path(scene.renderman.path_object_archive_animated,
                        scene, obj)
    else:
        return user_path(scene.renderman.path_object_archive_static,
                        scene, obj)

def duplis_updated_from_master(master, duplis):
    master_time = master.renderman.update_timestamp
    for dupli_name, dupli_type, m in duplis:
        if bpy.data.objects.get(dupli_name).renderman.update_timestamp > master_time:
            return True
    return False

def export_objects(ri, rpass, scene, motion):
    update_time = time.time()

    # Lists that hold names of candidates to consider for export.
    candidate_datablocks = []
    candidate_objects = []
    candidate_multi_material_datablocks = []
    candidate_multi_material_objects = []
    candidate_lights = []
    candidate_duplis = {}
    candidate_groups = []
    
    # Lists that hold names of datablocks that are already exported.
    exported_datablocks = []
    exported_objects = []
    exported_lights = []
    exported_duplis = []
    exported_groups = []
    
    # List to hold handles for archives and instances.
    candidate_instance_sources = []
    candidate_instance_handles = []
    candidate_archive_handles = []

    # list to hold materials to output
    candidate_material_handles = bpy.data.materials.keys()
    
    def returnHandleForName(passed_list, passed_name):
        # Expects list items to contain two entries: name,handle.
        for name,handle in passed_list:
            if name == passed_name:
                return handle
        return None

    def reviewObjectForDuplis (scene, ob_name, parent_name, candidate_duplis):
        ob = bpy.data.objects.get(ob_name)
        if ob:
            ob.dupli_list_create(scene, 'RENDER')
            for dob in ob.dupli_list:
                if dob.object != None:
                    if dob.hide:
                        # User has hidden the child object from rendering...
                        debug ("info","skipping export of [%s], it is hidden from rendering." % dob.object.name)
                    else:
                        # NOTE: parent_name is only really needed for particles because multiple systems on the same emitter can be in use.
                        dupli_name = "%s_%s_p%s" % (ob.name, ("%s~%s" % (parent_name,dob.object.name)), returnNameForNumber(dob.index))
                        if dob.object.type in SUPPORTED_INSTANCE_TYPES:
                            # This export object will ginstance the above datablock at the new world location.
                            if dob.object.name not in candidate_duplis:
                                candidate_duplis[dob.object.name] = []
                            candidate_duplis[dob.object.name].append((dob.object.type, dob.matrix.copy(), dupli_name))
                        elif dob.object.type == 'LAMP':
                            if dob.object.name not in candidate_duplis:
                                candidate_duplis[dob.object.name] = []
                            candidate_duplis[dob.object.name].append((dob.object.type, dob.matrix.copy(), dupli_name))
                        else:
                            debug ("warning","unsupported export type of [%s] found in dupli_list." % dob.object.type)
                else:
                    debug ("warning","None type object in dupli_list?")
            ob.dupli_list_clear()
        else:
            debug ("info","reviewObjectForDuplis: passed object [%s] is not in memory." % ob_name)

    # Begin first pass scan of the scene and populate various lists based upon objects discovered.
    for ob in renderable_objects(scene):
        debug ("info","PRMan: Scanning object [%s][%s]" % (ob.name, ob.type))
        if ob.type == 'EMPTY':
            # Support OBJECT and GROUP based duplication for Empties.
            if ob.dupli_type == 'GROUP' and ob.dupli_group != None:
                candidate_groups.append((ob.dupli_group.name))			# NOTE: The group will take care of exporting any datablocks.
                reviewObjectForDuplis (scene, ob.name, "", candidate_duplis)
            if ob.dupli_type == 'OBJECT' and ob.dupli_object != None:
                candidate_instance_sources.append(ob.dupli_object.name)
                reviewObjectForDuplis (scene, ob.name, "", candidate_duplis)
                
        elif ob.type == 'LAMP':
            # Not supporting dupli-group for lamp type objects at this time.
            candidate_lights.append((ob.name, ob.type))

        elif ob.type in SUPPORTED_INSTANCE_TYPES:
            if ob.parent and ob.parent.dupli_type in SUPPORTED_DUPLI_TYPES:
                # Skip rendering this object because it a child of a dupli object.
                # Add it as an instance source, however.
                candidate_instance_sources.append(ob.name)
            else:
                if ob.dupli_type in SUPPORTED_DUPLI_TYPES:
                    # This object has duplis.
                    reviewObjectForDuplis (scene, ob.name, "", candidate_duplis)

                if ob.particle_systems:
                    # NOTE: Support multiple particle systems.
                    contains_duplis = False
                    for psys in ob.particle_systems: 
                        if psys != None:
                            pset = psys.settings
                            if pset.use_render_emitter:
                                # User wants to render the emitter as well as the particles.
                                # In a multiple particle system situation any duplicate emitter objects will be filtered by uniquifyList.
                                candidate_objects.append((ob.name, ob.type))
                                candidate_datablocks.append((ob.name, ob.type))
                            if pset.render_type == 'OBJECT' and pset.dupli_object != None: contains_duplis = True
                            if pset.render_type == 'GROUP' and pset.dupli_group != None: contains_duplis = True

                    if contains_duplis:
                        # This object has duplis.
                        reviewObjectForDuplis (scene, ob.name, "", candidate_duplis)	# Should pass pset.name not "" for multi-psys support.
                    else:
                        pass
                        # Scan for hair based particle systems.
                        
                elif ob.dupli_type in SUPPORTED_DUPLI_TYPES:
                    # Dupli source meshes should not get rendered.
                    # But we do need to fetch the list of duplis they represent.
                    if ob.parent:
                        parent_name = ob.parent.name
                    else:
                        parent_name = ""
                    reviewObjectForDuplis(scene, ob.name, parent_name, candidate_duplis)
                else:
                    l = len(ob.data.materials)
                    if l > 1:
                        debug ("info","Adding multi material object and datablock [%s]." % ob.name)
                        candidate_multi_material_objects.append((ob.name, ob.type))
                        candidate_multi_material_datablocks.append((ob.name, ob.type))
                    else:
                        debug ("info","Adding single material object and datablock [%s]." % ob.name)
                        candidate_objects.append((ob.name, ob.type))
                        candidate_datablocks.append((ob.name, ob.type))

        elif ob.type == 'CURVE':
            candidate_objects.append((ob.name, ob.type))
        elif ob.type == 'CAMERA':
            pass
        else:
            debug ("warning","Unsupported object type [%s]." % ob.type)
    # End first pass through objects in the scene.
    
    # Lists that hold names of candidates to consider for export.
    debug ("info","\ncandidate_datablocks")
    printList(candidate_datablocks)
    debug ("info","\ncandidate_objects")
    printList(candidate_objects)
    debug ("info","\ncandidate_lights")
    printList(candidate_lights)
    debug ("info","\ncandidate_duplis")
    debug ("info", len(candidate_duplis))
    #printList(candidate_duplis)
    debug ("info","\ncandidate_groups")
    printList(candidate_groups)
    debug ("info","\ncandidate_multi_material_objects")
    printList(candidate_multi_material_objects)
    debug ("info","\ncandidate_multi_material_datablocks")
    printList(candidate_multi_material_datablocks)
    
    # Lists that hold names of datablocks that are already exported.
    debug ("info","\nexported_datablocks")
    printList(exported_datablocks)
    debug ("info","\nexported_objects")
    printList(exported_objects)
    debug ("info","\nexported_lights")
    printList(exported_lights)
    debug ("info","\nexported_duplis")
    debug ("info", len(exported_duplis))
    #printList(exported_duplis)
    debug ("info","\nexported_groups")
    printList(exported_groups)
    
    debug ("info","\ncandidate_instance_sources")
    printList(candidate_instance_sources)
    debug ("info","\ncandidate_instance_handles")
    printList(candidate_instance_handles)
    debug ("info","\ncandidate_archive_handles")
    printList(candidate_archive_handles)

    unique_groups = uniquifyList(candidate_groups)
    
    # Groups can reference objects that are not on renderable layers so review the objects in groups to add to the candidate list.
    for group_name in unique_groups:
        grp = bpy.data.groups.get(group_name)
        if grp != None:
            if len(grp.objects):
                for grp_ob in grp.objects:
                    if grp_ob.type in SUPPORTED_INSTANCE_TYPES:
                        candidate_datablocks.append((grp_ob.name, grp_ob.type))
                    elif grp_ob.type == 'LAMP':
                        candidate_lights.append((grp_ob.name, grp_ob.type))
            else:
                debug ("warning","group [%s] declared but contains no objects." % group_name)
        else:
            debug ("warning","referenced group [%s] is None." % group_name)
    # Export scene lights.
    export_comment(ri, '## LIGHTS')
    unique_lights = uniquifyList(candidate_lights)
    for ob_name, ob_type in unique_lights:
        ob_temp = bpy.data.objects.get(ob_name)
        if ob_temp != None:
            if ob_type == 'LAMP':
                export_light(rpass, scene, ri, ob_temp)
                exported_lights.append(ob_temp.name)
    
    #default bxdf AFTER lights
    export_default_bxdf(ri, 'default')
    #export archive of materials
    archive_filename = user_path(scene.renderman.path_object_archive_static,
                                scene).replace('{object}', 'materials')
    ri.Begin(archive_filename)
    for mat_name in candidate_material_handles:
        ri.ArchiveBegin('material.' + mat_name)
        export_material(ri, rpass, scene, bpy.data.materials[mat_name])
        ri.ArchiveEnd()
    ri.End()
    ri.ReadArchive(archive_filename)

    lazy_ribgen = scene.renderman.lazy_rib_gen

    # Export datablocks for archiving.
    #export_comment(ri, '## ARCHIVES')
    unique_datablocks = uniquifyList(candidate_datablocks)
    debug ("info","unique_datablocks: %s" % unique_datablocks)
    for ob_name, ob_type in unique_datablocks:
        ob_temp = bpy.data.objects.get(ob_name)
        if ob_temp != None:
            if hasFaces(ob_temp):
                # Check if this archive handle already exists.
                handle_name = ob_temp.data.name
                if is_smoke(ob_temp):
                    handle_name = ob_temp.name
                archive_handle = returnHandleForName(candidate_archive_handles,handle_name)
                if archive_handle == None:
                    # No matching handle has been written to the RIB file yet, we are first.
                    # Export this polymesh data as an archive to be referenced later on.
                    archive_filename = get_archive_filename(scene, ob_temp, motion)
                    candidate_archive_handles.append((ob_name, handle_name))
                    if not lazy_ribgen or check_if_archive_dirty(ob_temp.renderman.update_timestamp, archive_filename):
                        ri.Begin(archive_filename)
                        export_geometry(ri, scene, ob_temp, motion)
                        ri.End()
                        update_timestamp(rpass, ob_temp)
                    if ob_temp.particle_systems:
                        debug("info" , "The object has a particle system" , ob_temp)
                        
                        for psys in ob_temp.particle_systems:
                            if psys.settings.type == 'HAIR':
                                debug("info" , "The object has a particle system hair" , ob_temp)
                                strand_name = handle_name + "HAIR"
                                archive_filename = get_archive_filename(scene, ob_temp, motion, psys)
                                if not lazy_ribgen or check_if_archive_dirty(ob_temp.renderman.update_timestamp, archive_filename):
                                    ri.Begin(archive_filename)
                                    export_strands(ri, rpass, scene, ob_temp, motion)
                                    ri.End()
                            elif psys.settings.type == 'EMITTER':
                                debug("info" , "The object has a particle system Emitter" , ob_temp)
                                particle_name = handle_name + "PARTICLES"
                                archive_filename = get_archive_filename(scene, ob_temp, motion, psys)
                                if not lazy_ribgen or check_if_archive_dirty(ob_temp.renderman.update_timestamp, archive_filename):
                                    ri.Begin(archive_filename)
                                    export_particles(ri, rpass, scene, ob_temp, motion, psys)
                                    ri.End()

                    exported_datablocks.append(ob_name)
                else:
                    debug ("info","Skipping creating another archive of [%s], it already exists as an Archive in the RIB." % handle_name)
            else:
                debug ("warning","Datablock [%s] has no faces, skipping export?" % ob_name)
        else:
            debug ("warning","[%s] in unique_datablocks but not in memory?" % ob_name)

    # Export objects that reference archives.
    export_comment(ri, '## OBJECTS')
    debug ("info","candidate_archive_handles: %s" % candidate_archive_handles)
    debug ("info","candidate_objects: %s" % candidate_objects)
    unique_objects = uniquifyList(candidate_objects)
    debug ("info","unique_objects: %s" % unique_objects)
    for ob_name, ob_type in unique_objects:
        debug ("info","fetching [%s]" % ob_name)
        ob_temp = bpy.data.objects.get(ob_name)
        if ob_temp != None:
            if ob_temp.type in SUPPORTED_INSTANCE_TYPES:
                if hasFaces(ob_temp):
                    # See if we have already written out this datablock by fetching it's handle.
                    instance_handle = returnHandleForName(candidate_archive_handles,ob_name)
                    if instance_handle != None:
                        # We have a handle so it is ok to reference this with an object shader/transform.
                        archive_filename = get_archive_filename(scene, ob_temp, motion)
                        exportObjectArchive(ri, rpass, scene, ob_temp, archive_filename, motion, returnMatrixForObject(ob_temp), ob_name, instance_handle)
                        if ob_temp.particle_systems:
                            for psys in ob_temp.particle_systems:
                                if psys.settings.type == 'HAIR':
                                    hair_handle = instance_handle + "HAIR"
                                    archive_filename = get_archive_filename(scene, ob_temp, motion, psys)
                                    exportObjectArchive(ri, rpass, scene, ob_temp, archive_filename, motion,
                                        returnMatrixForObject(ob_temp), ob_name, hair_handle, 
                                        psys.settings.renderman.material_id - 1)
                                if psys.settings.type == 'EMITTER':
                                    particle_name = instance_handle + "PARTICLES"
                                    archive_filename = get_archive_filename(scene, ob_temp, motion, psys)
                                    exportObjectArchive(ri, rpass, scene, ob_temp, archive_filename, motion,
                                        Matrix.Identity(4), ob_name, particle_name, 
                                        psys.settings.renderman.material_id - 1, bounds=get_particle_bounds(psys.particles, scene.frame_current))
                        exported_objects.append(ob_name)
                    else:
                        debug ("info","Could not locate handle for [%s] it probably wasn't archive" % ob_name)
                else:
                    debug ("warning","Object [%s] has no faces, skipping export?" % ob_name)
            elif ob_type == 'CURVE':
                export_curve(ri, scene, ob_temp, motion)
            else:
                debug ("warning","unsupported object [%s] detected for export." % ob_name)
        else:
            debug ("warning","object [%s] in list but not in memory?" % ob_name)

    export_comment(ri, '## INSTANCES')
    #Get the object name of every possible particle or dupli source.
    debug ("info","unique_instance_sources: %s" % candidate_duplis.keys())
    
    for master_name, duplis in candidate_duplis.items():
        ob_master = bpy.data.objects.get(master_name)
        if ob_master == None:
            debug ("warning","instance master not found: %s" % master_name)
            continue
        
        #create archive name of master name
        archive_filename = user_path(scene.renderman.path_object_archive_static,
                                            scene).replace('{object}', master_name+'.' + 'INSTANCES')
        #check if dirty or any dupli updated
        if not lazy_ribgen or check_if_archive_dirty(ob_master.renderman.update_timestamp, archive_filename):
            #output object begin of master
            update_timestamp(rpass, ob_master)
            ri.Begin(archive_filename)
            instance_handle = ri.ObjectBegin()
            export_geometry(ri, scene, ob_master, motion)
            if len(ob_master.data.materials) > 0:
                export_material_archive(ri, ob_master.data.materials[0].name)
            ri.ObjectEnd()
            #for each dupli
            for dupli_type, m, dupli_name in duplis:
                #output object instance
                #ob_dupli = bpy.data.objects.get(master_name)
                if dupli_type in SUPPORTED_INSTANCE_TYPES:
                    if hasFaces(ob_master):
                        handle_name = ob_master.data.name
                        #print("candidate_instance_handles: %s" %candidate_instance_handles)
                        exportObjectInstance(ri, rpass, scene, ob_master, m, dupli_name, instance_handle)
                        exported_objects.append(dupli_name)
                    else:
                        debug ("warning","Dupli [%s] has no faces, skipping export?" % master_name)
                elif dupli_type == 'LAMP':
                    #exportLight (ri, scene, ob_temp, m, dupli_name)
                    exported_objects.append(dupli_name)
                else:
                    debug ("warning","Unsupported export type [%s] in dupli_list." % dupli_type)
            ri.End()
        #output readArchive
        ri.ReadArchive(archive_filename)       
        
    #for multi-material objects put them all in one rib
    export_comment(ri, '## MULTI-MATERIAL OBJECTS')
    for ob_candidate_name,ob_candidate_type in candidate_multi_material_objects:
        ob_temp = bpy.data.objects.get(ob_candidate_name)
        if ob_temp != None:
            if ob_temp.type == 'MESH':
                debug ("info","processing multi-material mesh [%s]." % ob_candidate_name)
                # The mesh with modifiers applied.
                me_source = ob_temp.to_mesh(scene,True,'RENDER')
                m = len(me_source.materials)
                #m = 1 #Atom 07042012 temporary disable.
                archive_filename = get_archive_filename(scene, ob_temp, motion)
                if m > 1  and \
                    not lazy_ribgen or check_if_archive_dirty(ob_temp.renderman.update_timestamp, archive_filename):
                    #Atom 04302012.
                    #export_comment(ri, 'Atom: Create a mesh for every material applied.\n')
                    # A list of all the vertices.
                    list_verts = []
                    for vertex in me_source.vertices:
                        list_verts.append(rounded_tuple(vertex.co.to_tuple()))

                    # Fetch the vertex and face list from the provided mesh type object.
                    list_faces_by_material = []
                    for face in me_source.polygons:
                        x = [f for f in face.vertices]
                        list_faces_by_material.append([face.material_index,x])
                    c = 0
                    ri.Begin(archive_filename)

                    for mat in me_source.materials:
                        me_name = "me_" + str(int(c))+ "-PIX_" + ob_candidate_name
                        me = returnNewMeshFromFaces(me_name,me_source,c)
                        if me != None:
                            ob_name = str(int(c))+ "-PIX_" + ob_candidate_name
                            
                            ri.AttributeBegin()
                            #just export the mesh
                            export_material_archive(ri, mat.name)
                            export_simple_polygon_mesh(ri, me_name, me)
                            ri.AttributeEnd()
                                
                            bpy.data.meshes.remove(me)
                        else:
                            debug ("info","export_objects: problem creating MESH [" + me_name + "] in memory.  Possibly due to a material without faces.")
                        c = c + 1
                    ri.End()

                if ob_temp.parent:
                    matrix = ob_temp.parent.matrix_world * ob_temp.matrix_local
                else:
                    matrix = ob_temp.matrix_world
                exportObjectArchive(ri, rpass, scene, ob_temp, archive_filename, motion, matrix, ob_name, ob_name, material=None)
                            
                update_timestamp(rpass, ob_temp)
            else:
                debug ("error","Unsupported multi-material object type [%s]." % ob.type)

#update the timestamp on an object from the time the rib writing started:
def update_timestamp(rpass, obj):
    if obj and rpass.update_time:
        obj.renderman.update_timestamp = rpass.update_time

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
            export_geometry_data(file, scene, ob, motion)
    
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
                    val_type = type(val).__name__
                    if val_type == 'IDPropertyArray':
                        param_type = "color %s" % (key)
                        params[param_type] = rib(val)
                    else:
                        param_type = "%s %s" % (type(val).__name__, key)
                        params[param_type] = val
    
    return params

def export_integrator(ri, rpass, scene, preview=False):
    rm = scene.renderman
    integrator = rm.integrator
    if preview or rpass.is_interactive:
        integrator = "PxrPathTracer"

    integrator_settings = getattr(rm, "%s_settings" % integrator)
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

def export_camera(ri, scene, motion, camera_to_use=None):
    
    if not scene.camera or scene.camera.type != 'CAMERA':
        return
        
    r = scene.render
    ob = camera_to_use if camera_to_use else scene.camera   
    cam = ob.data
    rm = scene.renderman
    
    xaspect, yaspect, aspectratio = render_get_aspect(r, cam)
    
    if rm.depth_of_field:
        if cam.dof_object:
            dof_distance = (ob.location - cam.dof_object.location).length
        else:
            dof_distance = cam.dof_distance
        ri.DepthOfField(rm.fstop, (cam.lens * 0.001), dof_distance)
        
    if scene.renderman.motion_blur:
        ri.Shutter(rm.shutter_open, rm.shutter_close)
        #ri.Option "shutter" "efficiency" [ %f %f ] \n' % (rm.shutter_efficiency_open, rm.shutter_efficiency_close))

    ri.Clipping(cam.clip_start, cam.clip_end)
    
    if cam.renderman.use_physical_camera:
        #use pxr Camera
        params = property_group_to_params(cam.renderman.PxrCamera_settings)
        if 'float fov' not in params:
            lens= cam.lens
            sensor = cam.sensor_height \
                if cam.sensor_fit == 'VERTICAL' else cam.sensor_width
            params['float fov'] = 360.0*math.atan((sensor*0.5)/lens/aspectratio)/math.pi
        ri.Projection("PxrCamera", params)
    elif cam.type == 'PERSP':
        lens= cam.lens
        
        sensor = cam.sensor_height \
            if cam.sensor_fit == 'VERTICAL' else cam.sensor_width

        fov = 360.0*math.atan((sensor*0.5)/lens/aspectratio)/math.pi
        ri.Projection("perspective", {"fov": fov})
    else:
        lens= cam.ortho_scale
        xaspect= xaspect*lens/(aspectratio*2.0)
        yaspect= yaspect*lens/(aspectratio*2.0)
        ri.Projection("orthographic")

    ri.ScreenWindow(-xaspect, xaspect, -yaspect, yaspect)

    export_camera_matrix(ri, scene, ob, motion)
    
    if camera_to_use:
        ri.Camera("world")
    
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
    ri.Option("searchpath", {"string archive": paths['archive']})

def export_header(ri):
    render_name = os.path.basename(bpy.data.filepath)
    export_comment(ri, 'Generated by PRMan for Blender, v%s.%s.%s \n' % (addon_version[0], addon_version[1], addon_version[2]))
    export_comment(ri, 'From File: %s on %s\n' % (render_name, time.strftime("%A %c")))
    
    
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
        ("allshadows", rm.holdout_settings.do_collector_shadow, "color", "color lpe:holdout;shadowcollector"),
        ("allreflections", rm.holdout_settings.do_collector_reflection, "color", "color lpe:holdout;reflectioncollector"),
        ("allindirectdiffuse", rm.holdout_settings.do_collector_indirectdiffuse, "color", "color lpe:holdout;indirectdiffusecollector"),
        ("allsubsurface", rm.holdout_settings.do_collector_subsurface, "color", "color lpe:holdout;subsurfacecollector"),
        ("allrefractions", rm.holdout_settings.do_collector_refraction, "color", "color lpe:holdout;refractioncollector")
    ]

    #Set bucket shape.
    if rpass.is_interactive:
        ri.Option("bucket", {"string order": [ 'spiral']})

    elif rm.bucket_shape == 'SPIRAL':
        settings = scene.render

        if rm.bucket_sprial_x <= settings.resolution_x and rm.bucket_sprial_y <= settings.resolution_y:
            if rm.bucket_sprial_x == -1 and rm.bucket_sprial_y == -1:
                ri.Option("bucket", {"string order": [ rm.bucket_shape.lower() ]})
            elif rm.bucket_sprial_x == -1:
                halfX = settings.resolution_x / 2
                debug("info", halfX)
                ri.Option("bucket", {"string order": [ rm.bucket_shape.lower() ], "orderorigin": [int(halfX) ,rm.bucket_sprial_y]})
            elif rm.bucket_sprial_y == -1:
                halfY = settings.resolution_y / 2
                ri.Option("bucket", {"string order": [ rm.bucket_shape.lower() ], "orderorigin": [rm.bucket_sprial_y, int(halfY) ]})
            else:
                ri.Option("bucket", {"string order": [ rm.bucket_shape.lower() ], "orderorigin": [rm.bucket_sprial_x ,rm.bucket_sprial_y]})
        else:
            debug("info", "OUTSLIDE LOOP")
            ri.Option("bucket", {"string order": [ rm.bucket_shape.lower() ]})
    else:
        ri.Option("bucket", {"string order": [ rm.bucket_shape.lower() ]})
    #declare display channels
    for aov, doit, declare_type, source in aovs:
        if doit and declare_type:
            params = {}
            if source:
                params['string source'] = source
            ri.DisplayChannel('%s %s' % (declare_type, aov), params)

    if(rm.display_driver == 'it'):
        if find_it_path() == None:
            debug("error", "RMS is not installed IT not available!")
            dspy_driver = 'multires'
        else:
            dspy_driver = rm.display_driver
    else:
        dspy_driver = rm.display_driver

    
    main_display = user_path(rm.path_display_driver_image, 
                scene=scene)
    image_base, ext = main_display.rsplit('.', 1)
    ri.Display(main_display, dspy_driver, "rgba", 
                {"quantize": [0, 0, 0, 0]})

    #now do aovs
    for aov, doit, declare, source in aovs:
        if doit:
            params = {"quantize": [0, 0, 0, 0]}
            if source and 'holdout' in source:
                params['int asrgba'] = 1
            ri.Display('+' + image_base + '.%s.' % aov + ext, dspy_driver, aov, params)

    if rm.do_denoise and not rpass.is_interactive:
        #add display channels for denoising
        denoise_aovs = [
        #(name, declare type/name, source, statistics, filter)
            ("Ci", 'color', None, None, None),
            ("a", 'float', None, None, None),
            ("mse", 'color', 'color Ci', 'mse', None),
            ("albedo", 'color', 'lpe:nothruput;noinfinitecheck;noclamp;unoccluded;overwrite;C(U2L)|O', None, None), 
            ("diffuse", 'color', 'color lpe:C(D[DS]*[LO])|O', None, None), 
            ("diffuse_mse", 'color', 'color lpe:C(D[DS]*[LO])|O', 'mse', None), 
            ("specular", 'color', 'color lpe:CS[DS]*[LO]', None, None), 
            ("specular_mse", 'color', 'color lpe:CS[DS]*[LO]', 'mse', None), 
            ("z", 'float', 'float z', None, True), 
            ("z_var", 'float', 'float z', "variance", True), 
            ("normal", 'normal', 'normal Nn', None, None), 
            ("normal_var", 'normal', 'normal Nn', "variance", None), 
            ("forward", 'vector', 'vector motionFore', None, None), 
            ("backward", 'vector', 'vector motionBack', None, None)
        ]

        for aov, declare_type, source, statistics, do_filter in denoise_aovs:
            params = {}
            if source:
                params['string source'] = source
            if statistics:
                params['string statistics'] = statistics
            if do_filter:
                params['string filter'] = rm.pixelfilter    
            ri.DisplayChannel('%s %s' % (declare_type, aov), params)

        #output denoise_data.exr
        ri.Display('+' + image_base + '.denoise.exr', 'openexr', 
            "Ci,a,mse,albedo,diffuse,diffuse_mse,specular,specular_mse,z,z_var,normal,normal_var,forward,backward",
            {"int asrgba": 1})
        



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

    if preview or rpass.is_interactive:
        hider_params['int maxsamples'] = rm.preview_max_samples
        hider_params['int minsamples'] = rm.preview_min_samples
        pv = rm.preview_pixel_variance

    ri.PixelVariance(pv)

    if rm.light_localization:
        ri.Option("shading",  {"int directlightinglocalizedsampling":4})

    if rm.do_denoise:
        hider_params['string pixelfiltermode'] = 'importance'
    
    if rm.hider == 'raytrace':
        ri.Hider(rm.hider, hider_params)

def write_rib(rpass, scene, ri):
    #info_callback('Generating RIB')
    
    # precalculate motion blur data
    rpass.motion_blur = None
    rpass.objects = renderable_objects(scene)
    rpass.archives = []

    motion = export_motion(rpass, scene)
    
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
    #export_scene_lights(ri, rpass, scene)

    export_objects(ri, rpass, scene, motion)
    
    ri.WorldEnd()

    ri.FrameEnd()
    
def write_preview_rib(rpass, scene, ri):
    preview_rib_data_path = \
            rib_path(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                    'preview', "preview_scene.rib"))
        
    export_header(ri)
    export_searchpaths(ri, rpass.paths)
    
    # temporary tiff display to be read back into blender render result
    ri.FrameBegin(1)
    ri.Display(os.path.basename(rpass.paths['render_output']), "tiff", "rgb",
                                {ri.DISPLAYQUANTIZE: [0, 0, 0, 0]})
    

    export_hider(ri, rpass, scene, preview=True)
    export_integrator(ri, rpass, scene, preview=True)
    

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
    export_material(ri, rpass, scene, mat, 'preview')
    preview_model(ri,mat)
    ri.AttributeEnd()
    
    ri.WorldEnd()
    ri.FrameEnd()

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

def interactive_initial_rib(rpass, scene, ri, prman):
    ri.Display('rerender', 'it', 'rgba')
    export_hider(ri, rpass, scene, True)

    ri.EditWorldBegin(rpass.paths['rib_output'], {"string rerenderer": "raytrace"})
    ri.Option('rerender', {'int[2] lodrange': [0,3]})      
    
    ri.ArchiveRecord("structure", ri.STREAMMARKER + "_initial")
    prman.RicFlush("_initial", 1, ri.FINISHRENDERING)

#flush the current edit
def edit_flush(ri, edit_num, prman):
    ri.ArchiveRecord("structure", ri.STREAMMARKER + "%d" % edit_num)
    prman.RicFlush("%d" % edit_num, 1, ri.SUSPENDRENDERING)

def issue_light_transform_edit(ri, obj):
    lamp = obj.data
    ri.EditBegin('attribute', {'string scopename': obj.data.name})
    export_transform(ri, obj, lamp.type == 'HEMI' or lamp.type == 'SUN')
    ri.EditEnd()
    

def issue_light_shader_edit(ri, rpass, obj, prman):
    if reissue_textures(ri, rpass, obj.data):
        rpass.edit_num += 1
        edit_flush(ri, rpass.edit_num, prman)

    ri.EditBegin('instance')
    export_light_shaders(ri, obj.data, do_geometry=False)
    ri.EditEnd()
            
def issue_camera_edit(ri, rpass, camera):
    ri.EditBegin('option')
    export_camera(ri, rpass.scene, {'transformation':[]}, camera_to_use=camera)
    ri.EditEnd()

def issue_shader_edit(ri, rpass, mats_to_edit, prman):
    tex_made = False
    for mat in mats_to_edit:
        if reissue_textures(ri, rpass, mat):
            tex_made = True

    #if texture made flush it
    if tex_made:
        rpass.edit_num += 1
        edit_flush(ri, rpass.edit_num, prman)

    ri.EditBegin('instance')
    for mat in mats_to_edit:
        export_material(ri, rpass, rpass.scene, mat)
    ri.EditEnd()

#search this material/lamp for textures to re txmake and do them
def reissue_textures(ri, rpass, mat):
    made_tex = False
    if mat.renderman.nodetree != '':
        textures = get_textures(mat)
        
        files = rpass.convert_textures(textures)
        if len(files) > 0:
            return True
    return False

#test the active object type for edits to do then do them
def issue_edits(rpass, ri, active, prman):
    
    do_edit = active.is_updated
    #first check out if there's edit to do    
    mats_to_edit = []
    if hasattr(active.data, 'materials'):
        #update the light position and shaders if updated
        for mat in active.data.materials:
            if mat != None and mat.renderman.nodetree != '':
                nt = bpy.data.node_groups[mat.renderman.nodetree]
                if nt.is_updated:
                    mats_to_edit.append(mat)
        if len(mats_to_edit) > 0:
            do_edit = True
    elif active.type == 'LAMP':
        nt = bpy.data.node_groups[active.data.renderman.nodetree]
        if nt.is_updated or nt.is_updated_data:
            do_edit = True

    if do_edit:
        rpass.edit_num += 1
        
        edit_flush(ri, rpass.edit_num, prman)
        #only update lamp if shader is update or pos, seperately
        if active.type == 'LAMP':
            lamp = active.data
            if active.is_updated:
                issue_light_transform_edit(ri, active)
            
            nt = bpy.data.node_groups[lamp.renderman.nodetree]
            if nt.is_updated or nt.is_updated_data:
                issue_light_shader_edit(ri, rpass, active, prman)
    
        elif active.type == 'CAMERA' and active.is_updated:
            issue_camera_edit(ri, rpass, active)
        else:
            #geometry can only edit shaders
            if len(mats_to_edit) > 0:
                issue_shader_edit(ri, rpass, mats_to_edit, prman)
    
    
