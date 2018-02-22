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
import pkg_resources
import platform

import click


# ================================================================================
# global
# ================================================================================

logger = logging.getLogger(__name__)


# ================================================================================
# main
# ================================================================================

@click.command(
    name='version',
    help='Show version.'
)
def main(**kwargs):
    logger.info('GridPipe %(gpipe_version)s, running on Python %(py_version)s', {
        'gpipe_version': _get_gpipe_version(),
        'py_version': platform.python_version()
    })


def _get_gpipe_version():
    try:
        return pkg_resources.require('gpipe')[0].version
    except Exception as exc:
        logger.exception('Failed to read package information: %s', exc)
        return 'UNKNOWN'
