# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import copy
from collections import deque
import operator
import sys
import threading
import weakref

if sys.version_info[0] <= 2:
    import thread
else:
    import _thread as thread # python 3 fallback

import pyuv
import six

from flower import stackless
from flower.registry import registry
from flower.time import Timeout, sleep, defer


def self():
    return stackless.getcurrent()


class ActorRef(object):

    __slots__ = ['ref', '_actor_ref', 'is_alive', '__dict__']

    __shared_state__ = dict(
            _ref_count = 0
    )

    def __init__(self, actor):
        self.__dict__ = self.__shared_state__
        self._actor_ref = weakref.ref(actor)

        # increment the ref counter
        with threading.RLock():
            self.ref = self._ref_count
            self._ref_count += 1

        #registry.insert(self)

    def __str__(self):
        return "<actor:%s>" % self.ref

    @property
    def actor(self):
        return self._actor_ref()

    @property
    def is_alive(self):
        return self.actor is not None

class Message(object):

    def __init__(self, source, dest, msg):
        self.source = source
        self.dest = dest
        self.msg = msg

    def send(self):
        target = self.dest.actor
        if not target:
            registry.unregister(self.dest)
            return

        target.send((self.source.ref, self.msg))

    def send_after(self, seconds):
        defer(seconds, self.send)



class Mailbox(object):
    """ a mailbox can accept any message from other actors.
    This is different from a channel since it doesn't block the sender.

    Each actors have an attached mailbox used to send him some any
    messages.
    """

    def __init__(self):
        self.messages = deque()
        self.channel = stackless.channel()
        self._lock = threading.RLock()

    def send(self, msg):
        """ append a message to the queue or if the actor is accepting
        messages send it directly to it """

        if self.channel is not None and self.channel.balance < 0:
            self.channel.send(msg)
        else:
            # no waiters append to the queue and return
            self.messages.append(msg)
            return

    def receive(self):
        """ fetch a message from the queue or wait for a new one """
        try:
            return self.messages.popleft()
        except IndexError:
            pass
        return self.channel.receive()

    def flush(self):
        with self._lock:
            while True:
                try:
                    yield self.messages.popleft()
                except IndexError:
                    raise StopIteration

    def clear(self):
        self.messages.clear()

class Actor(stackless.tasklet):

    """ An actor is like a tasklet but with a mailbox. """

    def __init__(self):
        stackless.tasklet.__init__(self)
        self.ref = ActorRef(self)
        self.links = []
        self.mailbox = Mailbox()
        self.scheduler = stackless.get_scheduler()

    @classmethod
    def spawn(cls, func, *args, **kwargs):
        instance = cls()

        # wrap func to be scheduled immediately
        def _func():
            func(*args, **kwargs)
            sleep(0.0)
        instance.bind(_func)
        instance.setup()
        return instance.ref

    @classmethod
    def spawn_link(cls, func, *args, **kwargs):
        curr = stackless.getcurrent()
        if not hasattr(curr, 'mailbox'):
            curr = cls.wrap(curr)

        if operator.indexOf(self.links, curr.ref) < 0:
            self.links.append(curr.ref)

        return cls.spawn(func, *args, **kwargs)

    @classmethod
    def spawn_after(cls, seconds, func, *args, **kwargs):
        instance = cls()

        def _fun(handle):
            handle.stop()
            instance.bind(func)
            instance.setup(func)
            sleep(0.0)

        t = pyuv.Timer(stackless.get_loop())
        t.start(_func, seconds, seconds)
        return instance.ref

    def unlink(self, ref):
        idx = operator.indexOf(self.links, curr.ref)
        if idx < 0:
            return
        with self._lock:
            del self.links[idx]

    @classmethod
    def wrap(cls, task):
        """ method to wrap a task to an actor """

        if hasattr(task, 'mailbox'):
            return

        return type('AnonymousActor', (cls, ), task)

    def send(self, msg):
        self.mailbox.send(msg)

    def receive(self):
        return self.mailbox.receive()

    def flush(self):
        return self.mailbox.flush()


spawn = Actor.spawn
spawn_link = Actor.spawn_link
spawn_after = Actor.spawn_after
wrap = Actor.wrap

def maybe_wrap(actor):
    if not hasattr(actor, 'mailbox'):
        return wrap(actor)
    return actor

def send(dest, msg):
    """ send a message to the destination """
    source = maybe_wrap(stackless.getcurrent())

    if isinstance(dest, six.string_types):
        dest = registry[dest]
    elif isinstance(dest, stackless.tasklet):
        dest = maybe_wrap(dest)

    mail = Message(source, dest, msg)
    mail.send()

def send_after(seconds, dest, msg):
    """ send a message after n seconds """

    if not seconds:
        return send(dest, msg)

    source = maybe_wrap(stackless.getcurrent())
    if isinstance(dest, six.string_types):
        dest = registry[dest]
    elif isinstance(dest, stackless.tasklet):
        dest = maybe_wrap(dest)

    mail = Message(source, dest, msg)
    mail.send_after(seconds)

def receive():
    curr = maybe_wrap(stackless.getcurrent())
    return curr.receive()

def flush():
    curr = maybe_wrap(stackless.getcurrent())
    curr.flush()
