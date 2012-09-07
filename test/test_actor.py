# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from flower.actor import receive, send, spawn, ActorRef
from flower import core


class Test_Actor:

    def test_simple(self):

        r_list = []
        def f():
            r_list.append(True)

        pid = spawn(f)
        assert isinstance(pid, ActorRef)
        assert pid.ref == 0
        assert hasattr(pid.actor, 'mailbox')

        core.run()

        assert r_list == [True]
        assert pid.actor is None
        assert pid.is_alive is False


    def test_mailbox(self):
        messages = []
        sources = []
        def f():
            while True:
                source, msg = receive()
                if not msg:
                    break
                if source.ref not in sources:
                    sources.append(source.ref)
                messages.append(msg)

        def f1(ref):
            msg = ['hello', ' ', 'world']
            for s in msg:
                send(ref, s)

        pid0 = spawn(f)
        pid1 = spawn(f1, pid0)

        core.run()

        assert messages == ['hello', ' ', 'world']
        assert sources == [2]

    def test_multiple_producers(self):
        messages = []
        sources = []
        def f():
            while True:
                source, msg = receive()
                if not msg:
                    break
                if source.ref not in sources:
                    sources.append(source.ref)
                messages.append(msg)

        def f1(ref):
            msg = ['hello', 'world']
            for s in msg:
                send(ref, s)

        def f2(ref):
            msg = ['brave', 'new', 'world', '']
            for s in msg:
                send(ref, s)

        pid0 = spawn(f)
        pid1 = spawn(f1, pid0)
        pid2 = spawn(f2, pid0)

        core.run()

        assert len(messages) == 5
        assert sources == [4, 5]


