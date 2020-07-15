from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty, BoolVectorProperty

from ...rman_utils import filepath_utils
from ...rman_utils import property_utils
from ...rfb_logger import rfb_log 
from ... import rman_config

import bpy

class RendermanLightPointer(bpy.types.PropertyGroup):
    def validate_light_obj(self, ob):
        if ob.type == 'LIGHT' and ob.data.renderman.renderman_light_role in ['RMAN_LIGHT', 'RMAN_LIGHTFILTER']:
            return True
        return False

    name: StringProperty(name="name")
    light_ob: PointerProperty(type=bpy.types.Object, poll=validate_light_obj)               

class RendermanLightGroup(bpy.types.PropertyGroup):
    def update_name(self, context):
        for member in self.members:
            rm = member.light_ob.renderman
            light_shader = rm.get_light_node()
            light_shader.lightGroup = self.name
            member.light_ob.update_tag(refresh={'DATA'})

    name: StringProperty(name="Group Name", update=update_name)
    members: CollectionProperty(type=RendermanLightPointer,
                                 name='Group Members')
    members_index: IntProperty(min=-1, default=-1) 

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

    name: StringProperty(name="Group Name", update=update_name)
    members: CollectionProperty(type=RendermanObjectPointer,
                                 name='Group Members')
    members_index: IntProperty(min=-1, default=-1)

class LightLinking(bpy.types.PropertyGroup):

    def update_link(self, context):
        self.light_ob.update_tag(refresh={'DATA'})
        for member in self.members:
            ob = member.ob_pointer
            if self.light_ob.data.renderman.renderman_light_role == 'RMAN_LIGHT':
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
        if ob.type == 'LIGHT' and ob.data.renderman.renderman_light_role in ['RMAN_LIGHT', 'RMAN_LIGHTFILTER']:
            return True
        return False

    light_ob: PointerProperty(type=bpy.types.Object, poll=validate_light_obj)       

    members: CollectionProperty(type=RendermanObjectPointer,
                                 name='Group Members')    

    members_index: IntProperty(min=-1, default=-1)                                      

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

classes = [      
    RendermanLightPointer,
    RendermanLightGroup,
    RendermanObjectPointer,
    RendermanGroup,
    LightLinking,
    RendermanMeshPrimVar,   
    RendermanOpenVDBChannel,
    RendermanAnimSequenceSettings
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