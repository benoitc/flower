# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import weakref
from flower.stackless import getcurrent


class local(object):
    """ a local class working like a thread.local class to keep local
    attrributes for a given tasklet """

    class _local_attr(object): pass

    def __init__(self):
        self._d = weakref.WeakKeyDictionary()

    def __getattr__(self, key):
        d = self._d
        curr = getcurrent()
        if not curr in d or not hasattr(d[curr], key):
            raise AttributeError(key)
        return getattr(d[curr], key)

    def __setattr__(self, key, value):
        if key == '_d':
            self.__dict__[key] = value
            object.__setattr__(self, key, value)
        else:
            d = self._d
            curr = getcurrent()
            if not curr in d:
                d[curr] = self._local_attr()
            setattr(d[curr], key, value)

    def __delattr__(self, key):
        d = self._d
        curr = getcurrent()
        if not curr in d or not hasattr(d[curr], key):
            raise AttributeError(key)
        delattr(d[curr], key)
