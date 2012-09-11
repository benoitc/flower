# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from collections import deque
import threading

import pyuv

from flower.core.uv import uv_server
from flower.core import (channel, schedule, schedule_remove, getcurrent,
        get_scheduler, tasklet)
from flower.net.base import Conn, Listener, Listen, NoMoreListener

class TCPConn(Conn):

    def __init__(self, client):
        self.client = client
        self.reading = False
        self.cr = channel()
        self._read_task = None

    def read(self):
        if not self.reading:
            self.client.start_read(self._on_read)
            self.reading = True
        return self.cr.receive()

    def write(self, data):
        return self.client.write(data)

    def writelines(self, seq):
        return self.client.writelines(seq)

    def local_address(self):
        return self.client.getsockame()

    def remote_address(self):
        return self.client.getpeername()

    def close(self):
        self.client.close()

    def _on_read(self, handle, data, error):
        if error:
            self.cr.send_exception(IOError(error))
        else:
            self.cr.send(data)
        schedule()

class TCPListen(Listen):
    """ A TCP listener """

    def __init__(self, addr=('0.0.0.0', 0)):
        # listeners are all couroutines waiting for a connections
        self.listeners = deque()
        self.uv = uv_server()
        self.sched = get_scheduler()
        self.task = getcurrent()
        self.listening = False

        self.handler = pyuv.TCP(self.uv.loop)
        self.handler.bind(addr)

    def accept(self):
        listener = Listener()
        self.listeners.append(listener)

        if not self.listening:
            self.handler.listen(self.on_connection)
        return listener.c.receive()

    def close(self):
        self.handler.close()

    def on_connection(self, server, error):
        if len(self.listeners):
            listener = self.listeners.popleft()

            # accept the connection
            client = pyuv.TCP(server.loop)
            server.accept(client)

            self.uv.wakeup()
            # return a new connection object to the listener
            conn = TCPConn(client)
            listener.c.send((conn, error))
            schedule()
        else:
            # we should probably do something there to drop connections
            self.task.throw(NoMoreListener)
