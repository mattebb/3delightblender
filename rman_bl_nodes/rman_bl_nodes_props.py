import bpy
from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty, BoolVectorProperty
from .. import rman_bl_nodes

class RendermanPluginSettings(bpy.types.PropertyGroup):
    pass

class RendermanCameraSettings(bpy.types.PropertyGroup):
    bl_label = "RenderMan Camera Settings"
    bl_idname = 'RendermanCameraSettings'

    def get_projection_name(self):
        return self.projection_type.replace('_settings', '')

    def get_projection_node(self):
        return getattr(self, self.projection_type + '_settings')

    def projection_items(self, context):
        items = []
        items.append(('none', 'None', 'None'))
        for n in rman_bl_nodes.__RMAN_PROJECTION_NODES__ :
            items.append((n.name, n.name, ''))
        return items

    projection_type: EnumProperty(
        items=projection_items, name='Projection Plugin')

    use_physical_camera: BoolProperty(
        name="Use Physical Camera", default=False)

    aperture_roundness: FloatProperty(
        name="Aperture Roundness", default=0.0, max=1.0, min=-1.0,
        description="A shape parameter, from -1 to 1.  When 0, the aperture is a regular polygon with straight sides.  Values between 0 and 1 give polygons with curved edges bowed out and values between 0 and -1 make the edges bow in")

    aperture_density: FloatProperty(
        name="Aperture Density", default=0.0, max=1.0, min=-1.0,
        description="The slope, between -1 and 1, of the (linearly varying) aperture density.  A value of zero gives uniform density.  Negative values make the aperture brighter near the center.  Positive values make it brighter near the rim")

class RendermanLightFilter(bpy.types.PropertyGroup):

    def get_filters(self, context):
        obs = context.scene.objects
        items = [('None', 'Not Set', 'Not Set')]
        for o in obs:
            if o.type == 'LIGHT' and o.data.renderman.renderman_type == 'FILTER':
                items.append((o.name, o.name, o.name))
        return items

    def update_name(self, context):
        self.name = self.filter_name

    name: StringProperty(default='SET FILTER')
    filter_name: EnumProperty(
        name="Linked Filter:", items=get_filters, update=update_name)


