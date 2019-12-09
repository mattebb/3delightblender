from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_blobby import RmanSgBlobby
from ..rman_utils import object_utils
from ..rman_utils import string_utils
from mathutils import Matrix

import bpy
import math

def get_mball_parent(mball):
    for ob in bpy.data.objects:
        if ob.data == mball:
            return ob

class RmanBlobbyTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'META' 

    def export(self, ob, db_name):

        sg_node = self.rman_scene.sg_scene.CreateBlobby(db_name)
        rman_sg_blobby = RmanSgBlobby(self.rman_scene, sg_node, db_name)

        self.update(ob, rman_sg_blobby)

        return rman_sg_blobby

    def export_deform_sample(self, rman_sg_blobby, ob, time_samples, time_sample):
        pass

    # many thanks to @rendermouse for this code
    def update(self, ob, rman_sg_blobby):
        rm = ob.renderman
        prim = rm.primitive

        # we are searching the global metaball collection for all mballs
        # linked to the current object context, so we can export them
        # all as one family in RiBlobby

        family = object_utils.get_meta_family(ob)
        master = bpy.data.objects[family]

        fam_blobs = []

        for mball in bpy.data.metaballs:
            fam_blobs.extend([el for el in mball.elements if get_mball_parent(
                el.id_data).name.split('.')[0] == family])

        # transform
        tform = []

        # opcodes
        op = []
        count = len(fam_blobs)
        for i in range(count):
            op.append(1001)  # only blobby ellipsoids for now...
            op.append(i * 16)

        for meta_el in fam_blobs:

            # Because all meta elements are stored in a single collection,
            # these elements have a link to their parent MetaBall, but NOT the actual tree parent object.
            # So I have to go find the parent that owns it.  We need the tree parent in order
            # to get any world transforms that alter position of the metaball.
            parent = get_mball_parent(meta_el.id_data)

            m = {}
            loc = meta_el.co

            # mballs that are only linked to the master by name have their own position,
            # and have to be transformed relative to the master
            ploc, prot, psc = parent.matrix_world.decompose()

            m = Matrix.Translation(loc)

            sc = Matrix(((meta_el.radius, 0, 0, 0),
                        (0, meta_el.radius, 0, 0),
                        (0, 0, meta_el.radius, 0),
                        (0, 0, 0, 1)))

            ro = prot.to_matrix().to_4x4()

            m2 = m @ sc @ ro
            tform = tform + string_utils.convert_val(parent.matrix_world @ m2)

        op.append(0)  # blob operation:add
        op.append(count)
        for n in range(count):
            op.append(n)

        primvar = rman_sg_blobby.sg_node.GetPrimVars()  
        rman_sg_blobby.sg_node.Define(count)
        primvar.SetIntegerArray(self.rman_scene.rman.Tokens.Rix.k_Ri_code, op, len(op))            
        primvar.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_floats, tform, len(tform))      
        #primvar.SetFloat(self.rman_scene.rman.Tokens.Rix.k_displacementbound_sphere, rm.displacementbound)
        rman_sg_blobby.sg_node.SetPrimVars(primvar)        
