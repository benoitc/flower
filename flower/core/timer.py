# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import heapq
import threading

import six

from .util import nanotime
from .tasks import (tasklet, schedule, schedule_remove, get_scheduler,
        getcurrent)


class Timers(object):

    __slots__ = ['__dict__', '_lock', 'sleeping']

    __shared_state__ = dict(
            _timers = {},
            _heap = [],
            _next = 0
    )


    def __init__(self):
        self.__dict__ = self.__shared_state__
        self._lock = threading.RLock()
        self.sleeping = None
        self.idle = True


    def add(self, t):
        with self._lock:
            self._add_timer(t)
            tasklet(self.timerproc)()

    def _add_timer(self, t):
        if not t.interval:
            return

        t.when = nanotime() + nanotime(t.interval)
        ht =  [t.when, t]
        heapq.heappush(self._heap, ht)
        self._timers[t] = ht

    def remove(self, t):
        with self._lock:
            try:
                ht = self._timers.pop(t)
                del self._heap[operator.indexOf(self._heap, ht)]
            except (IndexError, ValueError):
                pass

    def timerproc(self):
        while True:
            with self._lock:
                if not len(self._heap):
                    return

                last = heapq.heappop(self._heap)
                t = last[1]
                now = nanotime()
                delta = t.when - now
                if delta > 0:
                    heapq.heappush(self._heap, last)
                    schedule()
                else:
                    del self._timers[t]

                    # repeat ? reinsert the timer
                    if t.period and t.period is not None:
                        t.when += t.period * (1 - delta/t.periodà)
                        self._add_timer(t)

                    # run
                    t.callback(now, *t.args, **t.kwargs)

                    # nothing to do quit the task
                    break


timers = Timers()
add_timer = timers.add
remove_timer = timers.remove


class Timer(object):

    def __init__(self, callback, interval=None, period=None, args=None,
            kwargs=None):
        if not six.callable(callback):
            raise ValueError("callback must be a callable")

        self.callback = callback
        self.interval = interval
        self.period = period
        self.args = args or []
        self.kwargs = kwargs or {}
        self.when = 0

    def start(self):
        global timers
        self.when = nanotime() + nanotime(self.interval)
        add_timer(self)

    def stop(self):
        remove_timer(self)


def sleep(seconds=0):
    if not seconds:
        return

    sched = get_scheduler()
    curr = getcurrent()
    def ready(now):
        curr.blocked = False
        sched.append(curr)
        schedule()

    t = Timer(ready, seconds)
    t.start()

    curr.blocked = True
    schedule_remove()
