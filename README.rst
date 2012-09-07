Flower
======

.. image:: https://secure.travis-ci.org/benoitc/flower.png?branch=master
    :target: http://travis-ci.org/benoitc/flower

collection of modules to build distributed and reliable concurrent
systems in Python.


Simple example
--------------

A simple example showing how to create a consumer and use other actor
function to feed it.

.. code-block:: python

        from flower import stackless
        from flower.actor import spawn, receive, send

        messages = []
        sources = []
        def consumer():
            # wait for coming message in the current actor
            while True:
                source, msg = receive()
                if not msg:
                    break
                print("got message from %s: %s" % (source.ref, msg))

        def publisher1(ref):
            # an actor sending messages to the consumer
            msg = ['hello', 'world']
            for s in msg:
                send(ref, s)

        def publisher2(ref):
            msg = ['brave', 'new', 'world', '']
            for s in msg:
                send(ref, s)

        ref_consumer = spawn(consumer)
        spawn(publisher1, ref_consumer)
        spawn(publisher2, ref_consumer)

        stackless.run()


should return::

    $ python examples/actor_example.py
    got message from 1: hello
    got message from 2: brave
    got message from 1: world
    got message from 2: new
    got message from 2: world
