#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# run.py: implementation of CANCEL command to stop an execution of a workflow
#

import click

from ..utils.path import get_absolute_path
from ..workflow.execution import get_workflow_executor_class, get_workflow_executor_ids
from ..workflow.model import load_workflow


# ================================================================================
# main
# ================================================================================

@click.command(
    name='cancel',
    help='Cancel an excecution of a workflow.'
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
    '--dry-run',
    envvar='GPIPE_DRY_RUN',
    is_flag=True,
    help='Perform a trial run without deleting any files.'
)
@click.option(
    '--force',
    envvar='GPIPE_STOP_FORCE',
    is_flag=True,
    help='Stops an execution of a workflow even if there is a running task.'
)
@click.pass_obj
def main(obj, **kwargs):
    workflow, options = load_workflow(
        obj.global_options,
        get_absolute_path(kwargs['workflow_options']))

    executor_class = get_workflow_executor_class(kwargs['executor'])
    executor = executor_class(workflow, options)

    executor.cancel(dry_run=kwargs['dry_run'], force=kwargs['force'])
