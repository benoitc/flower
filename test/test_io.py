# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import os
import tempfile

from py.test import skip
from flower import stackless
from flower.io import IOChannel, UV_READABLE

class Test_IO:

    def test_readable(self):
        (r, w) = os.pipe()

        ret = []
        def _read(fd):
            c = IOChannel(r, events=UV_READABLE)
            c.receive()
            ret.append(os.read(fd, 10))
            c.stop()

        def _write(fd):
            os.write(fd, b"TEST")

        stackless.tasklet(_read)(r)
        stackless.tasklet(_write)(w)
        stackless.run()

        assert ret == [b"TEST"]
