Flower
======

.. image:: https://secure.travis-ci.org/benoitc/flower.png?branch=master
    :target: http://travis-ci.org/benoitc/flower

collection of modules to build distributed and reliable concurrent
systems in Python.

Requirements
------------

- Python from 2.6 to 3.x
- A platform supported by `libuv <https://github.com/joyent/libuv>`

Simple example
--------------

A simple example showing how to create a consumer and use other actor
function to feed it.

.. code-block:: python

        import flower

        messages = []
        sources = []
        def consumer():
            # wait for coming message in the current actor
            while True:
                source, msg = flower.receive()
                if not msg:
                    break
                print("got message from %s: %s" % (source.ref, msg))

        def publisher1(ref):
            # an actor sending messages to the consumer
            msg = ['hello', 'world']
            for s in msg:
                flower.send(ref, s)

        def publisher2(ref):
            msg = ['brave', 'new', 'world', '']
            for s in msg:
                flower.send(ref, s)

        ref_consumer = flower.spawn(consumer)
        flower.spawn(publisher1, ref_consumer)
        flower.spawn(publisher2, ref_consumer)

        flower.run()


should return::

    $ python examples/actor_example.py
    got message from 1: hello
    got message from 2: brave
    got message from 1: world
    got message from 2: new
    got message from 2: world


Installation
------------

Flower requires Python superior to 2.6 (yes Python 3 is supported)

To install flower using pip you must make sure you have a
recent version of distribute installed::

    $ curl -O http://python-distribute.org/distribute_setup.py
    $ sudo python distribute_setup.py
    $ easy_install pip


For now flower can only be installed from sources. To install or upgrade to the latest released version of flower::

    $ git clone https://github.com/benoitc/flower.git
    $ cd flower && pip install -r requirements.txt

License
-------

flower is available in the public domain (see UNLICENSE). flower is also
optionally available under the MIT License (see LICENSE), meant
especially for jurisdictions that do not recognize public domain
works.
