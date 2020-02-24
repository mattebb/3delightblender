from .rman_ui_base import _RManPanelHeader
from .rman_ui_base import CollectionPanel
from .rman_ui_base import PRManButtonsPanel
from ..rman_utils.draw_utils import _draw_ui_from_rman_config
from ..rman_utils.draw_utils import _draw_props
from ..rman_constants import NODE_LAYOUT_SPLIT
from ..rman_render import RmanRender
from ..icons.icons import load_icons
from ..rman_utils import object_utils
from bpy.types import Panel
import bpy

class OBJECT_PT_renderman_object_render(CollectionPanel, Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "Shading and Visibility"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        if context.object.type == 'CAMERA':
            return False        
        return (context.object and rd.engine in {'PRMAN_RENDER'})

    def draw_item(self, layout, context, item):
        ob = context.object
        rm = bpy.data.objects[ob.name].renderman
        ll = rm.light_linking
        index = rm.light_linking_index

        col = layout.column()
        col.prop(item, "group")
        col.prop(item, "mode")

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout
        ob = context.object
        rm = ob.renderman

        col = layout.column()
        _draw_ui_from_rman_config('rman_properties_object', 'OBJECT_PT_renderman_object_render', context, layout, rm)           

class OBJECT_PT_renderman_object_raytracing(CollectionPanel, Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "Ray Tracing"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        if context.object.type == 'CAMERA':
            return False        
        return (context.object and rd.engine in {'PRMAN_RENDER'})

    def draw_item(self, layout, context, item):
        col = layout.column()
        col.prop(item, "group")
        col.prop(item, "mode")

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout
        ob = context.object
        rm = ob.renderman

        col = layout.column()
        _draw_ui_from_rman_config('rman_properties_object', 'OBJECT_PT_renderman_object_raytracing', context, layout, rm)        

class OBJECT_PT_renderman_object_geometry(Panel, CollectionPanel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "RenderMan Geometry"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        if context.object.type in ['LIGHT']:
            return False
        return (context.object and rd.engine in {'PRMAN_RENDER'})

    def draw_item(self, layout, context, item):
        col = layout.column()
        col.prop(item, "name")
        col.prop(item, "type")

    def draw_props(self, layout, context):
        ob = context.object
        rm = ob.renderman
        anim = rm.archive_anim_settings
        active = context.active_object
        rman_type = object_utils._detect_primitive_(active)

        rman_render = RmanRender.get_rman_render()
        rman_interactive_running = rman_render.rman_interactive_running  

        col = layout.column()
        col.enabled = not rman_interactive_running           

        _draw_ui_from_rman_config('rman_properties_object', 'OBJECT_PT_renderman_object_geometry', context, layout, rm)                       

        rman_archive = load_icons().get("archive_RIB")
        col = layout.column()
        col.enabled = not rman_interactive_running
        col.operator("export.export_rib_archive",
                    text="Export Object as RIB Archive.", icon_value=rman_archive.icon_id)     

        col = layout.column()

    def draw_camera_props(self, layout, context):
        ob = context.object
        rm = ob.renderman        
        col = layout.column()
        col.prop(rm, "motion_segments_override")
        col.active = rm.motion_segments_override
        col.prop(rm, "motion_segments")         

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout
 
        if context.object.type == 'CAMERA':
            self.draw_camera_props(layout, context)
        else:
            self.draw_props(layout, context)

class OBJECT_PT_renderman_object_geometry_quadric(Panel, CollectionPanel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "Quadric"
    bl_parent_id = "OBJECT_PT_renderman_object_geometry"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        rm = context.object.renderman
        if context.object.type in ['LIGHT']:
            return False
        if rm.primitive != 'QUADRIC':
            return False
        return (context.object and rd.engine in {'PRMAN_RENDER'})

    def draw_item(self, layout, context, item):
        col = layout.column()
        col.prop(item, "name")
        col.prop(item, "type")

    def draw(self, context):

        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout        
        ob = context.object
        rm = ob.renderman
        active = context.active_object
        rman_type = object_utils._detect_primitive_(active)

        rman_render = RmanRender.get_rman_render()
        rman_interactive_running = rman_render.rman_interactive_running  

        col = layout.column()
        col.enabled = not rman_interactive_running        
        col = layout.column(align = True)   
        _draw_ui_from_rman_config('rman_properties_object', 'OBJECT_PT_renderman_object_geometry_quadric', context, layout, rm)      

class OBJECT_PT_renderman_object_geometry_runprogram(Panel, CollectionPanel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "Run Program"
    bl_parent_id = "OBJECT_PT_renderman_object_geometry"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        rm = context.object.renderman
        if context.object.type in ['LIGHT']:
            return False
        if rm.primitive != 'PROCEDURAL_RUN_PROGRAM':
            return False
        return (context.object and rd.engine in {'PRMAN_RENDER'})

    def draw_item(self, layout, context, item):
        col = layout.column()
        col.prop(item, "name")
        col.prop(item, "type")

    def draw(self, context):

        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout        
        ob = context.object
        rm = ob.renderman
        active = context.active_object
        rman_type = object_utils._detect_primitive_(active)

        rman_render = RmanRender.get_rman_render()
        rman_interactive_running = rman_render.rman_interactive_running  

        col = layout.column()
        col.enabled = not rman_interactive_running        
        col = layout.column(align = True)   
        _draw_ui_from_rman_config('rman_properties_object', 'OBJECT_PT_renderman_object_geometry_runprogram', context, layout, rm)                     

class OBJECT_PT_renderman_object_geometry_dynamic_load_dso(Panel, CollectionPanel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "Dynamic Load DSO"
    bl_parent_id = "OBJECT_PT_renderman_object_geometry"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        rm = context.object.renderman
        if context.object.type in ['LIGHT']:
            return False
        if rm.primitive != 'DYNAMIC_LOAD_DSO':
            return False
        return (context.object and rd.engine in {'PRMAN_RENDER'})

    def draw_item(self, layout, context, item):
        col = layout.column()
        col.prop(item, "name")
        col.prop(item, "type")

    def draw(self, context):

        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout        
        ob = context.object
        rm = ob.renderman
        active = context.active_object
        rman_type = object_utils._detect_primitive_(active)

        rman_render = RmanRender.get_rman_render()
        rman_interactive_running = rman_render.rman_interactive_running  

        col = layout.column()
        col.enabled = not rman_interactive_running        
        col = layout.column(align = True)   
        _draw_ui_from_rman_config('rman_properties_object', 'OBJECT_PT_renderman_object_geometry_dynamic_load_dso', context, layout, rm)                     

class OBJECT_PT_renderman_object_geometry_rib_archive(Panel, CollectionPanel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "RIB Archive"
    bl_parent_id = "OBJECT_PT_renderman_object_geometry"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        rm = context.object.renderman
        if context.object.type in ['LIGHT']:
            return False
        if rm.primitive != 'DELAYED_LOAD_ARCHIVE':
            return False
        return (context.object and rd.engine in {'PRMAN_RENDER'})

    def draw_item(self, layout, context, item):
        col = layout.column()
        col.prop(item, "name")
        col.prop(item, "type")

    def draw(self, context):

        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout        
        ob = context.object
        rm = ob.renderman
        anim = rm.archive_anim_settings
        active = context.active_object
        rman_type = object_utils._detect_primitive_(active)

        rman_render = RmanRender.get_rman_render()
        rman_interactive_running = rman_render.rman_interactive_running  

        col = layout.column()
        col.enabled = not rman_interactive_running        
        col = layout.column(align = True)   
        _draw_ui_from_rman_config('rman_properties_object', 'OBJECT_PT_renderman_object_geometry_rib_archive', context, layout, rm)                     
        col.prop(anim, "animated_sequence")
        if anim.animated_sequence:
            col = layout.column(align = True)
            col.prop(anim, "blender_start")
            col.prop(anim, "sequence_in")
            col.prop(anim, "sequence_out")

class OBJECT_PT_renderman_object_geometry_openvdb(Panel, CollectionPanel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "OpenVDB"
    bl_parent_id = "OBJECT_PT_renderman_object_geometry"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        rm = context.object.renderman
        if context.object.type in ['LIGHT']:
            return False
        if rm.primitive != 'OPENVDB':
            return False
        return (context.object and rd.engine in {'PRMAN_RENDER'})

    def draw_item(self, layout, context, item):
        col = layout.column()
        col.prop(item, "name")
        col.prop(item, "type")

    def draw(self, context):

        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout        
        ob = context.object
        rm = ob.renderman
        active = context.active_object
        rman_type = object_utils._detect_primitive_(active)

        rman_render = RmanRender.get_rman_render()
        rman_interactive_running = rman_render.rman_interactive_running  

        col = layout.column()
        col.enabled = not rman_interactive_running        
        col = layout.column(align = True)   
        _draw_ui_from_rman_config('rman_properties_object', 'OBJECT_PT_renderman_object_geometry_openvdb', context, layout, rm)                     
        self._draw_collection(context, layout, rm, "",
                            "collection.add_remove", "object.renderman",
                            "openvdb_channels", "openvdb_channel_index")

class OBJECT_PT_renderman_object_geometry_points(Panel, CollectionPanel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "Points"
    bl_parent_id = "OBJECT_PT_renderman_object_geometry"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        rm = context.object.renderman
        if context.object.type in ['LIGHT']:
            return False
        if rm.primitive != 'POINTS':
            return False
        return (context.object and rd.engine in {'PRMAN_RENDER'})

    def draw_item(self, layout, context, item):
        col = layout.column()
        col.prop(item, "name")
        col.prop(item, "type")

    def draw(self, context):

        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout        
        ob = context.object
        rm = ob.renderman
        active = context.active_object
        rman_type = object_utils._detect_primitive_(active)

        rman_render = RmanRender.get_rman_render()
        rman_interactive_running = rman_render.rman_interactive_running  

        col = layout.column()
        col.enabled = not rman_interactive_running        
        col = layout.column(align = True)   
        _draw_ui_from_rman_config('rman_properties_object', 'OBJECT_PT_renderman_object_geometry_points', context, layout, rm)                     

class OBJECT_PT_renderman_object_geometry_volume(Panel, CollectionPanel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "Volume"
    bl_parent_id = "OBJECT_PT_renderman_object_geometry"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        rm = context.object.renderman
        if context.object.type in ['LIGHT']:
            return False
        if rm.primitive != 'RI_VOLUME':
            return False
        return (context.object and rd.engine in {'PRMAN_RENDER'})

    def draw_item(self, layout, context, item):
        col = layout.column()
        col.prop(item, "name")
        col.prop(item, "type")

    def draw(self, context):

        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout        
        ob = context.object
        rm = ob.renderman
        active = context.active_object
        rman_type = object_utils._detect_primitive_(active)

        rman_render = RmanRender.get_rman_render()
        rman_interactive_running = rman_render.rman_interactive_running  

        col = layout.column()
        col.enabled = not rman_interactive_running        
        col = layout.column(align = True)   
        _draw_ui_from_rman_config('rman_properties_object', 'OBJECT_PT_renderman_object_geometry_volume', context, layout, rm)                     


class OBJECT_PT_renderman_object_geometry_attributes(Panel, CollectionPanel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "Attributes"
    bl_parent_id = "OBJECT_PT_renderman_object_geometry"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        if context.object.type in ['LIGHT']:
            return False
        return (context.object and rd.engine in {'PRMAN_RENDER'})

    def draw_item(self, layout, context, item):
        col = layout.column()
        col.prop(item, "name")
        col.prop(item, "type")

    def draw(self, context):

        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout        
        ob = context.object
        rm = ob.renderman
        anim = rm.archive_anim_settings
        active = context.active_object
        rman_type = object_utils._detect_primitive_(active)

        rman_render = RmanRender.get_rman_render()
        rman_interactive_running = rman_render.rman_interactive_running  

        col = layout.column()
        col.enabled = not rman_interactive_running        
        col = layout.column(align = True)   
        _draw_ui_from_rman_config('rman_properties_object', 'OBJECT_PT_renderman_object_geometry_attributes', context, layout, rm)               

class OBJECT_PT_renderman_object_custom_primvars(CollectionPanel, Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "Custom Primvars"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        if context.object.type == 'CAMERA':
            return False        
        return (context.object and rd.engine in {'PRMAN_RENDER'})

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout
        ob = context.object
        rm = ob.renderman

        col = layout.column()
        row = col.row()
 
        _draw_ui_from_rman_config('rman_properties_object', 'OBJECT_PT_renderman_object_custom_primvars', context, layout, rm)     

class OBJECT_PT_renderman_object_custom_attributes(CollectionPanel, Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "Custom Attributes"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        if context.object.type == 'CAMERA':
            return False        
        return (context.object and rd.engine in {'PRMAN_RENDER'})

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout
        ob = context.object
        rm = ob.renderman

        col = layout.column()

        _draw_ui_from_rman_config('rman_properties_object', 'OBJECT_PT_renderman_object_custom_attributes', context, layout, rm)             

class OBJECT_PT_renderman_object_matteid(Panel, _RManPanelHeader):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "Matte ID"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        if context.object.type == 'CAMERA':
            return False        
        return (context.object and rd.engine in {'PRMAN_RENDER'})    

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        layout = self.layout
        ob = context.object
        rm = ob.renderman

        col = layout.column()
        _draw_ui_from_rman_config('rman_properties_object', 'OBJECT_PT_renderman_object_matteid', context, layout, rm)             

classes = [
    OBJECT_PT_renderman_object_geometry,
    OBJECT_PT_renderman_object_geometry_quadric,
    OBJECT_PT_renderman_object_geometry_runprogram,
    OBJECT_PT_renderman_object_geometry_dynamic_load_dso,
    OBJECT_PT_renderman_object_geometry_rib_archive,
    OBJECT_PT_renderman_object_geometry_openvdb,
    OBJECT_PT_renderman_object_geometry_points,
    OBJECT_PT_renderman_object_geometry_volume,
    OBJECT_PT_renderman_object_geometry_attributes,
    OBJECT_PT_renderman_object_render,
    OBJECT_PT_renderman_object_raytracing,
    OBJECT_PT_renderman_object_custom_primvars,
    OBJECT_PT_renderman_object_custom_attributes,
    OBJECT_PT_renderman_object_matteid    
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)        