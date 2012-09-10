# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import time

import pyuv

def insert_callback(loop, fun, *args, **kwargs):

    def _cb(handle):
        handle.stop()
        fun(*args, **kwargs)

    idle = pyuv.Idle(loop)
    idle.start(_cb)


def nanotime(s=None):
    """ convert seconds to nanoseconds. If s is None, current time is
    returned """
    if s is not None:
        return s * 1000000000
    return time.time() * 1000000000

def from_nanotime(n):
    """ convert from nanotime to seconds """
    return n / 1.0e9
