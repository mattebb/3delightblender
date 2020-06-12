import bpy
from bpy.props import *

group_nodes = ['ShaderNodeGroup', 'NodeGroupInput', 'NodeGroupOutput']
# Default Types

# update node during ipr for a socket default_value


def update_func(self, context):
    # check if this prop is set on an input
    node = self.node if hasattr(self, 'node') else self

# socket name corresponds to the param on the node


class RendermanSocket:
    ui_open: BoolProperty(name='UI Open', default=True)

    def get_pretty_name(self, node):
        if node.bl_idname in group_nodes:
            return self.name
        else:
            return self.identifier

    def get_value(self, node):
        if node.bl_idname in group_nodes or not hasattr(node, self.name):
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
        elif node.bl_idname in group_nodes or node.bl_idname == "PxrOSLPatternNode":
            layout.prop(self, 'default_value',
                        text=self.get_pretty_name(node), slider=True)
        else:
            layout.prop(node, self.name,
                        text=self.get_pretty_name(node), slider=True)


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


# socket types (need this just for the ui_open)
class RendermanNodeSocketFloat(bpy.types.NodeSocketFloat, RendermanSocket):
    '''RenderMan float input/output'''
    bl_idname = 'RendermanNodeSocketFloat'
    bl_label = 'RenderMan Float Socket'

    default_value: FloatProperty(update=update_func)
    renderman_type: StringProperty(default='float')

    def draw_color(self, context, node):
        return (0.5, 0.5, 0.5, 1.0)


class RendermanNodeSocketInterfaceFloat(bpy.types.NodeSocketInterfaceFloat, RendermanSocketInterface):
    '''RenderMan float input/output'''
    bl_idname = 'RendermanNodeSocketInterfaceFloat'
    bl_label = 'RenderMan Float Socket'
    bl_socket_idname = 'RendermanNodeSocketFloat'

    default_value: FloatProperty()

    def draw_color(self, context):
        return (0.5, 0.5, 0.5, 1.0)


class RendermanNodeSocketInt(bpy.types.NodeSocketInt, RendermanSocket):
    '''RenderMan int input/output'''
    bl_idname = 'RendermanNodeSocketInt'
    bl_label = 'RenderMan Int Socket'

    default_value: IntProperty(update=update_func)
    renderman_type: StringProperty(default='int')

    def draw_color(self, context, node):
        return (1.0, 1.0, 1.0, 1.0)


class RendermanNodeSocketInterfaceInt(bpy.types.NodeSocketInterfaceInt, RendermanSocketInterface):
    '''RenderMan float input/output'''
    bl_idname = 'RendermanNodeSocketInterfaceInt'
    bl_label = 'RenderMan Int Socket'
    bl_socket_idname = 'RendermanNodeSocketInt'

    default_value: IntProperty()

    def draw_color(self, context):
        return (1.0, 1.0, 1.0, 1.0)


class RendermanNodeSocketString(bpy.types.NodeSocketString, RendermanSocket):
    '''RenderMan string input/output'''
    bl_idname = 'RendermanNodeSocketString'
    bl_label = 'RenderMan String Socket'
    default_value: StringProperty(update=update_func)
    is_texture: BoolProperty(default=False)
    renderman_type: StringProperty(default='string')


class RendermanNodeSocketStruct(bpy.types.NodeSocketString, RendermanSocket):
    '''RenderMan struct input/output'''
    bl_idname = 'RendermanNodeSocketStruct'
    bl_label = 'RenderMan Struct Socket'
    hide_value = True
    renderman_type = 'struct'
    default_value = ''

    def draw_color(self, context, node):
        return (1.0, 0.344, 0.0, 1.0)    

class RendermanNodeSocketBxdf(bpy.types.NodeSocketString, RendermanSocket):
    '''RenderMan bxdf input/output'''
    bl_idname = 'RendermanNodeSocketBxdf'
    bl_label = 'RenderMan Bxdf Socket'
    hide_value = True
    renderman_type = 'bxdf'
    default_value = ''



class RendermanNodeSocketInterfaceStruct(bpy.types.NodeSocketInterfaceString, RendermanSocketInterface):
    '''RenderMan struct input/output'''
    bl_idname = 'RendermanNodeSocketInterfaceStruct'
    bl_label = 'RenderMan Struct Socket'
    bl_socket_idname = 'RendermanNodeSocketStruct'
    hide_value = True

    def draw_color(self, context):
        return (1.0, 0.344, 0.0, 1.0)      

class RendermanNodeSocketInterfaceBxdf(bpy.types.NodeSocketInterfaceString, RendermanSocketInterface):
    '''RenderMan Bxdf input/output'''
    bl_idname = 'RendermanNodeSocketInterfaceBxdf'
    bl_label = 'RenderMan Bxdf Socket'
    bl_socket_idname = 'RendermanNodeSocketBxdf'
    hide_value = True

class RendermanNodeSocketColor(bpy.types.NodeSocketColor, RendermanSocket):
    '''RenderMan color input/output'''
    bl_idname = 'RendermanNodeSocketColor'
    bl_label = 'RenderMan Color Socket'

    default_value: FloatVectorProperty(size=3,
                                        subtype="COLOR", update=update_func)
    renderman_type: StringProperty(default='color')

    def draw_color(self, context, node):
        return (1.0, 1.0, .5, 1.0)


class RendermanNodeSocketInterfaceColor(bpy.types.NodeSocketInterfaceColor, RendermanSocketInterface):
    '''RenderMan color input/output'''
    bl_idname = 'RendermanNodeSocketInterfaceColor'
    bl_label = 'RenderMan Color Socket'
    bl_socket_idname = 'RendermanNodeSocketColor'

    default_value: FloatVectorProperty(size=3,
                                        subtype="COLOR")

    def draw_color(self, context):
        return (1.0, 1.0, .5, 1.0)


class RendermanNodeSocketVector(RendermanSocket, bpy.types.NodeSocketVector):
    '''RenderMan vector input/output'''
    bl_idname = 'RendermanNodeSocketVector'
    bl_label = 'RenderMan Vector Socket'
    hide_value = True

    default_value: FloatVectorProperty(size=3,
                                        subtype="EULER", update=update_func)
    renderman_type: StringProperty(default='vector')

    def draw_color(self, context, node):
        return (.25, .25, .75, 1.0)

class RendermanNodeSocketNormal(RendermanSocket, bpy.types.NodeSocketVector):
    '''RenderMan normal input/output'''
    bl_idname = 'RendermanNodeSocketNormal'
    bl_label = 'RenderMan Normal Socket'
    hide_value = True

    default_value: FloatVectorProperty(size=3,
                                        subtype="EULER", update=update_func)
    renderman_type: StringProperty(default='normal')

    def draw_color(self, context, node):
        return (.25, .25, .75, 1.0)

class RendermanNodeSocketPoint(RendermanSocket, bpy.types.NodeSocketVector):
    '''RenderMan point input/output'''
    bl_idname = 'RendermanNodeSocketPoint'
    bl_label = 'RenderMan Point Socket'
    hide_value = True

    default_value: FloatVectorProperty(size=3,
                                        subtype="EULER", update=update_func)
    renderman_type: StringProperty(default='point')

    def draw_color(self, context, node):
        return (.25, .25, .75, 1.0)                


class RendermanNodeSocketInterfaceVector(bpy.types.NodeSocketInterfaceVector, RendermanSocketInterface):
    '''RenderMan color input/output'''
    bl_idname = 'RendermanNodeSocketInterfaceVector'
    bl_label = 'RenderMan Vector Socket'
    bl_socket_idname = 'RendermanNodeSocketVector'
    hide_value = True

    default_value: FloatVectorProperty(size=3,
                                        subtype="EULER")

    def draw_color(self, context):
        return (.25, .25, .75, 1.0)

