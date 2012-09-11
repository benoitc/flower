# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import pyuv

from flower.net.tcp import TCPListen, TCPConn

class PipeConn(TCPConn):
    """ A Pipe connection """


class PipeListen(TCPListen):
    """ A Pipe listener """

    CONN_CLASS = PipeConn
    HANDLER_CLASS = pyuv.Pipe

def dial_pipe(addr):
    uv = uv_server()
    h = pyuv.Pipe(uv.loop)

    c = channel()
    def _on_connect(handle, error):
        c.send((handle, error))

    h.connect(addr, _on_connect)
    h1, error = c.receive()
    return (PipeConn(h1), error)
