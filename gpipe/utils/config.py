#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# config.py: configuration file manipulation
#

import os

import yaml

from .pyobject import once


# ================================================================================
# YAML loader
# ================================================================================

class GPipeYamlLoader(yaml.Loader):
    def __init__(self, stream):
        super(GPipeYamlLoader, self).__init__(stream)
        self._root = os.path.split(stream.name)[0]

    def include(self, node):
        path = os.path.join(self._root, self.construct_scalar(node))
        with open(path) as fin:
            return yaml.load(fin, GPipeYamlLoader)

    def to_absolute_path(self, node):
        return os.path.abspath(os.path.join(self._root, self.construct_scalar(node)))


def load_yaml_from_stream(stream):
    _register_include_directive()
    return yaml.load(stream, GPipeYamlLoader)


def load_yaml_from_file(path):
    with open(path) as fin:
        return load_yaml_from_stream(fin)


@once
def _register_include_directive():
    directives = ['include', 'to_absolute_path']
    for key in directives:
        GPipeYamlLoader.add_constructor(f'!{key}', getattr(GPipeYamlLoader, key))
