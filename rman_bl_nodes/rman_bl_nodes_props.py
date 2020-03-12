import bpy
from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty, BoolVectorProperty
from .. import rman_bl_nodes
from ..icons.icons import load_icons

class RendermanPluginSettings(bpy.types.PropertyGroup):
    pass

class RendermanLightFilter(bpy.types.PropertyGroup):

    def get_filters(self, context):
        obs = context.scene.objects
        items = [('None', 'Not Set', 'Not Set')]
        for o in obs:
            if o.type == 'LIGHT' and o.data.renderman.renderman_light_role == 'RMAN_LIGHTFILTER':
                items.append((o.name, o.name, o.name))
        return items

    def update_name(self, context):
        self.name = self.filter_name

    name: StringProperty(default='SET FILTER')
    filter_name: EnumProperty(
        name="Linked Filter:", items=get_filters, update=update_name)

class RendermanLightSettings(bpy.types.PropertyGroup):

    def get_light_node(self):
        '''
        Get the light shader node
        '''
        return getattr(self, self.light_node, None)

    def get_light_node_name(self):
        '''
        Get light shader name
        '''
        return self.light_node.replace('_settings', '')
    light_node: StringProperty(
        name="Light Node",
        default='')

    # thes are used for light filters
    color_ramp_node: StringProperty(default='')
    float_ramp_node: StringProperty(default='')

    def update_vis(self, context):
        light = self.id_data

    use_renderman_node: BoolProperty(
        name="Use RenderMans Light Node",
        description="Will enable RenderMan light Nodes, opening more options",
        default=False
    )

    def renderman_light_role_update(self, context):
        if self.renderman_light_role == 'RMAN_LIGHT':
            self.renderman_light_shader_update(context)
        else:
            self.renderman_light_filter_shader_update(context)

    renderman_light_role: EnumProperty(
        name="Light Type",
        items=[('RMAN_LIGHT', 'Light', 'RenderMan Light'),
               ('RMAN_LIGHTFILTER', 'Filter', 'RenderMan Light Filter')],
        update=renderman_light_role_update,
        default='RMAN_LIGHT'        
    )    

    def renderman_light_shader_update(self, context):
        light = self.id_data        
        light_shader = self.renderman_light_shader
        self.light_node = light_shader + "_settings"

        # update the Blender native light type
        if light_shader in ['PxrDomeLight', 'PxrEnvDayLight']:
            light.type = 'POINT'
        elif light_shader == 'PxrDistantLight':
            light.type = 'SUN'
        elif light_shader == 'PxrSphereLight':
            light.type = 'AREA'
            light.shape = 'ELLIPSE'
            light.size = 1.0
            light.size_y = 1.0
        elif light_shader == 'PxrDiskLight':
            light.type = 'AREA'
            light.shape = 'DISK'
            light.size = 1.0
            light.size_y = 1.0      
        else:
            light.type = 'AREA'
            light.shape = 'RECTANGLE'
            light.size = 1.0
            light.size_y = 1.0              

    def get_rman_light_shaders(self, context):
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

    renderman_light_shader: EnumProperty(
        name="RenderMan Light",
        items=get_rman_light_shaders,
        update=renderman_light_shader_update
    )

    def renderman_light_filter_shader_update(self, context):
        light = self.id_data
        light_shader = self.renderman_light_filter_shader
        self.light_node = light_shader + "_settings"

        light.type = 'AREA'
        light.shape = 'RECTANGLE'
        light.size = 1.0
        light.size_y = 1.0      
          
    def get_rman_light_filter_shaders(self, context):
        items = []
        items.append(('PxrBlockerLightFilter', 'PxrBlockerLightFilter', ''))
        for n in rman_bl_nodes.__RMAN_LIGHTFILTER_NODES__:
            if n.name != 'PxrBlockerLightFilter':
                items.append( (n.name, n.name, ''))
        return items

    renderman_light_filter_shader: EnumProperty(
        name="RenderMan Light Filter",
        items=get_rman_light_filter_shaders,
        update=renderman_light_filter_shader_update
    )    

    light_filters: CollectionProperty(
        type=RendermanLightFilter
    )
    light_filters_index: IntProperty(min=-1, default=-1)

    light_primary_visibility: BoolProperty(
        name="Light Primary Visibility",
        description="Camera visibility for this light",
        update=update_vis,
        default=True)

    mute: BoolProperty(
        name="Mute",
        description="Turn off this light",
        default=False)

    def update_solo(self, context):
        light = self.id_data
        scene = context.scene

        # if the scene solo is on already find the old one and turn off
        scene.renderman.solo_light = self.solo
        if self.solo:
            if scene.renderman.solo_light:
                for ob in scene.objects:
                    if ob.type == 'LIGHT' and ob.data.renderman != self and ob.data.renderman.solo:
                        ob.data.renderman.solo = False
                        break

    solo: BoolProperty(
        name="Solo",
        update=update_solo,
        description="Turn on only this light",
        default=False)

    renderman_lock_light_type: BoolProperty(
        name="Lock Type",
        default=False,
        description="Lock from changing light shader and light role."
    )

    # OLD PROPERTIES

    shadingrate: FloatProperty(
        name="Light Shading Rate",
        description="Shading Rate for lights.  Keep this high unless banding or pixellation occurs on detailed light maps",
        default=100.0)

    # illuminate
    illuminates_by_default: BoolProperty(
        name="Illuminates by default",
        description="The light illuminates objects by default",
        default=True)    

    renderman_type: EnumProperty(
        name="Light Type",
        items=[
               ('AREA', 'Light', 'Area Light'),
               ('ENV', 'Dome', 'Dome Light'),
               ('SKY', 'Env Daylight', 'Simulated Sky'),
               ('DIST', 'Distant', 'Distant Light'),
               ('SPOT', 'Spot', 'Spot Light'),
               ('POINT', 'Point', 'Point Light'),
               ('PORTAL', 'Portal', 'Portal Light'),
               ('FILTER', 'Filter', 'RenderMan Light Filter'),
               ('UPDATED', 'UPDATED', '')],
        default='UPDATED'
    )

    area_shape: EnumProperty(
        name="Area Shape",
        items=[('rect', 'Rectangle', 'Rectangle'),
               ('disk', 'Disk', 'Disk'),
               ('sphere', 'Sphere', 'Sphere'), 
               ('cylinder', 'Cylinder', 'Cylinder')],
        default='rect'
    )

    filter_type: EnumProperty(
        name="Area Shape",
        items=[('barn', 'Barn', 'Barn'),
               ('blocker', 'Blocker', 'Blocker'),
               #('combiner', 'Combiner', 'Combiner'),
               ('cookie', 'Cookie', 'Cookie'),
               ('gobo', 'Gobo', 'Gobo'),
               ('intmult', 'Multiply', 'Multiply'),
               ('ramp', 'Ramp', 'Ramp'),
               ('rod', 'Rod', 'Rod')
               ],
        default='blocker'
    )        

