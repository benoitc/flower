# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import threading
import time

import pyuv

from flower.core.util import thread_ident
from flower.core import channel

_tls = threading.local()

class IoTask(object):
    """ object used as a reference to the running IOLoop """

    def __init__(self, chan, async_handle, thread_id):
        self.chan = chan
        self.async_handle = async_handle
        self.thread_id = thread_id

    def __str__(self):
        return "iotask:%s" % self.thread_id

    def send(self, msg):
        # send the message but don't wait
        self.chan.send(msg)

        # wake up the IO thread
        self.async_handle.send()


class IoLoopExit(Exception):
    pass

class IoLoop(threading.Thread):
    """ The thread keeping an IO Loop """

    def __init__(self, iotask_chan):
        threading.Thread.__init__(self)

        self.iotask_chan = iotask_chan

        # iotthread interactions
        self.async_handle = None
        self.chan = None

        # runtime data
        self.running = False
        self.daemon = True

    def run(self):
        # initialize the loop
        loop = pyuv.Loop()

        # setup interactions channel & wakeup pipe
        self.chan = channel(100)
        self.async_handle = pyuv.Async(loop, self.wakeup_cb)

        # Send out the handle through which it will be abble to
        # interract with the loop
        new_iotask = IoTask(self.chan, self.async_handle, thread_ident())
        self.iotask_chan.send(new_iotask)

        # start the event loop
        self.running = True
        try:
            loop.run()
            raise RuntimeError
        finally:
            self.running = False

    def wakeup_cb(self, async_handle):
        cb = self.chan.receive()
        if isinstance(cb, IoLoopExit):
            return self.stop(async_handle)
        else:
            # execute the callback and pass it the loop
            print("exec %s" % cb)
            cb(async_handle.loop)

    def stop(self, async_handle):
        async_handle.close()

        def _walk(handle):
            if handle.active:
                handle.close()

        async_handle.loop.walk(_walk)

def spawn_iotask():
    """ spawn a new iotask """
    ch = channel()
    th = IoLoop(ch)
    th.start()
    # we should implement the select features here. Waiting that this
    # will do the trick
    #while True:
    #    if ch.balance > 0:
    #        break
    #    time.sleep(0.0001)
    return ch.receive()

def interract(iotask, msg):
    """ interract with the iothread, This is the only safe way to
    interract wirh the ioloop. """
    iotask.send(msg)

def exit(iotask):
    """ exit the iothread """
    iotask.send(IoLoopExit())


def default_iotask():
    """ there is actually one IO Loop per scheduler """
    try:
        return _tls.iotask
    except AttributeError:
        iotask = _tls.iotask = spawn_iotask()
        return iotask
