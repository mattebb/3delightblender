from ..rfb_logger import rfb_log
from ..rman_utils.osl_utils import readOSO
from . import rman_socket_utils
from .. import rman_render
from ..rman_utils import string_utils
from ..rman_utils import shadergraph_utils
from ..icons.icons import load_icons
from bpy.types import Menu
from bpy.props import EnumProperty, StringProperty, CollectionProperty
import _cycles
import bpy
import os
import shutil
import tempfile

NODE_LAYOUT_SPLIT = 0.5

# Base class for all custom nodes in this tree type.
# Defines a poll function to enable instantiation.
class RendermanShadingNode(bpy.types.ShaderNode):
    bl_label = 'Output'

    def update_mat(self, mat):
        if self.renderman_node_type == 'bxdf' and self.outputs['Bxdf'].is_linked:
            mat.specular_color = [1, 1, 1]
            mat.diffuse_color = [1, 1, 1, 1]
            #FIXME mat.use_transparency = False
            mat.specular_intensity = 0
            #mat.diffuse_intensity = 1

            if hasattr(self, "baseColor"):
                mat.diffuse_color[:3] = [i for i in self.baseColor]
            elif hasattr(self, "emitColor"):
                mat.diffuse_color[:3] = [i for i in self.emitColor]
            elif hasattr(self, "diffuseColor"):
                mat.diffuse_color = (*self.diffuseColor, 1.0)
            elif hasattr(self, "midColor"):
                mat.diffuse_color[:3] = [i for i in self.midColor]
            elif hasattr(self, "transmissionColor"):
                mat.diffuse_color[:3] = [i for i in self.transmissionColor]
            elif hasattr(self, "frontColor"):
                mat.diffuse_color[:3] = [i for i in self.frontColor]

            # specular intensity
            if hasattr(self, "specular"):
                mat.specular_intensity = self.specular
            elif hasattr(self, "SpecularGainR"):
                mat.specular_intensity = self.specularGainR
            elif hasattr(self, "reflectionGain"):
                mat.specular_intensity = self.reflectionGain

            # specular color
            if hasattr(self, "specularColor"):
                mat.specular_color[:3] = [i for i in self.specularColor]
            elif hasattr(self, "reflectionColor"):
                mat.specular_color[:3] = [i for i in self.reflectionColor]

            if self.bl_idname in ["PxrGlassBxdfNode", "PxrLMGlassBxdfNode"]:
                #FIXME mat.use_transparency = True
                mat.diffuse_color[3] = .5#alpha

            if self.bl_idname == "PxrLMMetalBxdfNode":
                mat.diffuse_color = [0, 0, 0, 1]
                mat.specular_intensity = 1
                mat.specular_color = self.specularColor
                mat.mirror_color = [1, 1, 1]

            elif self.bl_idname == "PxrLMPlasticBxdfNode":
                mat.specular_intensity = 1

    # all the properties of a shader will go here, also inputs/outputs
    # on connectable props will have the same name
    # node_props = None
    def draw_buttons(self, context, layout):
        icons = load_icons()
        nt = self.id_data
        out_node = shadergraph_utils.find_node_from_nodetree(nt, 'RendermanOutputNode')
        if out_node and self.name == out_node.solo_node_name:
            rman_icon = icons.get('rman_solo_on.png')
            layout.label(text='', icon_value=rman_icon.icon_id) 
        else:
            rman_icon = icons.get('out_%s.png' % self.bl_label, None )
            if not rman_icon:
                rman_icon = icons.get('out_unknown.png')
            layout.label(text='', icon_value=rman_icon.icon_id)             
        self.draw_nonconnectable_props(context, layout, self.prop_names)
        if self.bl_idname == "PxrOSLPatternNode":
            layout.operator("node.refresh_osl_shader")

    def draw_buttons_ext(self, context, layout):
        icons = load_icons()
        rman_icon = icons.get('out_%s.png' % self.bl_label, None )
        if not rman_icon:
            rman_icon = icons.get('out_unknown.png')
        layout.label(text='', icon_value=rman_icon.icon_id)             
        self.draw_nonconnectable_props(context, layout, self.prop_names)

    def draw_nonconnectable_props(self, context, layout, prop_names):   
        if self.bl_idname in ['PxrLayerPatternOSLNode', 'PxrSurfaceBxdfNode']:
            col = layout.column(align=True)
            for prop_name in prop_names:
                if prop_name not in self.inputs:
                    prop_meta = self.prop_meta[prop_name]
                    if 'widget' in prop_meta and prop_meta['widget'] == 'null' or \
                        'hidden' in prop_meta and prop_meta['hidden']:
                        continue
                    for name in getattr(self, prop_name):
                        if name.startswith('enable'):
                            col.prop(self, name, text=prop_name.split('.')[-1])
                            break
            return

        if self.bl_idname == "PxrOSLPatternNode" or self.bl_idname == "PxrSeExprPatternNode":
            prop = getattr(self, "codetypeswitch")
            layout.prop(self, "codetypeswitch")
            if getattr(self, "codetypeswitch") == 'INT':
                prop = getattr(self, "internalSearch")
                layout.prop_search(
                    self, "internalSearch", bpy.data, "texts", text="")
            elif getattr(self, "codetypeswitch") == 'EXT':
                prop = getattr(self, "shadercode")
                layout.prop(self, "shadercode")
            elif getattr(self, "codetypeswitch") == 'NODE':
                layout.prop(self, "expression")
        else:
            is_pxrramp = (self.plugin_name == 'PxrRamp')
            for prop_name in prop_names:
                prop_meta = self.prop_meta[prop_name]
                if 'widget' in prop_meta:
                    if prop_meta['widget'] == 'null' or \
                        'hidden' in prop_meta and prop_meta['hidden']:
                        continue
                    elif prop_meta['widget'] == 'colorramp':
                        node_group = bpy.data.node_groups[self.rman_fake_node_group]
                        ramp_name =  getattr(self, prop_name)
                        ramp_node = node_group.nodes[ramp_name]
                        layout.template_color_ramp(
                                ramp_node, 'color_ramp')    
                    elif prop_meta['widget'] == 'floatramp':
                        node_group = bpy.data.node_groups[self.rman_fake_node_group]
                        ramp_name =  getattr(self, prop_name)
                        ramp_node = node_group.nodes[ramp_name]
                        layout.template_curve_mapping(
                                ramp_node, 'mapping')                                                 

                if prop_name not in self.inputs:
                    if prop_meta['renderman_type'] == 'page':
                        if is_pxrramp:
                            # don't' show the old color ramp
                            if prop_name == 'Color Ramp (Manual)':
                                continue

                        ui_prop = prop_name + "_uio"
                        ui_open = getattr(self, ui_prop)
                        icon = 'DISCLOSURE_TRI_DOWN' if ui_open \
                            else 'DISCLOSURE_TRI_RIGHT'

                        split = layout.split(factor=NODE_LAYOUT_SPLIT)
                        row = split.row()
                        row.prop(self, ui_prop, icon=icon, text='',
                                 icon_only=True, emboss=False, slider=True)
                        row.label(text=prop_name.split('.')[-1] + ':')

                        if ui_open:
                            prop = getattr(self, prop_name)
                            self.draw_nonconnectable_props(
                                context, layout, prop)

                    
                    elif prop_meta['renderman_type'] == 'array':
                        row = layout.row(align=True)
                        col = row.column()
                        row = col.row()
                        arraylen = getattr(self, '%s_arraylen' % prop_name)             
                        row.label(text='%s Size' % prop_name)               
                        row.prop(self, '%s_arraylen' % prop_name, text='')

                    elif "Subset" in prop_name and prop_meta['type'] == 'string':
                        layout.prop_search(self, prop_name, bpy.data.scenes[0].renderman,
                                           "object_groups")
                    else:
                        if is_pxrramp and prop_name == 'useNewRamp':
                            # don't show useNewRamp param
                            continue
                        layout.prop(self, prop_name, slider=True)

    def copy(self, node):
        pass
    #    self.inputs.clear()
    #    self.outputs.clear()

    def RefreshNodes(self, context, nodeOR=None, materialOverride=None):

        # Compile shader.        If the call was from socket draw get the node
        # information anther way.
        if hasattr(context, "node"):
            node = context.node
        else:
            node = nodeOR

        out_path = string_utils.expand_string('{OUT}', asFilePath=True)
        compile_path = os.path.join(out_path, "shaders")

        if os.path.exists(compile_path):
            pass
        else:
            os.mkdir(compile_path)

        if getattr(node, "codetypeswitch") == "EXT":
            osl_path = user_path(getattr(node, 'shadercode'))
            FileName = os.path.basename(osl_path)
            FileNameNoEXT = os.path.splitext(FileName)[0]
            FileNameOSO = FileNameNoEXT
            FileNameOSO += ".oso"
            export_path = os.path.join(compile_path, FileNameOSO)
            if os.path.splitext(FileName)[1] == ".oso":
                out_file = os.path.join(compile_path, FileNameOSO)
                if not os.path.exists(out_file) or not os.path.samefile(osl_path, out_file):
                    shutil.copy(osl_path, out_file)
                # Assume that the user knows what they were doing when they
                # compiled the osl file.
                ok = True
            else:
                ok = node.compile_osl(osl_path, compile_path)
        elif getattr(node, "codetypeswitch") == "INT" and node.internalSearch:
            script = bpy.data.texts[node.internalSearch]
            osl_path = bpy.path.abspath(
                script.filepath, library=script.library)
            if script.is_in_memory or script.is_dirty or \
                    script.is_modified or not os.path.exists(osl_path):
                osl_file = tempfile.NamedTemporaryFile(
                    mode='w', suffix=".osl", delete=False)
                osl_file.write(script.as_string())
                osl_file.close()
                FileNameNoEXT = os.path.splitext(script.name)[0]
                FileNameOSO = FileNameNoEXT
                FileNameOSO += ".oso"
                node.plugin_name = FileNameNoEXT
                ok = node.compile_osl(osl_file.name, compile_path, script.name)
                export_path = os.path.join(compile_path, FileNameOSO)
                os.remove(osl_file.name)
            else:
                ok = node.compile_osl(osl_path, compile_path)
                FileName = os.path.basename(osl_path)
                FileNameNoEXT = os.path.splitext(FileName)[0]
                node.plugin_name = FileNameNoEXT
                FileNameOSO = FileNameNoEXT
                FileNameOSO += ".oso"
                export_path = os.path.join(compile_path, FileNameOSO)
        else:
            ok = False
            rfb_log().error("OSL: Shader cannot be compiled. Shader name not specified")
        # If Shader compiled successfully then update node.
        if ok:
            rfb_log().info("OSL: Shader Compiled Successfully!")
            # Reset the inputs and outputs
            node.outputs.clear()
            node.inputs.clear()
            # Read in new properties
            prop_names, shader_meta = readOSO(export_path)
            rfb_log().debug('OSL: %s MetaInfo: %s' % (str(prop_names), str(shader_meta)))
            # Set node name to shader name
            node.label = shader_meta["shader"]
            node.plugin_name = shader_meta["shader"]
            # Generate new inputs and outputs
            setattr(node, 'shader_meta', shader_meta)
            node.setOslProps(prop_names, shader_meta)
        else:
            rfb_log().error("OSL: NODE COMPILATION FAILED")

    def compile_osl(self, inFile, outPath, nameOverride=""):
        if not nameOverride:
            FileName = os.path.basename(inFile)
            FileNameNoEXT = os.path.splitext(FileName)[0]
            out_file = os.path.join(outPath, FileNameNoEXT)
            out_file += ".oso"
        else:
            FileNameNoEXT = os.path.splitext(nameOverride)[0]
            out_file = os.path.join(outPath, FileNameNoEXT)
            out_file += ".oso"
        ok = _cycles.osl_compile(inFile, out_file)

        return ok

    def update(self):
        rfb_log().debug("UPDATING: %s" % self.name)

    @classmethod
    def poll(cls, ntree):
        if hasattr(ntree, 'bl_idname'):
            return ntree.bl_idname == 'ShaderNodeTree'
        else:
            return True

    def setOslProps(self, prop_names, shader_meta):
        for prop_name in prop_names:
            prop_type = shader_meta[prop_name]["type"]
            if shader_meta[prop_name]["IO"] == "out":
                self.outputs.new(
                    rman_socket_utils.__RMAN_SOCKET_MAP__[prop_type], prop_name)
            else:
                prop_default = shader_meta[prop_name]["default"]
                if prop_type == "float":
                    prop_default = float(prop_default)
                elif prop_type == "int":
                    prop_default = int(float(prop_default))

                if prop_type == "matrix":
                    self.inputs.new(rman_socket_utils.__RMAN_SOCKET_MAP__["struct"], prop_name, prop_name)
                elif prop_type == "void":
                    pass
                elif 'lockgeom' in shader_meta[prop_name] and shader_meta[prop_name]['lockgeom'] == 0:
                    pass
                else:
                    input = self.inputs.new(rman_socket_utils.__RMAN_SOCKET_MAP__[shader_meta[prop_name]["type"]],
                                            prop_name, prop_name)
                    input.default_value = prop_default
                    if prop_type == 'struct' or prop_type == 'point':
                        input.hide_value = True
                    input.renderman_type = prop_type
        rfb_log().debug('osl', "Shader: ", shader_meta["shader"], "Properties: ",
              prop_names, "Shader meta data: ", shader_meta)
        compileLocation = self.name + "Compile"


class RendermanOutputNode(RendermanShadingNode):
    bl_label = 'RenderMan Material'
    renderman_node_type = 'output'
    bl_icon = 'MATERIAL'
    node_tree = None
    new_links = []

    def update_solo_node_name(self, context):
        rr = rman_render.RmanRender.get_rman_render()        
        if rr.rman_interactive_running:
            mat = getattr(bpy.context, 'material', None)
            if mat:
                rr.rman_scene_sync.update_material(mat)       

    solo_node_name: StringProperty(name='Solo Node', update=update_solo_node_name)
    solo_node_output: StringProperty(name='Solo Node Output')

    def init(self, context):
        self._init_inputs()   

    def _init_inputs(self):
        input = self.inputs.new('RendermanNodeSocketBxdf', 'Bxdf')
        input.hide_value = True
        input = self.inputs.new('RendermanNodeSocketLight', 'Light')
        input.hide_value = True
        input = self.inputs.new('RendermanNodeSocketDisplacement', 'Displacement')
        input.hide_value = True
        input = self.inputs.new('RendermanNodeSocketLightFilter', 'LightFilter')
        input.hide_value = True    

    def draw_buttons(self, context, layout):
        return

    def draw_buttons_ext(self, context, layout):
        return

    def insert_link(self, link):
        if link in self.new_links:
            pass
        else:
            self.new_links.append(link)

    # when a connection is made or removed see if we're in IPR mode and issue
    # updates
    def update(self):
        for link in self.new_links:
            if link.from_node.renderman_node_type != link.to_socket.renderman_type:
                # FIXME: this should removed eventually
                if link.to_socket.bl_idname == 'RendermanShaderSocket':
                    continue
                node_tree = self.id_data
                node_tree.links.remove(link)
        
        self.new_links.clear()

        # This sucks. There doesn't seem to be a way to tag the material
        # it needs updating, so we manually issue an edit
        rr = rman_render.RmanRender.get_rman_render()        
        if rr.rman_interactive_running:
            mat = getattr(bpy.context, 'material', None)
            if mat:
                rr.rman_scene_sync.update_material(mat)

class RendermanIntegratorsOutputNode(RendermanShadingNode):
    bl_label = 'RenderMan Integrators'
    renderman_node_type = 'integrators_output'
    bl_icon = 'MATERIAL'
    node_tree = None
    new_links = []

    def init(self, context):
        input = self.inputs.new('RendermanNodeSocketIntegrator', 'Integrator')

    def draw_buttons(self, context, layout):
        return

    def draw_buttons_ext(self, context, layout):   
        return

    def insert_link(self, link):
        if link in self.new_links:
            pass
        else:
            self.new_links.append(link)

    def update(self):
        for link in self.new_links:
            from_node_type = getattr(link.from_socket, 'renderman_type', None)
            if not from_node_type:
                continue            
            if from_node_type != 'integrator':
                node_tree = self.id_data
                node_tree.links.remove(link)

        self.new_links.clear()    
        world = getattr(bpy.context, 'world', None)
        if world:
            world.update_tag()

class RendermanSamplefiltersOutputNode(RendermanShadingNode):
    bl_label = 'RenderMan Sample Filters'
    renderman_node_type = 'samplefilters_output'
    bl_icon = 'MATERIAL'
    node_tree = None
    new_links = []

    def init(self, context):
        input = self.inputs.new('RendermanNodeSocketSampleFilter', 'samplefilter[0]')
        input.hide_value = True

    def add_input(self):
        input = self.inputs.new('RendermanNodeSocketSampleFilter', 'samplefilter[%d]' % (len(self.inputs)))
        input.hide_value = True

    def remove_input(self):
        socket = self.inputs[len(self.inputs)-1]
        if socket.is_linked:
            old_node = socket.links[0].from_node
            node_tree = self.id_data
            nodetree.remove(old_node)
        self.inputs.remove( socket )

    def draw_buttons(self, context, layout):
        row = layout.row(align=True)
        col = row.column()
        col.operator('node.add_samplefilter_node_socket', text='Add')
        col = row.column()
        col.enabled = len(self.inputs) > 1
        col.operator('node.remove_samplefilter_node_socket', text='Remove')
        return

    def draw_buttons_ext(self, context, layout):
        row = layout.row(align=True)
        col = row.column()
        col.operator('node.add_samplefilter_node_socket', text='Add')
        col = row.column()
        col.enabled = len(self.inputs) > 1
        col.operator('node.remove_samplefilter_node_socket', text='Remove')      
        return

    def insert_link(self, link):
        if link in self.new_links:
            pass
        else:
            self.new_links.append(link)

    def update(self):
        for link in self.new_links:
            from_node_type = getattr(link.from_socket, 'renderman_type', None)
            if not from_node_type:
                continue            
            if from_node_type != 'samplefilter':
                node_tree = self.id_data
                node_tree.links.remove(link)

        self.new_links.clear()  
        world = getattr(bpy.context, 'world', None)
        if world:
            world.update_tag()

class RendermanDisplayfiltersOutputNode(RendermanShadingNode):
    bl_label = 'RenderMan Display Filters'
    renderman_node_type = 'displayfilters_output'
    bl_icon = 'MATERIAL'
    node_tree = None
    new_links = []

    def init(self, context):
        input = self.inputs.new('RendermanNodeSocketDisplayFilter', 'displayfilter[0]')
        input.hide_value = True

    def add_input(self):
        input = self.inputs.new('RendermanNodeSocketDisplayFilter', 'displayfilter[%d]' % (len(self.inputs)))
        input.hide_value = True

    def remove_input(self):
        socket = self.inputs[len(self.inputs)-1]
        if socket.is_linked:
            old_node = socket.links[0].from_node
            node_tree = self.id_data
            nodetree.remove(old_node)
        self.inputs.remove( socket )        

    def draw_buttons(self, context, layout):
        row = layout.row(align=True)
        col = row.column()
        col.operator('node.add_displayfilter_node_socket', text='Add')
        col = row.column()
        col.enabled = len(self.inputs) > 1
        col.operator('node.remove_displayfilter_node_socket', text='Remove')        
        return

    def draw_buttons_ext(self, context, layout):
        row = layout.row(align=True)
        col = row.column()
        col.operator('node.add_displayfilter_node_socket', text='Add')
        col = row.column()
        col.enabled = len(self.inputs) > 1
        col.operator('node.remove_displayfilter_node_socket', text='Remove')      
        return

    def insert_link(self, link):
        if link in self.new_links:
            pass
        else:
            self.new_links.append(link)

    def update(self):
        for link in self.new_links:
            from_node_type = getattr(link.from_socket, 'renderman_type', None)
            if not from_node_type:
                continue
            if from_node_type != 'displayfilter':
                node_tree = self.id_data
                node_tree.links.remove(link)

        self.new_links.clear()     
        world = getattr(bpy.context, 'world', None)
        if world:
            world.update_tag()

