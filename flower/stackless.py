import __builtin__
from collections import deque
import operator
import sys
import threading

if sys.version_info[0] <= 2:
    import thread
else:
    import _thread as thread

_tls = thread._local()

import greenlet


class TaskletExit(Exception):
    pass

__builtin__.TaskletExit = TaskletExit

CoroutineExit = TaskletExit
_global_task_id = 0


def _coroutine_getcurrent():
    try:
        return _tls.current_coroutine
    except AttributeError:
        return _coroutine_getmain()

def _coroutine_getmain():
    try:
        return _tls.main_coroutine
    except AttributeError:
        main = coroutine()
        main._is_started = -1
        main._greenlet = greenlet.getcurrent()
        _tls.main_coroutine = main
        return _tls.main_coroutine


class bomb(object):
    def __init__(self, exp_type=None, exp_value=None, exp_traceback=None):
        self.type = exp_type
        self.value = exp_value
        self.traceback = exp_traceback

    def raise_(self):
        raise self.type, self.value, self.traceback


class coroutine(object):
    """ simple wrapper to bind lazily a greenlet to a function """

    _is_started = 0

    def __init__(self):
        self._greenlet = greenlet

    def bind(self, func, *args, **kwargs):
        def _run():
            _tls.current_coroutine = self
            self._is_started = 1
            func(*args, **kwargs)
        self._is_started = 0
        self._greenlet = greenlet.greenlet(_run)

    def switch(self):
        current = _coroutine_getcurrent()

        try:
            self._greenlet.switch()
        finally:
            _tls.current_coroutine = current

    def kill(self):
        current = _coroutine_getcurrent()
        if self is current:
            raise CoroutineExit

        if current._greenlet.parent is not self._greenlet:
            self._greenlet.parent = current._greenlet


        try:
            self._greenlet.throw(CoroutineExit)
        finally:
            _tls.current_coroutine = current

    @property
    def is_alive(self):
        return self._is_started < 0 or bool(self._greenlet)

    @property
    def is_zombie(self):
        return self._is_started > 0 and bool(self._greenlet.dead)

    getcurrent = staticmethod(_coroutine_getcurrent)


class ChannelWaiter(object):

    __slots__ = ['scheduler', 'task']

    def __init__(self, task, scheduler):
        self.task = task
        self.scheduler = scheduler

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


def _scheduler_remove(value):
    get_scheduler().remove(value)

def _scheduler_append(value, normal=True):
    get_scheduler().append(value)


def _scheduler_contains(value):
    scheduler = get_scheduler()
    return value in scheduler

def _scheduler_switch(current, next):
    scheduler = get_scheduler()
    return scheduler.switch(current, next)

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
            target.blocked = 0
            if self.schedule_all:
                # always schedule
                target.scheduler.append(target.task)
                do_schedule = True
            elif self.preference == -d:
                target.scheduler.append(target.task, False)
                do_schedule = True
            else:
                target.scheduler.append(target.task)
        else:
            # nobody is waiting
            source.blocked = d
            self.queue.append(source)
            _scheduler_remove(getcurrent())
            do_schedule = True

        if do_schedule:
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


class tasklet(coroutine):
    """
    A tasklet object represents a tiny task in a Python thread.
    At program start, there is always one running main tasklet.
    New tasklets can be created with methods from the stackless
    module.
    """
    tempval = None
    def __new__(cls, func=None, label=''):
        res = coroutine.__new__(cls)
        res.label = label
        res._task_id = None
        return res


    def __init__(self, func=None, label=''):
        coroutine.__init__(self)
        self._init(func, label)

    def _init(self, func=None, label=''):
        global _global_task_id
        self.func = func
        self.label = label
        self.alive = False
        self.blocked = False
        self.thread_id = thread.get_ident()
        self._task_id = _global_task_id
        _global_task_id += 1

    def __str__(self):
        return '<tasklet[%s, %s]>' % (self.label,self._task_id)

    __repr__ = __str__

    def __call__(self, *argl, **argd):
        return self.setup(*argl, **argd)

    def bind(self, func):
        """
        Binding a tasklet to a callable object.
        The callable is usually passed in to the constructor.
        In some cases, it makes sense to be able to re-bind a tasklet,
        after it has been run, in order to keep its identity.
        Note that a tasklet can only be bound when it doesn't have a frame.
        """
        if not callable(func):
            raise TypeError('tasklet function must be a callable')
        self.func = func


    def setup(self, *argl, **argd):
        """
        supply the parameters for the callable
        """
        if self.func is None:
            raise TypeError('tasklet function must be callable')
        func = self.func
        def _func():

            try:
                try:
                    func(*argl, **argd)
                except TaskletExit:
                    pass
            finally:
                _scheduler_remove(self)
                self.alive = False

        self.func = None
        coroutine.bind(self, _func)
        self.alive = True
        _scheduler_append(self)
        return self

    def run(self):
        self.insert()
        _scheduler_switch(getcurrent(), self)

    def kill(self):
        if self.is_alive:
            # Killing the tasklet by throwing TaskletExit exception.
            coroutine.kill(self)

        _scheduler_remove(self)
        self.alive = False

    def insert(self):
        if self.blocked:
            raise RuntimeError("You cannot run a blocked tasklet")
            if not self.alive:
                raise RuntimeError("You cannot run an unbound(dead) tasklet")
        _scheduler_append(self)

    def remove(self):
        if self.blocked:
            raise RuntimeError("You cannot remove a blocked tasklet.")
        if self is getcurrent():
            raise RuntimeError("The current tasklet cannot be removed.")
            # not sure if I will revive this  " Use t=tasklet().capture()"
        _scheduler_remove(self)

