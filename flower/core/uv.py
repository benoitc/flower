# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import os
import sys
import threading

if sys.version_info[0] <= 2:
    import thread
else:
    import _thread as thread # python 3 fallback

_tls = thread._local()

import pyuv

from flower.core.channel import channel
from flower.core.sched import tasklet, getcurrent

def get_fd(io):
    if not isinstance(io, int):
        if hasattr(io, 'fileno'):
            if callable(io.fileno):
                fd = io.fileno()
            else:
                fd = io.fileno
        else:
            raise ValueError("invalid file descriptor number")
    else:
        fd = io
    return fd


def uv_mode(m):
    if m == 0:
        return pyuv.UV_READABLE
    elif m == 1:
        return pyuv.UV_WRITABLE
    else:
        return pyuv.UV_READABLE | pyuv.UV_WRITABLE

class FDClosing(Exception):
    pass

class LoopExit(Exception):
    pass

class FD(object):

    """ file descriptor listener used by servers

    mode:
        0: read
        1: write
        2: read & write
    """

    def __init__(self, io):
        fno = get_fd(io)
        self.io = io
        self.fno = fno
        self.cw = channel()
        self.cr = channel()
        self.ncw = 0
        self.ncr = 0
        self._lock = threading.RLock()
        self._refcount = 0
        self.closing = False

    def __str__(self):
        return "fd: %s" % self.fno

    def incrref(self, closing=False):
        with self._lock:
            if self.closing == True or self.io is None:
                raise FDClosing("fd closing: %s" % self.fno)

            self._refcount += 1
            if closing:
                self.closing = True

    def decrref(self):
        with self._lock:
            if self.io is None:
                return

            self._refcount -= 1
            if self.closing and self._refcount == 0:
                if hasattr(self.io, "close"):
                    self.io.close()
                else:
                    os.close(self.fno)

    def close(self):
        with self._lock:
            self.incrref(True)
            uv_removefd(self)
            self.decref()

    def cr_send_cb(self, handle, event, errno):
        self.send(self.cr, event, errno)

    def cw_send_cb(self, handle, event, errno):
        self.send(self.cw, event, errno)

    def send(self, channel, event, errno):
        if errno:
            channel.send_exception(IOError, errno)
        else:
            channel.send(None)

class UV(object):

    def __init__(self):
        self.loop = pyuv.Loop()
        self._async = pyuv.Async(self.loop, self._wakeloop)
        self._async.unref()
        self.fds = {}
        self._lock = threading.RLock()
        self.running = False

        # start the server task
        self._runtask = tasklet(self.run)()

    def add_fd(self, fd, mode='r'):
        with self._lock:
            if fd in self.fds:
                poller = self.fds[fd]
            else:
                poller = pyuv.Poll(self.loop, fd.fno)

            with fd._lock:
                if mode == 'r' and not fd.ncr:
                    poller.start(pyuv.UV_READABLE, fd.cr_send_cb)
                    fd.ncr += 1
                elif mode == 'w' and not fd.ncw:
                    poller.start(pyuv.UV_WRITABLE, fd.cw_send_cb)
                    fd.ncw += 1
                elif mode == 'rw':
                    if not fd.ncr:
                        poller.start(pyuv.UV_READABLE, fd.cr_send_cb)
                        fd.ncr += 1
                    if not fd.ncw:
                        poller.start(pyuv.UV_WRITABLE, fd.cw_send_cb)
                        fd.ncw += 1

            if not self.running:
                self._runtask = tasklet(self.run)()

            return fd

    def remove_fd(self, fd):
        with self._lock:
            if fd not in self.fds:
                return
            else:
                poller = self.fds[fd]

            with fd._lock:
                poller.stop()
                fd.ncr = 0
                fd.ncw = 0
            return fd

    def _wakeloop(self, handle):
        if not self.running:
            self._runtask = tasklet(self.run)()

        self.loop.update_time()

    def wakeup(self):
        self._async.send()

    def switch(self):
        if not self.running:
            self._runtask = tasklet(self.run)()

        getcurrent().remove()
        self._runtask.switch()

    def run(self):
        self.running = True
        self.loop.run()
        self.running = False

_uv_server = None

def uv_server():
    global _tls

    try:
        return _tls.uv_server
    except AttributeError:
        uv_server = _tls.uv_server = UV()
        return uv_server

def uv_addfd(fd):
    uv = uv_server()
    uv.add_fd(fd)

def uv_removefd(fd):
    uv = uv_server()
    uv.remove_fd(fd)

def uv_sleep(seconds, ref=True):
    """ use the event loop for sleep. This an alternative to our own
    time events scheduler """

    uv = uv_server()
    c = channel()
    def _sleep_cb(handle):
        handle.stop()
        c.send(None)

    sleep = pyuv.Timer(uv.loop)
    sleep.start(_sleep_cb, seconds, seconds)
    if not ref:
        sleep.unref()

    c.receive()

def uv_idle(ref=True):
    """ use the event loop for idling. This an alternative to our own
    time events scheduler """

    uv = uv_server()
    c = channel()
    def _sleep_cb(handle):
        handle.stop()
        c.send(True)


    idle = pyuv.Idle(uv.loop)
    idle.start(_sleep_cb)
    if not ref:
        idle.unref()

    return c.receive()


