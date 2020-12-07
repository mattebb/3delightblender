from ..rfb_logger import rfb_log
from ..rfb_utils.osl_utils import readOSO
from ..rfb_utils import shadergraph_utils
from ..rfb_utils.node_desc import FLOAT3
from . import rman_socket_utils
from .. import rman_render
from .. import rman_bl_nodes
from .. import rfb_icons
from bpy.types import Menu
from bpy.props import EnumProperty, StringProperty, CollectionProperty
import _cycles
import bpy

class NODE_MT_renderman_param_presets_menu(Menu):
    bl_label = "Parameter Presets"
    bl_idname = "NODE_MT_renderman_param_presets_menu"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None      

    def draw(self, context):
        layout = self.layout
        nt = context.nodetree
        node = context.node
        socket = context.socket

        prop_name = socket.name
        prop_meta = node.prop_meta.get(prop_name, None)
        if prop_meta:            
            if 'presets' in prop_meta:
                for k,v in prop_meta['presets'].items():
                    layout.context_pointer_set("node", node)
                    layout.context_pointer_set("nodetree", nt)
                    layout.context_pointer_set('socket', socket)
                    op = layout.operator('node.rman_preset_set_param', text=k)
                    op.prop_name = prop_name
                    op.preset_name = k

class NODE_MT_renderman_node_solo_output_menu(Menu):
    bl_label = "Solo Node Output"
    bl_idname = "NODE_MT_renderman_node_solo_output_menu"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        nt = context.nodetree   
        node = context.node 

        solo_node = nt.nodes.get(node.solo_node_name)

        for o in solo_node.outputs:
            if o.renderman_type in ['float', 'color', 'normal', 'vector', 'point']:
                layout.context_pointer_set("node", node)
                layout.context_pointer_set("nodetree", nt)     
                op = layout.operator('node.rman_set_node_solo_output', text=o.name)
                op.solo_node_output = o.name      
                op.solo_node_name = node.solo_node_name               

