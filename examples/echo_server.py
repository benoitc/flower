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
