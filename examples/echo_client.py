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
