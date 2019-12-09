import bpy
from bpy.props import StringProperty, IntProperty, CollectionProperty, EnumProperty, BoolProperty
from bpy.types import PropertyGroup, UIList, Operator, Panel
from bpy_extras.io_utils import ImportHelper
from .rman_ui_base import _RManPanelHeader
from ..txmanager3 import txparams
from ..rman_utils import texture_utils
from .. import txmanager3 as txmngr3
import os
import uuid


class TxFileItem(PropertyGroup):
    """UIList item representing a TxFile"""

    name: StringProperty(
           name="Name",
           description="Image name",
           default="")

    tooltip: StringProperty(
           name="tooltip",
           description="Tool Tip",
           default="")

    nodeID: StringProperty(
            name="nodeID",
            description="Node ID (hidden)",
            default="")

    state: IntProperty(
            name="state",
            description="",
            default=0
            )

    enable: BoolProperty(
            name="enable",
            description="Enable or disable this TxFileItem",
            default=True
            )

    txsettings = ['texture_type', 
                  'smode', 
                  'tmode', 
                  'texture_format',
                  'data_type',
                  'resize']

    items = []
    for item in txparams.TX_TYPES:
        items.append((item, item, ''))        

    texture_type: EnumProperty(
           name="Texture Type",
           items=items,
           description="Texture Type",
           default=txparams.TX_TYPE_REGULAR)           

    items = []
    for item in txparams.TX_WRAP_MODES:
        items.append((item, item, ''))           

    smode: EnumProperty(
        name="S Wrap",
        items=items,
        default=txparams.TX_WRAP_MODE_PERIODIC)

    tmode: EnumProperty(
        name="T Wrap",
        items=items,
        default=txparams.TX_WRAP_MODE_PERIODIC)       

    items = []
    for item in txparams.TX_FORMATS:
        items.append((item, item, ''))

    texture_format: EnumProperty(
              name="Format", 
              default=txparams.TX_FORMAT_PIXAR,
              items=items,
              description="Texture format")

    items = []
    items.append(('default', 'default', ''))
    for item in txparams.TX_DATATYPES:
        items.append((item, item, ''))

    data_type: EnumProperty(
            name="Data Type",
            default=txparams.TX_DATATYPE_FLOAT,
            items=items,
            description="The data storage txmake uses")

    items = []
    for item in txparams.TX_RESIZES:
        items.append((item, item, ''))

    resize: EnumProperty(
            name="Resize",
            default=txparams.TX_RESIZE_UP_DASH,
            items=items,
            description="The type of resizing flag to pass to txmake")


class PRMAN_UL_Renderman_txmanager_list(UIList):
    """RenderMan TxManager UIList."""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):

        icons_map = {txmngr3.STATE_MISSING: 'ERROR',
                    txmngr3.STATE_EXISTS: 'CHECKBOX_HLT',
                    txmngr3.STATE_IS_TEX: 'TEXTURE',
                    txmngr3.STATE_IN_QUEUE: 'PLUS',
                    txmngr3.STATE_PROCESSING: 'TIME',
                    txmngr3.STATE_ERROR: 'CANCEL',
                    txmngr3.STATE_REPROCESS: 'TIME',
                    txmngr3.STATE_UNKNOWN: 'CANCEL',
                    txmngr3.STATE_INPUT_MISSING: 'ERROR'}
        

        txfile = None
        if item.nodeID != "":
            txfile = texture_utils.get_txmanager().txmanager.get_txfile_from_id(item.nodeID)
        else:
            txfile = texture_utils.get_txmanager().txmanager.get_txfile_from_path(item.name)
        if txfile:
            custom_icon = icons_map[txfile.state]
        else:
            custom_icon = 'CANCEL'

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon = custom_icon)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon = custom_icon)


class PRMAN_OT_Renderman_txmanager_parse_scene(Operator):
    """Parse scene for textures to add to to the txmanager"""

    bl_idname = "rman_txmgr_list.parse_scene"
    bl_label = "Parse Scene"

    def execute(self, context):
        rman_txmgr_list = context.scene.rman_txmgr_list
        rman_txmgr_list.clear()
        texture_utils.get_txmanager().txmanager.reset()
        texture_utils.parse_for_textures(context.scene)
        texture_utils.get_txmanager().txmake_all(blocking=False)
        return{'FINISHED'}


