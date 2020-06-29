from ..icons.icons import load_icons
from ..rman_render import RmanRender
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
        layout.operator_menu_enum(
                "object.rman_add_light", 'rman_light_name', text="RenderMan Light", icon='LIGHT')  
        layout.operator_menu_enum(
                "object.rman_add_light_filter", 'rman_lightfilter_name', text="RenderMan Light Filter", icon='LIGHT')   

        layout.menu('VIEW3D_MT_renderman_add_object_quadrics_menu')
     
        op = layout.operator('object.rman_add_rman_geo', text='RiVolume')
        op.rman_prim_type = 'RI_VOLUME'
        op.rman_default_name = 'RiVolume'

        op = layout.operator('object.rman_add_rman_geo', text='RIB Archive')
        op.rman_prim_type = 'DELAYED_LOAD_ARCHIVE'
        op.rman_default_name = 'RIB_Archive'        

        op = layout.operator('object.rman_add_rman_geo', text='RunProgram')
        op.rman_prim_type = 'PROCEDURAL_RUN_PROGRAM'
        op.rman_default_name = 'RiRunProgram'          

        op = layout.operator('object.rman_add_rman_geo', text='RiProcedural')
        op.rman_prim_type = 'DYNAMIC_LOAD_DSO'
        op.rman_default_name = 'RiProcedural'            
        
        op = layout.operator('object.rman_add_rman_geo', text='Brickmap Geometry')
        op.rman_prim_type = 'BRICKMAP'
        op.rman_default_name = 'BrickmapGeo'          

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
        op = layout.operator('object.rman_add_rman_geo', text='Sphere')
        op.rman_prim_type = 'QUADRIC'
        op.rman_quadric_type = 'SPHERE'

        op = layout.operator('object.rman_add_rman_geo', text='Cylinder')
        op.rman_prim_type = 'QUADRIC'
        op.rman_quadric_type = 'CYLINDER'

        op = layout.operator('object.rman_add_rman_geo', text='Cone')
        op.rman_prim_type = 'QUADRIC'
        op.rman_quadric_type = 'CONE'

        op = layout.operator('object.rman_add_rman_geo', text='Disk')
        op.rman_prim_type = 'QUADRIC'
        op.rman_quadric_type = 'DISK'      

        op = layout.operator('object.rman_add_rman_geo', text='Torus')
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
            layout.operator_menu_enum(
                "object.rman_add_bxdf", 'bxdf_name', text="Add New Material", icon='MATERIAL')         

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
    VIEW3D_MT_renderman_object_context_menu
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