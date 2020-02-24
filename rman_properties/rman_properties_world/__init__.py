import bpy
from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    IntProperty, CollectionProperty, EnumProperty, FloatProperty
from ..rman_properties_misc import RendermanMeshPrimVar     


class RendermanWorldSettings(bpy.types.PropertyGroup):

    def get_light_node(self):
        return getattr(self, self.light_node) if self.light_node else None

    def get_light_node_name(self):
        return self.light_node.replace('_settings', '')

    # do this to keep the nice viewport update
    def update_light_type(self, context):
        world = context.scene.world
        world_type = world.renderman.renderman_type
        if world_type == 'NONE':
            return
        # use pxr area light for everything but env, sky
        light_shader = 'PxrDomeLight'
        if world_type == 'SKY':
            light_shader = 'PxrEnvDayLight'

        self.light_node = light_shader + "_settings"

    def update_vis(self, context):
        light = context.scene.world

    renderman_type: EnumProperty(
        name="World Type",
        update=update_light_type,
        items=[
            ('NONE', 'None', 'No World'),
            ('ENV', 'Environment', 'Environment Light'),
            ('SKY', 'Sky', 'Simulated Sky'),
        ],
        default='NONE'
    )

    use_renderman_node: BoolProperty(
        name="Use RenderMans World Node",
        description="Will enable RenderMan World Nodes, opening more options",
        default=False, update=update_light_type)

    light_node: StringProperty(
        name="Light Node",
        default='')

    light_primary_visibility: BoolProperty(
        name="Light Primary Visibility",
        description="Camera visibility for this light",
        update=update_vis,
        default=True)

    shadingrate: FloatProperty(
        name="Light Shading Rate",
        description="Shading Rate for lights.  Keep this high unless banding or pixellation occurs on detailed light maps",
        default=100.0)

    # illuminate
    illuminates_by_default: BoolProperty(
        name="Illuminates by default",
        description="Illuminates objects by default",
        default=True)

classes = [         
    RendermanWorldSettings
]           

def register():

    for cls in classes:
        bpy.utils.register_class(cls)  

    bpy.types.World.renderman = PointerProperty(
        type=RendermanWorldSettings, name="Renderman World Settings")

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)