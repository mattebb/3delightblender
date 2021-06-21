from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, \
    CollectionProperty

from ... import rman_config
from ...rman_config import RmanBasePropertyGroup
from ..rman_properties_misc import RendermanOpenVDBChannel, RendermanAnimSequenceSettings 
from ..rman_properties_misc import RendermanLightPointer
from ...rfb_utils import shadergraph_utils

import bpy

class RendermanObjectSettings(RmanBasePropertyGroup, bpy.types.PropertyGroup):

    rman_config_name: StringProperty(name='rman_config_name',
                                    default='rman_properties_object')

    openvdb_channels: CollectionProperty(
        type=RendermanOpenVDBChannel, name="OpenVDB Channels")
    openvdb_channel_index: IntProperty(min=-1, default=-1)

    archive_anim_settings: PointerProperty(
        type=RendermanAnimSequenceSettings,
        name="Animation Sequence Settings")    

    hide_primitive_type: BoolProperty(
        name="Hide Primitive Type",
        default=False
    )

    rman_material_override: PointerProperty(
        name='Material',
        type=bpy.types.Material
    )    

    rman_lighting_excludesubset: CollectionProperty(
        name='lighting:excludesubset',
        type=RendermanLightPointer
    )

    rman_lightfilter_subset: CollectionProperty(
        name='lighting:excludesubset',
        type=RendermanLightPointer
    )

    export_archive: BoolProperty(
        name="Export as Archive",
        description="At render export time, store this object as a RIB archive",
        default=False)
    export_archive_path: StringProperty(
        name="Archive Export Path",
        description="Path to automatically save this object as a RIB archive",
        subtype='FILE_PATH',
        default="")

    export_as_coordsys: BoolProperty(
        name="Export As CoordSys",
        description="Export this empty as a coordinate system.",
        default=False)      

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
                    if shadergraph_utils.is_rman_light(ob, include_light_filters=False):
                        rm = ob.renderman
                        if rm != self and rm.solo:
                            rm.solo = False
                            break

    solo: BoolProperty(
        name="Solo",
        update=update_solo,
        description="Turn on only this light",
        default=False)        

classes = [         
    RendermanObjectSettings
]           

def register():

    for cls in classes:
        cls._add_properties(cls, 'rman_properties_object')
        bpy.utils.register_class(cls)  

    bpy.types.Object.renderman = PointerProperty(
        type=RendermanObjectSettings, name="Renderman Object Settings")

def unregister():

    del bpy.types.Object.renderman

    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass