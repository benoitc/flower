# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import os
import tempfile

from py.test import skip
from flower import core
from flower.io import IOChannel

class Test_IO:

    def test_readable(self):
        (r, w) = os.pipe()

        ret = []
        def _read(fd):
            c = IOChannel(r, mode=0)
            c.receive()
            ret.append(os.read(fd, 10))
            c.stop()

        def _write(fd):
            os.write(fd, b"TEST")

        core.tasklet(_read)(r)
        core.tasklet(_write)(w)
        core.run()

        assert ret == [b"TEST"]
