# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import os
import threading
import time
import pyuv

from flower.core.util import thread_ident
from flower.core import run, channel, tasklet
from flower.core import uv

def test_spawn(task=None):
    task = task or uv.spawn_iotask()
    uv.exit(task)

    assert isinstance(task, uv.IoTask)
    assert isinstance(task.async_handle, pyuv.Async)
    assert task.thread_id != thread_ident()
    assert task.thread_id not in list(threading.enumerate())

def test_default_task():
    test_spawn(uv.default_iotask())

def test_force_exit():
    task = uv.spawn_iotask()

    def cb(loop):
        def _cb(handle): return
        p = pyuv.Idle(loop)
        p.start(_cb)

    uv.interract(task, cb)
    uv.exit(task)

    time.sleep(0.1)
    assert isinstance(task, uv.IoTask)
    assert task.thread_id not in list(threading.enumerate())

def test_callback():

    ch = channel()

    def idle_cb(handle):
        handle.stop()
        ch.send(True)

    def loop_cb(loop):
        p = pyuv.Idle(loop)
        p.start(idle_cb)

    r_list = []
    def main():
        task = uv.spawn_iotask()
        uv.interract(task, loop_cb)
        r_list.append(ch.receive())
        uv.exit(task)

    tasklet(main())
    run()
    assert r_list == [True]

