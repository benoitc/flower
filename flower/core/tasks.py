# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.


from collections import deque
import operator
import sys

if sys.version_info[0] <= 2:
    import thread
else:
    import _thread as thread # python 3 fallback

_tls = thread._local()

import greenlet
import pyuv

import six

class TaskletExit(Exception):
    pass

try:
    import __builtin__
    __builtin__.TaskletExit = TaskletExit
except ImportError:
    import builtins
    setattr(builtins, 'TaskletExit', TaskletExit)

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
        self.throw(CoroutineExit)

    def throw(self, *args):
        current = _coroutine_getcurrent()
        try:
            self._greenlet.throw(*args)
        finally:
            _tls.current_coroutine = current

    @property
    def is_alive(self):
        return self._is_started < 0 or bool(self._greenlet)

    @property
    def is_zombie(self):
        return self._is_started > 0 and bool(self._greenlet.dead)

    getcurrent = staticmethod(_coroutine_getcurrent)

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
        if not six.callable(func):
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

    def raise_exception(self, exc, *args):
        if self.is_alive:
            coroutine.throw(self, exc, *args)

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


class LoopExit(Exception):
    pass


def _set_loop_status(status):
    _tls.is_loop_running = status

def _set_loop_task(task):
    _tls.loop_task = task

def _unset_loop_task():
    _tls.loop_task = None

class _LoopTask(tasklet):

    def __init__(self):
        tasklet.__init__(self, label='loop')
        self.loop = get_scheduler().loop
        self.func = self._run_loop
        # bind the coroutine
        self.setup()

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
        _scheduler_append(self, False)
        return self

    def schedule(self, handle):
        _set_loop_status(True)
        schedule()

    def _run_loop(self):
        self._timer = pyuv.Timer(self.loop)
        self._timer.start(self.schedule, 0.0001, 0.0001)
        self._timer.unref()

        # run the loop
        _set_loop_status(True)
        try:
            self.loop.run()
        finally:
            _set_loop_status(False)

class _Scheduler(object):

    def __init__(self):
        # defiain main tasklet
        self._main_coroutine = _coroutine_getmain()

        self._main_tasklet = _coroutine_getcurrent()
        self._main_tasklet.__class__ = tasklet
        six.get_method_function(self._main_tasklet._init)(self._main_tasklet,
                label='main')
        self._last_task = self._main_tasklet
        self.loop = pyuv.Loop()

        # used to make sure we can send messages in the same thread and
        # switch greenlets
        self._async = pyuv.Async(self.loop, self.wakeup)
        self._async.unref()

        self.thread_id = thread.get_ident()
        self._callback = None
        self._run_calls = []
        self._squeue = deque()
        self.append(self._main_tasklet)


    def send(self):
        self._async.send()

    def wakeup(self, handle):
        self.schedule()

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
            operator.indexOf(self._squeue, value)
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

def get_loop():
    try:
        is_running = _tls.is_loop_running
    except AttributeError:
        is_running = False

    if not is_running:
        loop_task = _LoopTask()
        _tls.loop_task = loop_task
    return get_scheduler().loop


def wakeup_loop():
    try:
        loop_task = _tls.loop_task
    except AttributeError:
        get_loop()
        loop_task = _tls.loop_task
    loop_task.switch()

def get_looptask():
    try:
        return _tls.loop_task
    except AttributeError:
        get_loop()
        return _tls.loop_task

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
    get_scheduler()
_bootstrap()
