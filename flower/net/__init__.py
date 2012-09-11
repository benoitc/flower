# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from flower.net.tcp import TCPListen, dial_tcp
from flower.net.udp import UDPListen, dial_udp
from flower.net.pipe import PipeListen, dial_pipe
from flower.net.sock import TCPSockListen, PipeSockListen

LISTEN_HANDLERS = dict(
        tcp = TCPListen,
        udp = UDPListen,
        pipe = PipeListen,
        socktcp = TCPSockListen,
        sockpipe = PipeSockListen)

DIAL_HANDLERS = dict(
        tcp = dial_tcp,
        udp = dial_udp,
        pipe = dial_pipe)


def Dial(proto, *args):
    """ A Dial is a generic client for stream-oriented protocols.

    Example::

        conn, err = Dial("tcp", ('127.0.0.1', 8000))
        conn.write("hello")
        print(conn.read())
    """

    try:
        dial_func = DIAL_HANDLERS[proto]
    except KeyError:
        raise ValueError("type should be tcp, udp or unix")
    return dial_func(*args)

dial = Dial # for pep8 lovers

def Listen(addr=('0.0.0.0', 0), proto="tcp", *args):
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

    try:
        listen_class = LISTEN_HANDLERS[proto]
    except KeyError:
        raise ValueError("type should be tcp, udp or unix")

    return listen_class(addr, *args)

listen = Listen # for pep8 lovers
