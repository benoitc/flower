# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import pytest
from py.test import skip
from flower.local import local
from flower import core

class Test_Local:

    def test_simple(self):
        d = local()
        d.a = 1
        assert d.a == 1
        d.a = 2
        assert d.a == 2

    def test_simple_delete(self):
        d = local()
        d.a = 1
        assert d.a == 1
        del d.a
        def f(): return d.a
        with pytest.raises(AttributeError):
            f()

    def test_simple_delete2(self):
        d = local()
        d.a = 1
        d.b = 2
        assert d.a == 1
        assert d.b == 2
        del d.a
        def f(): return d.a
        with pytest.raises(AttributeError):
            f()
        assert d.b == 2

    def test_local(self):
        d = local()
        d.a = 1

        r_list = []
        def f():
            try:
                d.a
            except AttributeError:
                r_list.append(True)

        core.tasklet(f)()
        core.schedule()

        assert r_list == [True]

    def test_local2(self):
        d = local()
        d.a = 1

        r_list = []
        def f():
            try:
                d.a
            except AttributeError:
                r_list.append(True)
            d.a = 2
            if d.a == 2:
                r_list.append(True)

        core.tasklet(f)()
        core.schedule()

        assert r_list == [True, True]
        assert d.a == 1



