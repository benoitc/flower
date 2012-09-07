import threading
from flower import stackless
import sys
if sys.version_info[0] <= 2:
    import thread
else:
    import _thread as thread
commandChannel = stackless.channel()

def master_func():
    commandChannel.send("ECHO 1")
    commandChannel.send("ECHO 2")
    commandChannel.send("ECHO 3")
    commandChannel.send("QUIT")

def slave_func():
    print("SLAVE STARTING")
    while 1:
        command = commandChannel.receive()
        print("SLAVE:", command)
        if command == "QUIT":
            break
    print("SLAVE ENDING")

def scheduler_run(tasklet_func):
    t = stackless.tasklet(tasklet_func)()
    while t.alive:
        stackless.run()

th = threading.Thread(target=scheduler_run, args=(master_func,))
th.start()

scheduler_run(slave_func)
