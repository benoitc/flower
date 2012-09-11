# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from flower.net.base import Listen
from flower.net.tcp import TCPListen
from flower.net.udp import UDPListen


UV_HANDLERS = dict(
        tcp = TCPListen,
        udp = UDPListen)

class Listen(Listen):
    """A Listener is a generic network listener for stream-oriented protocols.
    Multiple tasks  may invoke methods on a Listener simultaneously.

    Example::

            def handle_connection(conn):
                while True:
                    data = conn.read()
                    if not data:
                        break
                    conn.write(data)

            l = Listen(('127.0.0.1', 8000))

            try:
                while True:
                    try:
                        conn, err = l.accept()
                        t = tasklet(handle_connection)(conn)
                    except KeyboardInterrupt:
                        break
            finally:
                l.close()

            run()
    """


    def __init__(self, addr=('0.0.0.0', 0), proto="tcp", *args):
        try:
            self.listen_class = UV_HANDLERS[proto]
        except KeyError:
            raise ValueError("type should be tcp, udp or unix")

        self.listen_handle = self.listen_class(addr, *args)

    def accept(self):
        return self.listen_handle.accept()

    def close(self):
        return self.listen_handle.close()
