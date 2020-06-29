from ..icons.icons import load_icons
from ..rman_render import RmanRender
from .. import rman_bl_nodes
from ..rman_operators.rman_operators_utils import get_bxdf_items, get_light_items, get_lightfilter_items
from bpy.types import Menu
import bpy

class VIEW3D_MT_renderman_add_object_menu(Menu):
    bl_label = "RenderMan"
    bl_idname = "VIEW3D_MT_renderman_add_object_menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        icons = load_icons()

        rman_icon = icons.get('rman_arealight.png')
        layout.menu('VIEW3D_MT_RM_Add_Light_Menu', icon_value=rman_icon.icon_id)

        rman_icon = icons.get('rman_lightfilter.png')
        layout.menu('VIEW3D_MT_RM_Add_LightFilter_Menu', icon_value=rman_icon.icon_id)        

        layout.separator()
        layout.menu('VIEW3D_MT_renderman_add_object_quadrics_menu', icon='MESH_UVSPHERE')
        layout.separator()

        layout.separator()
        rman_icon = icons.get('out_PxrVolume.png')
        layout.menu('VIEW3D_MT_renderman_add_object_volumes_menu', icon_value=rman_icon.icon_id)
        layout.separator()        
     
        rman_icon = icons.get("rman_CreateArchive.png")
        op = layout.operator('object.rman_add_rman_geo', text='RIB Archive', icon_value=rman_icon.icon_id)
        op.rman_prim_type = 'DELAYED_LOAD_ARCHIVE'
        op.rman_default_name = 'RIB_Archive'    
        op.rman_open_filebrowser = True    

        op = layout.operator('object.rman_add_rman_geo', text='RunProgram')
        op.rman_prim_type = 'PROCEDURAL_RUN_PROGRAM'
        op.rman_default_name = 'RiRunProgram'          
        op.rman_open_filebrowser = True

        op = layout.operator('object.rman_add_rman_geo', text='RiProcedural')
        op.rman_prim_type = 'DYNAMIC_LOAD_DSO'
        op.rman_default_name = 'RiProcedural'            
        op.rman_open_filebrowser = True
        
        op = layout.operator('object.rman_add_rman_geo', text='Brickmap Geometry')
        op.rman_prim_type = 'BRICKMAP'
        op.rman_default_name = 'BrickmapGeo'          
        op.rman_open_filebrowser = True

class VIEW3D_MT_renderman_add_object_volumes_menu(Menu):
    bl_label = "Volumes"
    bl_idname = "VIEW3D_MT_renderman_add_object_volumes_menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        icons = load_icons()
        rman_icon = icons.get('rman_openvdb.png')
        op = layout.operator('object.rman_add_rman_geo', text='Import OpenVDB', icon_value=rman_icon.icon_id)
        op.rman_prim_type = ''
        op.bl_prim_type = 'VOLUME'
        op.rman_default_name = 'OpenVDB'    
        op.rman_open_filebrowser = True 

        rman_icon = icons.get('out_PxrVolume.png')
        op = layout.operator('object.rman_add_rman_geo', text='Volume Box', icon_value=rman_icon.icon_id)
        op.rman_prim_type = 'RI_VOLUME'
        op.rman_default_name = 'RiVolume'                         


class VIEW3D_MT_renderman_add_object_quadrics_menu(Menu):
    bl_label = "Quadrics"
    bl_idname = "VIEW3D_MT_renderman_add_object_quadrics_menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        icons = load_icons()
        op = layout.operator('object.rman_add_rman_geo', text='Sphere', icon='MESH_UVSPHERE')
        op.rman_prim_type = 'QUADRIC'
        op.rman_quadric_type = 'SPHERE'

        op = layout.operator('object.rman_add_rman_geo', text='Cylinder', icon='MESH_CYLINDER')
        op.rman_prim_type = 'QUADRIC'
        op.rman_quadric_type = 'CYLINDER'

        op = layout.operator('object.rman_add_rman_geo', text='Cone', icon='MESH_CONE')
        op.rman_prim_type = 'QUADRIC'
        op.rman_quadric_type = 'CONE'

        op = layout.operator('object.rman_add_rman_geo', text='Disk', icon='MESH_CIRCLE')
        op.rman_prim_type = 'QUADRIC'
        op.rman_quadric_type = 'DISK'      

        op = layout.operator('object.rman_add_rman_geo', text='Torus', icon='MESH_TORUS')
        op.rman_prim_type = 'QUADRIC'
        op.rman_quadric_type = 'TORUS'                                 

