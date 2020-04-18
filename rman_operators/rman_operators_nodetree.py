import bpy
from ..icons.icons import load_icons
from bpy.props import StringProperty, BoolProperty, EnumProperty
from .. import rman_cycles_convert
from ..rman_utils import shadergraph_utils
from .. import rman_bl_nodes

class SHADING_OT_convert_all_renderman_nodetree(bpy.types.Operator):

    ''''''
    bl_idname = "shading.convert_cycles_stuff"
    bl_label = "Convert All Cycles to RenderMan"
    bl_description = "Convert all Cycles nodetrees to RenderMan. This is not guaranteed to work. It is still recommended to use RenderMan only nodes."

    def execute(self, context):
        for mat in bpy.data.materials:
            mat.use_nodes = True
            nt = mat.node_tree
            if shadergraph_utils.is_renderman_nodetree(mat):
                continue
            output = nt.nodes.new('RendermanOutputNode')
            try:
                if not rman_cycles_convert.convert_cycles_nodetree(mat, output):
                    default = nt.nodes.new('PxrSurfaceBxdfNode')
                    default.location = output.location
                    default.location[0] -= 300
                    nt.links.new(default.outputs[0], output.inputs[0])
            except Exception as e:
                self.report({'ERROR'}, "Error converting " + mat.name)
                #self.report({'ERROR'}, str(e))
                # uncomment to debug conversion
                import traceback
                traceback.print_exc()

        for light in bpy.data.lights:
            if light.renderman.use_renderman_node:
                continue
            light.use_nodes = True
            light_type = light.type
            light.renderman.light_primary_visibility = False
            nt = light.node_tree

            light_shader = ''
            if light_type == 'SUN':
                light_shader = 'PxrDistantLight'  
            elif light_type == 'HEMI':
                light_shader = 'PxrDomeLight'
            elif light_type == 'AREA':
                if light.shape == 'DISK':
                    light_shader = 'PxrDiskLight'
                elif light.shape == 'ELLIPSE':
                    light_shader = 'PxrSphereLight'
                else:
                    light_shader = 'PxrRectLight'
            elif light_type == 'SPOT':
                light_shader = 'PxrDiskLight'
            elif light_type == 'POINT':
                light_shader = 'PxrSphereLight' 
            else:
                light_shader = 'PxrRectLight'            

            light.type = 'AREA'
            light.renderman.use_renderman_node = True

            output = nt.nodes.new('RendermanOutputNode')
            default = nt.nodes.new('%sLightNode' % light_shader)

            default.location = output.location
            default.location[0] -= 300
            nt.links.new(default.outputs[0], output.inputs[1])    

            output.inputs[0].hide = True
            output.inputs[2].hide = True
            output.inputs[3].hide = True      
            light.renderman.renderman_light_role = 'RMAN_LIGHT' 

            if light_type == 'SPOT':
                node = context.light.renderman.get_light_node()
                node.coneAngle = math.degrees(light.spot_size)
                node.coneSoftness = light.spot_blend                    

        # convert cycles vis settings
        for ob in context.scene.objects:
            if not ob.cycles_visibility.camera:
                ob.renderman.visibility_camera = False
            if not ob.cycles_visibility.diffuse or not ob.cycles_visibility.glossy:
                ob.renderman.visibility_trace_indirect = False
            if not ob.cycles_visibility.transmission:
                ob.renderman.visibility_trace_transmission = False
        return {'FINISHED'}

class SHADING_OT_convert_cycles_to_renderman_nodetree(bpy.types.Operator):

    ''''''
    bl_idname = "shading.convert_cycles_shader"
    bl_label = "Convert Cycles Shader"
    bl_description = "Try to convert the current Cycles Shader to RenderMan. This is not guaranteed to work. It is still recommended to use RenderMan only nodes."

    idtype: StringProperty(name="ID Type", default="material")
    bxdf_name: StringProperty(name="Bxdf Name", default="PxrDisneyBsdf")

    def execute(self, context):
        idtype = self.properties.idtype
        if idtype == 'node_editor':
            idblock = context.space_data.id
            idtype = 'material'
        else:
            context_data = {'material': context.material,
                            'light': context.light, 'world': context.scene.world}
            idblock = context_data[idtype]

        idblock.use_nodes = True
        nt = idblock.node_tree

        if idtype == 'material':
            output = nt.nodes.new('RendermanOutputNode')
            if context.material.grease_pencil:
                shadergraph_utils.convert_grease_pencil_mat(context.material, nt, output)

            elif not rman_cycles_convert.convert_cycles_nodetree(idblock, output):
                default = nt.nodes.new('%sBxdfNode' %
                                       self.properties.bxdf_name)
                default.location = output.location
                default.location[0] -= 300
                nt.links.new(default.outputs[0], output.inputs[0])

                if idblock.renderman.copy_color_params:
                    default.diffuseColor = idblock.diffuse_color
                    default.diffuseGain = idblock.diffuse_intensity
                    default.enablePrimarySpecular = True
                    default.specularFaceColor = idblock.specular_color

            output.inputs[3].hide = True
                      
        return {'FINISHED'}

class SHADING_OT_add_renderman_nodetree(bpy.types.Operator):

    ''''''
    bl_idname = "shading.add_renderman_nodetree"
    bl_label = "Add RenderMan Nodetree"
    bl_description = "Add a RenderMan shader node tree"

    idtype: StringProperty(name="ID Type", default="material")

    def get_type_items(self, context):
        icons = load_icons()
        rman_unknown_icon = icons.get("out_unknown.png")    
        items = []
        i = 0
        for i,n in enumerate(rman_bl_nodes.__RMAN_BXDF_NODES__):
            rman_bxdf_icon = icons.get("out_%s.png" % n.name, None)
            if not rman_bxdf_icon:
                items.append( (n.name, n.name, '', rman_unknown_icon.icon_id, i))
            else:
                items.append( (n.name, n.name, '', rman_bxdf_icon.icon_id, i))                
        return items        
    bxdf_name: EnumProperty(items=get_type_items, name="Material")    

    def execute(self, context):
        idtype = self.properties.idtype
        if idtype == 'node_editor':
            idblock = context.space_data.id
            idtype = 'material'
        else:
            context_data = {'material': context.material,
                            'light': context.light, 'world': context.scene.world}
            idblock = context_data[idtype]

        # nt = bpy.data.node_groups.new(idblock.name,
        #                              type='RendermanPatternGraph')
        #nt.use_fake_user = True
        idblock.use_nodes = True
        nt = idblock.node_tree

        if idtype == 'material':
            output = nt.nodes.new('RendermanOutputNode')
            if context.material.grease_pencil:
                shadergraph_utils.convert_grease_pencil_mat(context.material, nt, output)

            else:
                default = nt.nodes.new('%sBxdfNode' %
                                       self.properties.bxdf_name)
                default.location = output.location
                default.location[0] -= 300
                nt.links.new(default.outputs[0], output.inputs[0])

                '''
                if idblock.renderman.copy_color_params:
                    default.diffuseColor = idblock.diffuse_color
                    default.diffuseGain = idblock.diffuse_intensity
                    default.enablePrimarySpecular = True
                    default.specularFaceColor = idblock.specular_color
                '''

            output.inputs[3].hide = True
                      
        elif idtype == 'light':
            light_type = idblock.type
            light = idblock

            light_shader = ''
            if light_type == 'SUN':
                light_shader = 'PxrDistantLight'  
            elif light_type == 'HEMI':
                light_shader = 'PxrDomeLight'
            elif light_type == 'AREA':
                if light.shape == 'DISK':
                    light_shader = 'PxrDiskLight'
                elif light.shape == 'ELLIPSE':
                    light_shader = 'PxrSphereLight'
                else:
                    light_shader = 'PxrRectLight'
            elif light_type == 'SPOT':
                light_shader = 'PxrDiskLight'
            elif light_type == 'POINT':
                light_shader = 'PxrSphereLight' 
            else:
                light_shader = 'PxrRectLight'

            light.type = 'AREA'
            light.renderman.use_renderman_node = True

            output = nt.nodes.new('RendermanOutputNode')
            default = nt.nodes.new('%sLightNode' %
                                    light_shader)
            default.location = output.location
            default.location[0] -= 300
            nt.links.new(default.outputs[0], output.inputs[1])    

            output.inputs[0].hide = True
            output.inputs[2].hide = True
            output.inputs[3].hide = True

            light.renderman.renderman_light_role = 'RMAN_LIGHT'
            if light_type == 'SPOT':
                node = context.light.renderman.get_light_node()
                node.coneAngle = math.degrees(light.spot_size)
                node.coneSoftness = light.spot_blend            

        elif idtype == 'world':
            # world
            idblock.renderman.use_renderman_node = True
            if shadergraph_utils.find_node(idblock, 'RendermanIntegratorsOutputNode'):
                return {'FINISHED'}
            output = nt.nodes.new('RendermanIntegratorsOutputNode')
            default = nt.nodes.new('PxrPathTracerIntegratorNode')
            default.location = output.location
            default.location[0] -= 200
            nt.links.new(default.outputs[0], output.inputs[0]) 

            sf_output = nt.nodes.new('RendermanSamplefiltersOutputNode')
            sf_output.location = default.location
            sf_output.location[0] -= 300

            df_output = nt.nodes.new('RendermanDisplayfiltersOutputNode')
            df_output.location = sf_output.location
            df_output.location[0] -= 300
            
            # create a default background display filter set to world color
            bg = nt.nodes.new('PxrBackgroundDisplayFilterDisplayfilterNode')
            bg.backgroundColor = idblock.color
            bg.location = df_output.location
            bg.location[0] -= 300
            nt.links.new(bg.outputs[0], df_output.inputs[0])

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="Select a Material")
        col.prop(self, 'bxdf_name')      

    def invoke(self, context, event):

        idtype = self.properties.idtype
        if idtype == 'node_editor':
            idblock = context.space_data.id
            idtype = 'material'
        else:
            context_data = {'material': context.material,
                            'light': context.light, 'world': context.scene.world}
            idblock = context_data[idtype]

        # nt = bpy.data.node_groups.new(idblock.name,
        #                              type='RendermanPatternGraph')
        #nt.use_fake_user = True
        idblock.use_nodes = True
        nt = idblock.node_tree

        if idtype == 'material':        
            wm = context.window_manager
            return wm.invoke_props_dialog(self)  
        return self.execute(context)
        
classes = [
    SHADING_OT_convert_all_renderman_nodetree,
    SHADING_OT_convert_cycles_to_renderman_nodetree,
    SHADING_OT_add_renderman_nodetree,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    
    for cls in classes:
        bpy.utils.unregister_class(cls)        