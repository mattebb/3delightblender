import bpy

def get_db_name(ob, rman_type=''):
    db_name = ''    

    if rman_type != '' and rman_type != 'NONE':
        if rman_type == 'META':
            db_name = '%s-META' % (ob.name.split('.')[0])
        try:
            if rman_type == 'LIGHT':
                db_name = '%s-%s' % (ob.data.name_full, rman_type)
            else:
                '''
                For meshes etc., don't use the data name. This prevents us
                from re-using data when objects are linked, but because these instances
                can overrides attributes like turning the instance into a subdiv
                we have to treat them as their own object.
                '''
                db_name = '%s-%s' % (ob.name_full, rman_type)
        except:
            db_name = '%s-%s' % (ob.name_full, rman_type)
    elif isinstance(ob, bpy.types.Camera):
        db_name = '%s-CAMERA' % ob.name_full
    elif isinstance(ob, bpy.types.Material):
        db_name = '%s-MATERIAL' % ob.name_full
    elif isinstance(ob, bpy.types.Object):
        if ob.type == 'MESH':
            db_name = '%s-MESH' % ob.data.name_full
        elif ob.type == 'LIGHT':
            db_name = '%s-LIGHT' % ob.data.name_full
        elif ob.type == 'CAMERA':
            db_name = '%s-CAMERA' % ob.name_full
        elif ob.type == 'EMPTY':
            db_name = ob.name_full  


    return db_name

def get_meta_family(ob):
    return ob.name.split('.')[0]

def is_subd_last(ob):
    return ob.modifiers and \
        ob.modifiers[len(ob.modifiers) - 1].type == 'SUBSURF'


def is_subd_displace_last(ob):
    if len(ob.modifiers) < 2:
        return False

    return (ob.modifiers[len(ob.modifiers) - 2].type == 'SUBSURF' and
            ob.modifiers[len(ob.modifiers) - 1].type == 'DISPLACE')

def is_smoke(ob):
    for mod in ob.modifiers:
        if mod.type == "SMOKE" and mod.domain_settings:
            return True
    return False            

def is_subdmesh(ob):
    return (is_subd_last(ob) or is_subd_displace_last(ob))

# handle special case of fluid sim a bit differently
def is_deforming_fluid(ob):
    if ob.modifiers:
        mod = ob.modifiers[len(ob.modifiers) - 1]
        return mod.type == 'SMOKE' and mod.smoke_type == 'DOMAIN'

def _is_deforming_(ob):
    deforming_modifiers = ['ARMATURE', 'MESH_SEQUENCE_CACHE', 'CAST', 'CLOTH', 'CURVE', 'DISPLACE',
                           'HOOK', 'LATTICE', 'MESH_DEFORM', 'SHRINKWRAP', 'EXPLODE',
                           'SIMPLE_DEFORM', 'SMOOTH', 'WAVE', 'SOFT_BODY',
                           'SURFACE', 'MESH_CACHE', 'FLUID_SIMULATION',
                           'DYNAMIC_PAINT']
    if ob.modifiers:
        # special cases for auto subd/displace detection
        if len(ob.modifiers) == 1 and is_subd_last(ob):
            return False
        if len(ob.modifiers) == 2 and is_subd_displace_last(ob):
            return False

        for mod in ob.modifiers:
            if mod.type in deforming_modifiers:
                return True
    if ob.data and hasattr(ob.data, 'shape_keys') and ob.data.shape_keys:
        return True

    return is_deforming_fluid(ob)

def is_transforming(ob, recurse=False):
    transforming = (ob.animation_data is not None)
    if not transforming and ob.parent:
        transforming = is_transforming(ob.parent, recurse=True)
        if not transforming and ob.parent.type == 'CURVE' and ob.parent.data:
            transforming = ob.parent.data.use_path
    return transforming

def _detect_primitive_(ob):

    if isinstance(ob, bpy.types.ParticleSystem):
        return ob.settings.type

    rm = ob.renderman

    if rm.primitive == 'AUTO':
        if ob.type == 'MESH':
            if is_subdmesh(ob):
                return 'SUBDIVISION_MESH'
            elif is_smoke(ob):
                return 'SMOKE'
            else:
                return 'POLYGON_MESH'
        elif ob.type == 'LIGHT':
            return ob.type                       
        elif ob.type == 'CURVE':
            return 'CURVE'
        elif ob.type in ('SURFACE', 'FONT'):
            return 'POLYGON_MESH'
        elif ob.type == "META":
            return "META"
        elif ob.type == 'CAMERA':
            return 'CAMERA'
        else:
            return 'NONE'
    else:
        return rm.primitive    

def _get_used_materials_(ob):
    if ob.type == 'MESH' and len(ob.data.materials) > 0:
        if len(ob.data.materials) == 1:
            return [ob.data.materials[0]]
        mat_ids = []
        mesh = ob.data
        num_materials = len(ob.data.materials)
        for p in mesh.polygons:
            if p.material_index not in mat_ids:
                mat_ids.append(p.material_index)
            if num_materials == len(mat_ids):
                break
        return [mesh.materials[i] for i in mat_ids]
    else:
        return [ob.active_material]     

def _get_mesh_(mesh, get_normals=False):
    nverts = []
    verts = []
    P = []
    N = []

    for v in mesh.vertices:
        P.extend(v.co)

    for p in mesh.polygons:
        nverts.append(p.loop_total)
        verts.extend(p.vertices)
        if get_normals:
            if p.use_smooth:
                for vi in p.vertices:
                    N.extend(mesh.vertices[vi].normal)
            else:
                N.extend(list(p.normal) * p.loop_total)

    if len(verts) > 0:
        P = P[:int(max(verts) + 1) * 3]
    # return the P's minus any unconnected
    return (nverts, verts, P, N)      