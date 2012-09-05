# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information


import threading
from flower import stackless
import thread

import pyuv

time = __import__('time').time

class Ticker(stackless.channel):
    """A Ticker holds a synchronous channel that delivers `ticks' of a
    clock at intervals."""

    def __init__(self, interval, label=''):
        super(Ticker, self).__init__(label=label)
        self._interval = interval
        self._timer = pyuv.Timer(stackless.get_loop())
        self._timer.start(self._tick, interval, True)

    def _tick(self, handle):
        self.send(time())

    def stop(self):
        self._timer.stop()
