#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# module.py: python module manipulation
#

import contextlib
import inspect
import os
import sys
import uuid
from importlib.machinery import SourceFileLoader


# ================================================================================
# import
# ================================================================================

def import_file(path, module_name=None):
    if not module_name:
        module_name = f'gpipe.user.module_{uuid.uuid4().hex[:8]}'

    loader = SourceFileLoader(module_name, path)
    return loader.load_module()


def import_relative_file(relative_path, module_name=None):
    caller_path = inspect.getfile(sys._getframe(1))
    absolute_path = os.path.join(os.path.dirname(caller_path), relative_path)

    if (not os.path.exists(absolute_path)) and os.path.islink(caller_path):
        caller_path = os.readlink(caller_path)
        absolute_path = os.path.join(os.path.dirname(caller_path), relative_path)

    return import_file(absolute_path, module_name=module_name)


def expose_members(module):
    members = {k: v for k, v in module.__dict__.items() if not k.startswith('_')}
    sys._getframe(1).f_globals.update(members)


def expose_all_members(module):
    members = {k: v for k, v in module.__dict__.items() if not k.startswith('__')}
    sys._getframe(1).f_globals.update(members)


# ================================================================================
# bytecode
# ================================================================================

@contextlib.contextmanager
def pyco_suppressed():
    orig_flag = sys.dont_write_bytecode

    sys.dont_write_bytecode = True
    yield
    sys.dont_write_bytecode = orig_flag