class RendermanNodeSocketInterfaceVector(bpy.types.NodeSocketInterfaceVector, RendermanSocketInterface):
    '''RenderMan color input/output'''
    bl_idname = 'RendermanNodeSocketInterfaceVector'
    bl_label = 'RenderMan Vector Socket'
    bl_socket_idname = 'RendermanNodeSocketVector'
    hide_value = True

    default_value: FloatVectorProperty(size=3,
                                        subtype="EULER")

    def draw_color(self, context):
        return (.25, .25, .75, 1.0)

class RendermanNodeSocketInterfaceNormal(bpy.types.NodeSocketInterfaceVector, RendermanSocketInterface):
    '''RenderMan color input/output'''
    bl_idname = 'RendermanNodeSocketInterfaceNormal'
    bl_label = 'RenderMan Normal Socket'
    bl_socket_idname = 'RendermanNodeSocketNormal'
    hide_value = True

    default_value: FloatVectorProperty(size=3,
                                        subtype="EULER")

    def draw_color(self, context):
        return (.25, .25, .75, 1.0)

class RendermanNodeSocketInterfacePoint(bpy.types.NodeSocketInterfaceVector, RendermanSocketInterface):
    '''RenderMan color input/output'''
    bl_idname = 'RendermanNodeSocketInterfacePoint'
    bl_label = 'RenderMan Point Socket'
    bl_socket_idname = 'RendermanNodeSocketPoint'
    hide_value = True

    default_value: FloatVectorProperty(size=3,
                                        subtype="EULER")

    def draw_color(self, context):
        return (.25, .25, .75, 1.0)                        

class RendermanNodeSocketLight(bpy.types.NodeSocketString, RendermanSocket):
    '''RenderMan light input/output'''
    bl_idname = 'RendermanNodeSocketLight'
    bl_label = 'RenderMan Light Socket'
    hide_value = True
    renderman_type = 'light'
    default_value = ''

class RendermanNodeSocketInterfaceLight(bpy.types.NodeSocketInterfaceString, RendermanSocketInterface):
    '''RenderMan Light input/output'''
    bl_idname = 'RendermanNodeSocketInterfaceLight'
    bl_label = 'RenderMan Light Socket'
    bl_socket_idname = 'RendermanNodeSocketLight'
    hide_value = True        

class RendermanNodeSocketDisplacement(bpy.types.NodeSocketString, RendermanSocket):
    '''RenderMan displacement input/output'''
    bl_idname = 'RendermanNodeSocketDisplacement'
    bl_label = 'RenderMan Displacement Socket'
    hide_value = True
    renderman_type = 'displacement'
    default_value = ''

class RendermanNodeSocketInterfaceDisplacement(bpy.types.NodeSocketInterfaceString, RendermanSocketInterface):
    '''RenderMan Displacement input/output'''
    bl_idname = 'RendermanNodeSocketInterfaceDisplacement'
    bl_label = 'RenderMan Displacement Socket'
    bl_socket_idname = 'RendermanNodeSocketDisplacement'
    hide_value = True        

class RendermanNodeSocketLightFilter(bpy.types.NodeSocketString, RendermanSocket):
    '''RenderMan light filter input/output'''
    bl_idname = 'RendermanNodeSocketLightFilter'
    bl_label = 'RenderMan Light Filter Socket'
    hide_value = True
    renderman_type = 'lightfilter'
    default_value = ''

class RendermanNodeSocketInterfaceLightFilter(bpy.types.NodeSocketInterfaceString, RendermanSocketInterface):
    '''RenderMan Light Filter input/output'''
    bl_idname = 'RendermanNodeSocketInterfaceLightFilter'
    bl_label = 'RenderMan Light Filter Socket'
    bl_socket_idname = 'RendermanNodeSocketLightFilter'
    hide_value = True        

class RendermanNodeSocketSampleFilter(bpy.types.NodeSocketString, RendermanSocket):
    '''RenderMan sample filter input/output'''
    bl_idname = 'RendermanNodeSocketSampleFilter'
    bl_label = 'RenderMan Sample Filter Socket'
    hide_value = True
    renderman_type: StringProperty(default='samplefilter')
    default_value = ''

