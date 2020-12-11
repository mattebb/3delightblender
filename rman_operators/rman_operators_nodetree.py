import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
from .. import rman_cycles_convert
from ..rfb_utils import shadergraph_utils
from .. import rman_bl_nodes
from .rman_operators_utils import get_bxdf_items, get_projection_items
from ..rman_render import RmanRender
import math

class SHADING_OT_convert_all_renderman_nodetree(bpy.types.Operator):

    ''''''
    bl_idname = "material.rman_convert_all_cycles_shaders"
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
                    pxr_surface_node = rman_bl_nodes.__BL_NODES_MAP__['PxrSurface']
                    default = nt.nodes.new(pxr_surface_node)
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

            #light.type = 'AREA'
            if hasattr(light, 'size'):
                light.size = 0.0
            light.type = 'POINT'

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
                node = light.renderman.get_light_node()
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
    bl_idname = "material.rman_convert_cycles_shader"
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
            if not idblock:
                # try getting material from context.object
                ob = context.object
                rm = ob.renderman
                idblock = rm.rman_material_override            

        idblock.use_nodes = True
        nt = idblock.node_tree

        if idtype == 'material':
            output = nt.nodes.new('RendermanOutputNode')
            if idblock.grease_pencil:
                shadergraph_utils.convert_grease_pencil_mat(idblock, nt, output)

            elif not rman_cycles_convert.convert_cycles_nodetree(idblock, output):
                bxdf_node_name = rman_bl_nodes.__BL_NODES_MAP__[self.properties.bxdf_name]
                default = nt.nodes.new(bxdf_node_name)
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
    bl_idname = "material.rman_add_rman_nodetree"
    bl_label = "Add RenderMan Nodetree"
    bl_description = "Add a RenderMan shader node tree"

    idtype: StringProperty(name="ID Type", default="material")

    def get_type_items(self, context):
        return get_bxdf_items()

    bxdf_name: EnumProperty(items=get_type_items, name="Material")    

    def execute(self, context):
        idtype = self.properties.idtype
        if idtype == 'node_editor':
            idblock = context.space_data.id
            idtype = 'material'
        elif idtype == 'world':
            idblock = context.scene.world
        else:
            context_data = {'material': context.material,
                            'light': context.light, 'world': context.scene.world}
            idblock = context_data[idtype]
            if not idblock:
                # try getting material from context.object
                ob = context.object
                rm = ob.renderman
                idblock = rm.rman_material_override

        # nt = bpy.data.node_groups.new(idblock.name,
        #                              type='RendermanPatternGraph')
        #nt.use_fake_user = True
        idblock.use_nodes = True
        nt = idblock.node_tree

        if idtype == 'material':
            output = nt.nodes.new('RendermanOutputNode')
            if idblock.grease_pencil:
                shadergraph_utils.convert_grease_pencil_mat(idblock, nt, output)

            else:
                bxdf_node_name = rman_bl_nodes.__BL_NODES_MAP__[self.properties.bxdf_name]
                default = nt.nodes.new(bxdf_node_name)
                default.location = output.location
                default.location[0] -= 300
                nt.links.new(default.outputs[0], output.inputs[0])

                if self.properties.bxdf_name == 'PxrLayerSurface':
                    shadergraph_utils.create_pxrlayer_nodes(nt, default)

                default.update_mat(idblock)    

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
        elif idtype == 'world':
            idblock = context.scene.world
        else:
            context_data = {'material': context.material,
                            'light': context.light, 'world': context.scene.world}
            idblock = context_data[idtype]
            if not idblock:
                # try getting material from context.object
                ob = context.object
                rm = ob.renderman
                idblock = rm.rman_material_override            

        idblock.use_nodes = True
        nt = idblock.node_tree

        if idtype == 'material':      
            if idblock.grease_pencil:
                return self.execute(context)  
            wm = context.window_manager
            return wm.invoke_props_dialog(self)  
        return self.execute(context)

class PRMAN_OT_New_bxdf(bpy.types.Operator):
    bl_idname = "node.rman_new_bxdf"
    bl_label = "New RenderMan Material"
    bl_description = "Create a new material with a new RenderMan Bxdf"
    bl_options = {"REGISTER", "UNDO"}

    idtype: StringProperty(name="ID Type", default="material")
    
    def get_type_items(self, context):
        return get_bxdf_items()  

    bxdf_name: EnumProperty(items=get_type_items, name="Bxdf Name")

    def execute(self, context):
        ob = context.object
        bxdf_name = self.bxdf_name
        mat = bpy.data.materials.new(bxdf_name)
        ob.active_material = mat
        mat.use_nodes = True
        nt = mat.node_tree

        output = nt.nodes.new('RendermanOutputNode')
        bxdf_node_name = rman_bl_nodes.__BL_NODES_MAP__[bxdf_name]        
        default = nt.nodes.new('%sBxdfNode' % bxdf_node_name)
        default.location = output.location
        default.location[0] -= 300
        nt.links.new(default.outputs[0], output.inputs[0])
        if self.bxdf_name == 'PxrLayerSurface':
            shadergraph_utils.create_pxrlayer_nodes(nt, default)

        output.inputs[3].hide = True
        default.update_mat(mat)

        return {"FINISHED"}  

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

        idblock.use_nodes = True
        nt = idblock.node_tree

        if idtype == 'material':      
            if context.material.grease_pencil:
                return self.execute(context)  
            wm = context.window_manager
            return wm.invoke_props_dialog(self)  
        return self.execute(context)      

class PRMAN_OT_New_Material_Override(bpy.types.Operator):
    bl_idname = "node.rman_new_material_override"
    bl_label = "New RenderMan Material Override"
    bl_description = "Create a new material override"
    bl_options = {"REGISTER", "UNDO"}
    
    def get_type_items(self, context):
        return get_bxdf_items()  

    bxdf_name: EnumProperty(items=get_type_items, name="Bxdf Name")

    def execute(self, context):
        ob = context.object
        bxdf_name = self.bxdf_name
        mat = bpy.data.materials.new(bxdf_name)
        ob.renderman.rman_material_override = mat
        mat.use_nodes = True
        nt = mat.node_tree

        output = nt.nodes.new('RendermanOutputNode')
        bxdf_node_name = rman_bl_nodes.__BL_NODES_MAP__[bxdf_name]        
        default = nt.nodes.new(bxdf_node_name)
        default.location = output.location
        default.location[0] -= 300
        nt.links.new(default.outputs[0], output.inputs[0])
        if self.bxdf_name == 'PxrLayerSurface':
            shadergraph_utils.create_pxrlayer_nodes(nt, default)

        output.inputs[3].hide = True
        default.update_mat(mat)
        ob.update_tag(refresh={'OBJECT'})

        return {"FINISHED"}  

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="Select a Material")
        col.prop(self, 'bxdf_name')      

    def invoke(self, context, event):

        wm = context.window_manager
        return wm.invoke_props_dialog(self)        

class PRMAN_OT_Force_Material_Refresh(bpy.types.Operator):
    bl_idname = "node.rman_force_material_refresh"
    bl_label = "Force Refresh"
    bl_description = "Force Material to Refresh during IPR. Use this if your material is not responding to edits."
    
    def execute(self, context):
        rr = RmanRender.get_rman_render()
        if rr.rman_is_live_rendering:
            mat = getattr(context, "material", None)
            if mat:
                rr.rman_scene_sync.update_material(mat)

        return {"FINISHED"} 

class PRMAN_OT_Force_Light_Refresh(bpy.types.Operator):
    bl_idname = "node.rman_force_light_refresh"
    bl_label = "Force Refresh"
    bl_description = "Force Light to Refresh during IPR. Use this if your light is not responding to edits."
    
    def execute(self, context):
        rr = RmanRender.get_rman_render()
        if rr.rman_is_live_rendering:
            ob = getattr(context, "light", context.active_object)
            if ob:
                rr.rman_scene_sync.update_light(ob)

        return {"FINISHED"}       
        
class PRMAN_OT_Force_LightFilter_Refresh(bpy.types.Operator):
    bl_idname = "node.rman_force_lightfilter_refresh"
    bl_label = "Force Refresh"
    bl_description = "Force Light Filter to Refresh during IPR. Use this if your light filter is not responding to edits."
    
    def execute(self, context):
        rr = RmanRender.get_rman_render()
        if rr.rman_is_live_rendering:
            ob = getattr(context, "light_filter", context.active_object)
            if ob:
                rr.rman_scene_sync.update_light_filter(ob)

        return {"FINISHED"}  

class PRMAN_OT_Add_Projection_Nodetree(bpy.types.Operator):
    bl_idname = "node.rman_add_projection_nodetree"
    bl_label = "New Projection"
    bl_description = "Attach a RenderMan projection plugin"
    bl_options = {"REGISTER"}

    def get_type_items(self, context):
        return get_projection_items()  

    proj_name: EnumProperty(items=get_type_items, name="Projection")    
    
    def execute(self, context):
        ob = context.object
        if ob.type != 'CAMERA':
            return {'FINISHED'}

        nt = bpy.data.node_groups.new(ob.data.name, 'ShaderNodeTree')
        output = nt.nodes.new('RendermanProjectionsOutputNode')
        ob.data.renderman.rman_nodetree = nt

        proj_node_name = rman_bl_nodes.__BL_NODES_MAP__[self.proj_name]    
        default = nt.nodes.new(proj_node_name)
        default.location = output.location
        default.location[0] -= 300
        nt.links.new(default.outputs[0], output.inputs[0])      
        ob.update_tag(refresh={'DATA'})  

        return {"FINISHED"}          

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="Select a Projection")
        col.prop(self, 'proj_name')      

    def invoke(self, context, event):

        wm = context.window_manager
        return wm.invoke_props_dialog(self)           

classes = [
    SHADING_OT_convert_all_renderman_nodetree,
    SHADING_OT_convert_cycles_to_renderman_nodetree,
    SHADING_OT_add_renderman_nodetree,
    PRMAN_OT_New_bxdf,
    PRMAN_OT_New_Material_Override,
    PRMAN_OT_Force_Material_Refresh,
    PRMAN_OT_Force_Light_Refresh,
    PRMAN_OT_Force_LightFilter_Refresh,
    PRMAN_OT_Add_Projection_Nodetree
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