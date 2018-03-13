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

import click

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
    name='clean',
    help='Delete all files marked as "temporary".'
)
@click.argument(
    'workflow_options',
    envvar='GPIPE_WORKFLOW_OPTIONS',
    type=click.Path(exists=True),
    required=False
)
@click.option(
    '--dry-run',
    envvar='GPIPE_DRY_RUN',
    is_flag=True,
    help='Perform a trial run without deleting any files.'
)
@click.option(
    '--execution-id',
    envvar='GPIPE_EXECUTION_ID',
    help='Use a custom execution ID.'
)
@click.option(
    '--ignore-incomplete-tasks',
    envvar='GPIPE_CLEAN_IGNORE_INCOMPLETE_TASKS',
    is_flag=True,
    help='Deletes all temporary files even if there is an incomplete task.'
)
@click.pass_obj
def main(obj, **kwargs):
    #
    workflow, _ = load_workflow(
        obj.global_options,
        get_absolute_path(kwargs['workflow_options']))

    #
    if not workflow.is_completed:
        logger.warn('The following tasks are incomplete:')
        for task_name in workflow.incomplete_task_names:
            logger.warn('    * %(name)s', {'name': task_name})

        if not kwargs['ignore_incomplete_tasks']:
            return

    workflow.delete_temporary_files(kwargs['execution_id'], dry_run=kwargs['dry_run'])
