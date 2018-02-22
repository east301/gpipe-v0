#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# container.py: data structure
#

import contextlib

import deepmerge


# ================================================================================
# stack structure
# ================================================================================

class Stack(object):
    def __init__(self):
        self._items = []

    def push(self, item):
        self._items.append(item)

    def pop(self):
        self._items.pop()

    def peek(self):
        return self._items[-1]

    @contextlib.contextmanager
    def push_and_pop(self, item):
        self.push(item)
        yield item
        self.pop()


# ================================================================================
# dict helper
# ================================================================================

def merge_dicts(base, *nxts):
    result = base.copy()
    for nxt in nxts:
        deepmerge.always_merger.merge(result, nxt)

    return result