class PRMAN_OT_Renderman_txmanager_pick_images(Operator, ImportHelper):
    """Pick images from a directory."""

    bl_idname = "rman_txmgr_list.pick_images"
    bl_label = "Pick Images"

    filename: StringProperty(maxlen=1024)
    directory: StringProperty(maxlen=1024)
    files: CollectionProperty(type=bpy.types.PropertyGroup)

    def execute(self, context):

        rman_txmgr_list = context.scene.rman_txmgr_list
        rman_txmgr_list.clear()
        texture_utils.get_txmanager().txmanager.reset()

        if len(self.files) > 0:
            for f in self.files:
                img = os.path.join(self.directory, f.name)  
                item = context.scene.rman_txmgr_list.add()
                item.nodeID = str(uuid.uuid1())
                texture_utils.get_txmanager().txmanager.add_texture(item.nodeID, img)         
                item.name = img

        return{'FINISHED'}


class PRMAN_OT_Renderman_txmanager_clear_all_cache(Operator):
    """Clear RenderMan Texture cache"""

    bl_idname = "rman_txmgr_list.clear_all_cache"
    bl_label = "Clear Texture Cache"

    def execute(self, context):
        # needs to call InvalidateTexture

        return{'FINISHED'}

class PRMAN_OT_Renderman_txmanager_reconvert_all(Operator):
    """Clear all .tex files and re-convert."""

    bl_idname = "rman_txmgr_list.reconvert_all"
    bl_label = "RE-Convert All"

    def execute(self, context):
        texture_utils.get_txmanager().txmanager.delete_texture_files()
        texture_utils.get_txmanager().txmake_all(blocking=False)

        return{'FINISHED'}        

class PRMAN_OT_Renderman_txmanager_apply_preset(Operator):
    """Apply current settings to the selected texture."""

    bl_idname = "rman_txmgr_list.apply_preset"
    bl_label = "Apply preset"

    def execute(self, context):
        idx = context.scene.rman_txmgr_list_index
        item = context.scene.rman_txmgr_list[idx]
        
        txsettings = dict()
        for attr in item.txsettings:
            val = getattr(item, attr)
            if attr == 'data_type' and val == 'default':
                val = None
            txsettings[attr] = val

        if txsettings:
            txfile = None
            if item.nodeID != "":
                txfile = texture_utils.get_txmanager().txmanager.get_txfile_from_id(item.nodeID)
            else:
                txfile = texture_utils.get_txmanager().txmanager.get_txfile_from_path(item.name)
            txfile.params.set_params_from_dict(txsettings)

        return{'FINISHED'}        

class PRMAN_OT_Renderman_txmanager_add_texture(Operator):
    """Add texture."""

    bl_idname = "rman_txmgr_list.add_texture"
    bl_label = "add_texture"

    filepath: StringProperty()
    nodeID: StringProperty()

    def execute(self, context):
        txfile = texture_utils.get_txmanager().txmanager.get_txfile_from_path(self.filepath)
        if not txfile:
            return{'FINISHED'}

        item = None
        # check if nodeID already exists in the list
        for i in context.scene.rman_txmgr_list:
            if i.nodeID == self.nodeID:
                item = i
                break
        if not item:
            item = context.scene.rman_txmgr_list.add()
            item.nodeID = self.nodeID
        item.name = txfile.input_image
        params = txfile.params
        item.texture_type = params.texture_type
        item.smode = params.smode
        item.tmode = params.tmode
        item.texture_type = params.texture_type
        if params.data_type is not None:
            item.data_type = params.data_type
        item.resize = params.resize 
        item.state = txfile.state    
        if txfile.state == txmngr3.STATE_IS_TEX:
            item.enable = False  

        item.tooltip = '\n' + txfile.tooltip_text()    
        # FIXME: should also add the nodes that this texture is referenced in     

        return{'FINISHED'}        