class RendermanLightSettings(bpy.types.PropertyGroup):

    def get_light_node(self):
        if self.renderman_type == 'SPOT':
            light_shader = 'PxrRectLight' if self.id_data.use_square else 'PxrDiskLight'
            return getattr(self, light_shader + "_settings", None)
        return getattr(self, self.light_node, None)

    def get_light_node_name(self):
        if self.renderman_type == 'SPOT':
            return 'PxrRectLight' if self.id_data.use_square else 'PxrDiskLight'
        if self.renderman_type == 'PORTAL':
            return 'PxrPortalLight'
        else:
            return self.light_node.replace('_settings', '')

    light_node: StringProperty(
        name="Light Node",
        default='')

    # thes are used for light filters
    color_ramp_node: StringProperty(default='')
    float_ramp_node: StringProperty(default='')

    # do this to keep the nice viewport update
    def update_light_type(self, context):
        light = self.id_data
        light_type = light.renderman.renderman_type

        
        if light_type in ['SKY', 'ENV']:
            light.type = 'POINT'
        elif light_type == 'DIST':
            light.type = 'SUN'
        elif light_type == 'PORTAL':
            light.type = 'AREA'
        elif light_type == 'FILTER':
            light.type = 'AREA'
        else:
            light.type = light_type
        


        # use pxr area light for everything but env, sky
        light_shader = 'PxrRectLight'
        if light_type == 'ENV':
            light_shader = 'PxrDomeLight'
        elif light_type == 'SKY':
            light_shader = 'PxrEnvDayLight'
        elif light_type == 'PORTAL':
            light_shader = 'PxrPortalLight'
        elif light_type == 'POINT':
            light_shader = 'PxrSphereLight'
        elif light_type == 'DIST':
            light_shader = 'PxrDistantLight'
        elif light_type == 'FILTER':
            light_shader = 'PxrBlockerLightFilter'
        elif light_type == 'SPOT':
            light_shader = 'PxrRectLight' if light.use_square else 'PxrDiskLight'
        elif light_type == 'AREA':
            try:
                light.shape = 'RECTANGLE'
                light.size = 1.0
                light.size_y = 1.0
            except:
                pass

        self.light_node = light_shader + "_settings"
        if light_type == 'FILTER':
            self.update_filter_type(context)

        # setattr(node, 'renderman_portal', light_type == 'PORTAL')

    def update_area_shape(self, context):
        light = self.id_data
        area_shape = self.area_shape
        # use pxr area light for everything but env, sky
        light_shader = 'PxrRectLight'

        if area_shape == 'disk':
            light.shape = 'DISK'
            light_shader = 'PxrDiskLight'
        elif area_shape == 'sphere':
            light.shape = 'ELLIPSE'
            light_shader = 'PxrSphereLight'
        elif area_shape == 'cylinder':
            light.shape = 'RECTANGLE'
            light_shader = 'PxrCylinderLight'
        else:
            light.shape = 'RECTANGLE'

        self.light_node = light_shader + "_settings"

    def update_vis(self, context):
        light = self.id_data

    def update_filter_type(self, context):

        filter_name = 'IntMult' if self.filter_type == 'intmult' else self.filter_type.capitalize()
        # set the light type

        self.light_node = 'Pxr%sLightFilter_settings' % filter_name
        if self.filter_type in ['gobo', 'cookie']:
            self.id_data.id_data.type = 'AREA'
            self.id_data.shape = 'RECTANGLE'
        else:
            self.id_data.id_data.type = 'POINT'

        if self.filter_type in ['blocker', 'ramp', 'rod']:
            light = context.light
            if not light.use_nodes:
                light.use_nodes = True
            nt = light.node_tree
            if self.color_ramp_node not in nt.nodes.keys():
                # make a new color ramp node to use
                self.color_ramp_node = nt.nodes.new('ShaderNodeValToRGB').name
            if self.float_ramp_node not in nt.nodes.keys():
                self.float_ramp_node = nt.nodes.new(
                    'ShaderNodeVectorCurve').name

    use_renderman_node: BoolProperty(
        name="Use RenderMans Light Node",
        description="Will enable RenderMan light Nodes, opening more options",
        default=False, update=update_light_type)

    renderman_type: EnumProperty(
        name="Light Type",
        update=update_light_type,
        items=[('AREA', 'Area', 'Area Light'),
               ('ENV', 'Environment', 'Environment Light'),
               ('SKY', 'Sky', 'Simulated Sky'),
               ('DIST', 'Distant', 'Distant Light'),
               ('SPOT', 'Spot', 'Spot Light'),
               ('POINT', 'Point', 'Point Light'),
               ('PORTAL', 'Portal', 'Portal Light'),
               ('FILTER', 'Filter', 'Light Filter')],
        default='AREA'
    )

    area_shape: EnumProperty(
        name="Area Shape",
        update=update_area_shape,
        items=[('rect', 'Rectangle', 'Rectangle'),
               ('disk', 'Disk', 'Disk'),
               ('sphere', 'Sphere', 'Sphere'), 
               ('cylinder', 'Cylinder', 'Cylinder')],
        default='rect'
    )

    filter_type: EnumProperty(
        name="Area Shape",
        update=update_filter_type,
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

    light_filters: CollectionProperty(
        type=RendermanLightFilter
    )
    light_filters_index: IntProperty(min=-1, default=-1)

    shadingrate: FloatProperty(
        name="Light Shading Rate",
        description="Shading Rate for lights.  Keep this high unless banding or pixellation occurs on detailed light maps",
        default=100.0)

    # illuminate
    illuminates_by_default: BoolProperty(
        name="Illuminates by default",
        description="The light illuminates objects by default",
        default=True)

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
           RendermanCameraSettings,
           RendermanDisplayFilterSettings,
           RendermanSampleFilterSettings
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Light.renderman = PointerProperty(
        type=RendermanLightSettings, name="Renderman Light Settings")
    bpy.types.Camera.renderman = PointerProperty(
        type=RendermanCameraSettings, name="Renderman Camera Settings")        

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)           
