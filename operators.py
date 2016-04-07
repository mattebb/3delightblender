# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 Brian Savery
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#
# ##### END MIT LICENSE BLOCK #####

import bpy
import os
import subprocess
import bgl
import blf
import webbrowser
import addon_utils
from .icons.icons import load_icons
from operator import attrgetter, itemgetter

from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty

from .util import init_env
from .util import getattr_recursive
from .util import user_path
from .util import get_real_path
from .util import readOSO, find_it_path
from .util import get_Files_in_Directory

from .shader_parameters import tex_source_path
from .shader_parameters import tex_optimised_path

from .export import export_archive
from .export import get_texture_list
from .engine import RPass
from .export import debug
from .export import write_archive_RIB
from .export import EXCLUDED_OBJECT_TYPES
from . import engine

from .nodes import RendermanPatternGraph

from bpy_extras.io_utils import ExportHelper

class Renderman_open_stats(bpy.types.Operator):
    bl_idname = 'rman.open_stats'
    bl_label = "Open Last Stats"
    bl_description = "Open Last stats file"

    def execute(self, context):
        scene = context.scene
        rm = scene.renderman
        output_dir = os.path.dirname(user_path(rm.path_rib_output, scene=scene))
        bpy.ops.wm.url_open(url="file://" + os.path.join(output_dir, 'stats.xml'))
        return {'FINISHED'}

class Renderman_start_it(bpy.types.Operator):
    bl_idname = 'rman.start_it'
    bl_label = "Start IT"
    bl_description = "Start RenderMan's IT"

    def execute(self, context):
        scene = context.scene
        rm = scene.renderman
        it_path = find_it_path()
        if not it_path:
            print({"ERROR"},
                  "Could not find 'it'. Install RenderMan Studio.")
        else:
            environ = os.environ.copy()
            subprocess.Popen([it_path], env=environ, shell=True)
        return {'FINISHED'}

class Renderman_open_last_RIB(bpy.types.Operator):
    bl_idname = 'rman.open_rib'
    bl_label = "Open Last RIB Scene file."
    bl_description = "Opens the last generated Scene.rib file in the system default text editor."
    
    def invoke(self, context, event=None):
        rm = context.scene.renderman
        rpass = RPass(context.scene, interactive=False)
        path = rpass.paths['rib_output']
        if rm.editor_override == "":
            try:
                webbrowser.open(path)
            except Exception:
                debug('error',"File not available!")
        else:
            command = rm.editor_override + " " + path
            try:
                os.system(command)
            except Exception:
                debug('error',"File or text editor not available. (Check and make sure text editor is in system path.)")
        return {'FINISHED'}
    
class SHADING_OT_add_renderman_nodetree(bpy.types.Operator):

    ''''''
    bl_idname = "shading.add_renderman_nodetree"
    bl_label = "Add Renderman Nodetree"
    bl_description = "Add a renderman shader node tree linked to this material"

    idtype = StringProperty(name="ID Type", default="material")
    bxdf_name = StringProperty(name="Bxdf Name", default="PxrDisney")

    def execute(self, context):
        idtype = self.properties.idtype
        context_data = {'material': context.material, 'lamp': context.lamp, 'world':context.scene.world}
        idblock = context_data[idtype]

        nt = bpy.data.node_groups.new(idblock.name,
                                      type='RendermanPatternGraph')
        nt.use_fake_user = True
        idblock.renderman.nodetree = nt.name

        if idtype == 'material':
            output = nt.nodes.new('RendermanOutputNode')
            default = nt.nodes.new('%sBxdfNode' % self.properties.bxdf_name)
            default.location = output.location
            default.location[0] -= 300
            nt.links.new(default.outputs[0], output.inputs[0])
        elif idtype == 'lamp':
            # we only need to set the renderman type as the update method there 
            # handles making the nodetree
            light_type = idblock.type
            if light_type == "SUN":
                idblock.renderman.renderman_type = "DIST"
            elif light_type == "HEMI":
                idblock.renderman.renderman_type = "ENV"
            else:
                idblock.renderman.renderman_type = light_type
        else:
            idblock.renderman.renderman_type = "ENV"
            # light_type = idblock.type
            # light_shader = 'PxrStdAreaLightLightNode'
            # if light_type == 'SUN':
            #     context.lamp.renderman.type=
            #     light_shader = 'PxrStdEnvDayLightLightNode'
            # elif light_type == 'HEMI':
            #     light_shader = 'PxrStdEnvMapLightLightNode'
            # elif light_type == 'AREA' or light_type == 'POINT':
            #     idblock.type = "AREA"
            #     context.lamp.size = 1.0
            #     context.lamp.size_y = 1.0
                
            # else:
            #     idblock.type = "AREA"

            # output = nt.nodes.new('RendermanOutputNode')
            # default = nt.nodes.new(light_shader)
            # default.location = output.location
            # default.location[0] -= 300
            # nt.links.new(default.outputs[0], output.inputs[1])

        return {'FINISHED'}


class refresh_osl_shader(bpy.types.Operator):
    bl_idname = "node.refresh_osl_shader"
    bl_label = "Refresh OSL Node"
    bl_description = "Refreshes the OSL node This takes a second!!"

    def invoke(self, context, event):
        context.node.RefreshNodes(context)
        return {'FINISHED'}


class StartInteractive(bpy.types.Operator):

    ''''''
    bl_idname = "lighting.start_interactive"
    bl_label = "Start/Stop Interactive Rendering"
    bl_description = "Start/Stop Interactive Rendering, \
        must have 'it' installed"
    rpass = None
    is_running = False

    def draw(self, context):
        w = context.region.width
        h = context.region.height

        # Draw text area that PRMan is running.
        pos_x = w / 2 - 100
        pos_y = 20
        blf.enable(0, blf.SHADOW)
        blf.shadow_offset(0, 1, -1)
        blf.shadow(0, 5, 0.0, 0.0, 0.0, 0.8)
        blf.size(0, 32, 36)
        blf.position(0, pos_x, pos_y, 0)
        bgl.glColor4f(1.0, 0.0, 0.0, 1.0)
        blf.draw(0, "%s" % ('PRMan Interactive Mode Running'))
        blf.disable(0, blf.SHADOW)

    def invoke(self, context, event=None):
        if engine.ipr is None:
            engine.ipr = RPass(context.scene, interactive=True)
            engine.ipr.start_interactive()
            engine.ipr_handle = bpy.types.SpaceView3D.draw_handler_add(
                self.draw, (context,), 'WINDOW', 'POST_PIXEL')
            bpy.app.handlers.scene_update_post.append(
                engine.ipr.issue_transform_edits)
            bpy.app.handlers.load_pre.append(self.invoke)
        else:
            bpy.types.SpaceView3D.draw_handler_remove(
                engine.ipr_handle, 'WINDOW')
            bpy.app.handlers.scene_update_post.remove(
                engine.ipr.issue_transform_edits)
            engine.ipr.end_interactive()
            engine.ipr = None
            if context:
                for area in context.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
        return {'FINISHED'}

class ExportRIBObject(bpy.types.Operator):
    bl_idname = "export.export_rib_archive"
    bl_label = "Export Object as RIB Archive."
    bl_description = "Export single object as a RIB archive for use in other blend files or for other uses."

    export_mat = BoolProperty(
        name="Export Material",
        description="Do you want to export the material?",
        default=True)
        
    export_all_frames = BoolProperty(
        name="Export All Frames",
        description="Export entire animation time frame",
        default=False)
    
    filepath = bpy.props.StringProperty(
            subtype="FILE_PATH")
    
    filename = bpy.props.StringProperty(
            subtype="FILE_NAME",
            default="")
    
    @classmethod
    def poll(cls, context):
        return context.object is not None
    
    def execute(self, context):
        export_path = self.filepath
        export_range = self.export_all_frames
        export_mats = self.export_mat
        rpass = RPass(context.scene, interactive=False)
        object = context.active_object
        
        
        #rpass.convert_textures(get_texture_list(context.scene))
        rpass.ri.Option("rib", {"string asciistyle": "indented,wide"})
        
        #export_filename = write_single_RIB(rpass, context.scene, rpass.ri, object)
        export_sucess = write_archive_RIB(rpass, context.scene, rpass.ri, object,
                                         export_path, export_mats, export_range)

        
        
        if(export_sucess[0] == True):
            self.report({'INFO'}, "Archive Exported Successfully!")
            object.renderman.geometry_source = 'ARCHIVE'
            object.renderman.path_archive = export_sucess[1]
            object.renderman.object_name = object.name
            if(export_mats):
                object.renderman.material_in_archive = True
            else:
                object.renderman.material_in_archive = False
            object.show_bounds = True
            if(export_range == True):
                object.renderman.archive_anim_settings.animated_sequence = True
                object.renderman.archive_anim_settings.sequence_in = context.scene.frame_start
                object.renderman.archive_anim_settings.sequence_out = context.scene.frame_end
                object.renderman.archive_anim_settings.blender_start = context.scene.frame_current
            else:
                object.renderman.archive_anim_settings.animated_sequence = False
        else:
            self.report({'ERROR'}, "Archive Not Exported.")
        return {'FINISHED'}
    
    def invoke(self, context, event=None):
        
        context.window_manager.fileselect_add(self)
        return{'RUNNING_MODAL'}
        
 

''' # Item that is not needed because of new rib archiving system.
class ExportRIBArchive(bpy.types.Operator):
    bl_idname = "global.export_rib_archive"
    bl_label = "Export RIB Archives for scene"
    bl_description = "Export the scene to disk without rendering."

    def execute(self, context):
        rpass = RPass(context.scene, interactive=False)
        
        rpass.convert_textures(get_texture_list(context.scene))
        rpass.ri.Begin(rpass.paths['rib_output'])
        rpass.ri.Option("rib", {"string asciistyle": "indented,wide"})
        
        write_rib(rpass, context.scene, rpass.ri)
        
        rpass.ri.End()
        return {'FINISHED'}
'''



#################
# Sample scenes menu.
#################
# Watch out for global list!!
# It should be too long to be used but you never know.

blenderAddonPaths = addon_utils.paths()
rendermanExampleFilesList = []
for path in blenderAddonPaths:
    basePath = os.path.join(path, "PRMan-for-Blender", "examples")
    exists = os.path.exists(basePath)
    if exists:
        names = get_Files_in_Directory(basePath)
for name in names:
    class examplesRenderman(bpy.types.Operator):
        bl_idname = ("rendermanexamples." + name.lower())
        bl_label = name
        bl_description = name
        def invoke(self, context, event):
            sucess = self.loadFile(self, self.bl_label)
            if not sucess:
                self.report({'ERROR'}, "Example Does Not Exist!")
            return {'FINISHED'}
        
        def loadFile(self,context,exampleName):
            blenderAddonPaths = addon_utils.paths()
            for path in blenderAddonPaths:
                basePath = os.path.join(path, "PRMan-for-Blender", "examples")
                exists = os.path.exists(basePath)
                if exists:
                    examplePath = os.path.join(basePath, exampleName, exampleName + ".blend")
                    if(os.path.exists(examplePath)):
                        bpy.ops.wm.open_mainfile(filepath = examplePath)
                        return True
                    else:
                        return False
    rendermanExampleFilesList.append(examplesRenderman)

class LoadSceneMenu(bpy.types.Menu):
    bl_label = "RendermanExamples"
    bl_idname = "examples"

    def get_operator_failsafe(self, idname):
        op = bpy.ops
        for attr in idname.split("."):
            if attr not in dir(op):
                return lambda: None
            op = getattr(op, attr)
        return op

    def draw(self, context):
        for operator in rendermanExampleFilesList:
            self.layout.operator(operator.bl_idname)


def menu_draw(self, context):
    icons = load_icons()
    examples_menu = icons.get("help")
    self.layout.menu("examples", icon_value=examples_menu.icon_id)

# Yuck, this should be built in to blender... Yes it should
class COLLECTION_OT_add_remove(bpy.types.Operator):
    bl_label = "Add or Remove Paths"
    bl_idname = "collection.add_remove"

    action = EnumProperty(
        name="Action",
        description="Either add or remove properties",
        items=[('ADD', 'Add', ''),
               ('REMOVE', 'Remove', '')],
        default='ADD')
    context = StringProperty(
        name="Context",
        description="Name of context member to find renderman pointer in",
        default="")
    collection = StringProperty(
        name="Collection",
        description="The collection to manipulate",
        default="")
    collection_index = StringProperty(
        name="Index Property",
        description="The property used as a collection index",
        default="")
    defaultname = StringProperty(
        name="Default Name",
        description="Default name to give this collection item",
        default="")
    # BBM addition begin
    is_shader_param = BoolProperty(name='Is shader parameter', default=False)
    shader_type = StringProperty(
        name="shader type",
        default='surface')
    # BBM addition end

    def invoke(self, context, event):
        scene = context.scene
        # BBM modification
        if not self.properties.is_shader_param:
            id = getattr_recursive(context, self.properties.context)
            rm = id.renderman if hasattr(id, 'renderman') else id
        else:
            if context.active_object.name in bpy.data.lamps.keys():
                rm = bpy.data.lamps[context.active_object.name].renderman
            else:
                rm = context.active_object.active_material.renderman
            id = getattr(rm, '%s_shaders' % self.properties.shader_type)
            rm = getattr(id, self.properties.context)

        prop_coll = self.properties.collection
        coll_idx = self.properties.collection_index

        collection = getattr(rm, prop_coll)
        index = getattr(rm, coll_idx)

        # otherwise just add an empty one
        if self.properties.action == 'ADD':
            collection.add()

            index += 1
            setattr(rm, coll_idx, index)
            collection[-1].name = self.properties.defaultname
            # BBM addition begin
            # if coshader array, add the selected coshader
            if self.is_shader_param:
                coshader_name = getattr(rm, 'bl_hidden_%s_menu' % prop_coll)
                collection[-1].name = coshader_name
            # BBM addition end
        elif self.properties.action == 'REMOVE':
            if prop_coll == 'light_groups' and collection[index].name == 'All':
                return {'FINISHED'}
            elif prop_coll == 'object_groups' and collection[index].name == 'collector':
                return {'FINISHED'}
            else:
                collection.remove(index)
                setattr(rm, coll_idx, index - 1)

        return {'FINISHED'}

class OT_add_aov_list(bpy.types.Operator):
    bl_idname = 'renderman.add_aov_list'
    bl_label = 'Add aov list'
    
    def execute(self, context):
        scene = context.scene
        scene.renderman.aov_lists.add()
        active_layer = scene.render.layers.active
        # this sucks.  but can't find any other way to refer to render layer
        scene.renderman.aov_lists[-1].render_layer = active_layer.name
        return {'FINISHED'}


class OT_add_to_group(bpy.types.Operator):
    bl_idname = 'renderman.add_to_group'
    bl_label = 'Add Selected to Object Group'

    group_index = IntProperty(default=0)
    item_type = StringProperty(default='object')

    def execute(self, context):
        scene = context.scene
        group_index = self.properties.group_index
        item_type = self.properties.item_type

        object_group = scene.renderman.object_groups if item_type == 'object' \
            else  scene.renderman.light_groups
        object_group = object_group[group_index].members
        if hasattr(context, 'selected_objects'):
            
            members = object_group.keys()
            
            for ob in context.selected_objects:
                if ob.name not in members:
                    if item_type != 'light' or ob.type == 'LAMP':
                        do_add = True
                        if item_type == 'light' and ob.type == 'LAMP':
                            # check if light is already in another group
                            # can only be in one
                            for lg in scene.renderman.light_groups:
                                if ob.name in lg.members.keys():
                                    do_add = False
                                    self.report({'WARNING'}, "Lamp %s cannot be added to light group %s, already a member of %s" % (ob.name, scene.renderman.light_groups[group_index].name, lg.name))

                        if do_add:
                            ob_in_group = object_group.add()
                            ob_in_group.name = ob.name

        return {'FINISHED'}


class OT_remove_from_group(bpy.types.Operator):
    bl_idname = 'renderman.remove_from_group'
    bl_label = 'Remove Selected from Object Group'

    group_index = IntProperty(default=0)
    item_type = StringProperty(default='object')

    def execute(self, context):
        scene = context.scene
        group_index = self.properties.group_index
        item_type = self.properties.item_type

        object_group = scene.renderman.object_groups if item_type == 'object' \
            else  scene.renderman.light_groups
        object_group = object_group[group_index].members
        if hasattr(context, 'selected_objects'):
            for ob in context.selected_objects:
                if ob.name in object_group.keys():
                    index = object_group.keys().index(ob.name)
                    object_group.remove(index)
                
        return {'FINISHED'}


class OT_remove_add_rem_light_link(bpy.types.Operator):
    bl_idname = 'renderman.add_rem_light_link'
    bl_label = 'Add/Remove Selected from Object Group'

    add_remove = StringProperty(default='add')
    ll_name = StringProperty(default='')

    def execute(self, context):
        scene = context.scene

        add_remove = self.properties.add_remove
        ll_name = self.properties.ll_name

        if add_remove == 'add':
            ll = scene.renderman.ll.add()
            ll.name = ll_name
        else:
            ll_index = scene.renderman.ll.keys().index(ll_name)
            if engine.ipr is not None and engine.ipr.is_interactive_running:
                engine.ipr.remove_light_link(context, scene.renderman.ll[ll_index])
            scene.renderman.ll.remove(ll_index)
            

        return {'FINISHED'}


#################
#       Tab     #
#################

class Add_Subdiv_Sheme(bpy.types.Operator):
    bl_idname = "object.add_subdiv_sheme"
    bl_label = "Add Subdiv Sheme"
    bl_description = ""
    bl_options = {"REGISTER"}

    def execute(self, context):
        bpy.context.object.renderman.primitive = 'SUBDIVISION_MESH'

        return {"FINISHED"}
        
class RM_Add_Area(bpy.types.Operator):
    bl_idname = "object.mr_add_area"
    bl_label = "Add Renderman Area"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}
 
    def execute(self, context):
 
        bpy.ops.object.lamp_add(type='AREA')
        bpy.ops.shading.add_renderman_nodetree({'material':None,'lamp':bpy.context.active_object.data},idtype='lamp')
        return {"FINISHED"}

class RM_Add_Hemi(bpy.types.Operator):
    bl_idname = "object.mr_add_hemi"
    bl_label = "Add Renderman Hemi"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}
 
    def execute(self, context):
 
        bpy.ops.object.lamp_add(type='HEMI')
        bpy.ops.shading.add_renderman_nodetree({'material':None,'lamp':bpy.context.active_object.data},idtype='lamp')
        return {"FINISHED"}

class RM_Add_Sky(bpy.types.Operator):
    bl_idname = "object.mr_add_sky"
    bl_label = "Add Renderman Sky"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}
 
    def execute(self, context):
        bpy.ops.object.lamp_add(type='SUN')
        bpy.ops.shading.add_renderman_nodetree({'material':None,'lamp':bpy.context.active_object.data},idtype='lamp')
        bpy.context.object.data.renderman.renderman_type = 'SKY'
        
        
        return {"FINISHED"}

class Add_bxdf(bpy.types.Operator):
    bl_idname = "object.add_bxdf"
    bl_label = "Add BXDF"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}
    
    def get_type_items(self, context):
        items = []
        for nodetype in RendermanPatternGraph.nodetypes.values():
            if nodetype.renderman_node_type == 'bxdf':
                items.append((nodetype.bl_label, nodetype.bl_label,
                              nodetype.bl_label))
        items = sorted(items, key=itemgetter(1))
        return items
    bxdf_name = EnumProperty(items=get_type_items, name="Bxdf Name")
 
    def execute(self, context):
        selection = bpy.context.selected_objects
        bxdf_name = self.properties.bxdf_name
        mat = bpy.data.materials.new(bxdf_name)
        
        bpy.ops.shading.add_renderman_nodetree({'lamp':None, 'material':mat}, idtype='material', bxdf_name=bxdf_name)
        

        for obj in selection:
            if(obj.type not in EXCLUDED_OBJECT_TYPES):
                bpy.ops.object.material_slot_add()

                obj.material_slots[-1].material = mat

        return {"FINISHED"}

class add_GeoLight(bpy.types.Operator):
    bl_idname = "object.addgeoarealight"
    bl_label = "Add GeoAreaLight"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}
 
    bxdf_name = StringProperty(name="Bxdf Name", default="PxrDisney")
 
    def execute(self, context):
        selection = bpy.context.selected_objects
        bxdf_name = self.properties.bxdf_name
        mat = bpy.data.materials.new(bxdf_name)
 
        bpy.ops.shading.add_renderman_nodetree({'lamp':None, 'material':mat}, idtype='material')
        
        matName = mat.name
        nt = bpy.data.node_groups[matName]
        output = None
        for node in nt.nodes:
            if(node.name == "Output"):
                output = node
        geoLight = nt.nodes.new('PxrRectLightLightNode')
        geoLight["exposure"] = 5.0
        geoLight.location[0] -= 300
        geoLight.location[1] -= 420
        if(output is not None):
            nt.links.new(geoLight.outputs[0], output.inputs[1])
        for obj in selection:
            if(obj.type not in EXCLUDED_OBJECT_TYPES):
                bpy.ops.object.material_slot_add() 
                obj.material_slots[-1].material = mat
        return {"FINISHED"}

class Select_Lights(bpy.types.Operator):
    bl_idname = "object.selectlights"
    bl_label = "Select Lights"
 
    Light_Name = bpy.props.StringProperty(default="")
 
    def execute(self, context):
 
        bpy.ops.object.select_all(action='DESELECT')   
        bpy.data.objects[self.Light_Name].select=True
        bpy.context.scene.objects.active=bpy.data.objects[self.Light_Name]
 
        return {'FINISHED'}    
 
 
class Hemi_List_Menu(bpy.types.Menu):
    bl_idname = "object.hemi_list_menu"
    bl_label = "EnvLight list"
 
    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
 
        lamps = [obj for obj in bpy.context.scene.objects if obj.type == "LAMP"]
 
 
        if len(lamps): 
            for lamp in lamps:
                if lamp.data.type == 'HEMI' : 
                    name = lamp.name
                    op = layout.operator("object.selectlights", text = name, icon = 'LAMP_HEMI')
                    op.Light_Name = name
 
        else:
            layout.label("No EnvLight in the Scene")
 
class Area_List_Menu(bpy.types.Menu):
    bl_idname = "object.area_list_menu"
    bl_label = "AreaLight list"
 
    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
 
        lamps = [obj for obj in bpy.context.scene.objects if obj.type == "LAMP"]
 
 
        if len(lamps): 
            for lamp in lamps:
                if lamp.data.type == 'AREA' : 
                    name = lamp.name
                    op = layout.operator("object.selectlights", text = name, icon = 'LAMP_AREA')
                    op.Light_Name = name
 
        else:
            layout.label("No AreaLight in the Scene")
 
