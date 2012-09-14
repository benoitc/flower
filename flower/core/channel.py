# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from collections import deque
import sys
import threading

import six

from flower.core.sched import (
    schedule, getcurrent, get_scheduler,
    schedrem, thread_ident
)

class bomb(object):
    def __init__(self, exp_type=None, exp_value=None, exp_traceback=None):
        self.type = exp_type
        self.value = exp_value
        self.traceback = exp_traceback

    def raise_(self):
        six.reraise(self.type, self.value, self.traceback)

class ChannelWaiter(object):

    __slots__ = ['scheduler', 'task', 'thread_id', 'arg']

    def __init__(self, task, scheduler, arg):
        self.task = task
        self.scheduler = scheduler
        self.arg = arg
        self.thread_id = thread_ident()

    def __str__(self):
        "waiter: %s" % str(self.task)

class channel(object):
    """
    A channel provides a mechanism for two concurrently executing
    functions to synchronize execution and communicate by passing a
    value of a specified element type. A channel is the only thread-safe
    operation.

    The capacity, in number of elements, sets the size of the buffer in
    the channel. If the capacity is greater than zero, the channel is
    asynchronous: communication operations succeed without blocking if
    the buffer is not full (sends) or not empty (receives), and elements
    are received in the order they are sent. If the capacity is zero or
    absent, the communication succeeds only when both a sender and
    receiver are ready.
    """


    def __init__(self, capacity=None, label=''):
        self.capacity = capacity
        self.closing = False
        self.recvq = deque()
        self.sendq = deque()
        self._lock = threading.Lock()
        self.label = label
        self.preference = -1
        self.schedule_all = False

    def __str__(self):
        return 'channel[%s](%s,%s)' % (self.label, self.balance, self.queue)

    def close(self):
        """
        channel.close() -- stops the channel from enlarging its queue.

        If the channel is not empty, the flag 'closing' becomes true.
        If the channel is empty, the flag 'closed' becomes true.
        """
        self.closing = True

    @property
    def balance(self):
        return len(self.sendq) - len(self.recvq)

    @property
    def closed(self):
        return self.closing and not self.queue

    def open(self):
        """
        channel.open() -- reopen a channel. See channel.close.
        """
        self.closing = False

    def enqueue(self, d, waiter):
        if d > 0:
            return self.sendq.append(waiter)
        else:
            return self.recvq.append(waiter)

    def dequeue(self, d):
        if d > 0:
            return self.recvq.popleft()
        else:
            return self.sendq.popleft()

    def _channel_action(self, arg, d):
        """
        d == -1 : receive
        d ==  1 : send

        the original CStackless has an argument 'stackl' which is not used
        here.

        'target' is the peer tasklet to the current one
        """

        assert abs(d) == 1

        do_schedule = False
        curr = getcurrent()
        source = ChannelWaiter(curr, get_scheduler(), arg)

        if d > 0:
            if not self.capacity:
                cando = self.balance < 0
            else:
                cando = len(self.recvq) <= self.capacity
            dir = d
        else:
            if not self.capacity:
                cando = self.balance > 0
            else:
                cando = len(self.sendq) <= self.capacity
            dir = 0

        if _channel_callback is not None:
            with self._lock:
                _channel_callback(self, getcurrent(), dir, not cando)

        if cando:
            # there is somebody waiting
            try:
                target = self.dequeue(d)
            except IndexError:
                # capacity is not None but nobody is waiting
                if d > 0:
                    self.enqueue(dir, ChannelWaiter(None, None, arg))
                return None

            source.arg, target.arg = target.arg, source.arg
            if target.task is not None:
                if self.schedule_all:
                    target.scheduler.unblock(target.task)
                    do_schedule = True
                elif self.preference == -d:
                    target.scheduler.unblock(target.task, False)
                    do_schedule = True
                else:
                    target.scheduler.unblock(target.task)
        else:
            # nobody is waiting
            source.task.blocked == 1
            self.enqueue(dir, source)
            schedrem(source.task)
            do_schedule = True

        if do_schedule:
            schedule()


        if isinstance(source.arg, bomb):
            source.arg.raise_()
        return source.arg

    def receive(self):
        """
        channel.receive() -- receive a value over the channel.
        If no other tasklet is already sending on the channel,
        the receiver will be blocked. Otherwise, the receiver will
        continue immediately, and the sender is put at the end of
        the runnables list.
        The above policy can be changed by setting channel flags.
        """
        return self._channel_action(None, -1)

    def send_exception(self, exp_type, msg):
        self.send(bomb(exp_type, exp_type(msg)))

    def send_sequence(self, iterable):
        for item in iterable:
            self.send(item)

    def send(self, msg):
        """
        channel.send(value) -- send a value over the channel.
        If no other tasklet is already receiving on the channel,
        the sender will be blocked. Otherwise, the receiver will
        be activated immediately, and the sender is put at the end of
        the runnables list.
        """
        return self._channel_action(msg, 1)


_channel_callback = None

def set_channel_callback(channel_cb):
    global _channel_callback
    _channel_callback = channel_cb
