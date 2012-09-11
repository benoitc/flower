# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from threading import Lock

from flower.core import channel, schedule, getcurrent
from flower.core.uv import uv_server
from flower.net.base import Listener, IConn, IListen, IDial, NoMoreListener

class UDPConn(IConn):

    def __init__(self, addr, raddr, client=None):
        self.uv = uv_server()
        if client is None:
            self.client = pyuv.UDP(self.uv.loop)
            self.client.bind(raddr)
        else:
            self.client = client
        self.reading = true
        self.cr = channel
        self._raddr = raddr
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

class UDPListen(IListen):

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

                if error:
                    if error == 1:
                        msg = ""
                    else:
                        msg = bomb(IOError, IOError("uv error: %s" % error))
                else:
                    msg = data

                # emit last message
                conn.queue.append(msg)
                if conn.cr.balance < 0:
                    # someone is waiting, return last message
                    conn.cr.send(self.queue.popleft())

            elif len(self.listeners):
                listener = self.listeners.popleft()
                if error:
                    listener.c.send_exception(IOError, "uv error: %s" % error)
                else:
                    conn = UDPConn(addr)
                    conn.queue.append(data)
                    self.conns[addr] = conn
                    listener.c.send(conn, error)
            else:
                # we should probably do something there to drop connections
                self.task.throw(NoMoreListener)


            schedule()

    def addr(self):
        return self.handler.getsockname()

def dial_udp(laddr, raddr):
    uv = uv_server()
    h = pyuv.UDP(uv.loop)
    h.bind(laddr)

    return (UDPConn(laddr, raddr, h), None)