class PRMAN_PT_Renderman_txmanager_list(_RManPanelHeader, Panel):
    """RenderMan Texture Manager Panel."""

    bl_label = "RenderMan Texture Manager"
    bl_idname = "PRMAN_PT_Renderman_txmanager_list"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row()
        row.operator('rman_txmgr_list.parse_scene', text='Parse Scene')

        # FIXME: not totally working. The done callbacks fail
        #row.operator('rman_txmgr_list.pick_images', text='Pick Images')
        
        row.operator('rman_txmgr_list.reconvert_all', text='Reconvert')
        row.operator('rman_txmgr_list.clear_all_cache', text='Clear All Cache')        

        if scene.rman_txmgr_list_index >= 0 and scene.rman_txmgr_list:
            row = layout.row()
            row.template_list("PRMAN_UL_Renderman_txmanager_list", "The_List", scene,
                            "rman_txmgr_list", scene, "rman_txmgr_list_index", item_dyntip_propname="tooltip")


            item = scene.rman_txmgr_list[scene.rman_txmgr_list_index]

            row = layout.row()
            row.label(text='Texture Settings')
            row = layout.row()
            row.enabled = item.enable
            row.prop(item, "texture_type")
            row = layout.row()
            row.enabled = item.enable
            row.prop(item, "smode")
            row.prop(item, "tmode")
            row = layout.row()
            row.enabled = item.enable
            row.prop(item, "texture_format")
            row = layout.row()
            row.enabled = item.enable
            row.prop(item, "data_type")
            row = layout.row()
            row.enabled = item.enable
            row.prop(item, "resize")   
            row = layout.row()   
            row.enabled = item.enable      
            row.alignment = 'RIGHT'          
            row.operator('rman_txmgr_list.apply_preset', text='Apply')
            
            row = layout.row()
            row.alignment='CENTER'
            in_list = len(context.scene.rman_txmgr_list)
            progress = 'All Converted'
            qsize = texture_utils.get_txmanager().txmanager.workQueue.qsize()
            if qsize != 0:
                progress = 'Converting...%d left to convert' % (qsize)
            row.label(text=progress)
            

def index_updated(self, context):
    '''
    When the index updates, make sure the texture settings
    are in sync with the txmanager.
    '''
    idx = context.scene.rman_txmgr_list_index
    if idx < 0:
        return
    item = context.scene.rman_txmgr_list[idx]
    txfile = None
    if item.nodeID != "":
        txfile = texture_utils.get_txmanager().txmanager.get_txfile_from_id(item.nodeID)
    else:
        txfile = texture_utils.get_txmanager().txmanager.get_txfile_from_path(item.name)
    if txfile:
        params = txfile.params
        item.texture_type = params.texture_type
        item.smode = params.smode
        item.tmode = params.tmode
        item.texture_type = params.texture_type
        if params.data_type is not None:
            item.data_type = params.data_type
        item.resize = params.resize 
        if txfile.state == txmngr3.STATE_IS_TEX:
            item.enable = False

classes = [
    TxFileItem,
    PRMAN_UL_Renderman_txmanager_list,
    PRMAN_OT_Renderman_txmanager_parse_scene,
    PRMAN_OT_Renderman_txmanager_pick_images,
    PRMAN_OT_Renderman_txmanager_clear_all_cache,
    PRMAN_OT_Renderman_txmanager_reconvert_all,
    PRMAN_OT_Renderman_txmanager_apply_preset,
    PRMAN_OT_Renderman_txmanager_add_texture,
    PRMAN_PT_Renderman_txmanager_list
]

def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.rman_txmgr_list = CollectionProperty(type = TxFileItem)
    bpy.types.Scene.rman_txmgr_list_index = IntProperty(name = "RenderMan Texture Manager",
                                             default = 0, update=index_updated)


def unregister():

    del bpy.types.Scene.rman_txmgr_list
    del bpy.types.Scene.rman_txmgr_list_index

    for cls in classes:
        bpy.utils.unregister_class(cls)   