class DayLight_List_Menu(bpy.types.Menu):
    bl_idname = "object.daylight_list_menu"
    bl_label = "DayLight list"
 
    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
 
        lamps = [obj for obj in bpy.context.scene.objects if obj.type == "LAMP"]
 
 
        if len(lamps): 
            for lamp in lamps:
                if lamp.data.type == 'SUN' : 
                    name = lamp.name
                    op = layout.operator("object.selectlights", text = name, icon = 'LAMP_SUN')
                    op.Light_Name = name
 
        else:
            layout.label("No Daylight in the Scene")

class Select_Cameras(bpy.types.Operator):
    bl_idname = "object.select_cameras"
    bl_label = "Select Cameras"
 
    Camera_Name = bpy.props.StringProperty(default="")
 
    def execute(self, context):
 
        bpy.ops.object.select_all(action='DESELECT')   
        bpy.data.objects[self.Camera_Name].select=True
        bpy.context.scene.objects.active=bpy.data.objects[self.Camera_Name]
 
        return {'FINISHED'}    
            
class Camera_List_Menu(bpy.types.Menu):
    bl_idname = "object.camera_list_menu"
    bl_label = "Camera list"
 
    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
 
        cameras = [obj for obj in bpy.context.scene.objects if obj.type == "CAMERA"]
 
 
        if len(cameras): 
            for cam in cameras:
                name = cam.name
                op = layout.operator("object.select_cameras", text = name, icon = 'CAMERA_DATA')
                op.Camera_Name = name
 
        else:
            layout.label("No Camera in the Scene")

class DeleteLights(bpy.types.Operator):
    bl_idname = "object.delete_lights"
    bl_label = "Delete Lights"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        
        type_light = bpy.context.object.data.type
        bpy.ops.object.delete()
        
        lamps = [obj for obj in bpy.context.scene.objects if obj.type == "LAMP" and obj.data.type == type_light]
         
        if len(lamps): 
            lamps[0].select=True
            bpy.context.scene.objects.active=lamps[0]
            return {"FINISHED"}
        
        else :
            return {"FINISHED"}

class Deletecameras(bpy.types.Operator):
    bl_idname = "object.delete_cameras"
    bl_label = "Delete Cameras"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}
 
    def execute(self, context):
 
        type_camera = bpy.context.object.data.type
        bpy.ops.object.delete()
 
        camera = [obj for obj in bpy.context.scene.objects if obj.type == "CAMERA" and obj.data.type == type_camera]
 
        if len(camera): 
            camera[0].select=True
            bpy.context.scene.objects.active=camera[0]
            return {"FINISHED"}
 
        else :
            return {"FINISHED"}
        
 
class AddCamera(bpy.types.Operator):
    bl_idname = "object.add_prm_camera"
    bl_label = "Add Camera"
    bl_description = "Add a Camera in the Scene"
    bl_options = {"REGISTER", "UNDO"}
 
    def execute(self, context):
        
        bpy.context.space_data.lock_camera=False
        
        bpy.ops.object.camera_add()
 
        bpy.ops.view3d.object_as_camera()
         
        bpy.ops.view3d.viewnumpad(type="CAMERA")
         
        bpy.ops.view3d.camera_to_view()

        bpy.context.object.data.clip_end = 10000
        bpy.context.object.data.lens = 85
        

        return {"FINISHED"}

# Menus
compile_shader_menu_func = (lambda self, context: self.layout.operator(
    TEXT_OT_compile_shader.bl_idname))


def register():
    bpy.types.TEXT_MT_text.append(compile_shader_menu_func)
    bpy.types.TEXT_MT_toolbox.append(compile_shader_menu_func)
    bpy.types.INFO_MT_help.append(menu_draw)

def unregister():
    bpy.types.TEXT_MT_text.remove(compile_shader_menu_func)
    bpy.types.TEXT_MT_toolbox.remove(compile_shader_menu_func)
    bpy.types.INFO_MT_help.remove(menu_draw)
