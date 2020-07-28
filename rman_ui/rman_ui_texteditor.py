from ..rman_constants import RFB_ADDON_PATH
import bpy
import os

__TEMPLATE_BASE_PATH__ = os.path.join(RFB_ADDON_PATH, 'rman_text_templates')

submenu_classes = []

class TEXT_MT_templates_renderman_base(bpy.types.Menu):
    bl_label = "RenderMan"
    bl_idname = "OBJECT_MT_renderman_base_menu"

    def draw(self, context):
        global submenu_classes
        layout = self.layout
        for submenu in submenu_classes:
            layout.menu(submenu)

classes = [
    TEXT_MT_templates_renderman_base,
]

def register_renderman_template_submenus():
    global classes

    def draw(self, context):
        layout = self.layout  
        search_path = os.path.join(__TEMPLATE_BASE_PATH__, self.dir_name)
        self.path_menu(
            searchpaths=[search_path], 
            operator="text.open", 
            props_default={"internal": True}
        )                        

    for nm in os.listdir(__TEMPLATE_BASE_PATH__):
        typename = 'TEXT_MT_templates_renderman_%s' % nm
        ntype = type(typename, (bpy.types.Menu,), {})
        label = ' ' . join(nm.split('_'))
        ntype.bl_label = label
        ntype.bl_idname = 'OBJECT_MT_renderman_%s' % nm
        if "__annotations__" not in ntype.__dict__:
            setattr(ntype, "__annotations__", {})        
        ntype.draw = draw
        ntype.dir_name = nm
        classes.append(ntype)    
        submenu_classes.append(ntype.bl_idname)

def draw_item(self, context):
    layout = self.layout
    layout.menu(TEXT_MT_templates_renderman_base.bl_idname)

def register():
    register_renderman_template_submenus()

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TEXT_MT_templates.append(draw_item)    

def unregister():

    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass

    bpy.types.TEXT_MT_templates.remove(draw_item)        