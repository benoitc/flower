# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import operator
import threading
import weakref

import six

from flower import core
from flower.local import local

_local = local()

class Registry(object):
    """ actors registry. This rgistry is used to keep a trace of created
    actors """

    __slots__ = ['__dict__', '_lock']

    # share state between instances
    __shared_state__ = dict(
            _registered_names = {},
            _by_ref = {}
    )

    def __init__(self):
        self.__dict__ = self.__shared_state__
        self._lock = threading.RLock()


    def register(self, name, ref):
        """ register an actor ref with a name in the registry """
        with self._lock:

            if name in self._registered_names:
                if self._registered_names[name] == ref:
                    return
                raise KeyError("An actor is already registered for this name")

            self._registered_names[name] = ref
            if not ref in self._by_ref:
                self._by_ref[ref] = [name]
            else:
                self._by_ref[ref].append(name)

    def unregister(self, ref_or_name):
        """ unregister a name in the registery. If the name doesn't
        exist we safely ignore it. """
        try:
            if isinstance(ref_or_name, six.string_types):
                with self._lock:
                    ref = self._registered_names[ref_or_name]
                    names = self._by_ref[ref]
                    del names[operator.indexOf(names, ref_or_name)]
                    del self._registered_names[ref_or_name]
            else:
                with self._lock:
                    names = self._by_ref[ref_or_name]
                    for name in names:
                        del self._registered_names[name]
        except (KeyError, IndexError):
            pass

    def registered(self, ref=None):
        """ get an actor by it's ref """
        print(type(core.getcurrent()))
        if ref is None:
            try:
                ref = core.getcurrent().ref
            except AttributeError:
                return []


        print(ref)
        print(self._by_ref)

        if ref not in self._by_ref:
            return []
        print(self._by_ref[ref])
        return sorted(self._by_ref[ref])

    def by_name(self, name):
        """ get an actor by name """
        try:
            return self._registered_names[name]
        except KeyError:
            return None

    def __getitem__(self, ref_or_name):
        if isinstance(ref_or_name, six.string_types):
            return self.by_name(ref_or_name)
        else:
            return self.registered(ref_or_name)

    def __delitem__(self, ref_or_name):
        self.unregister(ref_or_name)

    def __contains__(self, ref_or_name):
        with self._lock:
            if isinstance(ref_or_name, six.string_types):
                return ref_or_name in self._registered_names
            else:
                return ref_or_name in self._by_ref

    def __iter__(self):
        return iter(self._registered_name.items())


registry = Registry()
register = registry.register
unregister = registry.unregister
registered = registry.registered
