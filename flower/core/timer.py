# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import heapq
import operator
import threading

import six

from .util import nanotime
from .tasks import (tasklet, schedule, schedule_remove, get_scheduler,
        getcurrent, taskwakeup, getmain)


class Timers(object):

    __slots__ = ['__dict__', '_lock', 'sleeping']

    __shared_state__ = dict(
            _timers = {},
            _heap = [],
            _next = 0,
            _timerproc = None
    )

    def __init__(self):
        self.__dict__ = self.__shared_state__
        self._lock = threading.RLock()
        self.sleeping = False


    def add(self, t):
        with self._lock:
            self._add_timer(t)

            if self.sleeping:
                self.sleeping = False
                taskwakeup(self._timerproc)

            if self._timerproc is None or not self._timerproc.alive:
                self._timerproc = tasklet(self.timerproc)()

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
            except (KeyError, IndexError):
                pass

    def timerproc(self):
        while True:
            self._lock.acquire()

            while True:
                if not len(self._heap):
                    delta = -1
                    break

                last = heapq.heappop(self._heap)
                t = last[1]
                now = nanotime()
                delta = t.when - now
                if delta > 0:
                    heapq.heappush(self._heap, last)
                    break
                else:
                    del self._timers[t]

                    # repeat ? reinsert the timer
                    if t.period is not None and t.period > 0:
                        np = nanotime(t.period)
                        t.when += np * (1 - delta/np)
                        ht =  [t.when, t]
                        heapq.heappush(self._heap, ht)
                        self._timers[t] = ht

                    # run
                    self._lock.release()
                    t.callback(now, t, *t.args, **t.kwargs)
                    self._lock.acquire()


            if delta < 0:
                self.sleeping = True
                self._lock.release()
                schedule_remove()
            else:
                self._lock.release()
                schedule()

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
        self.active = False

    def start(self):
        global timers
        self.active = True
        self.when = nanotime() + nanotime(self.interval)
        add_timer(self)

    def stop(self):
        remove_timer(self)
        self.active = False


def sleep(seconds=0):
    if not seconds:
        return

    sched = get_scheduler()
    curr = getcurrent()

    def ready(now, t):
        curr.blocked = False
        sched.append(curr)
        schedule()

    t = Timer(ready, seconds)
    t.start()

    if curr is not getmain():
        curr.blocked = True

    schedule_remove()
