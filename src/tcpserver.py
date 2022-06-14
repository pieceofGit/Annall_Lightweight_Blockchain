import sys
import socket
import threading  # from threading import Thread, active_count
import time
import json
import argparse
import time
import hashlib
from interfaces import ClientServer
from queue import Queue

"""
    TCP Server classes - to be used for Lightweight Blockchain project

    Decided not to use socketserver lib, for uglyness and inconsistent semantics
    However, exploit it and the code there in gratuitously

"""

BUFFER_SIZE = 4096


class ClientHandler(threading.Thread):
    # noinspection PyPep8Naming
    def __init__(
        self, connection, payload_q, confirm_q, bcdb, name=None, payload_id=None,
    ):
        threading.Thread.__init__(self)
        assert not connection is None

        print("hello")

        if not name is None:
            self.name = name
        if not payload_id is None:
            self.payload_id = payload_id
        self.connection = connection
        self.delay = 3
        self.terminate = False
        self.payload_queue = payload_q
        self.confirm_queue = confirm_q
        self.bcdb = bcdb

    def check_existance(self, hash: str, payload: str):
        cond_string = f'hash == "{hash}" AND payload == "{payload}"'
        entry = self.bcdb.select_entry(cond_string)
        return bool(entry)

    def run(self):
        # Where the actual service of the client request takes place
        print(f"[CLIENT START]: The thread: self.name")

        # initial handshake with client

        msg = json.dumps({"Server": "Hello", "name": self.name})
        print(f"[MESSAGE TO CLIENT] the message: {msg}")
        self.connection.send(msg.encode())

        data = self.connection.recv(BUFFER_SIZE)
        print(f"[RECEIVED DATA FROM CLIENT] {data}")
        msg = data.decode()

        # print("From client: ", msg)  # Should be: {'Client': "Hello", 'Name': name}
        d = json.loads(msg)
        self.name = d["name"]
        self.payload_id = d["payload_id"]

        # Service client requests until client terminates
        while not self.terminate:
            print("Not terminate...")
            if not self.confirm_queue.empty():
                print("queue is not empty...")
                data = self.confirm_queue.get()
                print(data)
                ts = time.gmtime()
                msg = json.dumps(
                    {
                        "time_added_to_chain": time.strftime("%Y-%m-%d %H:%M:%S", ts),
                        # "hash": "0000000000000bae09a7a393a8acded75aa67e46cb81f7acaa5ad94f9eacd103",
                        "hash": data[2],
                        # "hash": m.hexdigest(),  # is a hash of the payload id
                        "payload_id": data[0],
                        "is_verified": True,
                    }
                )
                try:
                    print("Sending confirmation to client payload was added: " + msg)
                    self.connection.send(msg.encode())
                except Exception as e:  # should really be more specific
                    print("exception", type(e), e)
                    self.terminate = True
                # print(msg)
            try:
                print("[PAYLOAD QUEUE] This is the payload queue: ",self.payload_queue)
                print("receive from client..")
                data = self.connection.recv(BUFFER_SIZE)    # Blocks on receiving data to socket connection from client
                print("received")
            except Exception as e:  # should really be more specific
                print("exception", type(e), e)
                self.terminate = True
                break
            print(f"[MESSAGE BEFORE DECODE] {msg}")
            msg = data.decode()
            print("Received: ", msg)
            print(type(msg))
            print(msg)
            print("[DECODE MESSAGE] decoding message from client")
            d = json.loads(msg) # Converts JSON string into a dictionary
            print("Received: ", d)
            if d["request_type"] == "verify":
                print("request verify")
                payload = f"{d['name']},{d['request_type']},{d['body']}"
                acc = json.dumps({"verified": True,})
                try:
                    self.connection.send(acc.encode())
                except Exception as e:  # should really be more specific
                    print("exception", type(e), e)
                    self.terminate = True
                    break
                if self.check_existance(d["hash"], payload):
                    resp = json.dumps({"verified": True,})
                else:
                    resp = json.dumps({"verified": False,})
                print("Sending to client verification: " + resp)
                self.connection.send(resp.encode())
            else:
                print("request NOT verify")
                self.payload_id = d["payload_id"]
                payload = f"{d['name']},{d['request_type']},{d['body']}"
                # payload = f"{d['name']},{d['Server']},{'dsfsdf'}"
                print(f"[PAYLOAD] {d['name']}, {d['request_type']}, {d['body']}")
                # Add new message to queue
                print(f"[PAYLOAD ADDED] added new payload: {payload}")
                # for i in self.payload_queue:
                #     print(f"[PAYLOAD] {i}")
                self.payload_queue.put((self.payload_id, payload))
                acc = json.dumps({"message_received": True,})
                try:
                    print("Sending message_received ack")
                    self.connection.send(acc.encode())
                except Exception as e:  # should really be more specific
                    print("exception", type(e), e)
                    self.terminate = True
                    break
            time.sleep(self.delay)

        print("Exiting run " + self.name)

    def __del__(self):
        print("Thread ", self.name, "closing connection")
        self.connection.close()