# Final output node, used as a dummy to find top level shaders
class RendermanBxdfNode(RendermanShadingNode):
    bl_label = 'Bxdf'
    renderman_node_type = 'bxdf'

    shading_compatibility = {'NEW_SHADING'}


class RendermanDisplacementNode(RendermanShadingNode):
    bl_label = 'Displacement'
    renderman_node_type = 'displace'

# Final output node, used as a dummy to find top level shaders


class RendermanPatternNode(RendermanShadingNode):
    bl_label = 'Texture'
    renderman_node_type = 'pattern'
    bl_type = 'TEX_IMAGE'
    bl_static_type = 'TEX_IMAGE'


class RendermanLightNode(RendermanShadingNode):
    bl_label = 'Light'
    renderman_node_type = 'light'

class RendermanLightfilterNode(RendermanShadingNode):
    bl_label = 'LightFilter'
    renderman_node_type = 'lightfilter'

class RendermanDisplayfilterNode(RendermanShadingNode):
    bl_label = 'DisplayFilter'
    renderman_node_type = 'displayfilter'

class RendermanSamplefilterNode(RendermanShadingNode):
    bl_label = 'SampleFilter'
    renderman_node_type = 'samplefilter'    

class RendermanIntegratorNode(RendermanShadingNode):
    bl_label = 'Integrator'
    renderman_node_type = 'integrator'

classes = [
    RendermanShadingNode,
    RendermanOutputNode,
    RendermanBxdfNode,
    RendermanDisplacementNode,
    RendermanPatternNode,
    RendermanLightNode,
    RendermanLightfilterNode,
    RendermanDisplayfilterNode,
    RendermanSamplefilterNode,
    RendermanSamplefiltersOutputNode,
    RendermanDisplayfiltersOutputNode,
    RendermanIntegratorsOutputNode,
    RendermanIntegratorNode,
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