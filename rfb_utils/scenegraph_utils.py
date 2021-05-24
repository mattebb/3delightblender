def set_material(sg_node, sg_material_node):
    '''Sets the material on a scenegraph group node and sets the materialid
    user attribute at the same time.

    Arguments:
        sg_node (RixSGGroup) - scene graph group node to attach the material.
        sg_material_node (RixSGMaterial) - the scene graph material node
    '''    


    sg_node.SetMaterial(sg_material_node)
    attrs = sg_node.GetAttributes()
    attrs.SetString('user:__materialid', sg_material_node.GetIdentifier().CStr())
    sg_node.SetAttributes(attrs) 