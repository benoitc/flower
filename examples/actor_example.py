from flower import spawn, receive, send, run

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

run()
