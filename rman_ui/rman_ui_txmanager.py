import bpy
from bpy.props import StringProperty, IntProperty, CollectionProperty, EnumProperty, BoolProperty, FloatProperty
from bpy.types import PropertyGroup, UIList, Operator, Panel
from bpy_extras.io_utils import ImportHelper
from .rman_ui_base import _RManPanelHeader
from ..rfb_utils import texture_utils
from ..rfb_utils import shadergraph_utils
from ..rfb_utils import scene_utils
from ..rfb_utils import object_utils
from .. import rman_render
from rman_utils.txmanager import txparams
from rman_utils import txmanager as txmngr
from .. import rfb_icons
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

    def colorspace_names(self, context):
        items = []
        items.append(('0', '', ''))
        mdict = texture_utils.get_txmanager().txmanager.color_manager.colorspace_names()
        for nm in mdict:
            items.append((nm, nm, ""))
        return items

    ocioconvert: EnumProperty(
            name="Color Space",
            description="colorspace",
            items=colorspace_names
            )

    txsettings = ['texture_type', 
                  's_mode', 
                  't_mode', 
                  'texture_format',
                  'data_type',
                  'resize',
                  'ocioconvert']

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

    s_mode: EnumProperty(
        name="S Wrap",
        items=items,
        default=txparams.TX_WRAP_MODE_PERIODIC)

    t_mode: EnumProperty(
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

    bumpRough: EnumProperty(
            name="Bump Rough",
            default="-1",
            items=(
                ("-1", "Off", ""),
                ("0", "Bump Map", ""),
                ("1", "Normal Map", "")
            )
    )
    bumpRough_factor: FloatProperty(
            name="Scale",
            default=2.0
    )

    bumpRough_invert: BoolProperty(
            name="Invert",
            default=False
    )

    bumpRough_invertU: BoolProperty(
            name="InvertU",
            default=False
    )    
    bumpRough_invertV: BoolProperty(
            name="InvertV",
            default=False
    )    
    bumpRough_refit: BoolProperty(
            name="Refit",
            default=False
    )    

class PRMAN_UL_Renderman_txmanager_list(UIList):
    """RenderMan TxManager UIList."""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):

        icons_map = {txmngr.STATE_MISSING: 'ERROR',
                    txmngr.STATE_EXISTS: 'CHECKBOX_HLT',
                    txmngr.STATE_IS_TEX: 'TEXTURE',
                    txmngr.STATE_IN_QUEUE: 'PLUS',
                    txmngr.STATE_PROCESSING: 'TIME',
                    txmngr.STATE_ERROR: 'CANCEL',
                    txmngr.STATE_REPROCESS: 'TIME',
                    txmngr.STATE_UNKNOWN: 'CANCEL',
                    txmngr.STATE_INPUT_MISSING: 'ERROR'}
        

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
    bl_description = "Parse the scene and look for textures that need converting."

    def execute(self, context):
        rman_txmgr_list = context.scene.rman_txmgr_list
        texture_utils.parse_for_textures(context.scene)
        texture_utils.get_txmanager().txmake_all(blocking=False)
        bpy.ops.rman_txmgr_list.refresh('EXEC_DEFAULT')
        return{'FINISHED'}

class PRMAN_OT_Renderman_txmanager_reset_state(Operator):
    """Reset State"""

    bl_idname = "rman_txmgr_list.reset_state"
    bl_label = "Reset State"
    bl_description = "All texture settings will be erased and the scene will be re-parsed. All manual edits will be lost."

    def execute(self, context):
        rman_txmgr_list = context.scene.rman_txmgr_list
        rman_txmgr_list.clear()
        texture_utils.get_txmanager().txmanager.reset()
        texture_utils.parse_for_textures(context.scene)
        texture_utils.get_txmanager().txmake_all(blocking=False)
        texture_utils.get_txmanager().txmanager.reset_state()
        return{'FINISHED'}

class PRMAN_OT_Renderman_txmanager_pick_images(Operator, ImportHelper):
    """Pick images from a directory."""

    bl_idname = "rman_txmgr_list.pick_images"
    bl_label = "Pick Images"
    bl_description = "Manually choose images on disk to convert."

    filename: StringProperty(maxlen=1024)
    directory: StringProperty(maxlen=1024)
    files: CollectionProperty(type=bpy.types.PropertyGroup)

    def execute(self, context):

        rman_txmgr_list = context.scene.rman_txmgr_list

        if len(self.files) > 0:
            for f in self.files:
                img = os.path.join(self.directory, f.name)  
                nodeID = str(uuid.uuid1())
                texture_utils.get_txmanager().txmanager.add_texture(nodeID, img) 
                bpy.ops.rman_txmgr_list.add_texture('EXEC_DEFAULT', filepath=img, nodeID=nodeID)
            texture_utils.get_txmanager().txmake_all(blocking=False)
            texture_utils.get_txmanager().txmanager.save_state()

        return{'FINISHED'}


