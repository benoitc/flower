


==========================================================================================




**DEPPRECATED** Flower is now superseded by `Offset <http://github.com/benoitc/offser>`_ .



==========================================================================================








Flower
======

.. image:: https://secure.travis-ci.org/benoitc/flower.png?branch=master
    :target: http://travis-ci.org/benoitc/flower

collection of modules to build distributed and reliable concurrent
systems in Python.

::

    a = “”

    def f():
       print(a)

    def hello():
        a = "hello, world"
        tasklet(f)()

Requirements
------------

- Python from 2.6 to 3.x
- A platform supported by `libuv <https://github.com/joyent/libuv>`

Simple example
--------------

A simple example showing how to create a simple echo server.

.. code-block:: python

    # Echo server program
    from flower import tasklet, run
    from flower.net import Listen


    # handle the connection. It return data to the sender.
    def handle_connection(conn):
        while True:
            data = conn.read()
            if not data:
                break

            conn.write(data)


    # Listen on tcp port 8000 on localhost
    l = Listen(('127.0.0.1', 8000), "tcp")
    try:
        while True:
            try:

                # wait for new connections (it doesn't block other tasks)
                conn, err = l.accept()

                # Handle the connection in a new task.
                # The loop then returns to accepting, so that
                # multiple connections may be served concurrently.

                t = tasklet(handle_connection)(conn)
            except KeyboardInterrupt:
                break
    finally:
        l.close()

    run()


And the echo client::

    from flower import tasklet, run, schedule
    from flower.net import Dial


    # connect to the remote server
    conn = Dial("tcp", ('127.0.0.1', 8000))

    # start to handle the connection
    # we send a string to the server and fetch the
    # response back

    for i in range(3):
        msg = "hello"
        print("sent %s" % msg)
        resp = conn.write(msg)
        ret = conn.read()
        print("echo: %s" % ret)

    conn.close()
    run()


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
