import bpy
from bpy.props import *
from ..rfb_utils import shadergraph_utils
from ..rfb_utils import draw_utils

# update node during ipr for a socket default_value
def update_func(self, context):
    # check if this prop is set on an input
    node = self.node if hasattr(self, 'node') else self

__CYCLES_GROUP_NODES__ = ['ShaderNodeGroup', 'NodeGroupInput', 'NodeGroupOutput']


# list for socket registration
# each element in the list should be:
# 
# - renderman type (str)
# - renderman type label (str)
# - bpy.types.NodeSocket class to inherit from
# - tuple to represent the color for the socket
# - bool to indicate whether to hide the value
# - dictionary of any properties wanting to be set

__RENDERMAN_TYPES_SOCKETS__ = [
    ('float', 'Float', bpy.types.NodeSocketFloat, (0.5, 0.5, 0.5, 1.0), False,
        {
            'default_value': FloatProperty(update=update_func),
        }
    ),
    ('int', 'Int', bpy.types.NodeSocketInt, (1.0, 1.0, 1.0, 1.0), False,
        {
            'default_value': IntProperty(update=update_func),
        }
    ),
    ('string', 'String', bpy.types.NodeSocketString, (0.25, 1.0, 0.25, 1.0), False,
        {
            'default_value': StringProperty(update=update_func),
            'is_texture': BoolProperty(default=False)
        }
    ),    
    ('struct', 'Struct', bpy.types.NodeSocketString, (1.0, 0.344, 0.0, 1.0), True,
        {
            'default_value': '',
            'struct_name': StringProperty(default='')
        }
    ),  
    ('vstruct', 'VStruct', bpy.types.NodeSocketString, (1.0, 0.0, 1.0, 1.0), True,
        {
            'default_value': '',
        }
    ),      
    ('bxdf', 'Bxdf', bpy.types.NodeSocketString, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ),      
    ('color', 'Color', bpy.types.NodeSocketColor, (1.0, 1.0, .5, 1.0), False,
        {
            'default_value': FloatVectorProperty(size=3, subtype="COLOR", update=update_func),
        }
    ),     
    ('vector', 'Vector', bpy.types.NodeSocketVector, (.25, .25, .75, 1.0), False,
        {
            'default_value':FloatVectorProperty(size=3, subtype="EULER", update=update_func),
        }
    ),      
    ('normal', 'Normal', bpy.types.NodeSocketVector, (.25, .25, .75, 1.0), False,
        {
            'default_value':FloatVectorProperty(size=3, subtype="EULER", update=update_func),
        }
    ), 
    ('point', 'Point', bpy.types.NodeSocketVector, (.25, .25, .75, 1.0), False,
        {
            'default_value':FloatVectorProperty(size=3, subtype="EULER", update=update_func),
        }
    ),     
    ('light', 'Light', bpy.types.NodeSocketString, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ),    
    ('lightfilter', 'LightFilter', bpy.types.NodeSocketString, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ),        
    ('displacement', 'Displacement', bpy.types.NodeSocketString, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ),       
    ('samplefilter', 'SampleFilter', bpy.types.NodeSocketString, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ),     
    ('displayfilter', 'DisplayFilter', bpy.types.NodeSocketString, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ),    
    ('integrator', 'Integrator', bpy.types.NodeSocketString, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ),      
    ('shader', 'Shader', bpy.types.NodeSocketShader, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ),  
    ('projection', 'Projection', bpy.types.NodeSocketString, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ),                    
]

# list for socket interface registration
# each element in the list should be:
# 
# - renderman type (str)
# - renderman type label (str)
# - bpy.types.NodeSocketInterface class to inherit from
# - tuple to represent the color for the socket
# - bool to indicate whether to hide the value
# - dictionary of any properties wanting to be set

__RENDERMAN_TYPES_SOCKET_INTERFACES__ =[
    ('float', 'Float', bpy.types.NodeSocketInterfaceFloat, (0.5, 0.5, 0.5, 1.0), False,
        {
            'default_value': FloatProperty() 
        }
    ),
    ('int', 'Int', bpy.types.NodeSocketInterfaceInt, (1.0, 1.0, 1.0, 1.0), False,
        {
            'default_value': IntProperty()
        }
    ),
    ('struct', 'Struct', bpy.types.NodeSocketInterfaceString, (1.0, 0.344, 0.0, 1.0), True,
        {
            'default_value': '',
            'struct_name': StringProperty(default='')
        }
    ),  
    ('vstruct', 'VStruct', bpy.types.NodeSocketInterfaceString, (1.0, 0.0, 1.0, 1.0), True,
        {
            'default_value': '',
        }
    ),      
    ('bxdf', 'Bxdf', bpy.types.NodeSocketInterfaceString, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ),       
    ('color', 'Color', bpy.types.NodeSocketInterfaceColor, (1.0, 1.0, .5, 1.0), False,
        {
            'default_value': FloatVectorProperty(size=3, subtype="COLOR", update=update_func),
        }
    ),      
    ('vector', 'Vector', bpy.types.NodeSocketInterfaceVector, (.25, .25, .75, 1.0), False,
        {
            'default_value': FloatVectorProperty(size=3, subtype="EULER")
        }
    ),         
    ('normal', 'Normal', bpy.types.NodeSocketInterfaceVector, (.25, .25, .75, 1.0), False,
        {
            'default_value': FloatVectorProperty(size=3, subtype="EULER")
        }
    ),       
    ('point', 'Point', bpy.types.NodeSocketInterfaceVector, (.25, .25, .75, 1.0), False,
        {
            'default_value': FloatVectorProperty(size=3, subtype="EULER")
        }
    ),             
    ('light', 'Light', bpy.types.NodeSocketInterfaceString, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ),      
    ('lightfilter', 'LightFilter', bpy.types.NodeSocketInterfaceString, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ),     
    ('displacement', 'Displacement', bpy.types.NodeSocketInterfaceString, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ),     
    ('samplefilter', 'SampleFilter', bpy.types.NodeSocketInterfaceString, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ),    
    ('displayfilter', 'DisplayFilter', bpy.types.NodeSocketInterfaceString, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ),             
    ('integrator', 'Integrator', bpy.types.NodeSocketInterfaceString, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ),         
    ('shader', 'Shader', bpy.types.NodeSocketInterfaceShader, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ), 
    ('projection', 'Projection', bpy.types.NodeSocketInterfaceShader, (0.25, 1.0, 0.25, 1.0), True,
        {
            'default_value': '',
        }
    ),           
]

class RendermanSocket:
    ui_open: BoolProperty(name='UI Open', default=True)

    def get_pretty_name(self, node):
        if node.bl_idname in __CYCLES_GROUP_NODES__:
            return self.name
        else:
            return self.identifier

    def get_value(self, node):
        if node.bl_idname in __CYCLES_GROUP_NODES__ or not hasattr(node, self.name):
            return self.default_value
        else:
            return getattr(node, self.name)

    def draw_color(self, context, node):
        return (0.25, 1.0, 0.25, 1.0)

    def draw_value(self, context, layout, node):
        layout.prop(node, self.identifier)

    def draw(self, context, layout, node, text):
        if self.is_linked or self.is_output or self.hide_value or not hasattr(self, 'default_value'):
            layout.label(text=self.get_pretty_name(node))
        elif node.bl_idname in __CYCLES_GROUP_NODES__ or node.bl_idname == "PxrOSLPatternNode":
            layout.prop(self, 'default_value',
                        text=self.get_pretty_name(node), slider=True)
        else:
            layout.prop(node, self.name,
                        text=self.get_pretty_name(node), slider=True)
        mat = getattr(context, 'material')
        if mat:
            output_node = shadergraph_utils.is_renderman_nodetree(mat)
            if not output_node:
                return
            if not self.is_linked and not self.is_output:
                draw_utils.draw_sticky_toggle(layout, node, self.name, output_node)

class RendermanSocketInterface:

    def draw_color(self, context):
        return (0.25, 1.0, 0.25, 1.0)

    def draw(self, context, layout):
        layout.label(text=self.name)

    def from_socket(self, node, socket):
        if hasattr(self, 'default_value'):
            self.default_value = socket.get_value(node)
        self.name = socket.name

    def init_socket(self, node, socket, data_path):
        sleep(.01)
        socket.name = self.name
        if hasattr(self, 'default_value'):
            socket.default_value = self.default_value

classes = []

def register_socket_classes():
    global classes

    def draw_color(self, context, node):
        return self.socket_color

    for socket_info in __RENDERMAN_TYPES_SOCKETS__:
        renderman_type = socket_info[0]
        label = socket_info[1]
        typename = 'RendermanNodeSocket%s' % label
        ntype = type(typename, (socket_info[2], RendermanSocket,), {})
        ntype.bl_label = 'RenderMan %s Socket' % label
        ntype.bl_idname = typename
        if "__annotations__" not in ntype.__dict__:
            setattr(ntype, "__annotations__", {})        
        ntype.draw_color = draw_color
        ntype.socket_color = socket_info[3]
        ntype.__annotations__['renderman_type'] = StringProperty(default='%s' % renderman_type)
        if socket_info[4]:
            ntype.__annotations__['hide_value'] = True
        ann_dict = socket_info[5]
        for k, v in ann_dict.items():
            ntype.__annotations__[k] = v

        classes.append(ntype)

def register_socket_interface_classes():
    global classes

    def draw_color(self, context):
        return self.socket_color

    for socket_info in __RENDERMAN_TYPES_SOCKET_INTERFACES__:
        renderman_type = socket_info[0]
        label = socket_info[1]
        typename = 'RendermanNodeSocketInterface%s' % label
        ntype = type(typename, (socket_info[2], RendermanSocketInterface,), {})        
        ntype.bl_label = 'RenderMan %s Socket' % label
        ntype.bl_idname = typename
        if "__annotations__" not in ntype.__dict__:
            setattr(ntype, "__annotations__", {})        
        ntype.draw_color = draw_color
        ntype.socket_color = socket_info[3]
        if socket_info[4]:
            ntype.__annotations__['hide_value'] = True        
        ann_dict = socket_info[5]
        for k, v in ann_dict.items():
            ntype.__annotations__[k] = v

def register():

    register_socket_classes()
    register_socket_interface_classes()

    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass   