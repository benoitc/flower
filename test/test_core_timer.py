# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import time

from flower.core.util import from_nanotime
from flower.core import run, tasklet
from flower.core.timer import Timer, sleep

def _wait():
    time.sleep(0.01)


def test_simple_timer():
    r_list = []
    def _func(now):
        r_list.append(from_nanotime(now))

    now = time.time()
    t = Timer(_func, 0.1)
    t.start()
    run()
    delay = r_list[0]
    assert (now + 0.09) <= delay <= (now + 0.11), delay


def test_multiple_timer():
    r1 = []
    def f(now):
        r1.append(from_nanotime(now))

    r2 = []
    def f1(now):
        r2.append(from_nanotime(now))

    now = time.time()

    t = Timer(f, 0.4)
    t.start()

    t1 = Timer(f1, 0.1)
    t1.start()

    run()
    assert r1[0] > r2[0]
    assert (now + 0.39) <= r1[0] <= (now + 0.41), r1[0]
    assert (now + 0.09) <= r2[0] <= (now + 0.11), r2[0]


def test_sleep():
    start = time.time()
    sleep(0.1)
    diff = time.time() - start
    assert 0.09 <= diff <= 0.11


def test_multiple_sleep():
    r1 = []
    def f():
        sleep(0.4)
        r1.append(time.time())

    r2 = []
    def f1():
        sleep(0.1)
        r2.append(time.time())

    tasklet(f)()
    tasklet(f1)()

    now = time.time()
    run()
    assert r1[0] > r2[0]
    assert (now + 0.39) <= r1[0] <= (now + 0.41), r1[0]
    assert (now + 0.09) <= r2[0] <= (now + 0.11), r2[0]



