# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from __future__ import absolute_import

import time
from py.test import skip
from flower import core

SHOW_STRANGE = False


import six
from six.moves import xrange

def dprint(txt):
    if SHOW_STRANGE:
        print(txt)

class Test_Channel:

    def test_simple_channel(self):
        output = []
        def print_(*args):
            output.append(args)

        def Sending(channel):
            print_("sending")
            channel.send("foo")

        def Receiving(channel):
            print_("receiving")
            print_(channel.receive())

        ch=core.channel()

        task=core.tasklet(Sending)(ch)

        # Note: the argument, schedule is taking is the value,
        # schedule returns, not the task that runs next

        #core.schedule(task)
        core.schedule()
        task2=core.tasklet(Receiving)(ch)
        #core.schedule(task2)
        core.schedule()

        core.run()

        assert output == [('sending',), ('receiving',), ('foo',)]

    def test_task_with_channel(self):
        pref = {}
        pref[-1] = ['s0', 'r0', 's1', 'r1', 's2', 'r2',
                    's3', 'r3', 's4', 'r4', 's5', 'r5',
                    's6', 'r6', 's7', 'r7', 's8', 'r8',
                    's9', 'r9']
        pref[0] =  ['s0', 'r0', 's1', 's2', 'r1', 'r2',
                    's3', 's4', 'r3', 'r4', 's5', 's6',
                    'r5', 'r6', 's7', 's8', 'r7', 'r8',
                    's9', 'r9']
        pref[1] =  ['s0', 's1', 'r0', 's2', 'r1', 's3',
                    'r2', 's4', 'r3', 's5', 'r4', 's6',
                    'r5', 's7', 'r6', 's8', 'r7', 's9',
                    'r8', 'r9']
        rlist = []

        def f(outchan):
            for i in range(10):
                rlist.append('s%s' % i)
                outchan.send(i)
            outchan.send(-1)

        def g(inchan):
            while 1:
                val = inchan.receive()
                if val == -1:
                    break
                rlist.append('r%s' % val)

        for preference in [-1, 0, 1]:
            rlist = []
            ch = core.channel()
            ch.preference = preference
            t1 = core.tasklet(f)(ch)
            t2 = core.tasklet(g)(ch)

            core.run()

            assert len(rlist) == 20
            assert rlist == pref[preference]

    def test_send_counter(self):
        import random

        numbers = list(range(20))
        random.shuffle(numbers)

        def counter(n, ch):
            for i in xrange(n):
                core.schedule()
            ch.send(n)

        ch = core.channel()
        for each in numbers:
            core.tasklet(counter)(each, ch)

        core.run()

        rlist = []
        while ch.balance:
            rlist.append(ch.receive())

        numbers.sort()
        assert rlist == numbers

    def test_receive_counter(self):
        import random

        numbers = list(range(20))
        random.shuffle(numbers)

        rlist = []
        def counter(n, ch):
            for i in xrange(n):
                core.schedule()
            ch.receive()
            rlist.append(n)

        ch = core.channel()
        for each in numbers:
            core.tasklet(counter)(each, ch)

        core.run()

        while ch.balance:
            ch.send(None)

        numbers.sort()
        assert rlist == numbers



    def test_balance_zero(self):
        ch=core.channel()
        assert ch.balance == 0

    def test_balance_send(self):
        def Sending(channel):
            channel.send("foo")

        ch=core.channel()

        task=core.tasklet(Sending)(ch)
        core.run()

        assert ch.balance == 1

    def test_balance_recv(self):
        def Receiving(channel):
            channel.receive()

        ch=core.channel()

        task=core.tasklet(Receiving)(ch)
        core.run()

        assert ch.balance == -1

    def test_run(self):
        output = []
        def print_(*args):
            output.append(args)

        def f(i):
            print_(i)

        core.tasklet(f)(1)
        core.tasklet(f)(2)
        core.run()

        assert output == [(1,), (2,)]


    def test_channel_callback(self):
        res = []
        cb = []
        def callback_function(chan, task, sending, willblock):
            cb.append((chan, task, sending, willblock))
        core.set_channel_callback(callback_function)
        def f(chan):
            chan.send('hello')
            val = chan.receive()
            res.append(val)

        chan = core.channel()
        task = core.tasklet(f)(chan)
        val = chan.receive()
        res.append(val)
        chan.send('world')
        assert res == ['hello','world']
        maintask = core.getmain()
        assert cb == [
            (chan, maintask, 0, 1),
            (chan, task, 1, 0),
            (chan, maintask, 1, 1),
            (chan, task, 0, 0)
        ]

    def test_bomb(self):
        try:
            1/0
        except:
            import sys
            b = core.bomb(*sys.exc_info())
        assert b.type is ZeroDivisionError
        if six.PY3:
            assert (str(b.value).startswith('division by zero') or
                    str(b.value).startswith('int division'))
        else:
            assert str(b.value).startswith('integer division')
        assert b.traceback is not None

    def test_send_exception(self):
        def exp_sender(chan):
            chan.send_exception(Exception, 'test')

        def exp_recv(chan):
            try:
                val = chan.receive()
            except Exception as exp:
                assert exp.__class__ is Exception
                assert str(exp) == 'test'

        chan = core.channel()
        t1 = core.tasklet(exp_recv)(chan)
        t2 = core.tasklet(exp_sender)(chan)
        core.run()

    def test_send_sequence(self):
        res = []
        lst = [1,2,3,4,5,6,None]
        iterable = iter(lst)
        chan = core.channel()
        def f(chan):
            r = chan.receive()
            while r:
                res.append(r)
                r = chan.receive()

        t = core.tasklet(f)(chan)
        chan.send_sequence(iterable)
        assert res == [1,2,3,4,5,6]

    def test_getruncount(self):
        assert core.getruncount() == 1
        def with_schedule():
            assert core.getruncount() == 2

        t1 = core.tasklet(with_schedule)()
        assert core.getruncount() == 2
        core.schedule()
        def with_run():
            assert core.getruncount() == 1

        t2 = core.tasklet(with_run)()
        core.run()

    def test_simple_pipe(self):
        def pipe(X_in, X_out):
            foo = X_in.receive()
            X_out.send(foo)

        X, Y = core.channel(), core.channel()
        t = core.tasklet(pipe)(X, Y)
        core.run()
        X.send(42)
        assert Y.receive() == 42

    def test_nested_pipe(self):
        dprint('tnp ==== 1')
        def pipe(X, Y):
            dprint('tnp_P ==== 1')
            foo = X.receive()
            dprint('tnp_P ==== 2')
            Y.send(foo)
            dprint('tnp_P ==== 3')

        def nest(X, Y):
            X2, Y2 = core.channel(), core.channel()
            t = core.tasklet(pipe)(X2, Y2)
            dprint('tnp_N ==== 1')
            X_Val = X.receive()
            dprint('tnp_N ==== 2')
            X2.send(X_Val)
            dprint('tnp_N ==== 3')
            Y2_Val = Y2.receive()
            dprint('tnp_N ==== 4')
            Y.send(Y2_Val)
            dprint('tnp_N ==== 5')

        X, Y = core.channel(), core.channel()
        t1 = core.tasklet(nest)(X, Y)
        X.send(13)
        dprint('tnp ==== 2')
        res = Y.receive()
        dprint('tnp ==== 3')
        assert res == 13
        if SHOW_STRANGE:
            raise Exception('force prints')

    def test_wait_two(self):
        """
        A tasklets/channels adaptation of the test_wait_two from the
        logic object space
        """
        def sleep(X, Y):
            dprint('twt_S ==== 1')
            value = X.receive()
            dprint('twt_S ==== 2')
            Y.send((X, value))
            dprint('twt_S ==== 3')

        def wait_two(X, Y, Ret_chan):
            Barrier = core.channel()
            core.tasklet(sleep)(X, Barrier)
            core.tasklet(sleep)(Y, Barrier)
            dprint('twt_W ==== 1')
            ret = Barrier.receive()
            dprint('twt_W ==== 2')
            if ret[0] == X:
                Ret_chan.send((1, ret[1]))
            else:
                Ret_chan.send((2, ret[1]))
            dprint('twt_W ==== 3')

        X = core.channel()
        Y = core.channel()
        Ret_chan = core.channel()

        core.tasklet(wait_two)(X, Y, Ret_chan)

        dprint('twt ==== 1')
        Y.send(42)

        dprint('twt ==== 2')
        X.send(42)
        dprint('twt ==== 3')
        value = Ret_chan.receive()
        dprint('twt ==== 4')
        assert value == (2, 42)


    def test_schedule_return_value(self):

        def task(val):
            value = core.schedule(val)
            assert value == val

        core.tasklet(task)(10)
        core.tasklet(task)(5)

        core.run()

    def test_nonblocking_channel(self):
        c = core.channel(100)
        r1 = c.receive()
        r2 = c.send(True)
        r3 = c.receive()
        r4 = c.receive()

        assert r1 is None
        assert r2 is None
        assert r3 == True
        assert r4 is None

    def test_async_channel(self):
        c = core.channel(100)

        unblocked_sent = 0
        for i in range(100):
            c.send(True)
            unblocked_sent += 1

        assert unblocked_sent == 100
        assert c.balance == 100

        unblocked_recv = []
        for i in range(100):
            unblocked_recv.append(c.receive())

        assert len(unblocked_recv) == 100

    def test_async_with_blocking_channel(self):

        c = core.channel(10)

        unblocked_sent = 0
        for i in range(10):
            c.send(True)
            unblocked_sent += 1

        assert unblocked_sent == 10
        assert c.balance == 10

        r_list = []
        def f():
            start = time.time()
            c.send(True)
            r_list.append(start)

        core.tasklet(f)()


        unblocked_recv = []
        for i in range(11):
            time.sleep(0.01)
            unblocked_recv.append(c.receive())
            core.schedule()


        core.run()

        diff = time.time() - r_list[0]

        assert len(unblocked_recv) == 11
        assert diff > 0.1
