#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# pyobject.py
#

import functools
import operator
from argparse import Namespace


# ================================================================================
# argparse.Namespace handling
# ================================================================================

def convert_dict_to_ns(root):
    if isinstance(root, dict):
        root = {k: convert_dict_to_ns(v) for k, v in root.items()}
        return Namespace(**root)
    elif isinstance(root, Namespace):
        root = {k: convert_dict_to_ns(v) for k, v in iterate_ns_entries(root)}
        return Namespace(**root)
    elif isinstance(root, (list, tuple)):
        return [convert_dict_to_ns(v) for v in root]
    else:
        return root


def convert_ns_to_dict(root):
    if isinstance(root, dict):
        return {k: convert_ns_to_dict(v) for k, v in root.items()}
    elif isinstance(root, Namespace):
        return {k: convert_ns_to_dict(v) for k, v in iterate_ns_entries(root)}
    elif isinstance(root, (list, tuple)):
        return [convert_ns_to_dict(v) for v in root]
    else:
        return root


def iterate_ns_entries(ns):
    for key in dir(ns):
        if not key.startswith('__'):
            yield key, getattr(ns, key)


# ================================================================================
# method invocation helper
# ================================================================================

def once(func):
    func._is_invoked = False

    @functools.wraps(func)
    def invoke_wrapped_func(*args, **kwargs):
        if not func._is_invoked:
            func._is_invoked = True
            return func(*args, **kwargs)

    return invoke_wrapped_func


# ================================================================================
# object proxy
# ================================================================================

def _new_method_proxy(func):
    def inner(self, *args, **kwargs):
        return func(self._get_proxy_target(), *args, **kwargs)

    return inner


class ObjectProxy(object):
    def __init__(self, getter):
        self._get_proxy_target = getter

    def __setattr__(self, name, value):
        if name == '_get_proxy_target':
            self.__dict__['_get_proxy_target'] = value
        else:
            setattr(self._get_proxy_target(), name, value)

    __getattr__ = _new_method_proxy(getattr)
    __delattr__ = _new_method_proxy(delattr)

    __bytes__ = _new_method_proxy(bytes)
    __str__ = _new_method_proxy(str)
    __bool__ = _new_method_proxy(bool)

    __dir__ = _new_method_proxy(dir)

    __class__ = property(_new_method_proxy(operator.attrgetter('__class__')))
    __eq__ = _new_method_proxy(operator.eq)
    __ne__ = _new_method_proxy(operator.ne)
    __hash__ = _new_method_proxy(hash)

    __getitem__ = _new_method_proxy(operator.getitem)
    __setitem__ = _new_method_proxy(operator.setitem)
    __delitem__ = _new_method_proxy(operator.delitem)

    __len__ = _new_method_proxy(len)
    __contains__ = _new_method_proxy(operator.contains)
