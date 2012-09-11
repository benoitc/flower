# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from threading import Lock

from flower.core import channel, schedule, getcurrent
from flower.core.uv import uv_server
from flower.net.base import Listener, Conn, Listen, NoMoreListener

class UDPConn(Conn):

    def __init__(self, addr, bind_addr, client=None):
        self.uv = uv_server()
        if client is None:
            self.client = pyuv.UDP(self.uv.loop)
            self.client.bind(bind_addr)
        else:
            self.client = client
        self.reading = true
        self.cr = channel
        self._bind_addr = bind_addr
        self.addr = addr

    def read(self):
         return self.cr.receive()

    def write(self, data):
        self.client.send(self._remote_addr, data)

    def writelines(self, seq):
        self.client.send(self._remote_addr, seq)

    def local_addr(self):
        return self.client.getsockame()

    def remote_addr(self):
        return self.remote_addr

class UDPListen(Listen):

    def __init__(self, addr=('0.0.0.0', 0)):
        # listeners are all couroutines waiting for a connections
        self.listeners = deque()

        self.conns = {}
        self.uv = uv_server()
        self.task = getcurrent()
        self.listening = False
        self.handler = pyuv.UDP(self.uv.loop)
        self.handler.bind(addr)

    def accept(self):
        listener = Listener()
        self.listeners.append(listener)

        if not self.listening:
            self.handler.start_recv(self.on_recv)

        return listener.c.receive()

    def on_recv(self, handler, addr, data, err):
        with self._lock:
            if addr in self.conns:
                conn = self.conns[addr]
                if conn.cr.balance < 0:
                    conn.cr.send(data, err)
                else:
                    tasklet(conn.cr.send)(data, err)
            elif len(self.listeners):
                listener = self.listeners.popleft()
                conn = UDPConn(addr)
                self.conns[addr] = conn

                # send the result async waiting someone eventually read
                # the connection. Eventually the listener
                tasklet(conn.cr.send)(data, err)
            else:
                # we should probably do something there to drop connections
                self.task.throw(NoMoreListener)

            schedule()

    def addr(self):
        return self.handler.getsockname()