class RendermanNodeSocketInterfaceSampleFilter(bpy.types.NodeSocketInterfaceString, RendermanSocketInterface):
    '''RenderMan Sample Filter input/output'''
    bl_idname = 'RendermanNodeSocketInterfaceSampleFilter'
    bl_label = 'RenderMan Sample Filter Socket'
    bl_socket_idname = 'RendermanNodeSocketSampleFilter'
    hide_value = True      

class RendermanNodeSocketDisplayFilter(bpy.types.NodeSocketString, RendermanSocket):
    '''RenderMan Display filter input/output'''
    bl_idname = 'RendermanNodeSocketDisplayFilter'
    bl_label = 'RenderMan Display Filter Socket'
    hide_value = True
    renderman_type: StringProperty(default='displayfilter')
    default_value = ''

class RendermanNodeSocketInterfaceDisplayFilter(bpy.types.NodeSocketInterfaceString, RendermanSocketInterface):
    '''RenderMan Display Filter input/output'''
    bl_idname = 'RendermanNodeSocketInterfaceDisplayFilter'
    bl_label = 'RenderMan Display Filter Socket'
    bl_socket_idname = 'RendermanNodeSocketDisplayFilter'
    hide_value = True      

class RendermanNodeSocketIntegrator(bpy.types.NodeSocketString, RendermanSocket):
    '''RenderMan Integrator input/output'''
    bl_idname = 'RendermanNodeSocketIntegrator'
    bl_label = 'RenderMan Integrator Socket'
    hide_value = True
    renderman_type: StringProperty(default='integrator')
    default_value = ''

class RendermanNodeSocketInterfaceIntegrator(bpy.types.NodeSocketInterfaceString, RendermanSocketInterface):
    '''RenderMan Integrator input/output'''
    bl_idname = 'RendermanNodeSocketInterfaceIntegrator'
    bl_label = 'RenderMan Integrator Socket'
    bl_socket_idname = 'RendermanNodeSocketIntegrator'
    hide_value = True     

# Custom socket type for connecting shaders

class RendermanShaderSocket(bpy.types.NodeSocketShader, RendermanSocket):
    '''RenderMan shader input/output'''
    bl_idname = 'RendermanShaderSocket'
    bl_label = 'RenderMan Shader Socket'
    hide_value = True
    renderman_type = 'shader'

# Custom socket type for connecting shaders


class RendermanShaderSocketInterface(bpy.types.NodeSocketInterfaceShader, RendermanSocketInterface):
    '''RenderMan shader input/output'''
    bl_idname = 'RendermanShaderInterfaceSocket'
    bl_label = 'RenderMan Shader Socket'
    bl_socket_idname = 'RendermanShaderSocket'
    hide_value = True

classes = [
    RendermanShaderSocket,
    RendermanNodeSocketColor,
    RendermanNodeSocketFloat,
    RendermanNodeSocketInt,
    RendermanNodeSocketString,
    RendermanNodeSocketVector,
    RendermanNodeSocketNormal,
    RendermanNodeSocketPoint,
    RendermanNodeSocketStruct,
    RendermanNodeSocketBxdf,
    RendermanNodeSocketLight,
    RendermanNodeSocketDisplacement,
    RendermanNodeSocketLightFilter,
    RendermanNodeSocketSampleFilter,    
    RendermanNodeSocketDisplayFilter,
    RendermanNodeSocketIntegrator,

    RendermanNodeSocketInterfaceFloat,
    RendermanNodeSocketInterfaceInt,
    RendermanNodeSocketInterfaceStruct,
    RendermanNodeSocketInterfaceBxdf,
    RendermanNodeSocketInterfaceLight,
    RendermanNodeSocketInterfaceDisplacement,
    RendermanNodeSocketInterfaceLightFilter,
    RendermanNodeSocketInterfaceSampleFilter,   
    RendermanNodeSocketInterfaceDisplayFilter,    
    RendermanNodeSocketInterfaceIntegrator,
    RendermanNodeSocketInterfaceColor,
    RendermanNodeSocketInterfaceVector,
    RendermanNodeSocketInterfaceNormal,
    RendermanNodeSocketInterfacePoint,
    RendermanShaderSocketInterface
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