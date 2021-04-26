import bpy
from ..rfb_utils import object_utils
from mathutils import Vector, Matrix

class PRMAN_OT_Renderman_mesh_reference_pose(bpy.types.Operator):
    bl_idname = 'mesh.freeze_reference_pose'
    bl_label = "Freeze Reference Pose"
    bl_description = "Use the mesh's points and normals for the current frame as the reference pose. This essentially adds the __Pref, __NPref, __Nref and __WNref primitive variables."

    def invoke(self, context, event=None):
        mesh = context.mesh
        ob = context.object
        rm = mesh.renderman
        rm.reference_pose.clear()
        
        matrix_world = ob.matrix_world
        mesh.calc_normals_split()
        for mv in mesh.vertices:
            rp = rm.reference_pose.add()
            rp.rman__Pref = mv.co

            v = Vector(mv.co)
            v = matrix_world @ v
            rp.rman__WPref = v
        
            rp.rman__Nref = mv.normal
            
            n = Vector(mv.normal)
            n = matrix_world @ n
            rp.rman__WNref = n

        mesh.free_normals_split()
        ob.update_tag(refresh={'DATA'})

        return {'FINISHED'}

classes = [
    PRMAN_OT_Renderman_mesh_reference_pose
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
def unregister():
   
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass
