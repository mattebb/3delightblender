import bpy
from .. import rman_bl_nodes
from ..icons.icons import load_icons
from ..rman_utils.scene_utils import EXCLUDED_OBJECT_TYPES
from bpy.props import EnumProperty

class PRMAN_OT_Add_Subdiv_Scheme(bpy.types.Operator):
    bl_idname = "object.add_subdiv_scheme"
    bl_label = "Add Subdiv Scheme"
    bl_description = ""
    bl_options = {"REGISTER"}

    def execute(self, context):
        for ob in context.selected_objects:
            if ob.type == 'MESH':
                rm = ob.data.renderman
                rm.rman_subdiv_scheme = 'catmull-clark'
        return {"FINISHED"}    

class PRMAN_OT_RM_Add_Light(bpy.types.Operator):
    bl_idname = "object.rman_add_light"
    bl_label = "Add RenderMan Light"
    bl_description = "Add a new RenderMan light to the scene"
    bl_options = {"REGISTER", "UNDO"}

    def get_type_items(self, context):
        icons = load_icons()
        rman_light_icon = icons.get("arealight")     
        items = []
        i = 0
        items.append(('PxrRectLight', 'PxrRectLight', '', rman_light_icon.icon_id, i))
        for n in rman_bl_nodes.__RMAN_LIGHT_NODES__:
            if n.name != 'PxrRectLight':
                i += 1
                items.append( (n.name, n.name, '', rman_light_icon.icon_id, i))
        return items

    rman_light_name: EnumProperty(items=get_type_items, name="Light Name")

    def execute(self, context):
        bpy.ops.object.light_add(type='AREA')
        bpy.ops.shading.add_renderman_nodetree(
        {'material': None, 'light': bpy.context.active_object.data}, idtype='light')
        bpy.context.object.data.renderman.renderman_light_shader = self.rman_light_name
        bpy.context.object.data.renderman.renderman_lock_light_type = True

        for ob in context.selected_objects:
            ob.name = self.rman_light_name
            ob.data.name = self.rman_light_name          

        return {"FINISHED"}

class PRMAN_OT_RM_Add_Light_Filter(bpy.types.Operator):
    bl_idname = "object.rman_add_light_filter"
    bl_label = "Add RenderMan Light Filter"
    bl_description = "Add a new RenderMan light filter to the scene"
    bl_options = {"REGISTER", "UNDO"}

    def get_type_items(self, context):
        items = []
        items.append(('PxrBlockerLightFilter', 'PxrBlockerLightFilter', ''))
        for n in rman_bl_nodes.__RMAN_LIGHTFILTER_NODES__:
            if n.name != 'PxrBlockerLightFilter':
                items.append( (n.name, n.name, ''))
        return items

    rman_lightfilter_name: EnumProperty(items=get_type_items, name="Light Filter Name")

    def execute(self, context):
        bpy.ops.object.light_add(type='AREA')
        bpy.ops.shading.add_renderman_nodetree(
        {'material': None, 'light': bpy.context.active_object.data}, idtype='light')
        bpy.context.object.data.renderman.renderman_light_filter_shader = self.rman_lightfilter_name
        bpy.context.object.data.renderman.renderman_light_role = 'RMAN_LIGHTFILTER'
        bpy.context.object.data.renderman.renderman_lock_light_type = True

        for ob in context.selected_objects:
            ob.name = self.rman_lightfilter_name
            ob.data.name = self.rman_lightfilter_name          

        return {"FINISHED"}        

class PRMAN_OT_Add_bxdf(bpy.types.Operator):
    bl_idname = "object.add_bxdf"
    bl_label = "Add BXDF"
    bl_description = "Add a new Bxdf to selected object"
    bl_options = {"REGISTER", "UNDO"}

    def get_type_items(self, context):
        icons = load_icons()
        rman_bxdf_icon = icons.get("pxrdisney")     
        items = []
        i = 0
        for i,n in enumerate(rman_bl_nodes.__RMAN_BXDF_NODES__):
            items.append( (n.name, n.name, '', rman_bxdf_icon.icon_id, i))
        return items        
    bxdf_name: EnumProperty(items=get_type_items, name="Bxdf Name")

    def execute(self, context):
        selection = bpy.context.selected_objects if hasattr(
            bpy.context, 'selected_objects') else []
        #selection = bpy.context.selected_objects
        bxdf_name = self.properties.bxdf_name
        mat = bpy.data.materials.new(bxdf_name)

        mat.use_nodes = True
        nt = mat.node_tree

        output = nt.nodes.new('RendermanOutputNode')
        default = nt.nodes.new('%sBxdfNode' % bxdf_name)
        default.location = output.location
        default.location[0] -= 300
        nt.links.new(default.outputs[0], output.inputs[0])

        if bxdf_name == 'PxrLayerSurface':
            mixer = nt.nodes.new("PxrLayerMixerPatternOSLNode")
            layer1 = nt.nodes.new("PxrLayerPatternOSLNode")
            layer2 = nt.nodes.new("PxrLayerPatternOSLNode")

            mixer.location = default.location
            mixer.location[0] -= 300

            layer1.location = mixer.location
            layer1.location[0] -= 300
            layer1.location[1] += 300

            layer2.location = mixer.location
            layer2.location[0] -= 300
            layer2.location[1] -= 300

            nt.links.new(mixer.outputs[0], default.inputs[0])
            nt.links.new(layer1.outputs[0], mixer.inputs['baselayer'])
            nt.links.new(layer2.outputs[0], mixer.inputs['layer1'])

        for obj in selection:
            if(obj.type not in EXCLUDED_OBJECT_TYPES):
                bpy.ops.object.material_slot_add()

                obj.material_slots[-1].material = mat

        return {"FINISHED"}        

classes = [
    PRMAN_OT_Add_Subdiv_Scheme,
    PRMAN_OT_RM_Add_Light,
    PRMAN_OT_RM_Add_Light_Filter,
    PRMAN_OT_Add_bxdf    
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
def unregister():
    
    for cls in classes:
        bpy.utils.unregister_class(cls)        