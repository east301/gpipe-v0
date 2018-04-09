#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# run.py: implementation of RUN command to run a workflow
#

import logging
import os

import click
import networkx

from ..utils.click_support import MutuallyExclusiveOption
from ..utils.path import get_absolute_path
from ..workflow.model import load_workflow


# ================================================================================
# global
# ================================================================================

logger = logging.getLogger(__name__)


# ================================================================================
# main
# ================================================================================

@click.command(
    name='graph',
    help='Creates file/task dependency graph.'
)
@click.argument(
    'workflow_options',
    envvar='GPIPE_WORKFLOW_OPTIONS',
    type=click.Path(exists=True)
)
@click.argument(
    'output',
    envvar='GPIPE_GRAPH_OUTPUT',
    type=click.Path()
)
@click.option(
    '--file',
    envvar='GPIPE_GRAPH_FILE',
    is_flag=True,
    cls=MutuallyExclusiveOption,
    help='Creates file dependency graph',
    mutually_exclusive=['task']
)
@click.option(
    '--task',
    envvar='GPIPE_GRAPH_TASK',
    is_flag=True,
    cls=MutuallyExclusiveOption,
    help='Creates task dependency graph',
    mutually_exclusive=['file']
)
@click.pass_obj
def main(obj, **kwargs):
    #
    workflow, workflow_options = load_workflow(
        obj.global_options,
        get_absolute_path(kwargs['workflow_options']))

    #
    if kwargs['file']:
        graph = workflow.file_dependency_graph
        graph = networkx.relabel_nodes(graph, {n: os.path.basename(n) for n in graph.nodes})

    else:
        graph = workflow.task_dependency_graph
        offset = len(workflow_options.gpipe.task_name_prefix)
        graph = networkx.relabel_nodes(graph, {n: n[offset:] for n in graph.nodes})

        start_nodes = [n for n in graph.nodes if graph.in_degree(n) == 0]
        graph.add_node('START')
        for start_node in start_nodes:
            graph.add_edge('START', start_node)

    #
    format = os.path.splitext(kwargs['output'])[1][1:]
    if format not in ('jpg', 'pdf', 'png'):
        raise Exception(f'Format not supported: {format}')

    #
    pydot_graph = networkx.nx_pydot.to_pydot(graph)
    pydot_graph.write(kwargs['output'], prog='dot', format=format)