class VIEW3D_MT_renderman_object_context_menu(Menu):
    bl_label = "RenderMan"
    bl_idname = "VIEW3D_MT_renderman_object_context_menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        icons = load_icons()
        rman_render = RmanRender.get_rman_render()
        is_rman_interactive_running = rman_render.rman_interactive_running     
        selected_objects = []
        selected_light_objects = []
        if context.selected_objects:
            for obj in context.selected_objects:
                if obj.type not in ['CAMERA', 'LIGHT', 'SPEAKER']:
                    selected_objects.append(obj)
                elif obj.type == 'LIGHT' and obj.data.renderman.renderman_light_role == 'RMAN_LIGHT':
                    selected_light_objects.append(obj)

        if not selected_objects and not selected_light_objects:
            column = layout.column()
            column.enabled = not is_rman_interactive_running
            row = column.row()
            rman_rib = icons.get('rman_rib_small.png')
            row.operator("rman.open_scene_rib", text='View RIB', icon_value=rman_rib.icon_id)            
            return

        if selected_light_objects:
            layout.operator_menu_enum(
                    "object.rman_add_light_filter", 'rman_lightfilter_name', text="Attach New Light Filter", icon='LIGHT')              

        layout.separator()
        if selected_objects:
            # Add Bxdf             
            rman_icon = icons.get('out_PxrSurface.png')
            layout.menu('VIEW3D_MT_RM_Add_bxdf_Menu', text='Add New Material', icon_value=rman_icon.icon_id)           

            # Make Selected Geo Emissive
            rman_meshlight = icons.get("out_PxrMeshLight.png")
            layout.operator("object.rman_create_meshlight", text="Convert to Mesh Light",
                            icon_value=rman_meshlight.icon_id)

            # Add Subdiv Sheme
            rman_subdiv = icons.get("rman_subdiv.png")
            layout.operator("object.rman_add_subdiv_scheme",
                            text="Convert to Subdiv", icon_value=rman_subdiv.icon_id)

            # Add/Create RIB Box /
            # Create Archive node
            rman_archive = icons.get("rman_CreateArchive.png")
            layout.operator("export.export_rib_archive",
                            icon_value=rman_archive.icon_id)

        # Diagnose        
        layout.separator()
        column = layout.column()
        column.enabled = not is_rman_interactive_running
        row = column.row()
        rman_rib = icons.get('rman_rib_small.png')
        row.operator("rman.open_scene_rib", text='View RIB', icon_value=rman_rib.icon_id)
        if selected_objects:
            row = column.row()
            row.operator("rman.open_selected_rib", text='View Selected RIB', icon_value=rman_rib.icon_id)    

class VIEW3D_MT_RM_Add_Light_Menu(bpy.types.Menu):
    bl_label = "Light"
    bl_idname = "VIEW3D_MT_RM_Add_Light_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        icons = load_icons()

        for nm, nm, description, icon, i in get_light_items():
            op = layout.operator('object.rman_add_light', text=nm, icon_value=icon)
            op.rman_light_name = nm                                      

class VIEW3D_MT_RM_Add_LightFilter_Menu(bpy.types.Menu):
    bl_label = "Light Filter"
    bl_idname = "VIEW3D_MT_RM_Add_LightFilter_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        icons = load_icons()

        for nm, nm, description, icon, i in get_lightfilter_items():
            op = layout.operator('object.rman_add_light_filter', text=nm, icon_value=icon)
            op.rman_lightfilter_name = nm                                   

class VIEW3D_MT_RM_Add_bxdf_Menu(bpy.types.Menu):
    bl_label = "Material"
    bl_idname = "VIEW3D_MT_RM_Add_bxdf_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        icons = load_icons()

        for nm, nm, description, icon, i in get_bxdf_items():
            op = layout.operator('object.rman_add_bxdf', text=nm, icon_value=icon)
            op.bxdf_name = nm         

def rman_add_object_menu(self, context):

    rd = context.scene.render
    if rd.engine != 'PRMAN_RENDER':
        return    

    layout = self.layout
    icons = load_icons()
    rman_icon = icons.get("rman_blender.png")    
    layout.menu('VIEW3D_MT_renderman_add_object_menu', text='RenderMan', icon_value=rman_icon.icon_id)

def rman_object_context_menu(self, context):

    rd = context.scene.render
    if rd.engine != 'PRMAN_RENDER':
        return    

    layout = self.layout
    icons = load_icons()
    rman_icon = icons.get("rman_blender.png")    
    layout.menu('VIEW3D_MT_renderman_object_context_menu', text='RenderMan', icon_value=rman_icon.icon_id)    

classes = [
    VIEW3D_MT_renderman_add_object_menu,
    VIEW3D_MT_renderman_add_object_quadrics_menu,
    VIEW3D_MT_renderman_add_object_volumes_menu,
    VIEW3D_MT_renderman_object_context_menu,
    VIEW3D_MT_RM_Add_Light_Menu,
    VIEW3D_MT_RM_Add_LightFilter_Menu,
    VIEW3D_MT_RM_Add_bxdf_Menu
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)  

    bpy.types.VIEW3D_MT_add.prepend(rman_add_object_menu)
    bpy.types.VIEW3D_MT_object_context_menu.prepend(rman_object_context_menu)


def unregister():
    bpy.types.VIEW3D_MT_add.remove(rman_add_object_menu)
    bpy.types.VIEW3D_MT_object_context_menu.remove(rman_object_context_menu)

    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass