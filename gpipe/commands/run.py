#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# run.py: implementation of RUN command to run a workflow
#

import click

from ..utils.path import get_absolute_path
from ..workflow.execution import (
    generate_execution_id,
    get_workflow_executor_class,
    get_workflow_executor_ids
)
from ..workflow.model import load_workflow


# ================================================================================
# main
# ================================================================================

@click.command(
    name='run',
    help='Run workflow specified by WORKFLOW and WORKFLOW_OPTIONS files.'
)
@click.argument(
    'workflow_options',
    envvar='GPIPE_WORKFLOW_OPTIONS',
    type=click.Path(exists=True),
    required=False
)
@click.option(
    '--executor',
    envvar='GPIPE_EXECUTOR',
    type=click.Choice(get_workflow_executor_ids()),
    default=get_workflow_executor_ids()[0],
    help='Executor to execute a workflow.'
)
@click.option(
    '--execution-id',
    envvar='GPIPE_EXECUTION_ID',
    help='Use a custom execution ID.'
)
@click.option(
    '--execution-count',
    envvar='GPIPE_EXECUTION_COUNT',
    type=int,
    help='Use a custom execution count.'
)
@click.option(
    '--dry-run',
    envvar='GPIPE_DRY_RUN',
    is_flag=True,
    help='Perform a trial run without submitting any tasks to GridEngine.'
)
@click.pass_obj
def main(obj, **kwargs):
    workflow, options = load_workflow(
        obj.global_options,
        get_absolute_path(kwargs['workflow_options']),
        execution_count=kwargs['execution_count'])

    executor_class = get_workflow_executor_class(kwargs['executor'])
    executor = executor_class(workflow, options)

    execution_id = generate_execution_id(kwargs['execution_id'], dry_run=kwargs['dry_run'])
    executor.execute(execution_id, dry_run=kwargs['dry_run'])