def handle_error(self, client_address):
    ## Handle an error gracefully.
    ## Print a traceback and continue.

    print("-" * 40, file=sys.stderr)
    print(
        "Exception happened during processing of request from",
        client_address,
        file=sys.stderr,
    )
    import traceback

    traceback.print_exc()
    print("-" * 40, file=sys.stderr)


# noinspection PyPep8Naming
class TCP_Server(ClientServer):
    ## A TCP_Server = each client request is served by a separate thread
    ## This is a blocking server.
    NumConnections = 0

    # noinspection PyPep8Naming
    # line 59 main.py: clients = TCP_Server("the server", TCP_IP, TCP_PORT, ClientHandler)

    def __init__(
        self, name, IPv4_addr, port, RequestHandlerClass, bcdb, max_listeners=5
    ):
        """ Constructor.
            Note: RequestHandlerClass is the class that handles request, and should be derived from Threads
        """
        self.name = name
        self.RequestHandlerClass = RequestHandlerClass
        self.__is_shut_down = threading.Event()
        self.__server_terminate = False
        self.running = False
        self.max_listeners = max_listeners
        self.threads = []
        self.payload_queue = Queue()
        self.confirm_queue = Queue()
        self.bcdb = bcdb

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.s.bind((IPv4_addr, port))
            self.s.listen(5)
        except Exception as e:
            print(
                "Error: Cannot setup socket - no point in continuing", type(e), e.args
            )
            raise

        print("Server started - listening at", IPv4_addr, ":", port)

    def accept(self):
        try:
            # Accepts socket and gets back the socket connection
            conn, addr = self.s.accept()    # Blocks on waiting for incoming connection
        except KeyboardInterrupt:
            self.__server_terminate = True
            print("Terminating server")
            raise
        else:
            TCP_Server.NumConnections += 1
            self.handle_client(conn, addr)

    def _cleanup_terminated_threads(self, _all=False):
        live_threads = []
        for t in self.threads:
            if not _all and t.is_alive():
                # print("Thread: ", t.name, "is alive and running")
                live_threads.append(t)
            else:
                if not t.is_alive():
                    print("Thread: ", t.name, "has terminated")
                t.join()
        self.threads = live_threads

    def handle_client(self, connection, addr):
        # cleanup terminated threads
        self._cleanup_terminated_threads()

        print(
            "Handle Client",
            TCP_Server.NumConnections,
            "total threads",
            threading.active_count(),
        )
        # TODO: Why does this thread look unlike other threads
        try:
            thread = self.RequestHandlerClass(
                connection,
                self.payload_queue,
                self.confirm_queue,
                self.bcdb,
                name=None,
            )
            self.threads.append(thread)
            thread.start()
        except KeyboardInterrupt:
            self.shutdown

    def run(self):
        # The main loop.
        # Server is listening to the socket. For each client request a new thread is created
        # dedicated to service that request.
        print("[PAYLOAD QUEUE] This is the payload queue: ",self.payload_queue)
        assert not self.running
        self.__is_shut_down.clear()
        try:
            self.running = True
            while not self.__server_terminate:
                # Calls accept to get connection
                self.accept()   # Blocks on waiting for a new connection
        except Exception as e:
            print("Error:", type(e), e.args)
            request, client_address = None, None
            handle_error(request, client_address)
        finally:
            self.__server_terminate = True
            if not self.s._closed:
                self.s.close()
            self.__is_shut_down.set()

    def shutdown(self):
        # Stops the run loop.
        # Blocks until the loop has finished. This must be called while
        # run() is running in another thread, or it will deadlock.
        # Unless massively abused, the assert will fail if misused.
        assert self.running
        self.__server_terminate = True
        self.__is_shut_down.wait()

    def __del__(self):
        # Wait for all threads to complete
        self._cleanup_terminated_threads(True)
        if not self.s._closed:  # closing listen socket
            self.s.close()


##

if __name__ == "__main__":

    ap = argparse.ArgumentParser()
    # ap.add_argument('-file', help='input data file (default stdin)')
    ap.add_argument(
        "-host",
        default="127.0.0.1",
        help="IP address of remote host (default 127.0.0.1)",
    )
    ap.add_argument(
        "-port",
        default=5005,
        type=int,
        help="port number to connect to at remote host (default 5005)",
    )
    a = ap.parse_args()

    print(sys.argv[0], "host: ", a.host, "port:", a.port)
    print()

    TCP_IP = a.host
    TCP_PORT = a.port

    WriterServer = TCP_Server("WriterServerTest", TCP_IP, TCP_PORT, ClientHandler, None)
    # WriterServer.run()
    # server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Start a thread with the server --
    # The server will then start a thread for each request
    server_thread = threading.Thread(target=WriterServer.run)
    # Exit the server thread when the main thread terminates
    server_thread.start()
    print("Server loop running in thread:", server_thread.name)

    while True:
        try:
            m = input(
                "Enter control command (exit, verbose):"
            )  # input format Type Name Text - where Each are a single word
            # cmd, param = m.split(" ", maxsplit=1)
        except Exception as e:
            print("ERROR:", type(e), e)
            break

    WriterServer.shutdown()