class PRMAN_OT_Renderman_txmanager_clear_all_cache(Operator):
    """Clear RenderMan Texture cache"""

    bl_idname = "rman_txmgr_list.clear_all_cache"
    bl_label = "Clear Texture Cache"
    bl_description = "Tell the core RenderMan to clear its texture cache."

    def execute(self, context):
        rr = rman_render.RmanRender.get_rman_render() 
        if rr.rman_interactive_running:    
            for item in context.scene.rman_txmgr_list:
                txfile = None
                if item.nodeID != "":
                    output_texture = texture_utils.get_txfile_from_id(item.nodeID)
                    rr.rictl.InvalidateTexture(output_texture)
                    
        return{'FINISHED'}

class PRMAN_OT_Renderman_txmanager_reconvert_all(Operator):
    """Clear all .tex files and re-convert."""

    bl_idname = "rman_txmgr_list.reconvert_all"
    bl_label = "RE-Convert All"
    bl_description = "Clear all .tex files for all input images and re-convert."

    def execute(self, context):
        texture_utils.get_txmanager().txmanager.delete_texture_files()
        texture_utils.get_txmanager().txmake_all(blocking=False)

        return{'FINISHED'}        

class PRMAN_OT_Renderman_txmanager_reconvert_selected(Operator):
    """Clear all .tex files and re-convert selected."""

    bl_idname = "rman_txmgr_list.reconvert_selected"
    bl_label = "RE-Convert Selected"
    bl_description = "Clear all .tex files for selected image and re-convert"

    def execute(self, context):
        idx = context.scene.rman_txmgr_list_index
        item = context.scene.rman_txmgr_list[idx]

        txfile = None
        if item.nodeID != "":
            txfile = texture_utils.get_txmanager().txmanager.get_txfile_from_id(item.nodeID)
        else:
            txfile = texture_utils.get_txmanager().txmanager.get_txfile_from_path(item.name)

        if txfile:           
            txfile.delete_texture_files()
            texture_utils.get_txmanager().txmake_all(blocking=False)

        return{'FINISHED'}               

class PRMAN_OT_Renderman_txmanager_apply_preset(Operator):
    """Apply current settings to the selected texture."""

    bl_idname = "rman_txmgr_list.apply_preset"
    bl_label = "Apply preset"
    bl_description = "Apply the current settings for this input image and re-convert."

    def execute(self, context):
        idx = context.scene.rman_txmgr_list_index
        item = context.scene.rman_txmgr_list[idx]
        
        txsettings = dict()
        for attr in item.txsettings:
            val = getattr(item, attr)
            if attr == 'data_type' and val == 'default':
                val = None
            txsettings[attr] = val

        # b2r
        bumprough = dict()
        if item.bumpRough != "-1":
            bumprough['normalmap'] = int(item.bumpRough)
            bumprough['factor'] = item.bumpRough_factor
            bumprough['invert'] = item.bumpRough_invert
            bumprough['invertU'] = item.bumpRough_invertU
            bumprough['invertV'] = item.bumpRough_invertV
            bumprough['refit'] = item.bumpRough_refit
        else:
            bumprough = list()        
        txsettings['bumprough'] = bumprough

        if txsettings:
            txfile = None
            if item.nodeID != "":
                txfile = texture_utils.get_txmanager().txmanager.get_txfile_from_id(item.nodeID)
            else:
                txfile = texture_utils.get_txmanager().txmanager.get_txfile_from_path(item.name)

            if txfile:
                txfile.params.from_dict(txsettings)
                txfile.delete_texture_files()
                texture_utils.get_txmanager().txmake_all(blocking=False)

        texture_utils.get_txmanager().txmanager.save_state()

        # update any nodes with colorspace in it
        tokens = item.nodeID.split('|')
        if len(tokens) < 3:
            return
        node_name,prop_name,ob_name = tokens            
        prop_colorspace_name = '%s_colorspace' % prop_name

        mdict = texture_utils.get_txmanager().txmanager.color_manager.colorspace_names()
        val = 0
        for i, nm in enumerate(mdict):
            if nm == item.ocioconvert:
                val = i+1
                break        

        node, ob = scene_utils.find_node_by_name(node_name, ob_name)
        if node:
            node[prop_colorspace_name] = val        

        return {'FINISHED'}        

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
        for idx, i in enumerate(context.scene.rman_txmgr_list):
            if i.nodeID == self.nodeID:
                item = i
                break
        if not item:
            item = context.scene.rman_txmgr_list.add()
            item.nodeID = self.nodeID
        item.name = txfile.input_image
        params = txfile.params
        item.texture_type = params.texture_type
        item.s_mode = params.s_mode
        item.t_mode = params.t_mode
        item.texture_format = params.texture_format
        if params.data_type is not None:
            item.data_type = params.data_type
        item.resize = params.resize 
        item.state = txfile.state    
        if txfile.state == txmngr.STATE_IS_TEX:
            item.enable = False  
        else:
            item.enable = True
        if params.ocioconvert:
            item.ocioconvert = params.ocioconvert

        if params.bumprough:
            bumprough = params.bumprough_as_dict()
            item.bumpRough = str(bumprough['normalmap'])
            item.bumpRough_factor = float(bumprough['factor'])
            item.bumpRough_invert = bool(bumprough['invert'])
            item.bumpRough_invertU = bool(bumprough['invertU'])
            item.bumpRough_invertV = bool(bumprough['invertV'])
            item.bumpRough_refit = bool(bumprough['refit'])
        else:
            params.bumpRough = "-1"

  
        item.tooltip = '\nNode ID: ' + item.nodeID + "\n" + str(txfile)
        # FIXME: should also add the nodes that this texture is referenced in     

        return{'FINISHED'}        

class PRMAN_OT_Renderman_txmanager_refresh(Operator):
    """Refresh Texture Manager"""

    bl_idname = "rman_txmgr_list.refresh"
    bl_label = "refresh"

    filepath: StringProperty()
    nodeID: StringProperty()

    def execute(self, context):

        for item in context.scene.rman_txmgr_list:
            txfile = texture_utils.get_txmanager().txmanager.get_txfile_from_id(item.nodeID)
            if not txfile:
                continue
            item.name = txfile.input_image
            params = txfile.params
            item.texture_type = params.texture_type
            item.s_mode = params.s_mode
            item.t_mode = params.t_mode
            item.texture_type = params.texture_type
            if params.data_type is not None:
                item.data_type = params.data_type
            item.resize = params.resize 
            item.state = txfile.state    
            if txfile.state == txmngr.STATE_IS_TEX:
                item.enable = False  
            else:
                item.enable = True
            if params.ocioconvert:
                item.ocioconvert = params.ocioconvert

            if params.bumprough:
                item.bumpRough = str(params.bumprough['normalmap'])
                item.bumpRough_factor = params.bumprough['factor']
                item.bumpRough_invert = params.bumprough['invert']
                item.bumpRough_invertU = params.bumprough['invertU']
                item.bumpRough_invertV = params.bumprough['invertV']
                item.bumpRough_refit = params.bumprough['refit']
            else:
                params.bumpRough = "-1"                
    
            item.tooltip = '\n' + item.nodeID + "\n" + str(txfile)


        return{'FINISHED'}    

class PRMAN_OT_Renderman_txmanager_remove_texture(Operator):

    bl_idname = "rman_txmgr_list.remove_texture"
    bl_label = "remove texture"

    nodeID: StringProperty()

    def execute(self, context):

        for i, item in enumerate(context.scene.rman_txmgr_list):
            if item.nodeID == self.properties.nodeID:
                context.scene.rman_txmgr_list.remove(i)
                break              

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
        rman_icon = rfb_icons.get_icon('rman_txmanager')        
        row.operator('rman_txmgr_list.open_txmanager', text='Open TxManager', icon_value=rman_icon.icon_id)

