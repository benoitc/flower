# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import time

import pytest

from flower import stackless
from flower.time import Ticker, Timeout, with_timeout, sleep, timeout_


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

        tf = stackless.tasklet(f)()
        stackless.run()

        assert len(rlist) == 3


    def test_simple_sleep(self):
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

        stackless.tasklet(f)()
        stackless.tasklet(f1)()
        stackless.run()

        assert rlist == ['b', 'a']


    def test_sleep2(self):
        rlist = []

        def f():
            sleep()
            rlist.append('a')

        def f1():
            rlist.append('b')

        stackless.tasklet(f)()
        stackless.tasklet(f1)()
        stackless.run()

        assert rlist == ['b', 'a']


    def test_simple_timeout(self):
        with pytest.raises(Timeout):
            timeout = Timeout(0.01)
            timeout.start()

            try:
                stackless.run()
                raise AssertionError('Must raise Timeout')

            finally:
                timeout.cancel()

    def test_timeout_in_task(self):

        raised = []
        def f():
            timeout = Timeout(0.01)
            timeout.start()
            try:
                stackless.schedule()
                raise AssertionError('Must raise Timeout')
            except Timeout:
                raised.append(True)
            finally:
                timeout.cancel()

        stackless.tasklet(f)()
        stackless.run()

        assert raised == [True]


    def test_timeout_in_task2(self):
        rlist = []
        def f():
            timeout = Timeout(0.01)
            timeout.start()
            try:
                stackless.schedule()
                raise AssertionError('Must raise Timeout')
            except Timeout:
                rlist.append(True)
            finally:
                timeout.cancel()
            stackless.schedule()

            rlist.append("test")

        stackless.tasklet(f)()
        stackless.run()

        assert rlist == [True, "test"]


    def test_timeout_with(self):
        with pytest.raises(Timeout):
            with Timeout(0.02):
                stackless.run()
                raise AssertionError('Must raise Timeout')

    def test_with_timeout(self):
        with pytest.raises(Timeout):
            with_timeout(0.01, sleep, 0.2)

            stackless.run()

    def test_timeout_decorator(self):

        @timeout_(0.02)
        def f():
            sleep(0.2)

        with pytest.raises(Timeout):
            f()
