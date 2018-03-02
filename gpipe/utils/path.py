#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# path.py: path/filesystem helpers
#

import functools
import os


class CachedFileSystemMetaResolver(object):
    @functools.lru_cache(maxsize=None)
    def exists(self, path):
        return os.path.exists(path)

    @functools.lru_cache(maxsize=None)
    def get_mtime(self, path):
        return os.path.getmtime(path)


def join_path(*args):
    return os.path.normpath(os.path.join(*args))


def get_absolute_path(path):
    return os.path.abspath(path) if path else None


def resolve_relative_path(path):
    return os.readlink(path) if os.path.islink(path) else path


def resolve_absolute_path(path):
    return os.path.abspath(resolve_relative_path(path))
