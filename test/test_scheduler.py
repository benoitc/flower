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

    def test_schedule_return_value(self):

        def task(val):
            value = core.schedule(val)
            assert value == val

        core.tasklet(task)(10)
        core.tasklet(task)(5)

        core.run()
