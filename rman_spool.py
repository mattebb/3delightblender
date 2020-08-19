import subprocess
import os
import getpass
import socket
import datetime
import bpy
from .rman_utils import string_utils
from .rman_utils import filepath_utils
from .rman_utils import display_utils
from .rman_utils.prefs_utils import get_pref
from .rman_config import __RFB_CONFIG_DICT__ as rfb_config
from .rfb_logger import rfb_log

#import tractor.api.author as author

class RmanSpool(object):

    def __init__(self, rman_render, rman_scene, depsgraph):
        self.rman_render = rman_render
        self.rman_scene = rman_scene
        if depsgraph:
            self.bl_scene = depsgraph.scene_eval
            self.depsgraph = depsgraph

    def end_block(self, f, indent_level):
        f.write("%s}\n" % ('\t' * indent_level))


    def write_parent_task_line(self, f, title, serial_subtasks, indent_level):
        f.write("%sTask {%s} -serialsubtasks %d -subtasks {\n" %
            ('\t' * indent_level, title, int(serial_subtasks)))


    def write_cmd_task_line(self, f, title, cmds, indent_level):
        f.write("%sTask {%s} -cmds {\n" % ('\t' * indent_level, title))
        for key, cmd in cmds:
            f.write("%sRemoteCmd -service {%s} {%s}\n" % ('\t' * (indent_level + 1),
                                                        key, " ".join(cmd)))
        f.write("%s}\n" % ('\t' * indent_level))


    def quote(self, filename):
        return '"%s"' % filename


    def write_job_attrs(self, f, frame_begin, frame_end):
        # write header
        f.write('##AlfredToDo 3.0\n')
        # job line
        bl_view_layer = self.depsgraph.view_layer.name
        job_title = 'untitled' if not bpy.data.filepath else \
            os.path.splitext(os.path.split(bpy.data.filepath)[1])[0]
        job_title += ' %s ' % bl_view_layer
        job_title += " frames %d-%d" % (frame_begin, frame_end) if frame_end \
            else " frame %d" % frame_begin

        vers_major, vers_minor, vers_modifier = filepath_utils.get_rman_version(filepath_utils.guess_rmantree())
        rman_vers = '%d.%d%s' % (vers_major, vers_minor, vers_modifier)

        job_params = {
            'title': job_title,
            'serialsubtasks': 1,
            'comment': 'Created by RenderMan for Blender',
            'envkey': '{prman-%s}' % rman_vers
        }

        # dirmaps
        dirmaps = ''
        for k in rfb_config['dirmaps']:
            dirmap = rfb_config['dirmaps'][k]
            dirmaps += '{ {%s} {%s} %s }' % (dirmap['from'], dirmap['to'], dirmap['zone'])
        if dirmaps:
            job_params['dirmaps'] = dirmaps

        job_str = 'Job'
        for key, val in job_params.items():
            if key == 'serialsubtasks':
                job_str += " -%s %s" % (key, str(val))
            else:
                job_str += " -%s {%s}" % (key, str(val))
        f.write(job_str + ' -subtasks {' + '\n')

    def blender_batch_render(self, bl_filename):

        out_dir = get_pref('env_vars').out       
        scene = self.bl_scene 
        rm = scene.renderman
        bl_view_layer = self.depsgraph.view_layer


        frame_begin = self.bl_scene.frame_start
        frame_end = self.bl_scene.frame_end
        if not rm.external_animation:
            frame_begin = self.bl_scene.frame_current
            frame_end = frame_begin
        
        alf_file = os.path.splitext(bpy.data.filepath)[0] + '.%s.alf' % bl_view_layer.name.replace(' ', '_')

        # open file
        f = open(alf_file, 'w')

        self.write_job_attrs(f, frame_begin, frame_end)


        self.write_parent_task_line(f, 'Frame Renders', False, 1)
        # for frame
        if frame_end is None:
            frame_end = frame_begin

        #bl_filename = bpy.data.filepath
        bl_blender_path = bpy.app.binary_path

        for frame_num in range(frame_begin, frame_end + 1):

            cmd_str = [bl_blender_path, '-b', bl_filename, '-f', str(frame_num)]

            self.write_cmd_task_line(f, 'Render frame %d' % frame_num, [('PixarRender',
                                                                    cmd_str)], 3)
        self.end_block(f, 1)

        # add cleanup
        f.write("} -cleanup {\n")
        f.write("    Cmd {TractorBuiltIn File delete %s}\n" % bl_filename)
        f.write("}\n")

        # end job
        f.close()      

        is_localqueue = (self.bl_scene.renderman.queuing_system == 'lq')

        if is_localqueue:
            lq = filepath_utils.find_local_queue()
            args = []
            args.append(lq)
            args.append(alf_file)
            rfb_log().info('Spooling job to LocalQueue: %s.', alf_file)
            subprocess.Popen(args)
        else:
            # spool to tractor
            tractor_engine ='tractor-engine'
            tractor_port = '80'
            owner = getpass.getuser()        

            tractor_cfg = rfb_config['tractor_cfg']
            tractor_engine = tractor_cfg.get('engine', tractor_engine)
            tractor_port = str(tractor_cfg.get('port', tractor_port))
            owner = tractor_cfg.get('user', owner)            

            if 'TRACTOR_ENGINE' in os.environ:
                tractor_env = os.environ['TRACTOR_ENGINE'].split(':')
                tractor_engine = tractor_env[0]
                if len(tractor_env) > 1:
                    tractor_port = tractor_env[1]

            if 'TRACTOR_USER' in os.environ:
                owner = os.environ['TRACTOR_USER']

            tractor_spool = filepath_utils.find_tractor_spool()
            args = []
            args.append(tractor_spool)
            args.append('--user=%s' % owner)
            args.append('--engine=%s:%s' % (tractor_engine, tractor_port))
            args.append(alf_file)
            rfb_log().info('Spooling job to Tractor: %s.', alf_file)
            subprocess.Popen(args)

    def batch_render(self):

        out_dir = get_pref('env_vars').out       
        scene = self.bl_scene 
        rm = scene.renderman
        bl_view_layer = self.depsgraph.view_layer


        frame_begin = self.bl_scene.frame_start
        frame_end = self.bl_scene.frame_end
        if not rm.external_animation:
            frame_begin = self.bl_scene.frame_current
            frame_end = frame_begin
        
        alf_file = os.path.splitext(bpy.data.filepath)[0] + '.%s.alf' % bl_view_layer.name.replace(' ', '_')

        # open file
        f = open(alf_file, 'w')

        self.write_job_attrs(f, frame_begin, frame_end)


        self.write_parent_task_line(f, 'Frame Renders', False, 1)
        # for frame
        if frame_end is None:
            frame_end = frame_begin

        for frame_num in range(frame_begin, frame_end + 1):
            #if frame_num in frame_texture_cmds or denoise:
            #    self.write_parent_task_line(f, 'Frame %d' % frame_num, True, 2)

            # render frame
            cdir = string_utils.expand_string(out_dir, asFilePath=True) 
            threads = rm.batch_threads 
            rib_file = string_utils.expand_string(rm.path_rib_output, 
                                                frame=frame_num,
                                                asFilePath=True)
            cmd_str = ['prman', '-Progress', '-cwd', self.quote(cdir), '-t:%d' %
                    threads, self.quote(rib_file)]
            if rm.recover:
                cmd_str.insert(5, '-recover 1')
            if rm.custom_cmd != '':
                cmd_str.insert(5, rm.custom_cmd)
            self.write_cmd_task_line(f, 'Render frame %d' % frame_num, [('PixarRender',
                                                                    cmd_str)], 3)
        self.end_block(f, 1)
        self.write_parent_task_line(f, 'Denoise Renders', False, 1)

        # denoise
        cur_frame = self.rman_scene.bl_frame_current
        for frame_num in range(frame_begin, frame_end + 1):
            self.rman_render.bl_frame_current = frame_num

            dspys_dict = display_utils.get_dspy_dict(self.rman_scene, expandTokens=False)            
            variance_file = string_utils.expand_string(dspys_dict['displays']['beauty']['filePath'], 
                                                frame=frame_num,
                                                asFilePath=True)               

            denoise_options = []
            if rm.denoise_cmd != '':
                denoise_options.append(rm.denoise_cmd)  
            if rm.denoise_gpu:
                denoise_options.append('--override gpuIndex 0 --')                          

            for dspy,params in dspys_dict['displays'].items():
                if not params['denoise']:
                    continue

                if params['denoise_mode'] == 'singleframe':

                    cmd_str = ['denoise'] + denoise_options
                    if dspy == 'beauty':
                        cmd_str.append(variance_file)
                    else:
                        cmd_str.append(variance_file)
                        aov_file = string_utils.expand_string(params['filePath'], 
                                                frame=frame_num,
                                                token_dict=token_dict,
                                                asFilePath=True)    
                        cmd_str.append(aov_file)

                self.write_cmd_task_line(f, 'Denoise frame %d' % frame_num,
                                        [('PixarRender', cmd_str)], 3)                                                                    
        self.rman_render.bl_frame_current = cur_frame
        self.end_block(f, 1)

        # end job
        f.write("}\n")
        f.close()      

        is_localqueue = (self.bl_scene.renderman.queuing_system == 'lq')

        if is_localqueue:
            lq = filepath_utils.find_local_queue()
            args = []
            args.append(lq)
            args.append(alf_file)
            rfb_log().info('Spooling job to LocalQueue: %s.', alf_file)
            subprocess.Popen(args)
        else:
            # spool to tractor
            tractor_engine ='tractor-engine'
            tractor_port = '80'
            owner = getpass.getuser()    

            tractor_cfg = rfb_config['tractor_cfg']
            tractor_engine = tractor_cfg.get('engine', tractor_engine)
            tractor_port = str(tractor_cfg.get('port', tractor_port))
            owner = tractor_cfg.get('user', owner)

            if 'TRACTOR_ENGINE' in os.environ:
                tractor_env = os.environ['TRACTOR_ENGINE'].split(':')
                tractor_engine = tractor_env[0]
                if len(tractor_env) > 1:
                    tractor_port = tractor_env[1]

            if 'TRACTOR_USER' in os.environ:
                owner = os.environ['TRACTOR_USER']

            tractor_spool = filepath_utils.find_tractor_spool()
            args = []
            args.append(tractor_spool)
            args.append('--user=%s' % owner)
            args.append('--engine=%s:%s' % (tractor_engine, tractor_port))
            args.append(alf_file)
            rfb_log().info('Spooling job to Tractor: %s.', alf_file)
            subprocess.Popen(args)

    """
    DISABLE THIS CODE FOR NOW
    The tractor author API is not compatible with python3
    Once it is, re-enable this, and uncomment the import line at the top

    def add_job_level_attrs(self, is_localqueue, job):
        for k in rfb_config['dirmaps']:
            dirmap = rfb_config['dirmaps'][k]
            job.newDirMap(src=str(dirmap['from']),
                        dst=str(dirmap['to']),
                        zone=str(dirmap['zone']))

    def _add_checkpoint_args(self, checkpoint_str, args):
        if checkpoint_str != '':
            args.append('-checkpoint')
            args.append(checkpoint_str)
            args.append('-recover')
            args.append('%r')    

    def add_prman_render_task(parentTask, title, threads, rib, img, args=[]):


        task = author.Task()
        task.title = title
        if img:
            task.preview = 'sho %s' % str(img)

        command = author.Command(local=False, service="PixarRender")
        command.argv = ["prman"]
        for arg in args:
            command.argv.append(arg)

        proj = mc.workspace(q=True, rd=True)
        for arg in ["-Progress", "-t:%d" % threads, "-cwd", "%%D(%s)" % proj,  "%%D(%s)" % rib]:
            command.argv.append(arg)

        task.addCommand(command)
        parentTask.addChild(task)

    def generate_rib_render_tasks(self, parent_task, tasktitle,
                                start, last, by, threads, do_bake, checkpoint):

        rm = self.bl_scene.renderman

        if anim is False:

            rib_expanded = string_utils.expand_string(rm.path_rib_output, frame=frame_num, bl_scene=self.bl_scene)
            img_expanded = ''

            frametasktitle = ("%s Frame: %d " %
                            (tasktitle, int(start)))
            frametask = author.Task()
            frametask.title = frametasktitle
            frametask.serialsubtasks = True

            prmantasktitle = "%s (render)" % frametasktitle
            args = []

            self._add_checkpoint_args(checkpoint, args)


            add_prman_render_task(frametask, prmantasktitle, threads,
                                rib_expanded, img_expanded, args)
            if not do_bake:
                generate_denoise_tasks(frametasktitle, frametask,
                                    displays, start)

            parent_task.addChild(frametask)

        else:
            parent_task.serialsubtasks = True

            renderframestask = author.Task()
            renderframestask.serialsubtasks = False
            renderframestasktitle = ("Render Layer: %s Camera: %s" %
                                    (str(layer), str(cam)))
            renderframestask.title = renderframestasktitle

            for iframe in range(int(start), int(last + 1), int(by)):
                rib_expanded = string_utils.expand_string(rm.path_rib_output, frame=frame_num, bl_scene=self.bl_scene)
                img_expanded = ''

                prmantasktitle = ("%s Frame: %d (prman)" %
                                (tasktitle, int(iframe)))
                args = []

                _add_checkpoint_args(checkpoint, args)

                add_prman_render_task(renderframestask, prmantasktitle, threads,
                                      rib_expanded, img_expanded, args)

            parent_task.addChild(renderframestask)


    def generate_job_file(self, is_localqueue, do_RIB, do_bake):

        job = author.Job()
        scene_name = self.bl_scene.name
        job.title = str(scene_name)
        job.serialsubtasks = True
        add_job_level_attrs(is_localqueue, job)

        checkpoint = ''
        # if we're checkpointing, temporarily turn off asrgba for all openexr displays


        threads = self.bl_scene.renderman.batch_threads
        by = 1
        start = self.bl_scene.frame_start
        end = self.bl_scene.frame_end
        anim = (start != end)

        tasktitle = "Render %s" % (str(scene_name))
        parent_task = author.Task()
        parent_task.title = tasktitle

        if do_RIB:
            generate_rib_render_tasks(is_localqueue, anim, parent_task, tasktitle,
                                    start, last, by, threads, do_bake, checkpoint)
        else:
            # blender batch
            # not sure how this would work
            pass

        # txmake tasks
        #txmakeTasks = generate_txmake_tasks()
        #job.addChild(txmakeTasks)

        job.addChild(parent_task)
        jobfile = os.path.splitext(bpy.data.filepath)[0] + '.alf'


        try:
            f = open(jobfile, 'w')
            as_tcl = job.asTcl()
            f.write(as_tcl)
            f.close()
        except IOError as ioe:
            pass
            #raise RfmError('IO Exception when writing job file %s: %s' % (jobfile, str(ioe)))
        except Exception as e:
            pass
            #raise RfmError('Could not write job file %s: %s' % (jobfile, str(e)))

        return [job, jobfile]

    
    def batch_render(self):

        is_localqueue = (self.bl_scene.renderman.queuing_system == 'tractor')

        do_RIB = True
        do_bake = False

        job, jobfile = self.generate_job_file(is_localqueue, do_RIB, do_bake)


        if is_localqueue:
            lq = filepath_utils.find_local_queue()
            args = []
            args.append(lq)
            args.append(jobfile)
            rfm_log().info('Spooling job to LocalQueue: %s.', jobfile)
            subprocess.Popen(args)
        else:
            # spool to tractor
            tractor_engine ='tractor-engine'
            tractor_port = '80'
            owner = getpass.getuser()

            # env var trumps rfm.config
            if 'TRACTOR_ENGINE' in os.environ:
                tractor_env = os.environ['TRACTOR_ENGINE'].split(':')
                tractor_engine = tractor_env[0]
                if len(tractor_env) > 1:
                    tractor_port = tractor_env[1]

            if 'TRACTOR_USER' in os.environ:
                owner = os.environ['TRACTOR_USER']

            try:
                spoolhost = socket.gethostname()
                job.spool(block=True, spoolfile=jobfile, spoolhost=spoolhost,
                        owner=owner, hostname=tractor_engine,
                        port=int(tractor_port))
                rfm_log().info('Spooling to Tractor Engine: %s:%s, Job File: %s', tractor_engine,
                            tractor_port, jobfile)
            except author.SpoolError as spoolError:
                pass

            except Exception as e:
                pass

    """