class RendermanDisplayFilterSettings(bpy.types.PropertyGroup):

    def get_filter_name(self):
        return self.filter_type.replace('_settings', '')

    def get_filter_node(self):
        return getattr(self, self.filter_type + '_settings')

    def displayfilter_items(self, context):
        items = []
        for n in rman_bl_nodes.__RMAN_DISPLAYFILTER_NODES__ :
            items.append((n.name, n.name, ''))
        return items        

    filter_type: EnumProperty(items=displayfilter_items, name='Filter')


class RendermanSampleFilterSettings(bpy.types.PropertyGroup):

    def get_filter_name(self):
        return self.filter_type.replace('_settings', '')

    def get_filter_node(self):
        return getattr(self, self.filter_type + '_settings')

    def samplefilter_items(self, context):
        items = []
        for n in rman_bl_nodes.__RMAN_SAMPLEFILTER_NODES__ :
            items.append((n.name, n.name, ''))
        return items               

    filter_type: EnumProperty(items=samplefilter_items, name='Filter')

classes = [RendermanLightFilter,
           RendermanLightSettings,
           RendermanPluginSettings,
           RendermanDisplayFilterSettings,
           RendermanSampleFilterSettings
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Light.renderman = PointerProperty(
        type=RendermanLightSettings, name="Renderman Light Settings")

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)           