class NODE_MT_renderman_connection_menu(Menu):
    bl_label = "Connect New"
    bl_idname = "NODE_MT_renderman_connection_menu"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None    

    def draw_output_node_menu(self, context):
        layout = self.layout
        nt = context.nodetree
        node = context.node
        socket = context.socket

        renderman_type = getattr(socket, 'renderman_type', socket.name.lower())

        if renderman_type == 'displacement':
            for n in rman_bl_nodes.__RMAN_DISPLACE_NODES__:
                layout.context_pointer_set("node", node)
                layout.context_pointer_set("nodetree", nt)
                rman_icon = rfb_icons.get_displacement_icon(n.name)
                op = layout.operator('node.rman_shading_create_node', text=n.name, icon_value=rman_icon.icon_id)
                op.node_name = '%sDisplaceNode' % n.name     
        elif renderman_type == 'integrator':    
            for n in rman_bl_nodes.__RMAN_INTEGRATOR_NODES__:
                layout.context_pointer_set("node", node)
                layout.context_pointer_set("nodetree", nt)
                rman_icon = rfb_icons.get_integrator_icon(n.name)
                op = layout.operator('node.rman_shading_create_node', text=n.name, icon_value=rman_icon.icon_id)
                op.node_name = '%sIntegratorNode' % n.name    
        elif 'samplefilter' in renderman_type:    
            for n in rman_bl_nodes.__RMAN_SAMPLEFILTER_NODES__:
                layout.context_pointer_set("node", node)
                layout.context_pointer_set("nodetree", nt)
                rman_icon = rfb_icons.get_samplefilter_icon(n.name)
                op = layout.operator('node.rman_shading_create_node', text=n.name, icon_value=rman_icon.icon_id)
                op.node_name = '%sSamplefilterNode' % n.name 
        elif 'displayfilter' in renderman_type:    
            for n in rman_bl_nodes.__RMAN_DISPLAYFILTER_NODES__:
                layout.context_pointer_set("node", node)
                layout.context_pointer_set("nodetree", nt)
                rman_icon = rfb_icons.get_displayfilter_icon(n.name)
                op = layout.operator('node.rman_shading_create_node', text=n.name, icon_value=rman_icon.icon_id)
                op.node_name = '%sDisplayfilterNode' % n.name                                                                              
        elif renderman_type == 'bxdf':    
            for bxdf_cat, bxdfs in rman_bl_nodes.__RMAN_NODE_CATEGORIES__['bxdf'].items():
                tokens = bxdf_cat.split('_')
                bxdf_category = ' '.join(tokens[1:])

                layout.context_pointer_set("node", node)
                layout.context_pointer_set("nodetree", nt)
                layout.context_pointer_set('socket', socket)
                layout.menu('NODE_MT_renderman_connection_submenu_%s' % bxdf_cat, text=bxdf_category.capitalize())    

        layout.separator()
        layout.label(text='__EXISTING__')
        for n in nt.nodes:
            if socket.is_linked and socket.links[0].from_node == n:
                continue
            if n == node:
                continue            
            for output in n.outputs:
                output_renderman_type = getattr(output, 'renderman_type', output.name.lower())
                if output_renderman_type == renderman_type:
                    op = layout.operator('node.rman_shading_connect_existing_node', text='_%s_' % n.name)
                    op.node_name = n.name       
                    break                 

    def draw_patterns_menu(self, context):
        layout = self.layout
        nt = context.nodetree
        node = context.node
        socket = context.socket
        prop_name = socket.name
        prop = getattr(node, prop_name, None)
        prop_meta = node.prop_meta[prop_name]
        renderman_type = prop_meta.get('renderman_type', 'pattern')
        renderman_type = prop_meta.get('renderman_array_type', renderman_type)

        if hasattr(prop_meta, 'vstruct') or prop_name == 'inputMaterial':
            for n in rman_bl_nodes.__RMAN_PATTERN_NODES__:
                for node_desc_param in n.outputs:
                    vstruct = getattr(node_desc_param, 'vstruct', None)
                    if vstruct:
                        layout.context_pointer_set("node", node)
                        layout.context_pointer_set("nodetree", nt)
                        rman_icon = rfb_icons.get_pattern_icon(n.name)
                        op = layout.operator('node.rman_shading_create_node', text=n.name, icon_value=rman_icon.icon_id)
                        op.node_name = '%sPatternNode' % n.name
                        if n.path.endswith('.oso'):
                            op.node_name = '%sPatternOSLNode' % n.name
                        break                                   

        elif renderman_type == 'bxdf':
            for bxdf_cat, bxdfs in rman_bl_nodes.__RMAN_NODE_CATEGORIES__['bxdf'].items():
                tokens = bxdf_cat.split('_')
                bxdf_category = ' '.join(tokens[1:])

                layout.context_pointer_set("node", node)
                layout.context_pointer_set("nodetree", nt)
                layout.context_pointer_set('socket', socket)
                layout.menu('NODE_MT_renderman_connection_submenu_%s' % bxdf_cat, text=bxdf_category.capitalize())                     

        else:    
            for pattern_cat, patterns in rman_bl_nodes.__RMAN_NODE_CATEGORIES__['pattern'].items():
                tokens = pattern_cat.split('_')
                pattern_category = ' '.join(tokens[1:])
                has_any = False
                for n in patterns[1]:
                    for node_desc_param in n.outputs:     
                        vstruct = getattr(node_desc_param, 'vstruct', None)
                        if vstruct:               
                            break               
                        if node_desc_param.type == renderman_type:
                            has_any = True
                            break
                        elif node_desc_param.type in FLOAT3 and renderman_type in FLOAT3:
                            has_any = True
                            break           
                if has_any:
                    layout.context_pointer_set("node", node)
                    layout.context_pointer_set("nodetree", nt)
                    layout.context_pointer_set('socket', socket)
                    layout.menu('NODE_MT_renderman_connection_submenu_%s' % pattern_cat, text=pattern_category.capitalize())       

        prop_name = socket.name
        prop_meta = node.prop_meta.get(prop_name, None)
        if prop_meta:            
            if 'presets' in prop_meta:
                layout.separator()
                layout.label(text='PRESETS')
                layout.context_pointer_set("node", node)
                layout.context_pointer_set("nodetree", nt)
                layout.context_pointer_set('socket', socket)        
                layout.menu('NODE_MT_renderman_param_presets_menu', text='Presets')

        layout.separator()
        layout.label(text='__EXISTING__')
        for n in nt.nodes:
            if socket.is_linked and socket.links[0].from_node == n:
                continue
            if n == node:
                continue
            for output in n.outputs:
                if not hasattr(output, 'renderman_type'):
                    continue
                if output.renderman_type == renderman_type:
                    op = layout.operator('node.rman_shading_connect_existing_node', text='_%s_' % n.name)
                    op.node_name = n.name
                    break

    def draw_patterns_all_menu(self, context):
        layout = self.layout
        nt = context.nodetree
        node = context.node
        socket = context.socket
        prop_name = socket.name
  
        for pattern_cat, patterns in rman_bl_nodes.__RMAN_NODE_CATEGORIES__['pattern'].items():
            tokens = pattern_cat.split('_')
            pattern_category = ' '.join(tokens[1:])

            layout.context_pointer_set("node", node)
            layout.context_pointer_set("nodetree", nt)
            layout.context_pointer_set('socket', socket)
            layout.menu('NODE_MT_renderman_connection_submenu_%s' % pattern_cat, text=pattern_category.capitalize())       

        layout.separator()
        layout.label(text='__EXISTING__')
        for n in nt.nodes:
            if socket.is_linked and socket.links[0].from_node == n:
                continue
            if n == node:
                continue
            op = layout.operator('node.rman_shading_connect_existing_node', text='_%s_' % n.name)

    def draw(self, context):
        layout = self.layout
        nt = context.nodetree
        node = context.node
        socket = context.socket
        if context.socket.is_linked:
            input_node = context.socket.links[0].from_node
            rman_icon = rfb_icons.get_icon('out_%s' % input_node.bl_label)
            layout.label(text=input_node.name, icon_value=rman_icon.icon_id)
            layout.separator()
            layout.context_pointer_set("node", node)
            layout.context_pointer_set("nodetree", nt)
            layout.context_pointer_set("socket", socket)
                        
            layout.operator('node.rman_shading_disconnect', text='Disconnect')
            layout.operator('node.rman_shading_remove', text='Remove')

        if node.bl_idname in [
                                'RendermanOutputNode', 
                                'RendermanSamplefiltersOutputNode', 
                                'RendermanDisplayfiltersOutputNode', 
                                'RendermanIntegratorsOutputNode']:
            layout.separator()                                
            self.draw_output_node_menu(context)
        else:
            if socket.is_linked:        
                prop_name = socket.name
                prop_meta = node.prop_meta[prop_name]
                vstruct = prop_meta.get('vstruct', False)
                if not vstruct and prop_name != 'inputMaterial':                
                    out_node = shadergraph_utils.find_node_from_nodetree(nt, 'RendermanOutputNode')
                    layout.context_pointer_set("node", out_node)
                    layout.context_pointer_set("nodetree", nt)      
                    rman_icon = rfb_icons.get_icon('rman_solo_on')
                    op = layout.operator('node.rman_set_node_solo', text='Solo Input Node', icon_value=rman_icon.icon_id)
                    op.refresh_solo = False
                    op.solo_node_name = socket.links[0].from_node.name            
            layout.separator()   
            if hasattr(node, 'prop_meta'):
                self.draw_patterns_menu(context)
            else:
                self.draw_patterns_all_menu(context)

classes = [
    NODE_MT_renderman_node_solo_output_menu,
    NODE_MT_renderman_param_presets_menu,
    NODE_MT_renderman_connection_menu
]

def register_renderman_bxdf_node_submenus():
    global classes

    def draw(self, context):
        layout = self.layout  
        nt = context.nodetree
        node = context.node
        socket = context.socket

        for bxdf_cat, bxdfs in rman_bl_nodes.__RMAN_NODE_CATEGORIES__['bxdf'].items():
            tokens = bxdf_cat.split('_')
            bxdf_category = ' '.join(tokens[1:])
            if bxdf_cat != self.bl_label:
                continue        
            for n in bxdfs[1]:
                rman_icon = rfb_icons.get_bxdf_icon(n.name)
                op = layout.operator('node.rman_shading_create_node', text=n.name, icon_value=rman_icon.icon_id)
                op.node_name = '%sBxdfNode' % n.name                     

    for bxdf_cat, bxdf in rman_bl_nodes.__RMAN_NODE_CATEGORIES__['bxdf'].items():
        typename = 'NODE_MT_renderman_connection_submenu_%s' % bxdf_cat
        ntype = type(typename, (Menu,), {})
        ntype.bl_label = bxdf_cat
        ntype.bl_idname = typename
        if "__annotations__" not in ntype.__dict__:
            setattr(ntype, "__annotations__", {})        
        ntype.draw = draw
        classes.append(ntype)    

