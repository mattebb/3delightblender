import bpy
from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty, BoolVectorProperty
from .. import rman_bl_nodes
from .. import rfb_icons
from ..rman_utils.shadergraph_utils import is_renderman_nodetree

class RendermanPluginSettings(bpy.types.PropertyGroup):
    pass

class RendermanLightFilter(bpy.types.PropertyGroup):

    name: StringProperty(default='SET FILTER')

    def update_linked_filter_ob(self, context):
        if not self.linked_filter_ob:
            self.name = 'Not Set'
        else:
            self.name = self.linked_filter_ob.name           

    def validate_obj(self, ob):
        if ob.type == 'LIGHT' and ob.data.renderman.renderman_light_role == 'RMAN_LIGHTFILTER':
            return True
        return False
    
    linked_filter_ob: PointerProperty(name='Light Filter', 
                        description='Light Filter',
                        type=bpy.types.Object,
                        update=update_linked_filter_ob,
                        poll=validate_obj
                        )    

class RendermanLightSettings(bpy.types.PropertyGroup):

    def get_light_node(self):
        '''
        Get the light shader node
        '''
        light = self.id_data
        output = None
        nt = light.node_tree
        if not nt:
            return None
        output = is_renderman_nodetree(light)

        if not output:
            return None

        if self.renderman_light_role == 'RMAN_LIGHT':
            socket = output.inputs[1]
            if socket.is_linked:
                return socket.links[0].from_node
        else:
            socket = output.inputs[3]
            if socket.is_linked:
                return socket.links[0].from_node    

        return None        

    def get_light_node_name(self):
        '''
        Get light shader name
        '''
        node = self.get_light_node()
        if node:
            return node.bl_label
        return ''

    light_node: StringProperty(
        name="Light Node",
        default='')

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
          
        if hasattr(light, 'size'):
            light.size = 0.0
        light.type = 'POINT'

    def get_rman_light_shaders(self, context):
        items = []
        i = 0
        rman_light_icon = rfb_icons.get_light_icon("PxrRectLight")
        items.append(('PxrRectLight', 'PxrRectLight', '', rman_light_icon.icon_id, i))
        for n in rman_bl_nodes.__RMAN_LIGHT_NODES__:
            if n.name != 'PxrRectLight':
                i += 1
                light_icon = rfb_icons.get_light_icon(n.name)
                items.append( (n.name, n.name, '', light_icon.icon_id, i))
        return items

    renderman_light_shader: EnumProperty(
        name="RenderMan Light",
        items=get_rman_light_shaders,
        update=renderman_light_shader_update
    )

    def renderman_light_filter_shader_update(self, context):
        light = self.id_data
        light_shader = self.get_light_node_name()

        if hasattr(light, 'size'):
            light.size = 0.0
        light.type = 'POINT'
          
    def get_rman_light_filter_shaders(self, context):
        items = []
        i = 0
        rman_light_icon = rfb_icons.get_lightfilter_icon("_PxrBlockerLightFilter")
        items.append(('PxrBlockerLightFilter', 'PxrBlockerLightFilter', '', rman_light_icon.icon_id, i))
        for n in rman_bl_nodes.__RMAN_LIGHTFILTER_NODES__:
            if n.name != 'PxrBlockerLightFilter':
                i += 1
                light_icon = rfb_icons.get_lightfilter_icon(n.name)
                items.append( (n.name, n.name, '', light_icon.icon_id, i))
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
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass        
