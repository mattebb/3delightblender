from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_mesh import RmanSgMesh
from ..rman_utils import object_utils
from ..rman_utils import string_utils

import bpy
import math

def _get_mats_faces_(nverts, material_ids):

    mats = {}
    for face_id, num_verts in enumerate(nverts):
        mat_id = material_ids[face_id]
        if mat_id not in mats:
            mats[mat_id] = []
        mats[mat_id].append(face_id)
    return mats

def _is_multi_material_(ob, mesh):
    if type(mesh) != bpy.types.Mesh or len(ob.data.materials) < 2 \
            or len(mesh.polygons) == 0:
        return False
    first_mat = mesh.polygons[0].material_index
    for p in mesh.polygons:
        if p.material_index != first_mat:
            return True
    return False

def _get_subd_creases_(mesh):
    creases = []

    # only do creases 1 edge at a time for now,
    # detecting chains might be tricky..
    for e in mesh.edges:
        if e.crease > 0.0:
            creases.append((e.vertices[0], e.vertices[1],
                            e.crease * e.crease * 10))
            # squared, to match blender appareance better
            #: range 0 - 10 (infinitely sharp)
    return creases

# requires facevertex interpolation
def _get_mesh_uv_(mesh, name="", flipvmode='NONE'):
    uvs = []
    if not name:
        uv_loop_layer = mesh.uv_layers.active
    else:
        # assuming uv loop layers and uv textures share identical indices
        idx = mesh.uv_textures.keys().index(name)
        uv_loop_layer = mesh.uv_layers[idx]

    if uv_loop_layer is None:
        return None

    for uvloop in uv_loop_layer.data:
        uvs.append(uvloop.uv.x)
        # renderman expects UVs flipped vertically from blender
        # best to do this in pattern, provided here as additional option
        if flipvmode == 'UV':
            uvs.append(1.0-uvloop.uv.y)
        elif flipvmode == 'TILE':
            uvs.append(math.ceil(uvloop.uv.y) - uvloop.uv.y + math.floor(uvloop.uv.y))
        elif flipvmode == 'NONE':
            uvs.append(uvloop.uv.y)

    return uvs

def _get_mesh_vcol_(mesh, name=""):
    vcol_layer = mesh.vertex_colors[name] if name != "" \
        else mesh.vertex_colors.active
    cols = []

    if vcol_layer is None:
        return None

    for vcloop in vcol_layer.data:
        cols.extend(vcloop.color)

    return cols    

def _get_mesh_vgroup_(ob, mesh, name=""):
    vgroup = ob.vertex_groups[name] if name != "" else ob.vertex_groups.active
    weights = []

    if vgroup is None:
        return None

    for v in mesh.vertices:
        if len(v.groups) == 0:
            weights.append(0.0)
        else:
            weights.extend([g.weight for g in v.groups
                            if g.group == vgroup.index])

    return weights

def _get_material_ids(ob, geo):
        
    material_ids = string_utils.convert_val([p.material_index for p in geo.polygons])
    return material_ids

def _get_primvars_(ob, geo, rixparams, interpolation=""):

    rm = ob.data.renderman

    interpolation = 'facevarying' if not interpolation else interpolation

    if rm.export_default_uv:
        flipvmode = 'NONE'
        if hasattr(rm, 'export_flipv'):
            flipvmode = rm.export_flipv
        uvs = _get_mesh_uv_(geo, flipvmode=flipvmode)
        if uvs and len(uvs) > 0:
            #primvars["%s float[2] st" % interpolation] = uvs
            rixparams.SetFloatArrayDetail("st", uvs, 2, interpolation)

    if rm.export_default_vcol:
        vcols = _get_mesh_vcol_(geo)
        if vcols and len(vcols) > 0:
            rixparams.SetColorDetail("Cs", string_utils.convert_val(vcols, type_hint="color"), interpolation)

    # custom prim vars

    for p in rm.prim_vars:
        if p.data_source == 'VERTEX_COLOR':
            vcols = _get_mesh_vcol_(geo, p.data_name)
            if vcols and len(vcols) > 0:
                rixparams.SetColorDetail(p.name, string_utils.convert_val(vcols, type_hint="color"), interpolation)

        elif p.data_source == 'UV_TEXTURE':
            flipvmode = 'NONE'
            if hasattr(rm, 'export_flipv'):
                flipvmode = rm.export_flipv
            uvs = _get_mesh_uv_(geo, p.data_name, flipvmode=flipvmode)
            if uvs and len(uvs) > 0:
                rixparams.SetFloatArrayDetail(p.name, uvs, 2, interpolation)

        elif p.data_source == 'VERTEX_GROUP':
            weights = _get_mesh_vgroup_(ob, geo, p.data_name)
            if weights and len(weights) > 0:
                rixparams.SetFloatDetail(p.name, weights, "vertex")

class RmanMeshTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'MESH' 

    def export(self, ob, db_name):
        prim_type = object_utils._detect_primitive_(ob)

        if prim_type not in ['POLYGON_MESH', 'SUBDIVISION_MESH']:
            return None
        
        sg_node = self.rman_scene.sg_scene.CreateMesh(db_name)
        rman_sg_mesh = RmanSgMesh(self.rman_scene, sg_node, db_name)

        self.update(ob, rman_sg_mesh)

        return rman_sg_mesh

    def export_deform_sample(self, rman_sg_mesh, ob, time_samples, time_sample):
        mesh = None
        mesh = ob.to_mesh()

        (nverts, verts, P, N) = object_utils._get_mesh_(mesh, get_normals=False)
        
        # if this is empty continue:
        if nverts == []:
            ob.to_mesh_clear() 
            return None

        nm_pts = int(len(P)/3)
        rman_sg_mesh.sg_node.Define( len(nverts), nm_pts, len(verts) )
        primvar = rman_sg_mesh.sg_node.GetPrimVars()
        
        if time_samples:        
            primvar.SetTimeSamples( time_samples )

        pts = list( zip(*[iter(P)]*3 ) )
        primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, pts, "vertex", time_sample)

        rman_sg_mesh.sg_node.SetPrimVars(primvar)

        ob.to_mesh_clear()         


    def update(self, ob, rman_sg_mesh, input_mesh=None):

        mesh = input_mesh
        if not mesh:
            mesh = ob.to_mesh()

        prim_type = object_utils._detect_primitive_(ob)

        get_normals = (prim_type == 'POLYGON_MESH')
        (nverts, verts, P, N) = object_utils._get_mesh_(mesh, get_normals=get_normals)
        
        # if this is empty continue:
        if nverts == []:
            ob.to_mesh_clear()
            return None

        npolys = len(nverts) 
        npoints = int(len(P)/3)
        numnverts = len(verts)

        rman_sg_mesh.sg_node.Define( npolys, npoints, numnverts )
        primvar = rman_sg_mesh.sg_node.GetPrimVars()
        primvar.Clear()

        pts = list( zip(*[iter(P)]*3 ) )
        primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, pts, "vertex")
        _get_primvars_(ob, mesh, primvar, "facevarying")   

        primvar.SetIntegerDetail(self.rman_scene.rman.Tokens.Rix.k_Ri_nvertices, nverts, "uniform")
        primvar.SetIntegerDetail(self.rman_scene.rman.Tokens.Rix.k_Ri_vertices, verts, "facevarying")            

        if prim_type == "SUBDIVISION_MESH":
            rman_sg_mesh.is_subdiv = True
            creases = _get_subd_creases_(mesh)
            tags = ['interpolateboundary', 'facevaryinginterpolateboundary']
            nargs = [1, 0, 0, 1, 0, 0]
            intargs = [ob.data.renderman.interp_boundary,
                    ob.data.renderman.face_boundary]
            floatargs = []
            stringargs = []     

            if len(creases) > 0:
                for c in creases:
                    tags.append('crease')
                    nargs.extend([2, 1, 0])
                    intargs.extend([c[0], c[1]])
                    floatargs.append(c[2])           
                
            primvar.SetStringArray(self.rman_scene.rman.Tokens.Rix.k_Ri_subdivtags, tags, len(tags))
            primvar.SetIntegerArray(self.rman_scene.rman.Tokens.Rix.k_Ri_subdivtagnargs, nargs, len(nargs))
            primvar.SetIntegerArray(self.rman_scene.rman.Tokens.Rix.k_Ri_subdivtagintargs, intargs, len(intargs))
            primvar.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_subdivtagfloatargs, floatargs, len(floatargs))
            primvar.SetStringArray(self.rman_scene.rman.Tokens.Rix.k_Ri_subdivtagstringtags, stringargs, len(stringargs))

            # TODO make this selectable
            rman_sg_mesh.sg_node.SetScheme(self.rman_scene.rman.Tokens.Rix.k_catmullclark) 

        elif prim_type == "POLYGON_MESH":
            rman_sg_mesh.is_subdiv = False
            rman_sg_mesh.sg_node.SetScheme(None)
            primvar.SetNormalDetail(self.rman_scene.rman.Tokens.Rix.k_N, N, "facevarying")            

        if _is_multi_material_(ob, mesh):
            material_ids = _get_material_ids(ob, mesh)
            for mat_id, faces in \
                _get_mats_faces_(nverts, material_ids).items():

                mat = ob.data.materials[mat_id]
                mat_handle = "material.%s" % mat.name
                sg_material = None
                if mat_handle in self.rman_scene.rman_materials:
                    sg_material = self.rman_scene.rman_materials[mat_handle]

                if mat_id == 0:
                    primvar.SetIntegerArray(self.rman_scene.rman.Tokens.Rix.k_shade_faceset, faces, len(faces))
                    rman_sg_mesh.sg_node.SetMaterial(sg_material)
                else: 
                    sg_sub_mesh =  self.rman_scene.sg_scene.CreateMesh("")
                    pvars = sg_sub_mesh.GetPrimVars()
                    sg_sub_mesh.Define( npolys, npoints, numnverts )
                    if prim_type == "SUBDIVISION_MESH":
                        sg_sub_mesh.SetScheme(self.rman_scene.rman.Tokens.Rix.k_catmullclark)
                    pvars.Inherit(primvar)
                    pvars.SetIntegerArray(self.rman_scene.rman.Tokens.Rix.k_shade_faceset, faces, len(faces))
                    sg_sub_mesh.SetPrimVars(pvars)
                    sg_sub_mesh.SetMaterial(sg_material)
                    rman_sg_mesh.sg_node.AddChild(sg_sub_mesh)                  

           
        #primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_displacementbound_sphere, ob.renderman.displacementbound)
        rman_sg_mesh.sg_node.SetPrimVars(primvar)

        if not input_mesh:
            ob.to_mesh_clear()      