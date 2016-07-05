
def end_block(f, indent_level):
    f.write("%s}\n" % ('\t' * indent_level))


def write_parent_task_line(f, title, serial_subtasks, indent_level):
    f.write("%sTask {%s} -serialsubtasks %d -subtasks {\n" %
            ('\t' * indent_level, title, int(serial_subtasks)))


def write_cmd_task_line(f, title, cmds, indent_level):
    f.write("%sTask {%s} -cmds {\n" % ('\t' * indent_level, title))
    for key, cmd in cmds:
        f.write("%sCmd -service {%s} {%s}\n" % ('\t' * (indent_level + 1),
                                                key, " ".join(cmd)))
    f.write("%s}\n" % ('\t' * indent_level))


def spool_render(rman_version_short, rib_files, denoise_files, frame_begin, frame_end=None, denoise=None):
    prefs = bpy.context.user_preferences.addons[__package__].preferences

    out_dir = prefs.env_vars.out
    alf_file = os.path.join(user_path(out_dir), 'spool.alf')
    per_frame_denoise = denoise == 'frame'
    crossframe_denoise = denoise == 'crossframe'

    # open file
    f = open(alf_file, 'w')
    # write header
    f.write('##AlfredToDo 3.0\n')
    # job line
    job_title = 'untitled' if bpy.data.filepath == '' else \
        os.path.splitext(os.path.split(bpy.data.filepath)[1])[0]
    job_title += " frames %d-%d" % (frame_begin, frame_end) if frame_end \
        else " frame %d" % frame_begin
    if per_frame_denoise:
        job_title += ' per-frame denoise'
    elif crossframe_denoise:
        job_title += ' crossframe_denoise'
    job_params = {
        'title': job_title,
        'serialsubtasks': 1,
        'envkey': 'prman-%s' % rman_version_short,
        'comment': 'Created by RenderMan for Blender'
    }
    job_str = 'Job'
    for key, val in job_params.items():
        if key == 'serialsubtasks':
            job_str += " -%s %s" % (key, str(val))
        else:
            job_str += " -%s {%s}" % (key, str(val))
    f.write(job_str + ' -subtasks {' + '\n')

    # collect textures find frame specific and job specific
    #write_parent_task_line(f, 'Job Textures', False, 1)
    # do job tx makes
    # for in_name,cmd_str in job_texture_cmds:
    #    write_cmd_task_line(f, "TxMake %s" % os.path.split(in_name)[-1],
    #                        [('PixarRender', cmd_str)], 2)
    #end_block(f, 1)

    write_parent_task_line(f, 'Frame Renders', False, 1)
    # for frame
    if frame_end is None:
        frame_end = frame_begin
    for frame_num in range(frame_begin, frame_end + 1):
        if len(frame_texture_cmds) or per_frame_denoise:
            write_parent_task_line(f, 'Frame %d' % frame_num, True, 2)

        # do frame specic txmake
        # if len(frame_texture_cmds):
        #    write_parent_task_line(f, 'Frame %d textures' % frame_num, False, 3)
        #    for in_name,cmd_str in frame_texture_cmds:
        #        write_cmd_task_line(f, "TxMake %s" % os.path.split(in_name)[-1],
        #                    [('PixarRender', cmd_str)], 4)
        #    end_block(f, 3)

        # render frame
        cmd_str = ['prman', '-Progress', '-cwd',
                   cdir, rib_files[frame_num - frame_begin]]
        write_cmd_task_line(f, 'Render frame %d' % frame_num, [('PixarRender',
                                                                cmd_str)], 3)

        # denoise frame
        if per_frame_denoise:
            cmd_str = ['denoise', denoise_files[frame_num - frame_begin][0]]
            write_cmd_task_line(f, 'Denoise frame %d' % frame_num,
                                [('PixarRender', cmd_str)], 3)

        if len(frame_texture_cmds) or per_frame_denoise:
            end_block(f, 2)
    end_block(f, 1)
    # crossframe denoise
    # if crossframe_denoise:
    #    write_cmd_task_line(f, 'Denoise all frames',
    #                        [('PixarRender', cmd_str)], 3)

    # end job
    f.write("}\n")
    return alf_file
