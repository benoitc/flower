# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information


time = __import__('time').time

from flower import core
from flower.core import timer
from flower.core.util import from_nanotime

class Ticker(core.channel):
    """A Ticker holds a synchronous channel that delivers `ticks' of a
    clock at intervals."""

    def __init__(self, interval, label=''):
        super(Ticker, self).__init__(label=label)
        self._interval = interval
        self._timer = timer.Timer(self._tick, interval, interval)
        self._timer.start()

    def _tick(self, now, h):
        self.send(from_nanotime(now))

    def stop(self):
        self._timer.stop()

def idle():
    """ By using this function the current tasklet will be scheduled asap"""

    sched = core.get_scheduler()
    curr = core.getcurrent()
    def ready(now, h):
        curr.blocked = False
        sched.append(curr)
        core.schedule()

    t = timer.Timer(ready, 0.0001)
    t.start()

    curr.blocked = True
    core.schedule_remove()

def sleep(seconds=0):
    """ sleep the current tasklet for a while"""
    if not seconds:
        idle()
    else:
        timer.sleep(seconds)

def defer(seconds, fun, *args, **kwargs):

    def _defer():
        loop = core.get_loop()
        c = Ticker(seconds)
        try:
            c.receive()
        finally:
            c.stop()
        fun(*args, **kwargs)

    core.tasklet(_defer)()