def register_renderman_pattern_node_submenus():

    global classes

    def draw_rman(self, context):
        layout = self.layout  
        nt = context.nodetree
        node = context.node
        socket = context.socket
        prop_name = socket.name
        prop = getattr(node, prop_name, None)
        if hasattr(node, 'prop_meta'):
            prop_meta = node.prop_meta[prop_name]
            renderman_type = prop_meta.get('renderman_type', 'pattern')
            renderman_type = prop_meta.get('renderman_array_type', renderman_type)
        else:
            renderman_type = 'pattern'
      
        for pattern_cat, patterns in rman_bl_nodes.__RMAN_NODE_CATEGORIES__['pattern'].items():
            tokens = pattern_cat.split('_')
            pattern_category = ' '.join(tokens[1:])
            if pattern_cat != self.bl_label:
                continue

            for n in patterns[1]:
                for node_desc_param in n.outputs:     
                    vstruct = getattr(node_desc_param, 'vstruct', None)
                    if vstruct:               
                        break
                    if renderman_type == 'pattern' or node_desc_param.type == renderman_type or (node_desc_param.type in FLOAT3 and renderman_type in FLOAT3):
                        rman_icon = rfb_icons.get_pattern_icon(n.name)
                        label = n.name
                        #if n.path.endswith('.oso'):
                        #    label = '%s.oso' % label
                        op = layout.operator('node.rman_shading_create_node', text=label, icon_value=rman_icon.icon_id)
                        op.node_name = '%sPatternNode' % n.name
                        if n.path.endswith('.oso'):
                            op.node_name = '%sPatternOSLNode' % n.name
                        break   


    for pattern_cat, patterns in rman_bl_nodes.__RMAN_NODE_CATEGORIES__['pattern'].items():
        typename = 'NODE_MT_renderman_connection_submenu_%s' % pattern_cat
        ntype = type(typename, (Menu,), {})
        ntype.bl_label = pattern_cat
        ntype.bl_idname = typename
        if "__annotations__" not in ntype.__dict__:
            setattr(ntype, "__annotations__", {})        
        ntype.draw = draw_rman
        classes.append(ntype)

def register_submenus():
    '''Register a blender menu per shading node category. We do this
    because Blender doesn't allow you to set properties on a menu class when drawing
    them, otherwise we would be able to filter the items in a menu dynamically
    '''    
    register_renderman_bxdf_node_submenus()
    register_renderman_pattern_node_submenus()

def register():
    register_submenus()

    for cls in classes:
        bpy.utils.register_class(cls)         

def unregister():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass
        