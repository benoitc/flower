# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from __future__ import absolute_import
from py.test import skip
from flower import core

SHOW_STRANGE = False


import six
from six.moves import xrange

def dprint(txt):
    if SHOW_STRANGE:
        print(txt)

class Test_Stackless:

    def test_simple(self):
        rlist = []

        def f():
            rlist.append('f')

        def g():
            rlist.append('g')
            core.schedule()

        def main():
            rlist.append('m')
            cg = core.tasklet(g)()
            cf = core.tasklet(f)()
            core.run()
            rlist.append('m')

        main()

        assert core.getcurrent() is core.getmain()
        assert rlist == 'm g f m'.split()

    def test_with_channel(self):
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

    def test_scheduling_cleanup(self):
        rlist = []
        def f():
            rlist.append('fb')
            core.schedule()
            rlist.append('fa')

        def g():
            rlist.append('gb')
            core.schedule()
            rlist.append('ga')

        def h():
            rlist.append('hb')
            core.schedule()
            rlist.append('ha')

        tf = core.tasklet(f)()
        tg = core.tasklet(g)()
        th = core.tasklet(h)()

        rlist.append('mb')
        core.run()
        rlist.append('ma')

        assert rlist == 'mb fb gb hb fa ga ha ma'.split()

    def test_except(self):
        rlist = []
        def f():
            rlist.append('f')
            return 1/0

        def g():
            rlist.append('bg')
            core.schedule()
            rlist.append('ag')

        def h():
            rlist.append('bh')
            core.schedule()
            rlist.append('ah')

        tg = core.tasklet(g)()
        tf = core.tasklet(f)()
        th = core.tasklet(h)()

        try:
            core.run()
            # cheating, can't test for ZeroDivisionError
        except ZeroDivisionError:
            rlist.append('E')
        core.schedule()
        core.schedule()

        assert rlist == "bg f E bh ag ah".split()

    def test_except_full(self):
        rlist = []
        def f():
            rlist.append('f')
            return 1/0

        def g():
            rlist.append('bg')
            core.schedule()
            rlist.append('ag')

        def h():
            rlist.append('bh')
            core.schedule()
            rlist.append('ah')

        tg = core.tasklet(g)()
        tf = core.tasklet(f)()
        th = core.tasklet(h)()

        try:
            core.run()
        except ZeroDivisionError:
            rlist.append('E')
        core.schedule()
        core.schedule()

        assert rlist == "bg f E bh ag ah".split()

    def test_kill(self):
        def f():pass
        t =  core.tasklet(f)()
        t.kill()
        assert not t.alive

    def test_catch_taskletexit(self):
        # Tests if TaskletExit can be caught in the tasklet being killed.
        global taskletexit
        taskletexit = False

        def f():
            try:
                core.schedule()
            except TaskletExit:
                global TaskletExit
                taskletexit = True
                raise

            t =  core.tasklet(f)()
            t.run()
            assert t.alive
            t.kill()
            assert not t.alive
            assert taskletexit

    def test_autocatch_taskletexit(self):
        # Tests if TaskletExit is caught correctly in core.tasklet.setup().
        def f():
            core.schedule()

        t = core.tasklet(f)()
        t.run()
        t.kill()


    # tests inspired from simple core.com examples

    def test_construction(self):
        output = []
        def print_(*args):
            output.append(args)

        def aCallable(value):
            print_("aCallable:", value)

        task = core.tasklet(aCallable)
        task.setup('Inline using setup')

        core.run()
        assert output == [("aCallable:", 'Inline using setup')]


        del output[:]
        task = core.tasklet(aCallable)
        task('Inline using ()')

        core.run()
        assert output == [("aCallable:", 'Inline using ()')]

        del output[:]
        task = core.tasklet()
        task.bind(aCallable)
        task('Bind using ()')

        core.run()
        assert output == [("aCallable:", 'Bind using ()')]

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

    def test_schedule(self):
        output = []
        def print_(*args):
            output.append(args)

        def f(i):
            print_(i)

        core.tasklet(f)(1)
        core.tasklet(f)(2)
        core.schedule()

        assert output == [(1,), (2,)]


    def test_cooperative(self):
        output = []
        def print_(*args):
            output.append(args)

        def Loop(i):
            for x in range(3):
                core.schedule()
                print_("schedule", i)

        core.tasklet(Loop)(1)
        core.tasklet(Loop)(2)
        core.run()

        assert output == [('schedule', 1), ('schedule', 2),
                          ('schedule', 1), ('schedule', 2),
                          ('schedule', 1), ('schedule', 2),]

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

    def test_schedule_callback(self):
        res = []
        cb = []
        def schedule_cb(prev, next):
            cb.append((prev, next))

        core.set_schedule_callback(schedule_cb)
        def f(i):
            res.append('A_%s' % i)
            core.schedule()
            res.append('B_%s' % i)

        t1 = core.tasklet(f)(1)
        t2 = core.tasklet(f)(2)
        maintask = core.getmain()
        core.run()
        assert res == ['A_1', 'A_2', 'B_1', 'B_2']
        assert len(cb) == 5
        assert cb[0] == (maintask, t1)
        assert cb[1] == (t1, t2)
        assert cb[2] == (t2, t1)
        assert cb[3] == (t1, t2)
        assert cb[4] == (t2, maintask)

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

    def test_schedule_return(self):
        def f():pass
        t1= core.tasklet(f)()
        r = core.schedule()
        assert r is core.getmain()
        t2 = core.tasklet(f)()
        r = core.schedule('test')
        assert r == 'test'

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
