# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from py.test import skip

from flower import stackless
from flower.time import Ticker

class Test_Ticket:

    def test_ticker(self):
        rlist = []

        def f():
            ticker = Ticker(0.1)
            i = 0
            while True:
                if i == 3: break
                t = ticker.receive()
                rlist.append(t)
                i += 1
            ticker.stop()

        tf = stackless.tasklet(f)()
        stackless.run()

        assert len(rlist) == 3
