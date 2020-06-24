from bpy.props import EnumProperty, StringProperty, BoolProperty
from operator import attrgetter, itemgetter
from .. import rman_bl_nodes
from ..rman_utils.shadergraph_utils import find_node, find_selected_pattern_node
from ..icons.icons import load_icons
import bpy
import os

def socket_node_input(nt, socket):
    return next((l.from_node for l in nt.links if l.to_socket == socket), None)

def socket_socket_input(nt, socket):
    return next((l.from_socket for l in nt.links if l.to_socket == socket and socket.is_linked),
                None)


def linked_sockets(sockets):
    if sockets is None:
        return []
    return [i for i in sockets if i.is_linked]

# Operators
# connect the pattern nodes in some sensible manner (color output to color input etc)
# TODO more robust
def link_node(nt, from_node, in_socket):
    out_socket = None
    # first look for resultF/resultRGB
    if type(in_socket).__name__ in ['RendermanNodeSocketColor',
                                    'RendermanNodeSocketVector']:
        out_socket = from_node.outputs.get('resultRGB',
                                           next((s for s in from_node.outputs
                                                 if type(s).__name__ == 'RendermanNodeSocketColor'), None))
    elif type(in_socket).__name__ == 'RendermanNodeSocketStruct':
        out_socket = from_node.outputs.get('pxrMaterialOut', None)
        if not out_socket:
            out_socket = from_node.outputs.get('result', None)

    else:
        out_socket = from_node.outputs.get('resultF',
                                           next((s for s in from_node.outputs
                                                 if type(s).__name__ == 'RendermanNodeSocketFloat'), None))

    if not out_socket:
        # try matching the first one we can find
        in_socket_type = type(in_socket).__name__
        for s in from_node.outputs:
            if type(s).__name__ == in_socket_type:
                out_socket = s
                break

    if out_socket:
        nt.links.new(out_socket, in_socket)    

class NODE_OT_add_displayfilter_node_socket(bpy.types.Operator):

    bl_idname = 'node.add_displayfilter_node_socket'
    bl_label = 'Add DisplayFilter Socket'
    bl_description = 'Add a new socket to the displayfilter output node'

    def execute(self, context):
        if hasattr(context, 'node'):
            node = context.node
        else:
            world = context.scene.world
            rm = world.renderman
            nt = world.node_tree

            node = find_node(world, 'RendermanDisplayfiltersOutputNode')
            if not node:
                return {'FINISHED'}

        node.add_input()
        return {'FINISHED'}   

        return {'FINISHED'}    

class NODE_OT_remove_displayfilter_node_socket(bpy.types.Operator):

    bl_idname = 'node.remove_displayfilter_node_socket'
    bl_label = 'Remove DisplayFilter Socket'
    bl_description = 'Remove a new socket to the displayfilter output node'

    def execute(self, context):
        if hasattr(context, 'node'):
            node = context.node
        else:
            world = context.scene.world
            rm = world.renderman
            nt = world.node_tree

            node = find_node(world, 'RendermanDisplayfiltersOutputNode')
            if not node:
                return {'FINISHED'}

        node.remove_input()
        return {'FINISHED'}                

class NODE_OT_add_samplefilter_node_socket(bpy.types.Operator):

    bl_idname = 'node.add_samplefilter_node_socket'
    bl_label = 'Add SampleFilter Socket'
    bl_description = 'Add a new socket to the samplefilter output node'

    def execute(self, context):
        if hasattr(context, 'node'):
            node = context.node
        else:
            world = context.scene.world
            rm = world.renderman
            nt = world.node_tree

            node = find_node(world, 'RendermanSamplefiltersOutputNode')
            if not node:
                return {'FINISHED'}

        node.add_input()
        return {'FINISHED'}   

class NODE_OT_remove_samplefilter_node_socket(bpy.types.Operator):

    bl_idname = 'node.remove_samplefilter_node_socket'
    bl_label = 'Remove SampleFilter Socket'
    bl_description = 'Remove a new socket to the samplefilter output node'

    def execute(self, context):
        if hasattr(context, 'node'):
            node = context.node
        else:
            world = context.scene.world
            rm = world.renderman
            nt = world.node_tree

            node = find_node(world, 'RendermanSamplefiltersOutputNode')
            if not node:
                return {'FINISHED'}

        node.remove_input()
        return {'FINISHED'}             

class NODE_OT_rman_node_remove(bpy.types.Operator):
    bl_idname = "node.rman_shading_remove"
    bl_label = "Remove Node"
    bl_description = "Remove the current connected node."

    def execute(self, context):

        nt = context.nodetree
        node = context.node
        socket = context.socket
        input_node = socket_node_input(nt, socket)

        nt.nodes.remove(input_node)
        return {'FINISHED'}

class NODE_OT_rman_node_disconnect(bpy.types.Operator):
    bl_idname = "node.rman_shading_disconnect"
    bl_label = "Disconnect Node"
    bl_description = "Disconnect the current connected node."

    def execute(self, context):

        nt = context.nodetree
        node = context.node
        socket = context.socket

        link = next((l for l in nt.links if l.to_socket == socket), None)
        nt.links.remove(link)

        return {'FINISHED'}

class NODE_OT_rman_node_create(bpy.types.Operator):
    bl_idname = "node.rman_shading_create_node"
    bl_label = "Create Node"
    bl_description = "Create and connect selected node."

    node_name: StringProperty(default="")

    def execute(self, context):
        nt = context.nodetree
        node = context.node
        socket = context.socket
        input_node = socket_node_input(nt, socket)

        if input_node is None:
            newnode = nt.nodes.new(self.node_name)
            newnode.location = node.location
            newnode.location[0] -= 300
            newnode.selected = False
            link_node(nt, newnode, socket)

        # replace input node with a new one
        else:
            newnode = nt.nodes.new(self.node_name)
            input = socket
            old_node = input.links[0].from_node
            link_node(nt, newnode, socket)
            newnode.location = old_node.location
            active_material = context.active_object.active_material
            newnode.update_mat(active_material)
            #nt.nodes.remove(old_node)
        return {'FINISHED'}

class NODE_OT_rman_node_connect_existing(bpy.types.Operator):
    bl_idname = "node.rman_shading_connect_existing_node"
    bl_label = "Connect Existing Node"
    bl_description = "Connect to an existing shading node"

    node_name: StringProperty(default="")

    def execute(self, context):
        nt = context.nodetree
        node = context.node
        socket = context.socket
        input_node = socket_node_input(nt, socket)
        newnode = None

        for n in nt.nodes:
            if n.name == self.node_name:
                newnode = n
                break
        
        if not newnode:
            # should never be true, but just in case
            return {'FINISHED'}

        if input_node is None:
            newnode.selected = False
            link_node(nt, newnode, socket)

        # replace input node with a new one
        else:
            input = socket
            old_node = input.links[0].from_node
            link_node(nt, newnode, socket)
            active_material = context.active_object.active_material
            newnode.update_mat(active_material)
        return {'FINISHED'}

class NODE_OT_rman_preset_set_param(bpy.types.Operator):
    bl_idname = "node.rman_preset_set_param"
    bl_label = "Set Param Preset"
    bl_description = "Set parameter from preset"

    prop_name: StringProperty(default="")
    preset_name: StringProperty(default="")

    def invoke(self, context, event):
        nt = context.nodetree
        node = context.node
        socket = context.socket

        prop_meta = node.prop_meta.get(self.prop_name, None)
        if prop_meta:            
            if 'presets' in prop_meta:
                val = prop_meta['presets'].get(self.preset_name, None)
                if val:
                    setattr(node, self.prop_name, val)

        return {'FINISHED'}

class NODE_OT_rman_node_set_solo(bpy.types.Operator):
    bl_idname = "node.rman_set_node_solo"
    bl_label = "Set Node Solo"
    bl_description = "Solo a node in material shader tree"

    solo_node_name: StringProperty(default="")
    refresh_solo: BoolProperty(default=False)

    def invoke(self, context, event):
        nt = context.nodetree
        output_node = context.node
        selected_node = None

        if self.refresh_solo:
            output_node.solo_node_name = ''
            output_node.solo_node_output = ''
            return {'FINISHED'}           

        if self.solo_node_name:
            output_node.solo_node_name = self.solo_node_name
            output_node.solo_node_output = ''
            return {'FINISHED'}        

        selected_node = find_selected_pattern_node(nt)

        if not selected_node:
            self.report({'ERROR'}, "Pattern node not selected")
            return {'FINISHED'}   

        output_node.solo_node_name = selected_node.name
        output_node.solo_node_output = ''

        return {'FINISHED'}        

class NODE_OT_rman_node_set_solo_output(bpy.types.Operator):
    bl_idname = "node.rman_set_node_solo_output"
    bl_label = "Set Node Solo Output"
    bl_description = "Select output for solo node"

    solo_node_output: StringProperty(default="")
    solo_node_name: StringProperty(default="")

    def invoke(self, context, event):
        nt = context.nodetree
        node = context.node
        node.solo_node_output = self.solo_node_output
        node.solo_node_name = self.solo_node_name

        return {'FINISHED'}         

class NODE_OT_rman_refresh_osl_shader(bpy.types.Operator):
    bl_idname = "node.refresh_osl_shader"
    bl_label = "Refresh OSL Node"
    bl_description = "Refreshes the OSL node This takes a second!!"

    def invoke(self, context, event):
        context.node.RefreshNodes(context)
        return {'FINISHED'}

classes = [
    NODE_OT_add_displayfilter_node_socket,
    NODE_OT_remove_displayfilter_node_socket,
    NODE_OT_add_samplefilter_node_socket,
    NODE_OT_remove_samplefilter_node_socket,
    NODE_OT_rman_node_disconnect,
    NODE_OT_rman_node_remove,
    NODE_OT_rman_node_create,
    NODE_OT_rman_node_connect_existing,
    NODE_OT_rman_preset_set_param,
    NODE_OT_rman_node_set_solo,
    NODE_OT_rman_node_set_solo_output,
    NODE_OT_rman_refresh_osl_shader
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