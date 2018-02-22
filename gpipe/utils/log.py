#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# log.py: Python logging module helpers
#

import inspect
import logging
import logging.config


# ================================================================================
# configuration
# ================================================================================

def configure_logging_system(
        log_file=None,
        disable_colored_logging=False,
        enable_debug=False):

    formatter = 'without_color' if disable_colored_logging else 'with_color'
    level = 'DEBUG' if enable_debug else 'INFO'
    handlers = ['console', 'file'] if log_file else ['console']

    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'without_color': {
                '()': 'logging.Formatter',
                'format': '%(asctime)s [%(levelname)-7s] %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'with_color': {
                '()': 'colorlog.ColoredFormatter',
                'format': '%(asctime)s %(log_color)s[%(levelname)-7s]%(reset)s %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'level': level,
                'class': 'logging.StreamHandler',
                'formatter': formatter
            },
            'file': {
                'level': level,
                'class': 'logging.FileHandler',
                'filename': log_file or '/dev/null',
                'formatter': 'without_color'
            }
        },
        'loggers': {
            '': {
                'handlers': handlers,
                'propagate': True,
                'level': level
            }
        }
    })


# ================================================================================
# logging method wrapper
# ================================================================================

def get_logger(name=None, depth=1):
    if not name:
        try:
            frame = inspect.stack()[depth]
            module = inspect.getmodule(frame[0])
            name = module.__name__
        except IndexError:
            name = 'UNKNOWN'

    return logging.getLogger(name)
