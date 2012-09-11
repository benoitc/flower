# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from collections import deque
import pyuv


from flower.core.uv import uv_server
from flower.core import (channel, schedule, getcurrent, get_scheduler,
        bomb)
from flower.net.base import IConn, Listener, IListen, NoMoreListener

class TCPConn(IConn):

    def __init__(self, client):
        self.client = client
        self.reading = False
        self.cr = channel()
        self.queue = deque()

    def read(self):
        if not self.reading:
            self.reading = True
            self.client.start_read(self._on_read)

        self.client.loop.update_time()
        try:
            retval = self.queue.popleft()
            if self.cr.balance < 0:
                self.cr.send(retval)

            if isinstance(retval, bomb):
                retval.raise_()
            return retval
        except IndexError:
            pass

        return self.cr.receive()

    def write(self, data):
        return self.client.write(data)

    def writelines(self, seq):
        return self.client.writelines(seq)

    def _wait_write(self, func, data):
        c = channel()
        def _wait_cb(handle, err):
            c.send(True)

        func(data, _wait_cb)
        c.receive()


    def local_address(self):
        return self.client.getsockame()

    def remote_address(self):
        return self.client.getpeername()

    def close(self):
        self.client.close()

    def _on_read(self, handle, data, error):
        if error:
            if error == 1: # EOF
                msg = ""
            else:
                msg = bomb(IOError, IOError("uv error: %s" % error))
        else:
            msg = data

        # append the message to the queue
        self.queue.append(msg)

        if self.cr.balance < 0:
            # someone is waiting, return last message
            self.cr.send(self.queue.popleft())

class TCPListen(IListen):
    """ A TCP listener """

    CONN_CLASS = TCPConn # connection object returned
    HANDLER_CLASS = pyuv.TCP # pyuv class used to handle the conenction

    def __init__(self, addr=('0.0.0.0', 0)):
        # listeners are all couroutines waiting for a connections
        self.listeners = deque()
        self.uv = uv_server()
        self.sched = get_scheduler()
        self.task = getcurrent()
        self.listening = False

        self.handler = self.HANDLER_CLASS(self.uv.loop)
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
            conn = self.CONN_CLASS(client)
            listener.c.send((conn, error))
            schedule()
        else:
            # we should probably do something there to drop connections
            self.task.throw(NoMoreListener)


def dial_tcp(addr):
    uv = uv_server()
    h = pyuv.TCP(uv.loop)

    c = channel()
    def _on_connect(handle, error):
        if error:
            c.send_exception(IOError, "uv error: %s" % error)
        else:
            c.send(handle)

    h.connect(addr, _on_connect)
    h1 = c.receive()
    return TCPConn(h1)
