from ..rman_operators.rman_operators_utils import get_bxdf_items, get_light_items, get_lightfilter_items
from .. import rman_bl_nodes
from .. import rfb_icons
import bpy

class NODE_MT_RM_Bxdf_Category_Menu(bpy.types.Menu):
    bl_label = "Bxdfs"
    bl_idname = "NODE_MT_RM_Bxdf_Category_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'
       
    def draw(self, context):
        layout = self.layout

        nt = getattr(context, 'nodetree', None)
        for bxdf_cat, bxdfs in rman_bl_nodes.__RMAN_NODE_CATEGORIES__['bxdf'].items():
            if not bxdfs[1]:
                continue
            tokens = bxdf_cat.split('_')
            if len(tokens) > 2:
                # this should be a subcategory/submenu
                continue                
            bxdf_category = ' '.join(tokens[1:])


            layout.context_pointer_set("nodetree", nt)
            layout.menu('NODE_MT_renderman_connection_submenu_%s' % bxdf_cat, text=bxdf_category.capitalize())  

class NODE_MT_RM_Pattern_Category_Menu(bpy.types.Menu):
    bl_label = "Patterns"
    bl_idname = "NODE_MT_RM_Pattern_Category_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'
       
    def draw(self, context):
        layout = self.layout

        nt = getattr(context, 'nodetree', None)
        for pattern_cat, patterns in rman_bl_nodes.__RMAN_NODE_CATEGORIES__['pattern'].items():
            if not patterns[1]:
                continue
            tokens = pattern_cat.split('_')
            if len(tokens) > 2:
                # this should be a subcategory/submenu
                continue            
            pattern_category = ' '.join(tokens[1:])
            if pattern_category == 'pxrsurface':
                continue
            layout.context_pointer_set("nodetree", nt)
            layout.menu('NODE_MT_renderman_connection_submenu_%s' % pattern_cat, text=pattern_category.capitalize()) 

class NODE_MT_RM_Displacement_Category_Menu(bpy.types.Menu):
    bl_label = "Displacement"
    bl_idname = "NODE_MT_RM_Displacement_Category_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'
       
    def draw(self, context):
        layout = self.layout

        nt = getattr(context, 'nodetree', None)
        for n in rman_bl_nodes.__RMAN_DISPLACE_NODES__:
            layout.context_pointer_set("nodetree", nt)
            rman_icon = rfb_icons.get_displacement_icon(n.name)
            op = layout.operator('node.rman_shading_create_node', text=n.name, icon_value=rman_icon.icon_id)
            op.node_name = '%sDisplaceNode' % n.name                                   

class NODE_MT_RM_PxrSurface_Category_Menu(bpy.types.Menu):
    bl_label = "PxrSurface"
    bl_idname = "NODE_MT_RM_PxrSurface_Category_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'
       
    def draw(self, context):
        layout = self.layout

        nt = getattr(context, 'nodetree', None)
        node_name = 'PxrLayer'
        layout.context_pointer_set("nodetree", nt)
        rman_icon = rfb_icons.get_pattern_icon(node_name)
        op = layout.operator('node.rman_shading_create_node', text=node_name, icon_value=rman_icon.icon_id)
        op.node_name = rman_bl_nodes.__BL_NODES_MAP__[node_name]   
        node_name = 'PxrLayerMixer'
        layout.context_pointer_set("nodetree", nt)
        rman_icon = rfb_icons.get_pattern_icon(node_name)
        op = layout.operator('node.rman_shading_create_node', text=node_name, icon_value=rman_icon.icon_id)
        op.node_name = rman_bl_nodes.__BL_NODES_MAP__[node_name]           

class NODE_MT_RM_Light_Category_Menu(bpy.types.Menu):
    bl_label = "Light"
    bl_idname = "NODE_MT_RM_Light_Category_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'
       
    def draw(self, context):
        layout = self.layout

        nt = getattr(context, 'nodetree', None)
        node_name = 'PxrMeshLight'
        layout.context_pointer_set("nodetree", nt)
        rman_icon = rfb_icons.get_light_icon(node_name)
        op = layout.operator('node.rman_shading_create_node', text=node_name, icon_value=rman_icon.icon_id)
        op.node_name = rman_bl_nodes.__BL_NODES_MAP__[node_name]                                


class NODE_MT_RM_Integrators_Category_Menu(bpy.types.Menu):
    bl_label = "Integrators"
    bl_idname = "NODE_MT_RM_Integrators_Category_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'
       
    def draw(self, context):
        layout = self.layout
        nt = getattr(context, 'nodetree', None)
        for n in rman_bl_nodes.__RMAN_INTEGRATOR_NODES__:
            layout.context_pointer_set("nodetree", nt)
            rman_icon = rfb_icons.get_integrator_icon(n.name)
            op = layout.operator('node.rman_shading_create_node', text=n.name, icon_value=rman_icon.icon_id)
            op.node_name = '%sIntegratorNode' % n.name    

class NODE_MT_RM_SampleFilter_Category_Menu(bpy.types.Menu):
    bl_label = "Sample Filters"
    bl_idname = "NODE_MT_RM_SampleFilter_Category_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'
       
    def draw(self, context):
        layout = self.layout
        nt = getattr(context, 'nodetree', None)
        for n in rman_bl_nodes.__RMAN_SAMPLEFILTER_NODES__:
            layout.context_pointer_set("nodetree", nt)
            rman_icon = rfb_icons.get_samplefilter_icon(n.name)
            op = layout.operator('node.rman_shading_create_node', text=n.name, icon_value=rman_icon.icon_id)
            op.node_name = '%sSamplefilterNode' % n.name         

class NODE_MT_RM_DisplayFilter_Category_Menu(bpy.types.Menu):
    bl_label = "Display Filters"
    bl_idname = "NODE_MT_RM_DisplayFilter_Category_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'
       
    def draw(self, context):
        layout = self.layout
        nt = getattr(context, 'nodetree', None)
        for n in rman_bl_nodes.__RMAN_DISPLAYFILTER_NODES__:
            layout.context_pointer_set("nodetree", nt)
            rman_icon = rfb_icons.get_displayfilter_icon(n.name)
            op = layout.operator('node.rman_shading_create_node', text=n.name, icon_value=rman_icon.icon_id)
            op.node_name = '%sDisplayfilterNode' % n.name          

classes = [
    NODE_MT_RM_Bxdf_Category_Menu,
    NODE_MT_RM_Pattern_Category_Menu,
    NODE_MT_RM_Displacement_Category_Menu,
    NODE_MT_RM_PxrSurface_Category_Menu,
    NODE_MT_RM_Light_Category_Menu,
    NODE_MT_RM_Integrators_Category_Menu,
    NODE_MT_RM_SampleFilter_Category_Menu,
    NODE_MT_RM_DisplayFilter_Category_Menu
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