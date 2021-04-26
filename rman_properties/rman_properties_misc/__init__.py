from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty, BoolVectorProperty

from ...rfb_utils import shadergraph_utils
from ...rfb_logger import rfb_log 
from ... import rman_config

import bpy

class RendermanUserTokenGroup(bpy.types.PropertyGroup):
    name: StringProperty(name="Name", default="")
    value: StringProperty(name="Value", default="")

class RendermanLightPointer(bpy.types.PropertyGroup):
    def validate_light_obj(self, ob):
        if shadergraph_utils.is_rman_light(ob, include_light_filters=True):
            return True
        return False

    name: StringProperty(name="name")
    light_ob: PointerProperty(type=bpy.types.Object, poll=validate_light_obj)               

class RendermanLightGroup(bpy.types.PropertyGroup):
    def update_name(self, context):
        for member in self.members:            
            member.light_ob.update_tag(refresh={'DATA'})

    def update_members_index(self, context):
        member = self.members[self.members_index]
        light_ob = member.light_ob
                
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        light_ob.select_set(True)
        context.view_layer.objects.active = light_ob        
        
    name: StringProperty(name="Group Name", update=update_name)
    members: CollectionProperty(type=RendermanLightPointer,
                                 name='Group Members')
    members_index: IntProperty(min=-1, default=-1,
                                 update=update_members_index) 

class RendermanObjectPointer(bpy.types.PropertyGroup):
    def update_name(self, context):
        if self.ob_pointer:
            self.ob_pointer.update_tag(refresh={'OBJECT'})        

    name: StringProperty(name="name", update=update_name)

    def update_ob_pointer(self, context):
        self.ob_pointer.update_tag(refresh={'OBJECT'})

    ob_pointer: PointerProperty(type=bpy.types.Object, update=update_ob_pointer)          

class RendermanGroup(bpy.types.PropertyGroup):
    def update_name(self, context):
        for member in self.members:
            member.ob_pointer.update_tag(refresh={'OBJECT'})

    def update_members_index(self, context):
        member = self.members[self.members_index]
        ob = member.ob_pointer
                
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob                  

    name: StringProperty(name="Group Name", update=update_name)
    members: CollectionProperty(type=RendermanObjectPointer,
                                 name='Group Members')
    members_index: IntProperty(min=-1, default=-1, update=update_members_index)

class LightLinking(bpy.types.PropertyGroup):

    def update_link(self, context):
        if self.light_ob.type == 'LIGHT':
            self.light_ob.update_tag(refresh={'DATA'})
        for member in self.members:
            ob = member.ob_pointer
            light_props = shadergraph_utils.get_rman_light_properties_group(self.light_ob)
            if light_props.renderman_light_role == 'RMAN_LIGHT':
                if self.illuminate == 'OFF':
                    subset = ob.renderman.rman_lighting_excludesubset.add()
                    subset.name = self.light_ob.name
                    subset.light_ob = self.light_ob
                else:
                    for j, subset in enumerate(ob.renderman.rman_lighting_excludesubset):
                        if subset.light_ob == self.light_ob:
                            ob.renderman.rman_lighting_excludesubset.remove(j)
                            break        
            ob.update_tag(refresh={'OBJECT'})

    def validate_light_obj(self, ob):
        if shadergraph_utils.is_rman_light(ob, include_light_filters=True):
            return True
        return False

    light_ob: PointerProperty(type=bpy.types.Object, poll=validate_light_obj)       

    members: CollectionProperty(type=RendermanObjectPointer,
                                 name='Group Members')    

    def update_members_index(self, context):
        member = self.members[self.members_index]
        ob = member.ob_pointer
                
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob                                      

    members_index: IntProperty(min=-1, default=-1, update=update_members_index)                                      

    illuminate: EnumProperty(
        name="Illuminate",
        update=update_link,
        items=[
              ('DEFAULT', 'Default', ''),
               ('ON', 'On', ''),
               ('OFF', 'Off', '')])    

