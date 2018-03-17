#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# execution.py: workflow executor
#

import abc
import datetime
import functools
import getpass
import os
import pkg_resources
import subprocess

import networkx
import lxml.etree

from ..utils.log import get_logger
from ..utils.path import join_path
from ..utils.template import render_template


# ================================================================================
# global
# ================================================================================

logger = get_logger()


# ================================================================================
# workflow executor interface
# ================================================================================

class WorkflowExecutor(metaclass=abc.ABCMeta):
    def __init__(self, workflow, options):
        self.workflow = workflow
        self.options = options

    @abc.abstractmethod
    def execute(self, execution_id, dry_run=False):
        raise NotImplementedError   # NOQA

    @abc.abstractmethod
    def cancel(self, dry_run=False):
        raise NotImplementedError   # NOQA


@functools.lru_cache()
def get_workflow_executor_ids():
    return [l.name.lower() for l in pkg_resources.iter_entry_points('gpipe_executors')]


def get_workflow_executor_class(name):
    executor_loaders = pkg_resources.iter_entry_points('gpipe_executors')
    executor_loaders = {l.name.lower(): l for l in executor_loaders}

    name = name.lower()
    if name in executor_loaders:
        return executor_loaders[name].load()
    else:
        raise Exception(f'Executor not found: {name}')


def generate_execution_id(user_execution_id, clean=False, dry_run=False):
    if user_execution_id:
        return user_execution_id

    else:
        execution_id = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
        if clean:
            execution_id += '.clean'
        if dry_run:
            execution_id += '.dry_run'

        logger.debug('Execution ID automatically generated: %(id)s', {'id': execution_id})
        return execution_id


# ================================================================================
# workflow executor implementation
# ================================================================================

class AbstractScriptFileBasedWorkflowExecutor(WorkflowExecutor):
    def __init__(self, workflow, options):
        super(AbstractScriptFileBasedWorkflowExecutor, self).__init__(workflow, options)

    def _generate_task_scripts(self, execution_id):
        #
        if self.workflow.is_completed:
            return []

        #
        graph = self.workflow.trimmed_task_dependency_graph
        orig_graph = self.workflow.task_dependency_graph

        script_paths = []
        for task_name in networkx.lexicographical_topological_sort(graph):
            tasks = graph.nodes[task_name]['tasks']
            use_array = len(orig_graph.nodes[task_name]['tasks']) > 1
            dependency_task_names = list(sorted(set(f'{s}.sh' for s, t in graph.edges if t == task_name)))

            script_path = join_path(
                self.workflow.work_directory_path,
                'logs',
                execution_id,
                f'{task_name}.sh')
            script_paths.append(script_path)

            if use_array:
                sub_script_paths = []
                for task in tasks:
                    sub_script_path = join_path(
                        self.workflow.work_directory_path,
                        'logs',
                        execution_id,
                        'array',
                        f'{task.id}.sh')

                    self._render_single_task_script(task, dependency_task_names, sub_script_path)
                    sub_script_paths.append(sub_script_path)

                self._render_array_task_script(
                    tasks, dependency_task_names, sub_script_paths, script_path)

            else:
                self._render_single_task_script(tasks[0], dependency_task_names, script_path)

        #
        return script_paths

    def _render_single_task_script(self, task, dependency_task_names, script_path):
        script = render_template(self._resolve_single_task_script_template_path(), {
            'script_path': script_path,
            'script_name': os.path.basename(script_path),
            'dependency_task_names': dependency_task_names,

            'workflow': self.workflow.options.gpipe.workflow,
            'workflow_directory': self.workflow.options.gpipe.workflow_directory,
            'workflow_options': self.workflow.options.gpipe.workflow_options,
            'workflow_options_directory': self.workflow.options.gpipe.workflow_options_directory,

            'module_file_directory_path': self.workflow.module_file_directory_path,

            'work_directory_path': self.workflow.work_directory_path,
            'log_directory_path': os.path.dirname(script_path),

            'id': task.id,
            'name': task.name,
            'modules': task.modules,
            'cpus': task.cpus,
            'memory': task.memory,
            'use_temporary_directory': task.use_temporary_directory,
            'temporary_directory_path': (f'{task.id}.temp' if task.use_temporary_directory else None),
            'hard_resources': task.hard_resources,
            'soft_resources': task.soft_resources,
            'inputs': list(task.iterate_inputs()),
            'outputs': list(task.iterate_outputs()),
            'script': task.script
        })

        self._create_parent_directory_if_not_exists(script_path)
        with open(script_path, 'w') as fout:
            fout.write(script)

    @abc.abstractmethod
    def _resolve_single_task_script_template_path(self):
        raise NotImplementedError   # NOQA

    def _render_array_task_script(self, tasks, dependency_task_names, sub_script_paths, script_path):
        script = render_template(self._resolve_array_task_script_template_path(), {
            'script_path': script_path,
            'script_name': os.path.basename(script_path),
            'dependency_task_names': dependency_task_names,

            'work_directory_path': self.workflow.work_directory_path,
            'log_directory_path': os.path.dirname(script_path),

            'name': tasks[0].name,
            'cpus': tasks[0].cpus,
            'memory': tasks[0].memory,
            'hard_resources': tasks[0].hard_resources,
            'soft_resources': tasks[0].soft_resources,

            'sub_script_paths': sub_script_paths
        })

        self._create_parent_directory_if_not_exists(script_path)
        with open(script_path, 'w') as fout:
            fout.write(script)

    @abc.abstractmethod
    def _resolve_array_task_script_template_path(self):
        raise NotImplementedError   # NOQA

    @functools.lru_cache()
    def _create_parent_directory_if_not_exists(cls, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)


class SGEWorkflowExecutor(AbstractScriptFileBasedWorkflowExecutor):
    def __init__(self, workflow, options):
        super(SGEWorkflowExecutor, self).__init__(workflow, options)

    def execute(self, execution_id, dry_run=False):
        #
        script_paths = self._generate_task_scripts(execution_id)
        if not script_paths:
            logger.info('No remailing task was found.')
            return

        #
        if dry_run:
            logger.info('%(num)d scripts generated', {'num': len(script_paths)})
            for path in script_paths:
                logger.info('    * %(path)s', {'path': path})

            logger.warn('No task was submitted to GridEngine (dry-run)')

        else:
            logger.info('Submitting %(num)d tasks to GridEngine', {'num': len(script_paths)})
            for path in script_paths:
                logger.info('    => %(name)s', {'name': os.path.basename(path)})
                subprocess.check_output(['qsub', '-terse', path])

    @functools.lru_cache()
    def _resolve_single_task_script_template_path(self):
        try:
            return self.options.gpipe.executors.sge.single_task_script_template
        except AttributeError:
            logger.debug('Using default single task script template.')
            return self._resolve_script_template_path('single_task_script_template.sh.j2')

    @functools.lru_cache()
    def _resolve_array_task_script_template_path(self):
        try:
            return self.options.gpipe.executors.sge.array_task_script_template
        except AttributeError:
            logger.debug('Using default array task script template.')
            return self._resolve_script_template_path('array_task_script_template.sh.j2')

    def _resolve_script_template_path(self, name):
        return join_path(os.path.dirname(__file__), 'sge', name)

    def cancel(self, dry_run=False, force=False):
        #
        xml = lxml.etree.fromstring(subprocess.check_output(['qstat', '-xml']))
        task_names = frozenset(f'{t.name}.sh' for t in self.workflow.tasks)

        tasks = []
        for job_list in xml.xpath('//job_list'):
            #
            job_owner = str(job_list.xpath('./JB_owner/text()')[0])
            assert job_owner == getpass.getuser()

            #
            job_id = int(job_list.xpath('./JB_job_number/text()')[0])
            job_name = str(job_list.xpath('./JB_name/text()')[0])
            job_state = str(job_list.xpath('./state/text()')[0])

            try:
                job_tasks = str(job_list.xpath('./tasks/text()')[0])
                job_id_full = f'{job_id}.{job_tasks}'
            except IndexError:
                job_id_full = job_id

            #
            if job_name in task_names:
                tasks.append((job_id_full, job_id, job_name, job_state))

        if not tasks:
            return

        #
        if dry_run:
            logger.warn('The following tasks will be cancelled:')
            for _, id, name, state in tasks:
                logger.info('    * [%(id)s] (%(state)s) %(name)s ', {
                    'id': id,
                    'state': state,
                    'name': name
                })

        else:
            #
            running_tasks = [t for t in tasks if t[-1].endswith('r')]
            if running_tasks:
                logger.warn('The following tasks are currently running:')
                for _, id, name, _ in running_tasks:
                    logger.warn('    * [%(id)s] %(name)s', {'id': id, 'name': name})

                if not force:
                    return

            #
            for id_full, id, name, state in tasks:
                logger.info('Cancelling a task: [%(id)s] (%(state)s) %(name)s', {
                    'id': id,
                    'state': state,
                    'name': name
                })

            all_task_ids = list(set(str(id) for _, id, _, _ in tasks))
            subprocess.check_output(['qdel'] + all_task_ids)
