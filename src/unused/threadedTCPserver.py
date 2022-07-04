import sys
import time
import json

import socket
import threading

# import socketserver
from socketserver import ThreadingMixIn, BaseRequestHandler, TCPServer

BUFFER_SIZE = 1024
ClientNames = [
    "orange",
    "apple",
    "pear",
    "banana",
    "kiwi",
    "apple",
    "banana",
    "lemon",
    "plum",
    "peach",
    "lime",
]


class RequestHandler(BaseRequestHandler):
    ## RequestHandler - handles a connection request from one client
    ## Can be used in threaded mode

    ##def __init__(self, request, client_address, server):
    # BaseRequestHandler.__init__(self, request, client_address, server)
    # self.request = request
    # self.client_address = client_address
    # self.server = server
    # self.setup()
    # try:
    #    self.handle()
    # finally:
    #    self.finish()

    def handle(self):
        # data = str(self.request.recv(1024), 'ascii')
        cur_thread = threading.current_thread()
        # response = bytes("{}: {}".format(cur_thread.name, data), 'ascii')
        # self.request.sendall(response)
        # Where the actual service of the client request takes place
        print("Starting Client:", cur_thread.name)

        # initial handshake with client
        msg = json.dumps({"Server": "Hello", "Name": ClientNames[2]})
        print("To Client  :", msg)
        self.request.sendall(msg.encode())
        # self.connection.send(msg.encode())

        data = self.request.recv(BUFFER_SIZE)
        msg = data.decode()
        print("From client:", msg)  # Should be: {'Client': "Hello", 'Name': name}
        d = json.loads(msg)
        self.name = d["Name"]

        # Service client requests until client terminates
        terminate = False
        while not terminate:
            msg = json.dumps({"Server Echo": self.name, "Request": "Whatever"})
            try:
                self.request.sendall(msg.encode())
                data = self.request.recv(BUFFER_SIZE)
            except Exception as e:  # should really be more specific
                print("exception", type(e), e)
                terminate = True
                break

            msg = data.decode()
            print("Event Received (recv): ", msg, " ", data)
            time.sleep(3)

        print("Exiting run ", cur_thread.name)


class ThreadedTCPServer(ThreadingMixIn, TCPServer):
    pass


"""def client(ip, port, message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, port))
        sock.sendall(bytes(message, 'ascii'))
        response = str(sock.recv(1024), 'ascii')
        print("Received: {}".format(response))
"""


if __name__ == "__main__":
    # Port 0 means to select an arbitrary unused port
    HOST, PORT = "localhost", 5005

    server = ThreadedTCPServer((HOST, PORT), RequestHandler)
    # server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    ip, port = server.server_address

    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    server_thread = threading.Thread(target=server.serve_forever)
    # Exit the server thread when the main thread terminates
    server_thread.daemon = True
    server_thread.start()
    print("Server loop running in thread:", server_thread.name)

    while True:
        pass

    server.shutdown()
