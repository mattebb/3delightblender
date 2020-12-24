import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
from ..rfb_utils import shadergraph_utils
from .. import rman_bl_nodes
from ..rman_constants import RMAN_STYLIZED_FILTERS, RMAN_STYLIZED_PATTERNS, RMAN_UTILITY_PATTERN_NAMES  
from ..rman_config import __RMAN_STYLIZED_TEMPLATES__

class PRMAN_OT_Enable_Sylized_Looks(bpy.types.Operator):
    bl_idname = "scene.rman_enable_stylized_looks"
    bl_label = "Enable Stylized Looks"
    bl_description = "Enable stylized looks. Objects still need to have a stylzed pattern connected to their material network, and stylized filters need to be added to the scene."
    bl_options = {'INTERNAL'}

    open_editor: BoolProperty(name="", default=False)
    
    def execute(self, context):
        scene = context.scene
        rm = scene.renderman
        rm.render_rman_stylized = 1
        bpy.ops.renderman.dspy_displays_reload('EXEC_DEFAULT')        
        if self.properties.open_editor:
            bpy.ops.scene.rman_open_stylized_editor('INVOKE_DEFAULT')

        return {"FINISHED"} 

class PRMAN_OT_Use_Sylized_Template(bpy.types.Operator):

    bl_idname = "scene.rman_use_stylized_template"
    bl_label = "Use Stylize Template"
    bl_description = "Stylized Template. This will enable stylized looks, attach a stylized pattern to the current selected objects, and add the stylized filters."
    bl_options = {'INTERNAL'}    

    def rman_stylized_templates(self, context):
        items = []
        for nm, settings in __RMAN_STYLIZED_TEMPLATES__.items():
            items.append((nm, nm, ""))        
        return items      

    stylized_template: EnumProperty(name="", items=rman_stylized_templates)    

    def execute(self, context):
        scene = context.scene
        rm = scene.renderman
        rm.render_rman_stylized = 1
        bpy.ops.renderman.dspy_displays_reload('EXEC_DEFAULT')        

        world = scene.world
        bpy.ops.node.rman_attach_stylized_pattern('EXEC_DEFAULT', stylized_pattern=self.properties.stylized_template)
        bpy.ops.node.rman_add_stylized_filter('EXEC_DEFAULT', filter_name=self.properties.stylized_template)

        world.update_tag()
        bpy.ops.scene.rman_open_stylized_editor('INVOKE_DEFAULT')

        return {"FINISHED"}     


class PRMAN_OT_Disable_Sylized_Looks(bpy.types.Operator):
    bl_idname = "scene.rman_disable_stylized_looks"
    bl_label = "Disable Stylized Looks"
    bl_description = "Disable stylized looks."
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        scene = context.scene
        rm = scene.renderman
        rm.render_rman_stylized = 0
        world = scene.world
        world.update_tag()
        bpy.ops.renderman.dspy_displays_reload('EXEC_DEFAULT')        

        return {"FINISHED"}                   

class PRMAN_OT_Attach_Stylized_Pattern(bpy.types.Operator):
    bl_idname = "node.rman_attach_stylized_pattern"
    bl_label = "Attach Stylized Pattern"
    bl_description = "Attach a stylized pattern node to your material network."
    bl_options = {'INTERNAL'}

    def rman_stylized_patterns(self, context):
        items = []
        i = 1

        items.append(("", "Patterns", "", "", 0))
        for f in RMAN_STYLIZED_PATTERNS:
            items.append((f, f, "", "", i))
            i += 1

        items.append(("", "Templates", "", "", 0))
        for nm, settings in __RMAN_STYLIZED_TEMPLATES__.items():
            items.append((nm, nm, "", "", i))        
            i += 1  
        return items      

    stylized_pattern: EnumProperty(name="", items=rman_stylized_patterns)

    def attach_pattern(self, context, ob):
        if len(ob.material_slots) < 1:
            return
        mat = ob.material_slots[0].material
        nt = mat.node_tree
        output = shadergraph_utils.is_renderman_nodetree(mat)
        if not output:
            return
        socket = output.inputs[0]
        if not socket.is_linked:
            return

        link = socket.links[0]
        node = link.from_node 
        prop_name = ''

        pattern_node_name = None
        pattern_settings = None
        if self.properties.stylized_pattern in RMAN_STYLIZED_PATTERNS:
            pattern_node_name = rman_bl_nodes.__BL_NODES_MAP__[self.properties.stylized_pattern]
        elif self.properties.stylized_pattern in __RMAN_STYLIZED_TEMPLATES__:
            settings = __RMAN_STYLIZED_TEMPLATES__[self.properties.stylized_pattern]
            pattern_tmplt = settings['patterns'] 
            for k, v in pattern_tmplt.items():  
                pattern_node_name = rman_bl_nodes.__BL_NODES_MAP__[k]      
                pattern_settings = v
                break
        else:
            return

        for nm in RMAN_UTILITY_PATTERN_NAMES:
            if hasattr(node, nm):
                prop_name = nm

            if shadergraph_utils.has_stylized_pattern_node(ob, node=node):
                continue

            prop_meta = node.prop_meta[prop_name]
            if prop_meta['renderman_type'] == 'array':

                array_len = getattr(node, '%s_arraylen' % prop_name)
                array_len += 1
                setattr(node, '%s_arraylen' % prop_name, array_len)      
                pattern_node = nt.nodes.new(pattern_node_name)   

                if pattern_settings:
                    for param_name, param_settings in pattern_settings['params'].items():
                        val = param_settings['value']
                        setattr(pattern_node, param_name, val)
            
                sub_prop_nm = '%s[%d]' % (prop_name, array_len-1)     
                nt.links.new(pattern_node.outputs['resultAOV'], node.inputs[sub_prop_nm])      

            else:
                if node.inputs[prop_name].is_linked:
                    continue

                pattern_node = nt.nodes.new(pattern_node_name) 

                if pattern_settings:                 
                    for param_name, param_settings in pattern_settings['params'].items():
                        val = param_settings['value']
                        setattr(pattern_node, param_name, val)
            
                nt.links.new(pattern_node.outputs['resultAOV'], node.inputs[prop_name])

    
    def execute(self, context):
        scene = context.scene
        selected_objects = context.selected_objects

        obj = getattr(context, "selected_obj", None)
        if obj:
            self.attach_pattern(context, obj)         
        else:
            for ob in selected_objects:
                self.attach_pattern(context, ob)         

        op = getattr(context, 'op_ptr', None)
        if op:
            op.selected_obj_name = '0'

        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        context.view_layer.objects.active = None               

        return {"FINISHED"}         

class PRMAN_OT_Add_Stylized_Filter(bpy.types.Operator):
    bl_idname = "node.rman_add_stylized_filter"
    bl_label = "Add Stylized Filter"
    bl_description = "Add a stylized filter to the scene."
    bl_options = {'INTERNAL'}

    def rman_stylized_filters(self, context):
        items = []
        i = 1

        items.append(("", "Filters", "", "", 0))
        for f in RMAN_STYLIZED_FILTERS:
            items.append((f, f, "", "", i))
            i += 1

        items.append(("", "Templates", "", "", 0))
        for nm, settings in __RMAN_STYLIZED_TEMPLATES__.items():
            items.append((nm, nm, "", "", i))        
            i += 1

        return items

    filter_name: EnumProperty(items=rman_stylized_filters, name="Filter Name")
    node_name: StringProperty(name="", default="")
    
    def execute(self, context):
        scene = context.scene
        world = scene.world
        rm = world.renderman
        nt = world.node_tree

        output = shadergraph_utils.find_node(world, 'RendermanDisplayfiltersOutputNode')
        if not output:
            bpy.ops.material.rman_add_rman_nodetree('EXEC_DEFAULT', idtype='world')
            output = shadergraph_utils.find_node(world, 'RendermanDisplayfiltersOutputNode') 

        use_template = False
        if self.properties.filter_name in RMAN_STYLIZED_FILTERS:
            use_template = False
        elif self.properties.filter_name in __RMAN_STYLIZED_TEMPLATES__:
            use_template = True
        else:
            return {"FINISHED"}            

        if use_template:
            settings = __RMAN_STYLIZED_TEMPLATES__[self.properties.filter_name]
            display_filters = settings['display_filters']
            for node_name, df_settings in display_filters.items():
                if node_name in nt.nodes:
                    continue
                node_type = df_settings['node']          
                filter_node_name = rman_bl_nodes.__BL_NODES_MAP__[node_type]
                filter_node = nt.nodes.new(filter_node_name)       
                filter_node.name = node_name
                for param_name, param_settings in df_settings['params'].items():
                    val = param_settings['value']
                    setattr(filter_node, param_name, val)

                free_socket = None
                for i, socket in enumerate(output.inputs):
                    if not socket.is_linked:
                        free_socket = socket
                        break

                if not free_socket:
                    bpy.ops.node.rman_add_displayfilter_node_socket('EXEC_DEFAULT')
                    free_socket = output.inputs[len(output.inputs)-1]

                nt.links.new(filter_node.outputs[0], free_socket)                  
        else:

            filter_name = self.properties.filter_name
            filter_node_name = rman_bl_nodes.__BL_NODES_MAP__[filter_name]
            filter_node = nt.nodes.new(filter_node_name) 

            free_socket = None
            for i, socket in enumerate(output.inputs):
                if not socket.is_linked:
                    free_socket = socket
                    break

            if not free_socket:
                bpy.ops.node.rman_add_displayfilter_node_socket('EXEC_DEFAULT')
                free_socket = output.inputs[len(output.inputs)-1]

            nt.links.new(filter_node.outputs[0], free_socket)
            if self.properties.node_name != "":
                filter_node.name = self.properties.node_name

        op = getattr(context, 'op_ptr', None)
        if op:
            op.stylized_filter = filter_node.name

        world.update_tag()

        return {"FINISHED"}       

classes = [
    PRMAN_OT_Enable_Sylized_Looks,
    PRMAN_OT_Use_Sylized_Template,
    PRMAN_OT_Disable_Sylized_Looks,
    PRMAN_OT_Attach_Stylized_Pattern,
    PRMAN_OT_Add_Stylized_Filter
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