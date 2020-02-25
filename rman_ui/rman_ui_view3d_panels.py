from ..rman_render import RmanRender
from ..icons.icons import load_icons
from .rman_ui_base import _RManPanelHeader
import bpy

class PRMAN_PT_Renderman_UI_Panel(bpy.types.Panel, _RManPanelHeader):
    '''Adds a RenderMan panel to the RenderMan VIEW_3D side tab
    '''

    bl_label = "RenderMan"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Renderman"

    def draw(self, context):
        icons = load_icons()
        layout = self.layout
        scene = context.scene
        rm = scene.renderman

        # save Scene
        # layout.operator("wm.save_mainfile", text="Save Scene", icon='FILE_TICK')

        # layout.separator()

        if context.scene.render.engine != "PRMAN_RENDER":
            return

        # Render
        rman_render = RmanRender.get_rman_render()
        is_rman_interactive_running = rman_render.rman_interactive_running        

        if not is_rman_interactive_running:

            row = layout.row(align=True)
            rman_render_icon = icons.get("render")
            row.operator("render.render", text="Render",
                        icon_value=rman_render_icon.icon_id)

            row.prop(context.scene, "rm_render", text="",
                    icon='DISCLOSURE_TRI_DOWN' if context.scene.rm_render else 'DISCLOSURE_TRI_RIGHT')

            if context.scene.rm_render:
                scene = context.scene
                rd = scene.render

                box = layout.box()
                row = box.row(align=True)

                # Display Driver
                row.prop(rm, "render_into")

                # presets
                row = box.row(align=True)
                row.label(text="Sampling Preset:")
                row.menu("PRMAN_MT_presets", text=bpy.types.WM_MT_operator_presets.bl_label)
                row.operator("render.renderman_preset_add", text="", icon='ADD')
                row.operator("render.renderman_preset_add", text="",
                            icon='REMOVE').remove_active = True

                # denoise, holdouts and selected row
                row = box.row(align=True)
                #row.prop(rm, "do_denoise", text="Denoise")
                row.prop(rm, "do_holdout_matte", text="Render Holdouts")
                
                #row.prop(rm, "render_selected_objects_only",
                #         text="Render Selected")


                # animation
                row = box.row(align=True)
                rman_batch = icons.get("batch_render")
                row.operator("render.render", text="Render Animation",
                            icon_value=rman_batch.icon_id).animation = True

                # row = box.row(align=True)
                # rman_batch = icons.get("batch_render")
                # row.operator("render.render",text="Batch Render",icon_value=rman_batch.icon_id).animation=True

                # #Resolution
                # row = box.row(align=True)
                # sub = row.column(align=True)
                # sub.label(text="Resolution:")
                # sub.prop(rd, "resolution_x", text="X")
                # sub.prop(rd, "resolution_y", text="Y")
                # sub.prop(rd, "resolution_percentage", text="")

                # # layout.prop(rm, "display_driver")
                # #Sampling
                # row = box.row(align=True)
                # row.label(text="Sampling:")
                # row = box.row(align=True)
                # col = row.column()
                # col.prop(rm, "pixel_variance")
                # row = col.row(align=True)
                # row.prop(rm, "min_samples", text="Min Samples")
                # row.prop(rm, "max_samples", text="Max Samples")
                # row = col.row(align=True)
                # row.prop(rm, "max_specular_depth", text="Specular Depth")
                # row.prop(rm, "max_diffuse_depth", text="Diffuse Depth")

            # IPR

            # Start IPR
            
            #row = layout.row(align=True)
            #rman_rerender_controls = icons.get("start_ipr")
            #row.operator('lighting.start_interactive', text="Start IPR",
            #                icon_value=rman_rerender_controls.icon_id)

            #row.prop(context.scene, "rm_ipr", text="",
            #            icon='DISCLOSURE_TRI_DOWN' if context.scene.rm_ipr else 'DISCLOSURE_TRI_RIGHT')
            

            if context.scene.rm_ipr:

                scene = context.scene
                rm = scene.renderman

                # STart IT
                rman_it = icons.get("start_it")
                layout.operator("rman.start_it", text="Start IT",
                                icon_value=rman_it.icon_id)

                # Interactive and Preview Sampling
                box = layout.box()
                row = box.row(align=True)

                col = row.column()
                col.prop(rm, "preview_pixel_variance")
                row = col.row(align=True)
                row.prop(rm, "preview_min_samples", text="Min Samples")
                row.prop(rm, "preview_max_samples", text="Max Samples")
                row = col.row(align=True)
                row.prop(rm, "preview_max_specular_depth",
                            text="Specular Depth")
                row.prop(rm, "preview_max_diffuse_depth", text="Diffuse Depth")
                row = col.row(align=True)

            row = layout.row(align=True)
            rman_batch = icons.get("batch_render")

            row.operator("renderman.external_render",
                        text="External Render", icon_value=rman_batch.icon_id)

            row.prop(context.scene, "rm_render_external", text="",
                    icon='DISCLOSURE_TRI_DOWN' if context.scene.rm_render_external else 'DISCLOSURE_TRI_RIGHT')
            if context.scene.rm_render_external:
                scene = context.scene
                rd = scene.render

                box = layout.box()
                row = box.row(align=True)

                # Display Driver
                # row.prop(rm, "display_driver", text='Render into')

                # animation
                row = box.row(align=True)
                row.prop(rm, "external_animation")

                row = box.row(align=True)
                row.enabled = rm.external_animation
                row.prop(scene, "frame_start", text="Start")
                row.prop(scene, "frame_end", text="End")

                # presets
                row = box.row(align=True)
                row.label(text="Sampling Preset:")
                row.menu("PRMAN_MT_presets")

                #row = box.row(align=True)
                #row.prop(rm, "render_selected_objects_only",
                #        text="Render Selected")

                # spool render
                row = box.row(align=True)
                col = row.column()
                col.prop(rm, "queuing_system", text='')            

        else:
            row = layout.row(align=True)
            rman_rerender_controls = icons.get("stop_ipr")
            row.operator('lighting.stop_interactive', text="Stop IPR",
                            icon_value=rman_rerender_controls.icon_id)            

        layout.separator()

        # Create Camera
        row = layout.row(align=True)
        row.operator("object.add_prm_camera",
                     text="Add Camera", icon='CAMERA_DATA')

        row.prop(context.scene, "prm_cam", text="",
                 icon='DISCLOSURE_TRI_DOWN' if context.scene.prm_cam else 'DISCLOSURE_TRI_RIGHT')

        if context.scene.prm_cam:
            ob = bpy.context.object
            box = layout.box()
            row = box.row(align=True)
            row.menu("PRMAN_MT_Camera_List_Menu",
                     text="Camera List", icon='CAMERA_DATA')

            if ob.type == 'CAMERA':

                row = box.row(align=True)
                row.prop(ob, "name", text="", icon='LIGHT_HEMI')
                row.prop(ob, "hide_viewport", text="")
                row.prop(ob, "hide_render",
                         icon='RESTRICT_RENDER_OFF', text="")
                row.operator("object.delete_cameras",
                             text="", icon='PANEL_CLOSE')

                row = box.row(align=True)
                row.scale_x = 2
                row.operator("view3d.object_as_camera", text="", icon='CURSOR')

                row.scale_x = 2
                row.operator("view3d.view_camera", text="", icon='VISIBLE_IPO_ON')

                if context.space_data.lock_camera == False:
                    row.scale_x = 2
                    row.operator("wm.context_toggle", text="",
                                 icon='UNLOCKED').data_path = "space_data.lock_camera"
                elif context.space_data.lock_camera == True:
                    row.scale_x = 2
                    row.operator("wm.context_toggle", text="",
                                 icon='LOCKED').data_path = "space_data.lock_camera"

                row.scale_x = 2
                row.operator("view3d.camera_to_view",
                             text="", icon='VIEW3D')

                row = box.row(align=True)
                row.label(text="Depth Of Field :")

                row = box.row(align=True)
                row.prop(context.object.data.dof, "focus_object", text="")
                #row.prop(context.object.data.cycles, "aperture_type", text="")

                row = box.row(align=True)
                row.prop(context.object.data.dof, "focus_distance", text="Distance")

            else:
                row = layout.row(align=True)
                row.label(text="No Camera Selected")

        layout.separator()

        # Create Env Light
        row = layout.row(align=True)
        rman_RMSEnvLight = icons.get("envlight")
        row.operator("object.mr_add_hemi", text="Add EnvLight",
                     icon_value=rman_RMSEnvLight.icon_id)

        lights = [obj for obj in bpy.context.scene.objects if obj.type == "LIGHT"]

        light_hemi = False
        light_area = False
        light_point = False
        light_spot = False
        light_sun = False

        if len(lights):
            for light in lights:
                if light.data.type == 'HEMI':
                    light_hemi = True

                if light.data.type == 'AREA':
                    light_area = True

                if light.data.type == 'POINT':
                    light_point = True

                if light.data.type == 'SPOT':
                    light_spot = True

                if light.data.type == 'SUN':
                    light_sun = True

        if light_hemi:

            row.prop(context.scene, "rm_env", text="",
                     icon='DISCLOSURE_TRI_DOWN' if context.scene.rm_env else 'DISCLOSURE_TRI_RIGHT')

            if context.scene.rm_env:
                ob = bpy.context.object
                box = layout.box()
                row = box.row(align=True)
                row.menu("PRMAN_MT_Hemi_List_Menu",
                         text="EnvLight List", icon='LIGHT_HEMI')

                if ob.type == 'LIGHT' and ob.data.type == 'HEMI':

                    row = box.row(align=True)
                    row.prop(ob, "name", text="", icon='LIGHT_HEMI')
                    row.prop(ob, "hide_viewport", text="")
                    row.prop(ob, "hide_render",
                             icon='RESTRICT_RENDER_OFF', text="")
                    row.operator("object.delete_lights",
                                 text="", icon='PANEL_CLOSE')
                    row = box.row(align=True)
                    row.prop(ob, "rotation_euler", index=2, text="Rotation")

                else:
                    row = layout.row(align=True)
                    row.label(text="No EnvLight Selected")

        # Create Area Light

        row = layout.row(align=True)
        rman_RMSAreaLight = icons.get("arealight")
        row.operator("object.mr_add_area", text="Add AreaLight",
                     icon_value=rman_RMSAreaLight.icon_id)

        lights = [obj for obj in bpy.context.scene.objects if obj.type == "LIGHT"]

        light_hemi = False
        light_area = False
        light_point = False
        light_spot = False
        light_sun = False

        if len(lights):
            for light in lights:
                if light.data.type == 'HEMI':
                    light_hemi = True

                if light.data.type == 'AREA':
                    light_area = True

                if light.data.type == 'POINT':
                    light_point = True

                if light.data.type == 'SPOT':
                    light_spot = True

                if light.data.type == 'SUN':
                    light_sun = True

        if light_area:

            row.prop(context.scene, "rm_area", text="",
                     icon='DISCLOSURE_TRI_DOWN' if context.scene.rm_area else 'DISCLOSURE_TRI_RIGHT')

            if context.scene.rm_area:
                ob = bpy.context.object
                box = layout.box()
                row = box.row(align=True)
                row.menu("PRMAN_MT_Area_List_Menu",
                         text="AreaLight List", icon='LIGHT_AREA')

                if ob.type == 'LIGHT' and ob.data.type == 'AREA':

                    row = box.row(align=True)
                    row.prop(ob, "name", text="", icon='LIGHT_AREA')
                    row.prop(ob, "hide_viewport", text="")
                    row.prop(ob, "hide_render",
                             icon='RESTRICT_RENDER_OFF', text="")
                    row.operator("object.delete_lights",
                                 text="", icon='PANEL_CLOSE')

                else:
                    row = layout.row(align=True)
                    row.label(text="No AreaLight Selected")

        # Daylight

        row = layout.row(align=True)
        rman_PxrStdEnvDayLight = icons.get("daylight")
        row.operator("object.mr_add_sky", text="Add Daylight",
                     icon_value=rman_PxrStdEnvDayLight.icon_id)

        lights = [obj for obj in bpy.context.scene.objects if obj.type == "LIGHT"]

        light_hemi = False
        light_area = False
        light_point = False
        light_spot = False
        light_sun = False

        if len(lights):
            for light in lights:
                if light.data.type == 'SUN':
                    light_sun = True

                if light.data.type == 'HEMI':
                    light_hemi = True

                if light.data.type == 'AREA':
                    light_area = True

                if light.data.type == 'POINT':
                    light_point = True

                if light.data.type == 'SPOT':
                    light_spot = True

        if light_sun:

            row.prop(context.scene, "rm_daylight", text="",
                     icon='DISCLOSURE_TRI_DOWN' if context.scene.rm_daylight else 'DISCLOSURE_TRI_RIGHT')

            if context.scene.rm_daylight:
                ob = bpy.context.object
                box = layout.box()
                row = box.row(align=True)
                row.menu("PRMAN_MT_DayLight_List_Menu",
                         text="DayLight List", icon='LIGHT_SUN')

                if ob.type == 'LIGHT' and ob.data.type == 'SUN':

                    row = box.row(align=True)
                    row.prop(ob, "name", text="", icon='LIGHT_SUN')
                    row.prop(ob, "hide_viewport", text="")
                    row.prop(ob, "hide_render",
                             icon='RESTRICT_RENDER_OFF', text="")
                    row.operator("object.delete_lights",
                                 text="", icon='PANEL_CLOSE')

                else:
                    row = layout.row(align=True)
                    row.label(text="No DayLight Selected")

        # Dynamic Binding Editor

        # Create Holdout

        # Open Linking Panel
        # row = layout.row(align=True)
        # row.operator("renderman.lighting_panel")

        selected_objects = []
        if context.selected_objects:
            for obj in context.selected_objects:
                if obj.type not in ['CAMERA', 'LIGHT', 'SPEAKER']:
                    selected_objects.append(obj)

        if selected_objects:
            layout.separator()
            layout.label(text="Seleced Objects:")
            box = layout.box()

            # Create PxrLM Material
            render_PxrDisney = icons.get("pxrdisney")
            box.operator_menu_enum(
                "object.add_bxdf", 'bxdf_name', text="Add New Material", icon='MATERIAL')

            # Make Selected Geo Emissive∂
            rman_RMSGeoAreaLight = icons.get("geoarealight")
            box.operator("object.addgeoarealight", text="Make Emissive",
                         icon_value=rman_RMSGeoAreaLight.icon_id)

            # Add Subdiv Sheme
            rman_subdiv = icons.get("add_subdiv_sheme")
            box.operator("object.add_subdiv_sheme",
                         text="Make Subdiv", icon_value=rman_subdiv.icon_id)

            # Add/Create RIB Box /
            # Create Archive node
            rman_archive = icons.get("archive_RIB")
            box.operator("export.export_rib_archive",
                         icon_value=rman_archive.icon_id)
        # Create Geo LightBlocker

        # Update Archive !! Not needed with current system.

        # Open Last RIB
        #rman_open_last_rib = icons.get("open_last_rib")
        #layout.prop(rm, "path_rib_output",icon_value=rman_open_last_rib.icon_id)

        # Inspect RIB Selection

        # Shared Geometry Attribute

        # Add/Atach Coordsys

        # Open Tmake Window  ?? Run Tmake on everything.

        # Create OpenVDB Visualizer
        layout.separator()
        # RenderMan Doc
        rman_help = icons.get("help")
        layout.operator("wm.url_open", text="RenderMan Docs",
                        icon_value=rman_help.icon_id).url = "https://github.com/prman-pixar/RenderManForBlender/wiki/Documentation-Home"
        rman_info = icons.get("info")
        layout.operator("wm.url_open", text="About RenderMan",
                        icon_value=rman_info.icon_id).url = "https://renderman.pixar.com/store/intro"

        # Reload the addon
        # rman_reload = icons.get("reload_plugin")
        # layout.operator("renderman.restartaddon", icon_value=rman_reload.icon_id)

        # Enable the menu item to display the examples menu in the RenderMan
        # Panel.
        layout.separator()
        layout.menu("PRMAN_MT_examples", icon_value=rman_help.icon_id)    

classes = [
    PRMAN_PT_Renderman_UI_Panel,

]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)        