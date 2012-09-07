import threading
from flower import schedule, run, getruncount, schedule, tasklet

try:
    from thread import get_ident
except ImportError: #python 3
    from _thread import get_ident

def secondary_thread_func():
    runcount = getruncount()
    print("THREAD(2): Has", runcount, "tasklets in its scheduler")

def main_thread_func():
    print("THREAD(1): Waiting for death of THREAD(2)")
    while thread.is_alive():
        schedule()
    print("THREAD(1): Death of THREAD(2) detected")

mainThreadTasklet = tasklet(main_thread_func)()

thread = threading.Thread(target=secondary_thread_func)
thread.start()

print("we are in %s" % get_ident())
run()
