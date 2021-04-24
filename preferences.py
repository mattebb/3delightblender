# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 - 2021 Pixar
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
import sys
import os
from bpy.types import AddonPreferences
from bpy.props import CollectionProperty, BoolProperty, StringProperty, FloatProperty
from bpy.props import IntProperty, PointerProperty, EnumProperty, FloatVectorProperty

from .rfb_utils import envconfig_utils
from . import rfb_logger
from . import rfb_icons

class RendermanPreferencePath(bpy.types.PropertyGroup):
    path: StringProperty(name="", subtype='DIR_PATH')

class RendermanDeviceDesc(bpy.types.PropertyGroup):
    name: StringProperty(name="", default="")
    id: IntProperty(default=-1)
    version_major: IntProperty(default=0)
    version_minor: IntProperty(default=0)
    use: BoolProperty(name="Use", default=False)

class RendermanPreferences(AddonPreferences):
    bl_idname = __package__

    def find_xpu_cpu_devices(self):
        # for now, there's only one CPU
        if len(self.rman_xpu_cpu_devices) < 1:
            device = self.rman_xpu_cpu_devices.add()
            device.name = "CPU 0"
            device.id = 0
            device.use = True

    def find_xpu_gpu_devices(self):
        try:
            import rman

            count = rman.pxrcore.GetGpgpuCount(rman.pxrcore.k_cuda)
            gpu_device_names = list()

            # try and add ones that we don't know about
            for i in range(count):
                desc = rman.pxrcore.GpgpuDescriptor()
                rman.pxrcore.GetGpgpuDescriptor(rman.pxrcore.k_cuda, i, desc)
                gpu_device_names.append(desc.name)

                found = False
                for device in self.rman_xpu_gpu_devices:
                    if device.name == desc.name:
                        found = True
                        break

                if not found:
                    device = self.rman_xpu_gpu_devices.add()
                    device.name = desc.name
                    device.version_major = desc.major
                    device.version_minor = desc.minor
                    device.id = i
                    if len(self.rman_xpu_gpu_devices) == 1:
                        # always use the first one, if this is our first time adding
                        # gpus
                        device.use = True

            # now, try and remove devices that no longer exist
            name_list = [device.name for device in self.rman_xpu_gpu_devices]
            for nm in name_list:
                if nm not in gpu_device_names:
                    self.rman_xpu_gpu_devices.remove(self.rman_xpu_gpu_devices.find(nm))

        except Exception as e:
            rfb_logger.rfb_log().debug("Exception when getting GPU devices: %s" % str(e))
            pass

    def find_xpu_devices(self):
        self.find_xpu_cpu_devices()
        self.find_xpu_gpu_devices()


    # find the renderman options installed
    def find_installed_rendermans(self, context):
        options = [('NEWEST', 'Newest Version Installed',
                    'Automatically updates when new version installed. NB: If an RMANTREE environment variable is set, this will always take precedence.')]
        for vers, path in envconfig_utils.get_installed_rendermans():
            options.append((path, vers, path))
        return options

    rman_xpu_cpu_devices: bpy.props.CollectionProperty(type=RendermanDeviceDesc)
    rman_xpu_gpu_devices: bpy.props.CollectionProperty(type=RendermanDeviceDesc)

    def fill_gpu_devices(self, context):
        items = []
        items.append(('-1', 'None', ''))
        for device in self.rman_xpu_gpu_devices:
            items.append(('%d' % device.id, '%s (%d.%d)' % (device.name, device.version_major, device.version_minor), ''))
                  
        return items

    rman_xpu_gpu_selection: EnumProperty(name="GPU Device",
                                        items=fill_gpu_devices
                                        )

    rman_xpu_device: EnumProperty(name="Devices",
                                description="Select category",
                                items=[
                                    ("CPU", "CPU", ""),
                                    ("GPU", "GPU", "")
                                ]
                                )

    rmantree_choice: EnumProperty(
        name='RenderMan Version to use',
        description='Leaving as "Newest" will automatically update when you install a new RenderMan version',
        # default='NEWEST',
        items=find_installed_rendermans
    )

    rmantree_method: EnumProperty(
        name='RenderMan Location',
        description='''How RenderMan should be detected.  Most users should leave to "Detect". 
                    Users should restart Blender after making a change.
                    ''',
        items=[('ENV', 'Get From RMANTREE Environment Variable',
                'This will use the RMANTREE set in the enviornment variables'),
                ('DETECT', 'Choose From Installed', 
                '''This will scan for installed RenderMan locations to choose from.'''),
                ('MANUAL', 'Set Manually', 'Manually set the RenderMan installation (for expert users)')],
        default='ENV')

    path_rmantree: StringProperty(
        name="RMANTREE Path",
        description="Path to RenderMan Pro Server installation folder",
        subtype='DIR_PATH',
        default='')

    draw_ipr_text: BoolProperty(
        name="Draw IPR Text",
        description="Draw notice on View3D when IPR is active",
        default=True)

    draw_panel_icon: BoolProperty(
        name="Draw Panel Icon",
        description="Draw an icon on RenderMan Panels",
        default=True)

    path_fallback_textures_path: StringProperty(
        name="Fallback Texture Path",
        description="Fallback path for textures, when the current directory is not writable",
        subtype='FILE_PATH',
        default=os.path.join('<OUT>', 'textures'))        

    path_fallback_textures_path_always: BoolProperty(
        name="Always Fallback",
        description="Always use the fallback texture path regardless",
        default=False)              

    rman_scene_version_padding: IntProperty(
        name="Version Padding",
        description="The number of zeros to pad the version token",
        default=3,
        min=1, max=4
    )
    rman_scene_take_padding: IntProperty(
        name="Take Padding",
        description="The number of zeros to pad the take token",
        default=2,
        min=1, max=4
    )    

    rman_scene_version_increment: EnumProperty(
        name="Increment Version",
        description="The version number can be set to automatically increment each time you render",
        items=[
            ('MANUALLY', 'Manually', ''),
            ('RENDER', 'On Render', ''),
            ('BATCH RENDER', 'On Batch Render', '')
        ],
        default='MANUALLY'
    )

    rman_scene_take_increment: EnumProperty(
        name="Increment Take",
        description="The take number can be set to automatically increment each time you render",
        items=[
            ('MANUALLY', 'Manually', ''),
            ('RENDER', 'On Render', ''),
            ('BATCH RENDER', 'On Batch Render', '')
        ],        
        default='MANUALLY'
    )    

    def update_rman_logging_level(self, context):
        level = rfb_logger.__LOG_LEVELS__[self.rman_logging_level]
        rfb_logger.set_logger_level(level)

    rman_logging_level: EnumProperty(
        name='Logging Level',
        description='''Log level verbosity. Advanced: Setting the RFB_LOG_LEVEL environment variable will override this preference. Requires a restart.
                    ''',
        items=[('CRITICAL', 'Critical', ''),
                ('ERROR', 'Error', ''),
                ('WARNING', 'Warning', ''),
                ('INFO', 'Info', ''),
                ('VERBOSE', 'Verbose', ''),
                ('DEBUG', 'Debug', ''),
        ],
        default='WARNING',
        update=update_rman_logging_level)

    rman_logging_file: StringProperty(
        name='Logging File',
        description='''A file to write logging to. This will always write at DEBUG level. Setting the RFB_LOG_FILE environment variable will override this preference. Requires a restart.''',
        default = '',
        subtype='FILE_PATH'
    )

    rman_do_preview_renders: BoolProperty(
        name="Render Previews",
        description="Enable rendering of material previews. This is considered a WIP.",
        default=False)

    rman_preview_renders_minSamples: IntProperty(
        name="Preview Min Samples",
        description="Minimum samples for preview renders",
        default=0,
        min=0, soft_max=4,
    )
    rman_preview_renders_maxSamples: IntProperty(
        name="Preview Max Samples",
        description="Maximum samples for preview renders",
        default=1,
        min=1, soft_max=4,
    )  
    rman_preview_renders_pixelVariance: FloatProperty(
        name="Pixel Variance",
        description="Maximum samples for preview renders",
        default=0.15,
        min=0.001, soft_max=0.5,
    )          

    rman_viewport_draw_bucket: BoolProperty(
        name="Draw Bucket Marker",    
        description="Unchechk this if you do not want the bucket markers in the viewport",
        default=True
    )

    rman_viewport_draw_progress: BoolProperty(
        name="Draw Progress Bar",    
        description="Unchechk this if you do not want the progress bar in the viewport",
        default=True
    )    

    rman_viewport_crop_color: FloatVectorProperty(
        name="CropWindow Color",
        description="Color of the cropwindow border in the viewport when in IPR.",
        default=(0.0, 0.498, 1.0, 1.0), 
        size=4,
        subtype="COLOR")     

    rman_viewport_bucket_color: FloatVectorProperty(
        name="Bucket Marker Color",
        description="Color of the bucket markers in the viewport when in IPR.",
        default=(0.0, 0.498, 1.0, 1.0), 
        size=4,
        subtype="COLOR")  

    rman_viewport_progress_color: FloatVectorProperty(
        name="Progress Bar Color",
        description="Color of the progress bar in the viewport when in IPR.",
        default=(0.0, 0.498, 1.0, 1.0), 
        size=4,
        subtype="COLOR")                

    rman_editor: StringProperty(
        name="Editor",
        subtype='FILE_PATH',
        description="Text editor excutable you want to use to view RIB.",
        default=""
    )

    rman_show_cycles_convert: BoolProperty(
        name="Convert Cycles Nodes",
        default=False,
        description="Add convert Cycles Networks buttons to the material properties panel. N.B.: This isn't guaranteed to fully convert Cycles networks successfully. Also, because of differences in OSL implementations, converted networks may cause stability problems when rendering."

    )

    rman_render_nurbs_as_mesh: BoolProperty(
        name="NURBS as Mesh",
        default=True,
        description="Render all NURBS surfaces as meshes."
    )

    rman_emit_default_params: BoolProperty(
        name="Emit Default Params",
        default=False,
        description="Controls whether or not parameters that are not changed from their defaults should be emitted to RenderMan. Turning this on is only useful for debugging purposes."
    )

    rman_show_advanced_params: BoolProperty(
        name="Show Advanced",
        default=False,
        description="Show advanced preferences"
    )

    rman_config_dir: StringProperty(
        name="Config Directory",
        subtype='DIR_PATH',
        description="Path to JSON configuration files. Requires a restart.",
        default=""
    )    

    rman_viewport_refresh_rate: FloatProperty(
        name="Viewport Refresh Rate",
        description="The number of seconds to wait before the viewport refreshes during IPR.",
        default=0.01,
        precision=5,
        min=0.00001,
        max=0.1
    )    

    # For the preset browser
    rpbConfigFile: StringProperty(default='')
    rpbUserLibraries: CollectionProperty(type=RendermanPreferencePath)
    rpbSelectedLibrary: StringProperty(default='')
    rpbSelectedCategory: StringProperty(default='')
    rpbSelectedPreset: StringProperty(default='')

    def update_stats_config(self, context):
        bpy.ops.renderman.update_stats_config('INVOKE_DEFAULT')

    # For roz stats
    rman_roz_logLevel: EnumProperty(
                        name="Log Level",
                        default='3',        
                        items=[('0', 'None', ''),
                                ('1', 'Severe', ''),
                                ('2', 'Error', ''),
                                ('3', 'Warning', ''),
                                ('4', 'Info', ''),
                                ('5', 'Debug', ''),
                            ],
                        description="Change the logging level for the live statistics system.",
                        update=update_stats_config
                        )
    rman_roz_grpcEnabled: BoolProperty(name="Send Stats to 'it' HUD", default=True, 
                                        description="Turn this off if you don't want stats to be sent to the 'it' HUD.",
                                        update=update_stats_config)
    rman_roz_webSocketEnabled: BoolProperty(name="Enable Websocket Server", default=True, 
                                        description="Turning this off will disable the live statistics system in RfB. In most circumstances, this should not be off. Turning it off could cause error-proned behavior.",
                                        update=update_stats_config)

    def draw_xpu_devices(self, context, layout):
        if self.rman_xpu_device == 'CPU':
            device = self.rman_xpu_cpu_devices[0]
            layout.prop(device, 'use', text='%s' % device.name)
        else:
            if len(self.rman_xpu_gpu_devices) < 1:
                layout.label(text="No compatible GPU devices found.", icon='INFO')
            else:
                '''
                ## TODO: For when XPU can support multiple gpu devices...
                for device in self.rman_xpu_gpu_devices:
                    layout.prop(device, 'use', text='%s (%d.%d)' % (device.name, device.version_major, device.version_minor))
                '''

                # Else, we only can select one GPU
                layout.prop(self, 'rman_xpu_gpu_selection')

                

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False        
        layout = self.layout

        rman_r_icon = rfb_icons.get_icon("rman_blender")

        row = layout.row()
        row.use_property_split = False
        col = row.column()
        col.prop(self, 'rmantree_method')
        
        if self.rmantree_method == 'DETECT':
            col.prop(self, 'rmantree_choice')
            if self.rmantree_choice == 'NEWEST':
                col.label(text="RMANTREE: %s " % envconfig_utils.reload_envconfig().rmantree)
        elif self.rmantree_method == 'ENV':
            col.label(text="RMANTREE: %s" % envconfig_utils.reload_envconfig().rmantree)
        else:
            col.prop(self, "path_rmantree")
        if envconfig_utils.reload_envconfig() is None:
            row = layout.row()
            row.alert = True
            row.label(text='Error in RMANTREE. Reload addon to reset.', icon='ERROR')
            return

        # Behavior Prefs
        row = layout.row()
        row.label(text='Behavior', icon_value=rman_r_icon.icon_id)
        row = layout.row()
        col = row.column()
        col.prop(self, 'rman_do_preview_renders')  
        col.prop(self, 'rman_render_nurbs_as_mesh')
        col.prop(self, 'rman_show_cycles_convert')     
        col.prop(self, 'rman_emit_default_params')          

        # XPU Prefs
        if sys.platform != ("darwin") and not envconfig_utils.envconfig().is_ncr_license:
            row = layout.row()
            row.label(text='XPU', icon_value=rman_r_icon.icon_id)
            row = layout.row()
            row.use_property_split = False
            row.prop(self, 'rman_xpu_device', expand=True)
            row = layout.row()
            row.use_property_split = False
            self.find_xpu_devices()
            col = row.column()      
            box = col.box()  
            self.draw_xpu_devices(context, box)

        # Workspace
        row = layout.row()
        row.label(text='Workspace', icon_value=rman_r_icon.icon_id)
        row = layout.row()
        col = row.column()
        col.prop(self, 'path_fallback_textures_path')
        col.prop(self, 'path_fallback_textures_path_always')
        col.prop(self, "rman_scene_version_padding")
        col.prop(self, "rman_scene_take_padding")
        col.prop(self, "rman_scene_version_increment")
        col.prop(self, "rman_scene_take_increment")

        # UI Prefs
        row = layout.row()
        row.label(text='UI', icon_value=rman_r_icon.icon_id)
        row = layout.row()
        col = row.column()
        col.prop(self, 'rman_viewport_crop_color')
        col.prop(self, 'rman_viewport_draw_bucket')
        if self.rman_viewport_draw_bucket:
            col.prop(self, 'rman_viewport_bucket_color')   
        col.prop(self, 'rman_viewport_draw_progress')
        if self.rman_viewport_draw_progress:
            col.prop(self, 'rman_viewport_progress_color')                
        col.prop(self, 'draw_ipr_text')
        col.prop(self, 'draw_panel_icon')
        col.prop(self, 'rman_editor')

        # Logging
        row = layout.row()
        row.label(text='Logging', icon_value=rman_r_icon.icon_id)
        row = layout.row()
        col = row.column()
        col.prop(self, 'rman_logging_level')
        col.prop(self, 'rman_logging_file')

        # Advanced
        row = layout.row()      
        row.use_property_split = False
        row.use_property_decorate = True          
        row.prop(self, 'rman_show_advanced_params')              

        row = layout.row()
        col = row.column() 
        ui_open = getattr(self, 'rman_show_advanced_params')
        if ui_open:
            col.label(text='Live Statistics', icon_value=rman_r_icon.icon_id)
            row = col.row()
            col = row.column()
            col.prop(self, 'rman_roz_logLevel')  
            col.prop(self, 'rman_roz_grpcEnabled')
            col.prop(self, 'rman_roz_webSocketEnabled')    
            if self.rman_roz_webSocketEnabled:
                try:
                    from .rman_stats import RfBStatsManager
                    stats_mgr = RfBStatsManager.get_stats_manager()
                    split = layout.split()
                    row = split.row()
                    col = row.column()
                    col.label(text='')
                    col = row.column()
                    if stats_mgr:
                        if stats_mgr.is_connected():
                            col.operator('renderman.disconnect_stats_render')
                        else:
                            col.operator('renderman.attach_stats_render')
           
                except Exception as e:
                    rfb_logger.rfb_log().debug("Could not import rman_stats: %s" % str(e))
                    pass                

            row = layout.row()
            col = row.column()
            col.label(text='Other', icon_value=rman_r_icon.icon_id)

            col.prop(self, 'rman_viewport_refresh_rate')  
            col.prop(self, 'rman_config_dir')   
            if self.rman_do_preview_renders:
                col.prop(self, 'rman_preview_renders_minSamples')
                col.prop(self, 'rman_preview_renders_maxSamples')
                col.prop(self, 'rman_preview_renders_pixelVariance') 

classes = [
    RendermanPreferencePath,
    RendermanDeviceDesc,
    RendermanPreferences
]

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError as e:
            rfb_logger.rfb_log().debug("Could not register class, %s, because: %s" % (str(cls), str(e)))
            pass


def unregister():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass
