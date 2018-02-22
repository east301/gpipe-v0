#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# template.py: templating powered by Jinja2
#

import functools
import os
import pkg_resources

import jinja2


# ================================================================================
# jinja2 wrapper functions
# ================================================================================

def render_template(path, context):
    template_dir, template_name = os.path.split(path)

    loader = jinja2.FileSystemLoader(template_dir)
    env = _create_jinja2_environment(loader)
    template = env.get_template(template_name)

    return template.render(context)


def render_template_string(template, context):
    env = _create_jinja2_environment(None)
    template = env.from_string(template)

    return template.render(context)


def _create_jinja2_environment(loader):
    env = jinja2.Environment(loader=loader)
    env.filters.update(_load_jinja2_filters())
    return env


@functools.lru_cache()
def _load_jinja2_filters():
    filters = {}
    for loader in pkg_resources.iter_entry_points('gpipe_template_filter_factories'):
        filters.update(loader.load()())

    return filters


# ================================================================================
# jinja2 filters
# ================================================================================

def get_jinja2_filters():
    return {
        'dirname': os.path.dirname,
        'basename': os.path.basename,
        'extension': extension,
        'without_extension': without_extension,

        'kb': kb,
        'mb': mb,
        'gb': gb,
        'KB': kb,
        'MB': mb,
        'GB': gb
    }


def extension(path):
    return os.path.splitext(path)[1]


def without_extension(path):
    return os.path.splitext(path)[0]


def kb(bytes):
    return '{:.02f}'.format(bytes / 1000)


def mb(bytes):
    return '{:.02f}'.format(bytes / 1000 / 1000)


def gb(bytes):
    return '{:.02f}'.format(bytes / 1000 / 1000 / 1000)


# ================================================================================
# string manipulation helpers
# ================================================================================

def undent(text):
    #
    offset = 0
    for line in text.splitlines():
        if not line.strip():
            continue

        offset = len(line) - len(line.lstrip())
        break

    #
    return '\n'.join([l[offset:] for l in text.splitlines()]).strip()