class _Scheduler(object):

    def __init__(self):
        # defiain main tasklet
        self._main_coroutine = _coroutine_getmain()

        self._main_tasklet = _coroutine_getcurrent()
        self._main_tasklet.__class__ = tasklet
        self._main_tasklet._init.im_func(self._main_tasklet, label='main')
        self._last_task = self._main_tasklet

        self._callback = None
        self._run_calls = []
        self._squeue = deque()
        self.append(self._main_tasklet)

    def set_callback(self, cb):
        self._callback = cb

    def append(self, value, normal=True):
        if normal:
            self._squeue.append(value)
        else:
            self._squeue.rotate(-1)
            self._squeue.appendleft(value)
            self._squeue.rotate(1)

    def remove(self, value):
        try:
            del self._squeue[operator.indexOf(self._squeue, value)]
        except ValueError:
            pass

    def switch(self, current, next):
        prev = self._last_task
        if (self._callback is not None and prev is not next):
            self._callback(prev, next)
        self._last_task = next
        assert not next.blocked
        if next is not current:
            next.switch()

        return current

    def schedule(self, retval=None):
        mtask = self.getmain()
        curr = self.getcurrent()

        if retval is None:
            retval = curr

        while True:
            if self._squeue:
                if self._squeue[0] is curr:
                    self._squeue.rotate(-1)
                task = self._squeue[0]
            elif self._run_calls:
                task = self._run_calls.pop()
            else:
                raise RuntimeError("no runnable tasklet left")
            self.switch(curr, task)

            if curr is self._last_task:
                return retval


    def run(self):
        curr = self.getcurrent()
        self._run_calls.append(curr)
        self.remove(curr)
        try:
            self.schedule()
            assert not self._squeue
        finally:
            self.append(curr)

    def runcount(self):
        return len(self._squeue)

    def getmain(self):
        return self._main_tasklet

    def getcurrent(self):
        curr = _coroutine_getcurrent()
        if curr == self._main_coroutine:
            return self._main_tasklet
        else:
            return curr

    def __contains__(self, value):
        try:
            operator.indexOf(_squeue, value)
            return True
        except ValueError:
            return False

_channel_callback = None

def set_channel_callback(channel_cb):
    global _channel_callback
    _channel_callback = channel_cb


def get_scheduler():
    global _tls
    try:
        return _tls.scheduler
    except AttributeError:
        scheduler = _tls.scheduler = _Scheduler()
        return scheduler

def getruncount():
    sched = get_scheduler()
    return sched.runcount()

def getcurrent():
    return get_scheduler().getcurrent()

def getmain():
    return get_scheduler().getmain()


def set_schedule_callback(scheduler_cb):
    sched = get_scheduler()
    sched.set_callback(scheduler_cb)

def schedule(retval=None):
    scheduler = get_scheduler()
    return scheduler.schedule(retval=retval)

def schedule_remove(retval=None):
    scheduler = get_scheduler()
    scheduler.remove(scheduler.getcurrent())
    return scheduler.schedule(retval=retval)

def run():
    sched = get_scheduler()
    sched.run()

# bootstrap the scheduler
def _bootstrap():
    _ = get_scheduler()
_bootstrap()
