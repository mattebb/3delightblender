from ..icons.icons import load_icons
from ..rman_render import RmanRender
from bpy.types import Menu
import bpy

class NODE_MT_renderman_add_object_menu(Menu):
    bl_label = "RenderMan"
    bl_idname = "NODE_MT_renderman_add_object_menu"

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

        rman_render = RmanRender.get_rman_render()
        is_rman_interactive_running = rman_render.rman_interactive_running     
        selected_objects = []
        if context.selected_objects:
            for obj in context.selected_objects:
                if obj.type not in ['CAMERA', 'LIGHT', 'SPEAKER']:
                    selected_objects.append(obj)

        if selected_objects:
            layout.separator()
            layout.label(text="Seleced Objects:")

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
        layout.label(text='Diagnose')
        column = layout.column()
        column.enabled = not is_rman_interactive_running
        row = column.row()
        rman_rib = icons.get('rman_rib_small.png')
        row.operator("rman.open_scene_rib", text='View RIB', icon_value=rman_rib.icon_id)
        if selected_objects:
            row = column.row()
            row.operator("rman.open_selected_rib", text='View Selected RIB', icon_value=rman_rib.icon_id)                         


def rman_add_object_menu(self, context):

    layout = self.layout
    icons = load_icons()
    rman_icon = icons.get("rman_blender.png")    
    layout.menu('NODE_MT_renderman_add_object_menu', text='RenderMan', icon_value=rman_icon.icon_id)

classes = [
    NODE_MT_renderman_add_object_menu
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)  

    bpy.types.VIEW3D_MT_add.prepend(rman_add_object_menu)


def unregister():
    bpy.types.VIEW3D_MT_add.remove(rman_add_object_menu)

    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass