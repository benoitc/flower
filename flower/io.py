# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import pyuv
from flower import core

UV_ALL = pyuv.UV_READABLE | pyuv.UV_WRITABLE
UV_READABLE = pyuv.UV_READABLE
UV_WRITABLE = pyuv.UV_WRITABLE


class IOChannel(core.channel):

    def __init__(self, io, events=UV_ALL, label=''):
        super(IOChannel, self).__init__(label=label)
        if not isinstance(io, int):
            if hasattr(io, 'fileno'):
                if callable(io.fileno):
                    io = io.fileno()
                else:
                    io = io.fileno
            else:
                raise ValueError("invalid file descriptor number")

        self.io = io
        self._poller = pyuv.Poll(core.get_loop(), io)
        self._poller.start(events, self._tick)

    def _tick(self, handle, events, errno):
        if errno:
            self.send_exception(IOError, errno)
        else:
            self.send(events)

    def stop(self):
        self._poller.stop()
        self.close()
