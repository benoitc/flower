# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import pyuv

from flower.net.tcp import TCPListen, TCPConn

class PIPEConn(TCPConn):
    """ A PIPE connection """


class PIPEListen(TCPListen):
    """ A PIPE listener """

    CONN_CLASS = PIPEConn
    HANDLER_CLASS = pyuv.PIPE
