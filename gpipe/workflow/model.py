#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# workflow.py: lasses for declaration of workflow
#

import collections
import contextlib
import datetime
import functools
import hashlib
import io
import itertools
import os
import subprocess

import humanfriendly
import jsonschema
import networkx
import yaml
from accessor.accessors import FailLoudAccessor

from ..utils.config import load_yaml_from_file
from ..utils.container import Stack, merge_dicts
from ..utils.log import get_logger
from ..utils.module import import_file, pyco_suppressed
from ..utils.path import CachedFileSystemMetaResolver, get_absolute_path, join_path
from ..utils.pyobject import ObjectProxy, convert_dict_to_ns, convert_ns_to_dict
from ..utils.template import render_template_string, undent
from .execution import generate_execution_id


# ================================================================================
# global
# ================================================================================

logger = get_logger()


# ================================================================================
# path declaration
# ================================================================================

class InputOutputPath(str):
    def __new__(cls, value, permanent=True, timestamp_ignored=False):
        obj = str.__new__(cls, value)
        obj._is_permanent = permanent
        obj._timestamp_ignored = timestamp_ignored
        return obj

    @property
    def is_permanent(self):
        return self._is_permanent

    @is_permanent.setter
    def set_permanent(self, value):
        self._is_permanent = value

    @property
    def is_temporary(self):
        return not self._is_permanent

    @is_temporary.setter
    def set_temporary(self, value):
        self._is_permanent = not value

    @property
    def timestamp_ignored(self):
        return self._timestamp_ignored

    @timestamp_ignored.setter
    def set_timestamp_ignored(self, value):
        self._timestamp_ignored = value


def permanent(path_or_paths):
    return _permanent_or_temporary(path_or_paths, True)


def temporary(path_or_paths):
    return _permanent_or_temporary(path_or_paths, False)


def _permanent_or_temporary(path_or_paths, permanent):
    if isinstance(path_or_paths, str):
        return InputOutputPath(path_or_paths, permanent=permanent)
    elif isinstance(path_or_paths, (list, tuple)):
        assert all(isinstance(p, str) for p in path_or_paths)
        return [InputOutputPath(p, permanent=permanent) for p in path_or_paths]
    else:
        raise Exception


def timestamp_ignored(path_or_paths):
    if isinstance(path_or_paths, str):
        return InputOutputPath(path_or_paths, timestamp_ignored=True)
    elif isinstance(path_or_paths, (list, tuple)):
        assert all(isinstance(p, str) for p in path_or_paths)
        return [InputOutputPath(p, timestamp_ignored=True) for p in path_or_paths]
    else:
        raise Exception


# ================================================================================
# task & workflow declaration
# ================================================================================

class Task(object):
    def __init__(
            self,
            name,
            modules=None,
            cpus=None,
            memory=None,
            use_temporary_directory=None,
            temporary_directory_path=None,
            hard_resources=None,
            soft_resources=None,
            inputs=None,
            outputs=None,
            parameters=None,
            script=None):

        self.name = name
        self.modules = modules or []
        self.cpus = cpus or 1
        self.memory = memory or humanfriendly.parse_size('1GB')
        self.use_temporary_directory = use_temporary_directory or False
        self.temporary_directory_path = temporary_directory_path
        self.hard_resources = hard_resources or []
        self.soft_resources = soft_resources or []
        self.inputs = inputs or collections.OrderedDict()
        self.outputs = outputs or {}
        self.parameters = parameters or {}
        self.script = script or ''

    @property
    @functools.lru_cache()
    def id(self):
        hasher = hashlib.md5()
        for key, path in itertools.chain(self.iterate_inputs(), self.iterate_outputs()):
            hasher.update(path.encode('utf-8'))

        return '{}.{}'.format(self.name, hasher.hexdigest()[:8])

    def iterate_inputs(self):
        yield from self._iterate_inputs_or_outputs(self.inputs)

    def iterate_outputs(self):
        yield from self._iterate_inputs_or_outputs(self.outputs)

    @classmethod
    def _iterate_inputs_or_outputs(cls, sources):
        for key, path_or_paths in sorted(sources.items()):
            if isinstance(path_or_paths, str):
                yield key, path_or_paths
            elif isinstance(path_or_paths, (list, tuple)):
                for path in path_or_paths:
                    yield key, path
            else:
                raise Exception

    def render(self, options):
        #
        context = {
            'options': convert_ns_to_dict(options),
            'workflow': options.gpipe.workflow,
            'workflow_directory': options.gpipe.workflow_directory,
            'workflow_options': options.gpipe.workflow_options,
            'workflow_options_directory': options.gpipe.workflow_options_directory,
            'modules': self.modules,
            'cpus': self.cpus,
            'memory': self.memory,
            'use_temporary_directory': self.use_temporary_directory,
            'temporary_directory_path': self.temporary_directory_path,
            'hard_resources': self.hard_resources,
            'soft_resources': self.soft_resources
        }
        context.update(self.parameters)

        name = render_template_string(self.name, context)
        inputs = {k: self._render_path(v, context) for k, v in self.inputs.items()}
        outputs = {k: self._render_path(v, context) for k, v in self.outputs.items()}

        #
        context.update(inputs)
        context.update(outputs)

        script = undent(render_template_string(self.script, context))

        #
        return Task(
            name=name,
            modules=self.modules,
            cpus=self.cpus,
            memory=self.memory,
            hard_resources=self.hard_resources,
            soft_resources=self.soft_resources,
            use_temporary_directory=self.use_temporary_directory,
            temporary_directory_path=self.temporary_directory_path,
            inputs=inputs,
            outputs=outputs,
            parameters=self.parameters,
            script=script
        )

    @classmethod
    def _render_path(cls, path, context):
        if isinstance(path, str):
            new_path = render_template_string(path, context)
            permanent = path.is_permanent if isinstance(path, InputOutputPath) else True
            timestamp_ignored = path.timestamp_ignored if isinstance(path, InputOutputPath) else False
            return InputOutputPath(new_path, permanent=permanent, timestamp_ignored=timestamp_ignored)

        elif isinstance(path, (list, tuple)):
            return [cls._render_path(p, context) for p in path]

        else:
            raise Exception('Unsupported')


class WorkflowBuilder(object):
    def __init__(self, option_file_path, options, execution_count):
        self.option_file_path = option_file_path
        self.options = options
        self.execution_count = execution_count
        self.task_name_prefix = self._resolve_task_name_prefix(options)
        self.tasks = []

    @classmethod
    def _resolve_task_name_prefix(cls, options):
        try:
            return options.gpipe.task_name_prefix
        except AttributeError:
            return ''

    def add_task(self, task):
        self.tasks.append(task.render(self.options))

    def build(self):
        return Workflow(self.option_file_path, self.options, self.tasks)


class Workflow(object):
    def __init__(self, option_file_path, options, tasks):
        self.options = options
        self.tasks = tasks

        self.module_file_directory_path = self._resolve_module_file_directory_path(options.gpipe.workflow)
        self.work_directory_path = self._resolve_work_directory(option_file_path, options)

        self.file_system_meta_resolver = CachedFileSystemMetaResolver()

    @classmethod
    def _resolve_module_file_directory_path(cls, workflow_file_path):
        #
        if workflow_file_path:
            path = join_path(os.path.dirname(workflow_file_path), 'modulefiles')
            if os.path.isdir(path):
                logger.info('modulefiles directory found: %(path)s', {'path': path})
                return path

        #
        if os.environ.get('MODULEPATH'):
            logger.warn('Using MODULEPATH from environment variable: %(path)s', {'path': os.environ['MODULEPATH']})
            return os.environ['MODULEPATH']

        #
        logger.warn('MODULEPATH counld not be found, and it will not be set.')
        return None

    @classmethod
    def _resolve_work_directory(cls, option_file_path, options):
        #
        if not option_file_path:
            return os.getcwd()

        #
        option_file_directory_path = os.path.dirname(option_file_path)

        try:
            return join_path(option_file_directory_path, options.gpipe.work_directory)

        except AttributeError:
            logger.warn('Work directory was not set in workflow option file.')
            logger.warn('Using option file directory as work directory: %(path)s', {
                'path': option_file_directory_path
            })
            return option_file_directory_path

    @property
    def is_completed(self):
        return len(self.trimmed_task_dependency_graph.nodes) == 0

    @property
    @functools.lru_cache()
    def task_names(self):
        return networkx.lexicographical_topological_sort(self.task_dependency_graph)

    @property
    @functools.lru_cache()
    def incomplete_task_names(self):
        return networkx.lexicographical_topological_sort(self.trimmed_task_dependency_graph)

    @property
    @functools.lru_cache()
    def file_dependency_graph(self):
        return self._build_file_dependency_graph()

    @property
    @functools.lru_cache()
    def trimmed_file_dependency_graph(self):
        return self._remove_completed_file_dependencies(self.file_dependency_graph)

    @property
    @functools.lru_cache()
    def task_dependency_graph(self):
        return self._transform_file_dependency_graph_to_task_dependency_graph(
            self.file_dependency_graph)

    @property
    @functools.lru_cache()
    def trimmed_task_dependency_graph(self):
        return self._transform_file_dependency_graph_to_task_dependency_graph(
            self.trimmed_file_dependency_graph)

    def _build_file_dependency_graph(self):
        #
        graph = networkx.DiGraph()
        for task in self.tasks:
            for _, input in task.iterate_inputs():
                for _, output in task.iterate_outputs():
                    if graph.has_edge(input, output):
                        raise Exception
                    else:
                        graph.add_edge(input, output, task=task)

        #
        incomplete_task_ids = self._get_incomplete_task_ids(graph)

        for edge_key in graph.edges:
            edge = graph.edges[edge_key]
            edge['completed'] = edge['task'].id not in incomplete_task_ids

        return graph

    def _get_incomplete_task_ids(self, graph):
        #
        makefile_content = self._generate_makefile_from_file_dependency_graph(graph)
        timestamp_ignored_files = self._get_timestamp_ignored_files()

        make_command = ['make', '--dry-run', '--directory', self.work_directory_path, '--file', '-']
        for path in timestamp_ignored_files:
            make_command.extend(['--assume-old', path])

        #
        try:
            make_output = subprocess.check_output(
                make_command,
                input=makefile_content.encode('utf-8'),
                stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as exc:
            raise Exception(f'Execution of make failed: {exc.output}') from exc

        incomplete_task_ids = set()
        for line in make_output.decode('utf-8').splitlines():
            line = line.strip()
            if line.startswith('%GR%'):
                incomplete_task_ids.add(line.strip().split('\t')[1])

        return incomplete_task_ids

    def _generate_makefile_from_file_dependency_graph(self, graph):
        #
        fout = io.StringIO()

        #
        terminal_files = []
        temporary_files = []

        for node in graph.nodes:
            if graph.out_degree(node) == 0:
                terminal_files.append(node)
            if node.is_temporary:
                temporary_files.append(node)

        print('.DEFAULT_GOAL: all', file=fout)
        print(f'all: {" ".join(terminal_files)}', file=fout)
        print(file=fout)

        if temporary_files:
            print(f'.SECONDARY: {" ".join(temporary_files)}', file=fout)
            print(file=fout)

        #
        for target in graph.nodes:
            sources = [s for s, t in graph.in_edges(target)]
            task_ids = list(sorted(set(graph.edges[s, target]['task'].id for s in sources)))

            if sources:
                print(f'{target}: {" ".join(sources)}', file=fout)
                for task_id in task_ids:
                    print(f'\t%GR%\t{task_id}', file=fout)

                print(file=fout)

        #
        return fout.getvalue()

    def _get_timestamp_ignored_files(self):
        result = set()
        for task in self.tasks:
            for _, path in itertools.chain(task.iterate_inputs(), task.iterate_outputs()):
                if path.timestamp_ignored:
                    result.add(path)

        return result

    def _remove_completed_file_dependencies(self, graph):
        edges_to_be_removed = set()
        for edge_key in graph.edges:
            if graph.edges[edge_key]['completed']:
                edges_to_be_removed.add(edge_key)

        result = graph.copy()
        for source, target in edges_to_be_removed:
            result.remove_edge(source, target)

        return result

    def _transform_file_dependency_graph_to_task_dependency_graph(self, graph):
        result = networkx.DiGraph()
        for node0, node1 in graph.edges:
            task1 = graph.edges[node0, node1]['task']
            self._add_task_to_task_dependency_graph(result, task1)

            for node2 in graph.neighbors(node1):
                task2 = graph.edges[node1, node2]['task']
                self._add_task_to_task_dependency_graph(result, task2)

                result.add_edge(task1.name, task2.name)

        return result

    def _add_task_to_task_dependency_graph(self, graph, task):
        if graph.has_node(task.name):
            tasks = graph.nodes[task.name]['tasks']
            if task not in tasks:
                tasks.append(task)
        else:
            graph.add_node(task.name, tasks=[task])

    def delete_temporary_files(self, execution_id, dry_run=True):
        #
        target_files = []
        for task in sorted(self.tasks, key=lambda t: (t.name, t.id)):
            for _, orig_path in task.iterate_outputs():
                if orig_path.is_temporary:
                    full_path = join_path(self.work_directory_path, orig_path)
                    if os.path.exists(full_path):
                        target_files.append(full_path)

        #
        if target_files:
            logger.warn('The following files will be deleted:')
            for path in target_files:
                logger.warn('  * %(path)s', {'path': path})
        else:
            logger.info('No file will be deleted.')
            return

        if dry_run:
            return

        #
        execution_id = generate_execution_id(execution_id, clean=True)
        now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        log_file_path = join_path(self.work_directory_path, 'logs', execution_id, f'clean-{now}.yml')

        logger.info('Writing files to be deleted into log file: %(path)s', {'path': log_file_path})

        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        with open(log_file_path, 'w') as fout:
            yaml.dump({
                'deleted_at': now,
                'files': target_files
            }, fout)

        for path in target_files:
            logger.warn('Deleting: %(path)s', {'path': path})
            os.remove(path)


# ================================================================================
# workflow declaration helpers
# ================================================================================

_workflow_builder_stack = Stack()
_task_stack = Stack()


@contextlib.contextmanager
def workflow(workflow_option_path, options, execution_count):
    b = WorkflowBuilder(workflow_option_path, options, execution_count)
    with _workflow_builder_stack.push_and_pop(b) as builder:
        yield builder


@contextlib.contextmanager
def task(name):
    name = _workflow_builder_stack.peek().task_name_prefix + name
    with _task_stack.push_and_pop(Task(name)) as task:
        yield task
        _workflow_builder_stack.peek().add_task(task)


def resolve_inputs(task_name, key):
    return list(_resolve_inputs_or_outputs(task_name, key, lambda t: t.iterate_inputs()))


def resolve_input(task_name, key):
    return list(resolve_inputs(task_name, key))[0]


def resolve_outputs(task_name, key):
    return list(_resolve_inputs_or_outputs(task_name, key, lambda t: t.iterate_outputs()))


def resolve_output(task_name, key):
    return list(resolve_outputs(task_name, key))[0]


def _resolve_inputs_or_outputs(task_name, key, input_output_getter):
    builder = _workflow_builder_stack.peek()

    task_name = _workflow_builder_stack.peek().task_name_prefix + task_name
    task_name = Task(task_name).render(builder.options).name

    for task in builder.tasks:
        if task.name == task_name:
            for k, p in input_output_getter(task):
                if k == key:
                    yield p


def _new_task_attribute_setter(key, default=None, converter=None):
    def do_set(value=None):
        if value is None:
            value = default
        if converter is not None:
            value = converter(value)

        setattr(_task_stack.peek(), key, value)

    return do_set


def _new_task_list_attribute_item_appender(key):
    def do_append(value):
        getattr(_task_stack.peek(), key).append(value)

    return do_append


def _new_task_dict_attribute_item_appender(key):
    def do_append(k, v):
        getattr(_task_stack.peek(), key)[k] = v

    return do_append


def _convert_memory_size(value):
    if isinstance(value, str):
        return humanfriendly.parse_size(value)
    elif callable(value):
        return value(_workflow_builder_stack.peek().execution_count)
    else:
        raise Exception('Unsupported')


log = ObjectProxy(lambda: get_logger(depth=3))  # depth=3: model -> pyobject -> user workflow
options = ObjectProxy(lambda: _workflow_builder_stack.peek().options)

module = _new_task_list_attribute_item_appender('modules')
cpus = _new_task_attribute_setter('cpus')
memory = _new_task_attribute_setter('memory', converter=_convert_memory_size)
use_temporary_directory = _new_task_attribute_setter('use_temporary_directory', default=True)
hard_resource = _new_task_list_attribute_item_appender('hard_resources')
soft_resource = _new_task_list_attribute_item_appender('soft_resources')
input = _new_task_dict_attribute_item_appender('inputs')
output = _new_task_dict_attribute_item_appender('outputs')
parameter = _new_task_dict_attribute_item_appender('parameters')
script = _new_task_attribute_setter('script')


# ================================================================================
# workflow file manipulation helpers
# ================================================================================

def load_workflow(global_options, workflow_options_path, execution_count=None):
    #
    workflow_options = _load_workflow_options(workflow_options_path, global_options)
    execution_count = _get_execution_count(execution_count, workflow_options)

    #
    logger.info('Loading workflow:')
    logger.info('    => workflow file:        %(path)s', {'path': workflow_options.gpipe.workflow})
    logger.info('    => workflow option file: %(path)s', {'path': workflow_options_path})
    logger.info('    => execution count:      %(count)s', {'count': execution_count or '(null)'})

    #
    with pyco_suppressed():
        with workflow(workflow_options_path, workflow_options, execution_count) as builder:
            import_file(workflow_options.gpipe.workflow)
            return builder.build(), workflow_options


def _load_workflow_options(workflow_options_path, global_options):
    #
    workflow_options_path = get_absolute_path(workflow_options_path)

    result = {
        'gpipe': {
            'workflow': None,
            'work_directory': None,
            'task_name_prefix': ''
        }
    }

    if global_options:
        result = merge_dicts(result, global_options)
    if workflow_options_path:
        result = merge_dicts(result, load_yaml_from_file(workflow_options_path))

    if result['gpipe']['workflow'] is None:
        raise Exception('workflow is not specified')
    else:
        if os.path.relpath(result['gpipe']['workflow']):
            result['gpipe']['workflow'] = join_path(
                os.path.dirname(workflow_options_path), result['gpipe']['workflow'])

    if result['gpipe']['work_directory'] is None:
        wd = os.path.abspath(os.getcwd())
        logger.warn('Using current directory as work directory: %(path)s', {'path': wd})
        result['gpipe']['work_directory'] = wd

    #
    result['gpipe']['workflow_directory'] = os.path.dirname(result['gpipe']['workflow'])
    result['gpipe']['workflow_options'] = workflow_options_path
    result['gpipe']['workflow_options_directory'] = os.path.dirname(workflow_options_path)

    #
    _add_workflow_option_attribute_resolver(result)
    return convert_dict_to_ns(result)


def _add_workflow_option_attribute_resolver(options):
    #
    def get(path):
        return FailLoudAccessor(path).resolve(path)

    def get_or_default(path, default):
        try:
            return get(path)
        except ValueError:
            return default

    def get_or_none(path):
        return get_or_default(path, None)

    def contains(path):
        try:
            get(path)
            return True
        except ValueError:
            return False

    def validate(properties):
        options0 = {k: v for k, v in options.items() if k not in accessors}  # hide accessors
        try:
            jsonschema.validate(options0, {
                'type': 'object',
                'properties': properties,
                'required': list(properties.keys())
            })
        except jsonschema.ValidationError as exc:
            raise Exception(f'Failed to validate workflow options: {exc.message}') from exc

    #
    accessors = {
        'get': get,
        'get_or_default': get_or_default,
        'get_or_none': get_or_none,
        'contains': contains,
        'validate': validate
    }
    options.update(accessors)


def _get_execution_count(user_execution_count, workflow_options):
    #
    if user_execution_count is not None:
        return user_execution_count

    #
    log_directory_path = join_path(workflow_options.gpipe.work_directory, 'logs')
    if os.path.exists(log_directory_path):
        execution_count = len([n for n in os.listdir(log_directory_path) if '.' not in n]) + 1
    else:
        execution_count = 1

    logger.info('Execution count automatically determined: %(count)d', {
        'count': execution_count
    })

    return execution_count
