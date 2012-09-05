# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information


import threading
from flower import stackless

import pyuv

time = __import__('time').time

class Ticker(stackless.channel):
    """A Ticker holds a synchronous channel that delivers `ticks' of a
    clock at intervals."""

    def __init__(self, interval, label=''):
        super(Ticker, self).__init__(label=label)
        self._interval = interval
        self._timer = pyuv.Timer(stackless.get_loop())
        self._timer.start(self._tick, interval, interval)

    def _tick(self, handle):
        self.send(time())

    def stop(self):
        self._timer.stop()

def sleep(delay=0, ref=True):
    """ sleep the current tasklet for a while, if ref is False, it won't
    block the loop if it quit"""
    c = stackless.channel()
    def wakeup(handle):
        handle.stop()
        c.send(None)

    if delay == 0:
        w = pyuv.Idle(stackless.get_loop())
        w.start(wakeup)
    else:
        w = pyuv.Timer(stackless.get_loop())
        w.start(wakeup, delay, delay)

    if not ref:
        w.unref()
    c.receive()

class Timeout(BaseException):
    """\
    Raise *exception* in the current tasklet after given time period::

        timeout.start()
        try:
            ...  # exception will be raised here, after the timeout
        finally:
            timeout.cancel()

        When *exception* is omitted or ``None``, the :class:`Timeout`
        instance itself is raised:

    You can also use the with statement::

        with Timeout(seconds, exception) as timeout:
            pass  # ... code block ...
     """

    def __init__(self, seconds=None, timeout_ex=None):
        self.seconds = seconds
        self.timeout_ex = timeout_ex
        self._current_task = None
        self._timer = None

    def start(self):
        """Schedule the timeout."""
        if self.seconds is None:
            return

        self._current_task = stackless.getcurrent()
        self._timer = pyuv.Timer(stackless.get_loop())
        self._timer.start(self._throw, self.seconds, 0)
        stackless.wakeup_loop()

    def _throw(self, handle):
        # stop the timer
        handle.stop()

        if not self.timeout_ex:
            exp = self
        else:
            exp = self.timeout_ex

        # throw the exception
        self._current_task.throw(exp)

    def cancel(self):
        if self._timer is not None:
            self._timer.stop()

    def active(self):
        return self._timer is not None and self._timer.active

    def __str__(self):
        return 'timeout[%s] (%ss)' % (self.label, self.seconds)

    def __enter__(self):
        if not self._timer:
            self.start()
        return self

    def __exit__(self, typ, value, tb):
        self.cancel()
        if value is self and self.timeout_ex is False:
            return True

def with_timeout(seconds, func, *args, **kwargs):
    """
    timeout wrapper. A custom class exception can be passed using the
    `timeout_ex` argument.
    """
    timeout_ex = kwargs.pop("timeout_ex", None)
    with Timeout(seconds, timeout_ex):
        return func(*args, **kwargs)

def timeout_(seconds=None, timeout_ex=None):
    """ timeout decorator::

        @timeout_(0.2)
        def f():
            pass
    """

    def _wrapper(func):
        def _inner(*args, **kwargs):
            with Timeout(seconds=seconds, timeout_ex=timeout_ex):
                func(*args, **kwargs)
        return _inner
    return _wrapper
