# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from collections import deque
import sys
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

    __slots__ = ['scheduler', 'task', 'thread_id']

    def __init__(self, task, scheduler):
        self.task = task
        self.scheduler = scheduler
        self.thread_id = thread_ident()

    def __get_tempval(self):
        return self.task.tempval

    def __set_tempval(self, tempval):
        self.task.tempval = tempval

    tempval = property(__get_tempval, __set_tempval)

    def __get_blocked(self):
        return self.task.blocked

    def __set_blocked(self, blocked):
        self.task.blocked = blocked

    blocked = property(__get_blocked, __set_blocked)

class channel(object):
    """
    A channel object is used for communication between tasklets.
    By sending on a channel, a tasklet that is waiting to receive
    is resumed. If there is no waiting receiver, the sender is suspended.
    By receiving from a channel, a tasklet that is waiting to send
    is resumed. If there is no waiting sender, the receiver is suspended.

    Attributes:

    preference
    ----------
    -1: prefer receiver
     0: don't prefer anything
     1: prefer sender

    Pseudocode that shows in what situation a schedule happens:

    def send(arg):
        if !receiver:
            schedule()
        elif schedule_all:
            schedule()
        else:
            if (prefer receiver):
                schedule()
            else (don't prefer anything, prefer sender):
                pass

        NOW THE INTERESTING STUFF HAPPENS

    def receive():
        if !sender:
            schedule()
        elif schedule_all:
            schedule()
        else:
            if (prefer sender):
                schedule()
            else (don't prefer anything, prefer receiver):
                pass

        NOW THE INTERESTING STUFF HAPPENS

    schedule_all
    ------------
    True: overwrite preference. This means that the current tasklet always
          schedules before returning from send/receive (it always blocks).
          (see Stackless/module/channelobject.c)
    """


    def __init__(self, label=''):
        self.balance = 0
        self.closing = False
        self.queue = deque()
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
    def closed(self):
        return self.closing and not self.queue

    def open(self):
        """
        channel.open() -- reopen a channel. See channel.close.
        """
        self.closing = False

    def _channel_action(self, arg, d):
        """
        d == -1 : receive
        d ==  1 : send

        the original CStackless has an argument 'stackl' which is not used
        here.

        'target' is the peer tasklet to the current one
        """
        do_schedule = False
        assert abs(d) == 1

        source = ChannelWaiter(getcurrent(), get_scheduler())
        source.tempval = arg
        if d > 0:
            cando = self.balance < 0
            dir = d
        else:
            cando = self.balance > 0
            dir = 0

        if _channel_callback is not None:
            _channel_callback(self, source.task, dir, not cando)

        self.balance += d
        if cando:
            # there is somebody waiting
            target = self.queue.popleft()
            source.tempval, target.tempval = target.tempval, source.tempval
            if self.schedule_all:
                # always schedule
                target.scheduler.unblock(target.task)
                do_schedule = True
            elif self.preference == -d:
                target.scheduler.unblock(target.task, False)
                do_schedule = True
            else:
                target.scheduler.unblock(target.task)

            sched = target.scheduler

        else:
            # nobody is waiting
            sched = source.scheduler
            source.blocked = 1
            self.queue.append(source)
            schedrem(getcurrent())
            do_schedule = True

        if do_schedule:
            if sched.thread_id == thread_ident():
                schedule()

        retval = source.tempval
        if isinstance(retval, bomb):
            retval.raise_()
        return retval

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
