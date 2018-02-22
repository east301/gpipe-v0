#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# cli.py: CLI frontend of GridRunner
#

import argparse
import logging
import logging.config
import pkg_resources

import click
import dotenv
from click_help_colors import HelpColorsCommand, HelpColorsGroup

from .utils.config import load_yaml_from_file
from .utils.container import merge_dicts
from .utils.log import configure_logging_system
from .utils.pyobject import once


# ================================================================================
# global
# ================================================================================

logger = logging.getLogger(__name__)


# ================================================================================
# main
# ================================================================================

def main():
    dotenv.load_dotenv(dotenv.find_dotenv())
    _patch_click()
    _load_commands()
    _run_click()


# ================================================================================
# internal
# ================================================================================

@once
def _patch_click():
    #
    orig_command = click.command

    def new_command(*args, **kwargs):
        def wrap(func):
            kwargs.update({
                'cls': HelpColorsCommand,
                'help_headers_color': 'yellow',
                'help_options_color': 'green'
            })
            return orig_command(*args, **kwargs)(func)

        return wrap

    #
    click.command = new_command


@once
def _load_commands():
    for loader in pkg_resources.iter_entry_points('gpipe_commands'):
        _run_click.add_command(loader.load())


@click.group(
    cls=HelpColorsGroup,
    help_headers_color='yellow',
    help_options_color='green'
)
@click.option(
    '--global-option-file',
    envvar='GPIPE_GLOBAL_OPTION_FILE',
    type=click.Path(exists=True),
    multiple=True,
    help='Path to a file which contains global options.'
)
@click.option(
    '--log-file',
    envvar='GPIPE_LOG_FILE',
    type=click.Path(),
    help='Path to a file in which terminal outputs are written.'
)
@click.option(
    '--disable-colored-logging',
    envvar='GPIPE_DISABLE_COLORED_LOGGING',
    is_flag=True,
    help='Disable colored logging feature.'
)
@click.option(
    '--debug',
    envvar='GPIPE_DEBUG',
    is_flag=True,
    help='Shows debug outputs.'
)
@click.pass_context
def _run_click(ctx, **kwargs):
    configure_logging_system(
        log_file=kwargs['log_file'],
        disable_colored_logging=kwargs['disable_colored_logging'],
        enable_debug=kwargs['debug'])

    ctx.obj = argparse.Namespace(
        global_options=_load_global_options(kwargs['global_option_file'])
    )


def _load_global_options(paths):
    #
    if not paths:
        return {}

    #
    logger.info('Loading global option file:')

    result = {}
    for path in paths:
        logger.info('    * %(path)s', {'path': path})
        result = merge_dicts(result, load_yaml_from_file(path))

    return result
