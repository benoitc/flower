# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import pyuv
from flower.core import channel
from flower.core.uv import get_fd, uv_mode, uv_server

from pyuv import errno

class IOChannel(channel):
    """ channel to wait on IO events for a specific fd. It now use the UV server
    facility.

        mode:
        0: read
        1: write
        2: read & write"""

    def __init__(self, io, mode=0, label=''):
        super(IOChannel, self).__init__(label=label)

        fno = get_fd(io)
        self.io = io
        uv = uv_server()
        self._poller = pyuv.Poll(uv.loop, fno)
        self._poller.start(uv_mode(mode), self._tick)

    def _tick(self, handle, events, error):
        print("error")
        if error:
            if error == errno.EBADF:
                self.handle.close()
                self.send(None)
            else:
                self.send_exception(IOError, "uv error: %s" % errno)
        else:
            self.send(events)

    def stop(self):
        self._poller.stop()
        self.close()

def wait_read(io):
    """ wrapper around IOChannel to only wait when a device become
    readable """
    c = IOChannel(io)
    try:
        return c.receive()
    finally:
        c.close()

def wait_write(io):
    """ wrapper around IOChannel to only wait when a device become
    writanle """
    c = IOChannel(io, 1)
    try:
        return c.receive()
    finally:
        c.close()
