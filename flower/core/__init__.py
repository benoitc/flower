# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from flower.core.sched import (tasklet,  get_scheduler, getruncount,
        getcurrent, getmain, set_schedule_callback, schedule,
        schedule_remove, run, taskwakeup)

from flower.core.channel import (bomb, channel, set_channel_callback)


def defer(func, *args, **kwargs):
    """ A "defer" function invokes a function whose execution is
    deferred to the moment the surrounding function returns. """
    return lambda f: func(*args, **kwargs)
