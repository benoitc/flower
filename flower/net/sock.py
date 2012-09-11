# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from collections import deque
from io import DEFAULT_BUFFER_SIZE
import threading

import socket
import sys

import pyuv

from flower.core import (channel, schedule, schedule_remove, getcurrent,
        get_scheduler, tasklet, bomb)
from flower.core.uv import uv_server
from flower.io import wait_read, wait_write
from flower.net.base import IConn, Listener, IListen, NoMoreListener
from flower.net.util import parse_address, is_ipv6

IS_WINDOW = sys.platform == 'win32'

if IS_WINDOW:
    from errno import WSAEWOULDBLOCK as EWOULDBLOCK
    EAGAIN = EWOULDBLOCK
else:
    from errno import EINVAL
    from errno import EWOULDBLOCK

try:
    from errno import EBADF
except ImportError:
    EBADF = 9

# sys.exc_clear was removed in Python3 as the except block of a try/except
# performs the same task. Add it as a no-op method.
try:
    sys.exc_clear
except AttributeError:
    def exc_clear():
        return
    sys.exc_clear = exc_clear

if sys.version_info < (2, 7, 0, 'final'):
    # in python 2.6 socket.recv_into doesn't support bytesarray
    import array

    def recv_into(sock, b):
        l = max(len(b), DEFAULT_BUFFER_SIZE)
        buf = sock.recv(l)
        recved = len(buf)
        b[0:recved] = buf
        return recved
else:
    def recv_into(sock, b):
        return sock.recv_into(b)

# from gevent code
if sys.version_info[:2] < (2, 7):
    _get_memory = buffer
elif sys.version_info[:2] < (3, 0):
    def _get_memory(string, offset):
        try:
            return memoryview(string)[offset:]
        except TypeError:
            return buffer(string, offset)
else:
    def _get_memory(string, offset):
        return memoryview(string)[offset:]


class SockConn(IConn):

    def __init__(self, client, laddr, addr):
        # set connection info
        self.client = client
        self.client.setblocking(0)
        self.timeout = socket.getdefaulttimeout()
        self.laddr = laddr
        self.addr = addr

        # utilies used to fetch & send ata
        self.cr = channel() # channel keeping readers waiters
        self.cw = channel() # channel keeping writers waiters
        self.queue = deque() # queue of readable data
        self.uv = uv_server()
        self.rpoller = None
        self.wpoller = None
        self._lock = threading.RLock()
        self.ncr = 0 # reader refcount
        self.ncw = 0 # writer refcount

        self.closing = False


    def read(self):
        if self.closing:
            return ""

        while True:
            try:
                retval = self.queue.popleft()
                if self.cr.balance < 0:
                    self.cr.send(retval)

                if isinstance(retval, bomb):
                    retval.raise_()

                return retval
            except IndexError:
                pass

            msg = None
            buf = bytearray(DEFAULT_BUFFER_SIZE)
            try:
                recvd = recv_into(self.client, buf)
                msg =  bytes(buf[0:recvd])
            except socket.error:
                ex = sys.exc_info()[1]
                if ex.args[0] == EBADF:
                    msg = ""
                    self.closing = True
                if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                    msg = bomb(ex, sys.exc_info()[2])
                    self.closing = True
                exc_clear()

            if msg is None:
                res = self._watch_read()
                if res is not None:
                    self.queue.append(res)

            else:
                self.queue.append(msg)

    def write(self, data):
        data_sent = 0
        while data_sent < len(data):
            data_sent += self._send(_get_memory(data, data_sent))

    def writelines(self, data):
        for s in seq:
            self.write(data)

    def local_addr(self):
        return self.laddr

    def remote_addr(self):
        return self.addr

    def close(self):
        self.client.close()

        # stop polling
        if self.wpoller is not None:
            self.wpoller.stop()
            self.wpoller = None

        if self.rpoller is not None:
            self.rpoller.stop()
            self.rpoller = None

    def _watch_read(self):
        self._lock.acquire()
        if not self.rpoller:
            self.rpoller = pyuv.Poll(self.uv.loop, self.client.fileno())
            self.rpoller.start(pyuv.UV_READABLE, self._on_read)

        # increase the reader refcount
        self.ncr += 1
        self._lock.release()
        try:
            self.cr.receive()
        finally:
            self._lock.acquire()
            # decrease the refcount
            self.ncr -= 1
            # if no more waiters, close the poller
            if self.ncr <= 0:
                self.rpoller.stop()
                self.rpoller = None
            self._lock.release()

    def _on_read(self, handle, events, error):
        if error and error is not None:
            self.readable = False
            if errno == 1:
                self.closing = True
                msg = ""
            else:
                msg = bomb(IOError, IOError("uv error: %s" % error))
        else:
            self.readable = True

        self.cr.send(None)

    def _send(self, data):
        while True:
            try:
               return self.client.send(data)
            except socket.error:
                ex = sys.exc_info()[1]
                if ex.args[0] == EBADF:
                    self.closing = True
                    return
                if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                    raise
                exc_clear()

            # wait for newt write
            self._watch_write()

    def _watch_write(self):
        self._lock.acquire()

        # create a new poller
        if not self.wpoller:
            self.wpoller = pyuv.Poll(self.uv.loop, self.client.fileno())
            self.wpoller.start(pyuv.UV_WRITABLE, self._on_write)

        # increase the writer refcount
        self.ncw += 1

        self._lock.release()

        try:
            self.cw.receive()
        finally:
            self._lock.acquire()
            self.ncw -= 1
            if self.ncw <= 0:
                self.wpoller.stop()
                self.wpoller = None
            self._lock.release()


    def _on_write(self, handle, events, errors):
        if not errors:
            self.cw.send()

    def _read(self):
        buf = bytearray(DEFAULT_BUFFER_SIZE)
        try:
            recvd = recv_into(self.client, buf)
            msg =  bytes(buf[0:recvd])
        except socket.error:
            ex = sys.exc_info()[1]
            if ex.args[0] == EBADF:
                msg =  ""
            if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                msg = bomb(ex, sys.exc_info()[2])
            exc_clear()
        return msg


class TCPSockListen(IListen):

    def __init__(self, addr, *args, **kwargs):

        sock = None
        fd = None
        if "sock" in kwargs:
            # we passed a socket in the kwargs, just use it
            sock = kwargs['sock']
            fd = sock.fileno()
        elif isinstance(addr, int):
            # we are reusing a socket here
            fd = addr
            if "family" not in kwargs:
                family = socket.AF_INET
            else:
                family = kwargs['family']
            sock = socket.fromfd(fd, family, socket.SOCK_STREAM)
        else:
            # new socket
            addr = parse_address(addr)
            if is_ipv6(addr[0]):
                family = socket.AF_INET6
            else:
                family = socket.AF_INET

            sock = socket.socket(family, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            nodelay = kwargs.get('nodelay', True)
            if family == socket.AF_INET and nodelay:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            sock.bind(addr)
            sock.setblocking(0)
            fd = sock.fileno()

        self.sock = sock
        self.fd = fd
        self.addr = addr
        self.backlog = kwargs.get('backlog', 128)
        self.timeout = socket.getdefaulttimeout()
        self.uv = uv_server()
        self.poller = None
        self.listeners = deque()
        self.task = getcurrent()

        # start to listen
        self.sock.listen(self.backlog)

    def accept(self):
        """ start the accept loop. Let the OS handle accepting balancing
        between listeners """

        if self.poller is None:
            self.poller = pyuv.Poll(self.uv.loop, self.fd)
            self.poller.start(pyuv.UV_READABLE, self._on_read)

        listener = Listener()
        self.listeners.append(listener)
        return listener.c.receive()

    def addr(self):
        return self.addr

    def close(self):
        if self.poller is not None:
            self.poller.stop()
        self.sock.close()

    def _on_read(self, handle, events, error):
        if error:
            handle.stop()
            self.poller = None
        else:
            res = None
            try:
                res = self.sock.accept()
            except socket.error:
                exc_info = sys.exc_info()
                ex = exc_info[1]
                if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                    self.task.throw(*exc_info)
                exc_clear()

            if res is not None:
                client, addr = res
                self._on_connection(client, addr)

    def _on_connection(self, client, addr):
        if len(self.listeners):
            listener = self.listeners.popleft()

            self.uv.wakeup()

            # return a new connection object to the listener
            conn =  SockConn(client, self.addr, addr)
            listener.c.send((conn, None))
            schedule()
        else:
            # we should probably do something there to drop connections
            self.task.throw(NoMoreListener)

class PipeSockListen(TCPSockListen):

    def __init__(self, addr, *args, **kwargs):
        fd = kwargs.get('fd')
        if fd is None:
            try:
                os.remove(addr)
            except OSError:
                pass

        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        nodelay = kwargs.get('nodelay', True)
        if family == socket.AF_INET and nodelay:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        if fd is None:
            sock.bind(addr)
        sock.setblocking(0)

        self.sock = sock
        self.fd = fd
        self.addr = addr
        self.backlog = kwargs.get('backlog', 128)
        self.timeout = socket.getdefaulttimeout()

        # start to listen
        self.sock.listen(self.backlog)
