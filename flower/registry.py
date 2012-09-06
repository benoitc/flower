# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import operator
import threading
from weakref import WeakKeyDictionary, WeakValueDictionary

import six

from flower import stackless

class Registry(object):
    """ actors registry. This rgistry is used to keep a trace of created
    actors """

    # share state between instances
    __shared_state__ = dict(
            _actors = WeakValueDictionary(),
            _registered_names = {},
            _names_by_id = {}
    )

    def __init__(self):
        self.__dict__ = self.__shared_state__
        self._lock = threading.RLock()


    def insert(self, actor=None):
        """ insert an actor instance in the registery """
        if actor is None:
            actor = stackless.getcurrent()

        actor_id = id(actor)
        self._actors[actor_id] = actor
        return actor_id

    def remove(self, actor=None):
        """ remove an actor from the registery """
        if actor is None:
            actor = stackless.getcurrent()
            actor_id = id(actor)
        elif not isinstance(actor, int):
            actor_id = id(actor)
        else:
            actor_id = actor

        del self._actors[actor_id]

        # remove the actor from registered names as well
        try:
            names = self._names_by_id.pop(actor_id)
            for n in names:
                del self._registered_names[n]
        except KeyError:
            pass

    def register(self, name, actor=None):
        """ register an actor id with a name in the registry """
        if actor is None:
            actor = stackless.getcurrent()
            actor_id = id(actor)
        elif not isinstance(actor, int):
            actor_id = id(actor)
        else:
            actor_id = actor

        with self._lock:
            if actor_id not in self._actors:
                raise KeyError("Actor with %s id is unknown" % actor_id)

            if name in self._registered_names:
                if self._registered_names[name] == actor_id:
                    return
                raise KeyError("An actor is already registered for this name")

            self._registered_names[name] = actor_id
            if not actor_id in self._names_by_id:
                self._names_by_id[actor_id] = []
            self._names_by_id[actor_id].append(name)

    def unregister(self, name):
        """ unregister a name in the registery """

        if isinstance(name, int):
            names = self._names_by_id[name]
            with self._lock:
                for n in names:
                    del self._registered_names[n]
                del self._names_by_id[name]
        else:
            actor_id = self._registered_names[name]
            names  = self._names_by_id[actor_id]
            del self._registered_names[name]
            del names[operator.indexOf(names, name)]

    def by_id(self, actor):
        """ get an actor by it's id """
        try:
            return self._actors[actor]
        except KeyError:
            raise KeyError("Actor with %s id is unknown" % actor)

    def by_name(self, name):
        """ get an actor by name """
        try:
            return self.by_id(self._registered_names[name])
        except KeyError:
            raise KeyError("Actor with %s name is unknown" % name)

    def __getitem__(self, actor):
        if isinstance(actor, six.string_types):
            return self.by_name(actor)
        else:
            return self.by_id(actor)

    def __delitem__(self, actor):
        if isinstance(actor, six.string_types):
            actor = self._registered_names[actor]
        self.remove(actor)

    def __contains__(self, actor):
        with self._lock:
            if isinstance(actor, six.string_types):
                return actor in self._registered_names
            else:
                return actor in self._actors

    def __iter__(self):
        for actor in self._actors:
            yield self._actors[actor]


registry = Registry()
insert = registry.insert
remove = registry.remove
register = registry.register
unregister = registry.unregister
