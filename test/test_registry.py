# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import pytest

from flower.actor import spawn, ActorRef
from flower.registry import (registry, register, unregister,
        registered, Registry)
from flower import stackless



class Test_Registry:

    def test_simple(self):
        def f(): return

        pid = spawn(f)
        register("test", pid)

        assert pid in registry
        assert "test" in registry
        assert registry["test"] ==  pid
        assert registry[pid] == ["test"]

        del registry[pid]
        assert registry["test"] is None

        stackless.run()

    def test_registered(self):
        r_list = []
        def f():
            print("ici %s" % registered())
            print(registry._by_ref)
            [r_list.append(r) for r in registered()]

        pid = spawn(f)
        register("b", pid)
        register("a", pid)



        assert 'a' in registry
        assert 'b' in registry
        assert registered(pid) == ['a', 'b']

        pid.actor.switch()
        assert r_list == ['a', 'b']


    def test_share_registry(self):
        r = Registry()

        def f(): return
        pid = spawn(f)
        register("test1", pid)

        assert "test1" in registry
        assert registry["test1"] is pid
        assert "test1" in r
        assert r["test1"] == registry["test1"]
