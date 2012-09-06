# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import pytest

from flower.registry import Registry, registry, insert, remove
from flower import stackless

class Test_Registry:

    def test_simple(self):
        r = Registry()

        class _Dummy(object):
            pass

        obj = _Dummy()
        oid = id(obj)

        ret_oid = r.insert(obj)

        assert ret_oid == oid
        assert ret_oid in r
        assert obj is r[oid]

        r.remove(ret_oid)
        assert ret_oid not in r

    def test_share_registry(self):
        r = Registry()
        r1 = Registry()

        class _Dummy(object):
            pass

        obj = _Dummy()
        ret_oid = r.insert(obj)

        assert ret_oid in r1
        r.remove(ret_oid)

        assert ret_oid not in r
        assert ret_oid not in r1

    def test_multiple(self):
        r = Registry()

        class _Dummy(object):
            pass

        o1 = _Dummy()
        id1 = id(o1)
        o2 = _Dummy()
        id2 = id(o2)

        assert o1 is not o2
        assert id1 != id2

        r.insert(o1)
        r.insert(o2)

        assert id1 in r
        assert id2 in r

        r_list = list(r)

        assert len(r_list) == 2
        assert o1 in r_list
        assert o2 in r_list

        r.remove(id1)
        assert id1 not in r
        assert id2 in r

        r.remove(id2)
        assert id2 not in r

    def test_register(self):
        r = Registry()

        class _Dummy(object):
            pass

        o1 = _Dummy()
        id1 = id(o1)
        o2 = _Dummy()
        id2 = id(o2)

        ret_id1 = r.insert(o1)
        assert ret_id1 == id1
        assert id1 in r

        r.register("test", ret_id1)
        assert "test" in r
        assert r["test"] is o1

        with pytest.raises(KeyError):
            r.register("test2", id2)

        r.insert(o2)
        r.register("test2", id2)
        assert "test2" in r

        r.unregister("test")
        assert "test" not in r

        r.register("test", ret_id1)
        assert "test" in r


        with pytest.raises(KeyError):
            r.register("test", id2)

        r.unregister(id1)
        assert "test" not in r

        del r["test2"]
        assert id2 not in r

        del r[id1]


    def test_register_current(self):
        r = Registry()

        actor = stackless.getcurrent()
        with pytest.raises(KeyError):
            r.register("test")


        actor_id = r.insert(stackless.getcurrent())
        r.register("test")
        assert "test" in r
        assert r["test"] is stackless.getcurrent()

        del r['test']

    def test_main_registry(self):
        r = Registry()

        class _Dummy(object):
            pass

        o = _Dummy()
        oid = registry.insert(o)

        assert oid in r
        del registry[oid]
        assert oid not in r
