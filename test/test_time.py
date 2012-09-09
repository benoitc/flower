# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import os
import time

import pytest
from py.test import skip

from flower import core
from flower.time import Ticker, sleep

IS_TRAVIS = False

if os.environ.get('TRAVIS') and os.environ.get('TRAVIS') is not None:
    IS_TRAVIS = True

class Test_Time:

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

        tf = core.tasklet(f)()
        core.run()

        assert len(rlist) == 3


    def test_simple_sleep(self):
        if IS_TRAVIS:
            skip()
        start = time.time()
        sleep(0.02)
        delay = time.time() - start
        assert 0.02 - 0.004 <= delay < 0.02 + 0.02, delay


    def test_sleep(self):
        rlist = []

        def f():
            sleep(0.2)
            rlist.append('a')

        def f1():
            rlist.append('b')

        core.tasklet(f)()
        core.tasklet(f1)()
        core.run()

        assert rlist == ['b', 'a']


    def test_sleep2(self):
        rlist = []

        def f():
            sleep()
            rlist.append('a')

        def f1():
            rlist.append('b')

        core.tasklet(f)()
        core.tasklet(f1)()
        core.run()

        assert rlist == ['b', 'a']