class RendermanMeshPrimVar(bpy.types.PropertyGroup):
    name: StringProperty(
        name="Variable Name",
        description="Name of the exported renderman primitive variable")
    data_name: StringProperty(
        name="Data Name",
        description="Name of the Blender data to export as the primitive variable")
    data_source: EnumProperty(
        name="Data Source",
        description="Blender data type to export as the primitive variable",
        items=[('VERTEX_GROUP', 'Vertex Group', ''),
               ('VERTEX_COLOR', 'Vertex Color', ''),
               ('UV_TEXTURE', 'UV Texture', '')
               ]
    )
class RendermanMeshReferencePose(bpy.types.PropertyGroup):

    rman__Pref: FloatVectorProperty(name='rman__Pref',
                                default=(0,0, 0), size=3,
                                subtype="XYZ")

    rman__WPref: FloatVectorProperty(name='rman__WPref',
                                default=(0,0, 0), size=3,
                                subtype="XYZ")    
                                
    rman__Nref: FloatVectorProperty(name='rman__Nref',
                                default=(0,0, 0), size=3,
                                subtype="XYZ")    

    rman__WNref: FloatVectorProperty(name='rman__WNref',
                                default=(0,0, 0), size=3,
                                subtype="XYZ")                                    


class RendermanOpenVDBChannel(bpy.types.PropertyGroup):
    name: StringProperty(name="Channel Name")
    type: EnumProperty(name="Channel Type",
                        items=[
                            ('float', 'Float', ''),
                            ('vector', 'Vector', ''),
                            ('color', 'Color', ''),
                        ])

class RendermanAnimSequenceSettings(bpy.types.PropertyGroup):
    animated_sequence: BoolProperty(
        name="Animated Sequence",
        description="Interpret this archive as an animated sequence (converts #### in file path to frame number)",
        default=False)
    sequence_in: IntProperty(
        name="Sequence In Point",
        description="The first numbered file to use",
        default=1)
    sequence_out: IntProperty(
        name="Sequence Out Point",
        description="The last numbered file to use",
        default=24)
    blender_start: IntProperty(
        name="Blender Start Frame",
        description="The frame in Blender to begin playing back the sequence",
        default=1)

class Tab_CollectionGroup(bpy.types.PropertyGroup):

    #################
    #       Tab     #
    #################

    bpy.types.Scene.rm_ipr = BoolProperty(
        name="IPR settings",
        description="Show some useful setting for the Interactive Rendering",
        default=False)

    bpy.types.Scene.rm_render = BoolProperty(
        name="Render settings",
        description="Show some useful setting for the Rendering",
        default=False)

    bpy.types.Scene.rm_render_external = BoolProperty(
        name="Render settings",
        description="Show some useful setting for external rendering",
        default=False)

    bpy.types.Scene.rm_help = BoolProperty(
        name="Help",
        description="Show some links about RenderMan and the documentation",
        default=False)

    bpy.types.Scene.rm_env = BoolProperty(
        name="Envlight",
        description="Show some settings about the selected Env light",
        default=False)

    bpy.types.Scene.rm_area = BoolProperty(
        name="AreaLight",
        description="Show some settings about the selected Area Light",
        default=False)

    bpy.types.Scene.rm_daylight = BoolProperty(
        name="DayLight",
        description="Show some settings about the selected Day Light",
        default=False)

    bpy.types.Scene.prm_cam = BoolProperty(
        name="Renderman Camera",
        description="Show some settings about the camera",
        default=False)        

classes = [      
    RendermanUserTokenGroup,
    RendermanLightPointer,
    RendermanLightGroup,
    RendermanObjectPointer,
    RendermanGroup,
    LightLinking,
    RendermanMeshPrimVar,   
    RendermanMeshReferencePose,
    RendermanOpenVDBChannel,
    RendermanAnimSequenceSettings,
    Tab_CollectionGroup
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