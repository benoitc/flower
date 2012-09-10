# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import pyuv
from flower.core import channel
from flower.core.uv import get_fd, uv_mode, uv_server


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

    def _tick(self, handle, events, errno):
        if errno:
            self.send_exception(IOError, errno)
        else:
            self.send(events)

    def stop(self):
        self._poller.stop()
        self.close()
