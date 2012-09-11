# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import time

try:
    from thread import get_ident as thread_ident
except ImportError:
    from _thread import get_ident as thread_ident


def nanotime(s=None):
    """ convert seconds to nanoseconds. If s is None, current time is
    returned """
    if s is not None:
        return s * 1000000000
    return time.time() * 1000000000

def from_nanotime(n):
    """ convert from nanotime to seconds """
    return n / 1.0e9
