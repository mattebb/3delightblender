import bpy
import os
import subprocess
from .. import rman_bl_nodes
from ..icons.icons import load_icons
from ..rman_utils.scene_utils import EXCLUDED_OBJECT_TYPES
from ..rman_utils.filepath_utils import find_it_path, find_local_queue
from bpy.props import EnumProperty

class PRMAN_OT_RM_Add_Subdiv_Scheme(bpy.types.Operator):
    bl_idname = "object.rman_add_subdiv_scheme"
    bl_label = "Convert to Subdiv"
    bl_description = "Convert selected object to a subdivision surface"
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
        rman_light_icon = icons.get("out_PxrRectLight.png")
        items = []
        i = 0
        items.append(('PxrRectLight', 'PxrRectLight', '', rman_light_icon.icon_id, i))
        for n in rman_bl_nodes.__RMAN_LIGHT_NODES__:
            if n.name != 'PxrRectLight':
                i += 1
                light_icon = icons.get("out_%s.png" % n.name, None)
                if not light_icon:
                    items.append( (n.name, n.name, '', rman_light_icon.icon_id, i))
                else:
                    items.append( (n.name, n.name, '', light_icon.icon_id, i))
        return items

    rman_light_name: EnumProperty(items=get_type_items, name="Light Name")

    def execute(self, context):
        bpy.ops.object.light_add(type='AREA')
        bpy.context.object.data.renderman.renderman_lock_light_type = True
        bpy.context.object.data.use_nodes = True

        for ob in context.selected_objects:
            ob.name = self.rman_light_name
            ob.data.name = self.rman_light_name    

        nt = bpy.context.object.data.node_tree
        output = nt.nodes.new('RendermanOutputNode')                 
        default = nt.nodes.new('%sLightNode' % self.rman_light_name)
        default.location = output.location
        default.location[0] -= 300
        nt.links.new(default.outputs[0], output.inputs[1])           
        output.inputs[0].hide = True
        output.inputs[2].hide = True
        output.inputs[3].hide = True    

        bpy.context.object.data.renderman.renderman_light_role = 'RMAN_LIGHT'          

        return {"FINISHED"}

class PRMAN_OT_RM_Add_Light_Filter(bpy.types.Operator):
    bl_idname = "object.rman_add_light_filter"
    bl_label = "Add RenderMan Light Filter"
    bl_description = "Add a new RenderMan light filter to the scene"
    bl_options = {"REGISTER", "UNDO"}

    def get_type_items(self, context):
        icons = load_icons()
        items = []
        i = 0
        rman_light_icon = icons.get("out_PxrBlockerLightFilter.png")
        items.append(('PxrBlockerLightFilter', 'PxrBlockerLightFilter', '', rman_light_icon.icon_id, i))
        for n in rman_bl_nodes.__RMAN_LIGHTFILTER_NODES__:
            if n.name != 'PxrBlockerLightFilter':
                i += 1
                light_icon = icons.get("out_%s.png" % n.name, None)
                if not light_icon:                
                    items.append( (n.name, n.name, '', rman_light_icon.icon_id, i))
                else:
                    items.append( (n.name, n.name, '', light_icon.icon_id, i))
        return items

    rman_lightfilter_name: EnumProperty(items=get_type_items, name="Light Filter Name")

    def execute(self, context):
        bpy.ops.object.light_add(type='AREA')
        bpy.context.object.data.renderman.renderman_lock_light_type = True
        bpy.context.object.data.use_nodes = True

        for ob in context.selected_objects:
            ob.name = self.rman_lightfilter_name
            ob.data.name = self.rman_lightfilter_name               

        nt = bpy.context.object.data.node_tree
        output = nt.nodes.new('RendermanOutputNode')
        default = nt.nodes.new('%sLightfilterNode' % self.rman_lightfilter_name)
        default.location = output.location
        default.location[0] -= 300
        nt.links.new(default.outputs[0], output.inputs[3])   
        output.inputs[0].hide = True
        output.inputs[1].hide = True
        output.inputs[2].hide = True   

        bpy.context.object.data.renderman.renderman_light_role = 'RMAN_LIGHTFILTER'

        return {"FINISHED"}        

class PRMAN_OT_RM_Add_bxdf(bpy.types.Operator):
    bl_idname = "object.rman_add_bxdf"
    bl_label = "Add BXDF"
    bl_description = "Add a new Bxdf to selected object"
    bl_options = {"REGISTER", "UNDO"}

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
    bxdf_name: EnumProperty(items=get_type_items, name="Bxdf Name")

    def execute(self, context):
        selection = bpy.context.selected_objects if hasattr(
            bpy.context, 'selected_objects') else []
        bxdf_name = self.properties.bxdf_name
        mat = bpy.data.materials.new(bxdf_name)

        mat.use_nodes = True
        nt = mat.node_tree

        output = nt.nodes.new('RendermanOutputNode')
        default = nt.nodes.new('%sBxdfNode' % bxdf_name)
        default.location = output.location
        default.location[0] -= 300
        nt.links.new(default.outputs[0], output.inputs[0])
        output.inputs[3].hide = True  

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

class PRMAN_OT_RM_Create_MeshLight(bpy.types.Operator):
    bl_idname = "object.rman_create_meshlight"
    bl_label = "Create Mesh Light"
    bl_description = "Convert selected object to a mesh light"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        selection = bpy.context.selected_objects
        mat = bpy.data.materials.new("PxrMeshLight")

        mat.use_nodes = True
        nt = mat.node_tree

        output = nt.nodes.new('RendermanOutputNode')
        geoLight = nt.nodes.new('PxrMeshLightLightNode')
        geoLight.location[0] -= 300
        geoLight.location[1] -= 420
        if(output is not None):
            nt.links.new(geoLight.outputs[0], output.inputs[1])

        # add PxrBlack Bxdf
        default = nt.nodes.new('PxrBlackBxdfNode')
        default.location = output.location
        default.location[0] -= 300
        if (default is not None):
            nt.links.new(default.outputs[0], output.inputs[0])

        for obj in selection:
            if(obj.type not in EXCLUDED_OBJECT_TYPES):
                bpy.ops.object.material_slot_add()
                obj.material_slots[-1].material = mat
        return {"FINISHED"}

class PRMAN_OT_Renderman_start_it(bpy.types.Operator):
    bl_idname = 'rman.start_it'
    bl_label = "Start 'it'"
    bl_description = "Start RenderMan's it"

    def execute(self, context):
        it_path = find_it_path()
        if not it_path:
            self.report({"ERROR"},
                        "Could not find 'it'.")
        else:
            environ = os.environ.copy()
            subprocess.Popen([it_path], env=environ, shell=True)
        return {'FINISHED'}        

class PRMAN_OT_Renderman_start_localqueue(bpy.types.Operator):
    bl_idname = 'rman.start_localqueue'
    bl_label = "Start Local Queue"
    bl_description = "Start LocalQueue"

    def execute(self, context):
        lq_path = find_local_queue()
        if not lq_path:
            self.report({"ERROR"},
                        "Could not find LocalQueue.")
        else:
            environ = os.environ.copy()
            subprocess.Popen([lq_path], env=environ, shell=True)
        return {'FINISHED'}        

class PRMAN_OT_Select_Cameras(bpy.types.Operator):
    bl_idname = "object.select_cameras"
    bl_label = "Select Cameras"

    Camera_Name: bpy.props.StringProperty(default="")

    def execute(self, context):

        bpy.ops.object.select_all(action='DESELECT')
        bpy.data.objects[self.Camera_Name].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects[self.Camera_Name]

        return {'FINISHED'}


class PRMAN_MT_Camera_List_Menu(bpy.types.Menu):
    #bl_idname = "object.camera_list_menu"
    bl_label = "Camera list"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        cameras = [
            obj for obj in bpy.context.scene.objects if obj.type == "CAMERA"]

        if len(cameras):
            for cam in cameras:
                name = cam.name
                op = layout.operator(
                    "object.select_cameras", text=name, icon='CAMERA_DATA')
                op.Camera_Name = name

        else:
            layout.label(text="No Camera in the Scene")

class PRMAN_OT_Deletecameras(bpy.types.Operator):
    bl_idname = "object.delete_cameras"
    bl_label = "Delete Cameras"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        type_camera = bpy.context.object.data.type
        bpy.ops.object.delete()

        camera = [obj for obj in bpy.context.scene.objects if obj.type ==
                  "CAMERA" and obj.data.type == type_camera]

        if len(camera):
            camera[0].select = True
            bpy.context.view_layer.objects.active = camera[0]
            return {"FINISHED"}

        else:
            return {"FINISHED"}


class PRMAN_OT_AddCamera(bpy.types.Operator):
    bl_idname = "object.add_prm_camera"
    bl_label = "Add Camera"
    bl_description = "Add a Camera in the Scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        bpy.context.space_data.lock_camera = False

        bpy.ops.object.camera_add()

        bpy.ops.view3d.object_as_camera()

        bpy.ops.view3d.view_camera()

        bpy.ops.view3d.camera_to_view()

        bpy.context.object.data.clip_end = 10000
        bpy.context.object.data.lens = 85

        return {"FINISHED"}

class PRMAN_OT_Renderman_open_stats(bpy.types.Operator):
    bl_idname = 'rman.open_stats'
    bl_label = "Open Frame Stats"
    bl_description = "Open Current Frame stats file"

    def execute(self, context):
        scene = context.scene
        rm = scene.renderman        
        output_dir = string_utils.expand_string(rm.path_rib_output, 
                                                frame=scene.frame_current, 
                                                asFilePath=True)  
        output_dir = os.path.dirname(output_dir)            
        bpy.ops.wm.url_open(
            url="file://" + os.path.join(output_dir, 'stats.%04d.xml' % scene.frame_current))
        return {'FINISHED'}

classes = [
    PRMAN_OT_RM_Add_Subdiv_Scheme,
    PRMAN_OT_RM_Add_Light,
    PRMAN_OT_RM_Add_Light_Filter,
    PRMAN_OT_RM_Add_bxdf,
    PRMAN_OT_RM_Create_MeshLight,
    PRMAN_OT_Renderman_start_it,
    PRMAN_OT_Renderman_start_localqueue,
    PRMAN_OT_Select_Cameras,
    PRMAN_MT_Camera_List_Menu,
    PRMAN_OT_Deletecameras,
    PRMAN_OT_AddCamera,    
    PRMAN_OT_Renderman_open_stats  
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
def unregister():
    
    for cls in classes:
        bpy.utils.unregister_class(cls)        