class PRMAN_OT_Renderman_open_txmanager(Operator):

    bl_idname = "rman_txmgr_list.open_txmanager"
    bl_label = "Open TxManager"

    nodeID: StringProperty(default='')

    def execute(self, context):
        return{'FINISHED'}         

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        row = layout.row()
        row.operator('rman_txmgr_list.parse_scene', text='Parse Scene')
        row.operator('rman_txmgr_list.reset_state', text='Reset', icon='FILE_REFRESH')         
        row.operator('rman_txmgr_list.pick_images', text='Pick Images', icon='FILE_FOLDER')        
        row.operator('rman_txmgr_list.reconvert_all', text='Reconvert All')
        #row.operator('rman_txmgr_list.clear_all_cache', text='Clear All Cache')      
         

        if scene.rman_txmgr_list_index >= 0 and scene.rman_txmgr_list:
            row = layout.row()
            row.template_list("PRMAN_UL_Renderman_txmanager_list", "The_List", scene,
                            "rman_txmgr_list", scene, "rman_txmgr_list_index", item_dyntip_propname="tooltip")

            if scene.rman_txmgr_list_index < len(scene.rman_txmgr_list):

                item = scene.rman_txmgr_list[scene.rman_txmgr_list_index]

                row = layout.row()
                row.label(text='Texture Settings')
                row = layout.row()
                row.enabled = item.enable
                row.prop(item, "texture_type")
                row = layout.row()
                row.enabled = item.enable
                row.prop(item, "s_mode")
                row.prop(item, "t_mode")
                row = layout.row()
                row.enabled = item.enable
                row.prop(item, "texture_format")
                row = layout.row()
                row.enabled = item.enable
                row.prop(item, "data_type")
                row = layout.row()
                row.enabled = item.enable
                row.prop(item, "resize")   
                if item.ocioconvert != '0':
                    row = layout.row()
                    row.enabled = item.enable
                    row.prop(item, "ocioconvert")   
                    dst = texture_utils.get_txmanager().txmanager.color_manager.scene_colorspace_name
                    row.label(text='%s' % dst if dst else txmngr.NO_COLORSPACE)        

                # b2r
                row = layout.row()   
                row.prop(item, "bumpRough")
                if item.bumpRough != "-1":
                    row = layout.row()
                    row.alignment = "RIGHT"
                    row.label(text="")
                    row.prop(item, "bumpRough_factor")
                    row.prop(item, "bumpRough_invert")
                    row.prop(item, "bumpRough_invertU")
                    row.prop(item, "bumpRough_invertV")
                    row.prop(item, "bumpRough_refit")


                row = layout.row()   
                row.enabled = item.enable      
                row.alignment = 'RIGHT'          
                row.operator('rman_txmgr_list.reconvert_selected', text='Reconvert')
                row.operator('rman_txmgr_list.apply_preset', text='Apply')
                
                '''
                row = layout.row()
                row.alignment='CENTER'
                in_list = len(context.scene.rman_txmgr_list)
                progress = 'All Converted'
                qsize = texture_utils.get_txmanager().txmanager.workQueue.qsize()
                if qsize != 0:
                    progress = 'Converting...%d left to convert' % (qsize)
                row.label(text=progress)        
                '''

    def invoke(self, context, event):
        if self.properties.nodeID != '':
            for i, item in enumerate(context.scene.rman_txmgr_list):
                if item.nodeID == self.properties.nodeID:
                    context.scene.rman_txmgr_list_index = i
                    break

        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=700)     
            
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
        item.s_mode = params.s_mode
        item.t_mode = params.t_mode
        item.texture_format = params.texture_format
        item.texture_type = params.texture_type
        if params.data_type is not None:
            item.data_type = params.data_type
        item.resize = params.resize 
        if txfile.state == txmngr.STATE_IS_TEX:
            item.enable = False
        else:
            item.enable = True
        if params.ocioconvert:
            item.ocioconvert = params.ocioconvert

        if params.bumprough:
            bumprough = params.bumprough_as_dict()
            item.bumpRough = str(bumprough['normalmap'])
            item.bumpRough_factor = float(bumprough['factor'])
            item.bumpRough_invert = bool(bumprough['invert'])
            item.bumpRough_invertU = bool(bumprough['invertU'])
            item.bumpRough_invertV = bool(bumprough['invertV'])
            item.bumpRough_refit = bool(bumprough['refit'])
        else:
            params.bumpRough = "-1"  

        item.tooltip = '\nNode ID: ' + item.nodeID + "\n" + str(txfile)                      

classes = [
    TxFileItem,
    PRMAN_UL_Renderman_txmanager_list,
    PRMAN_OT_Renderman_txmanager_parse_scene,
    PRMAN_OT_Renderman_txmanager_reset_state,
    PRMAN_OT_Renderman_txmanager_pick_images,
    PRMAN_OT_Renderman_txmanager_clear_all_cache,
    PRMAN_OT_Renderman_txmanager_reconvert_all,
    PRMAN_OT_Renderman_txmanager_reconvert_selected,
    PRMAN_OT_Renderman_txmanager_apply_preset,
    PRMAN_OT_Renderman_txmanager_add_texture,
    PRMAN_OT_Renderman_txmanager_refresh,
    PRMAN_PT_Renderman_txmanager_list,
    PRMAN_OT_Renderman_open_txmanager,
    PRMAN_OT_Renderman_txmanager_remove_texture    
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
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass  