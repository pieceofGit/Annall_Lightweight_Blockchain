import sys
import socket
import threading  # from threading import Thread, active_count
import time
import json
import argparse
import time

from interfaces import ClientServer, verbose_print, vverbose_print
from queue import Queue

"""
    TCP Server classes - to be used for Lightweight Blockchain project

    Decided not to use socketserver lib, for uglyness and inconsistent semantics
    However, exploit it and the code there in gratuitously

"""

BUFFER_SIZE = 4096
LOCAL = True   # Connect to specific socket or any available

class ClientHandler(threading.Thread):
    # noinspection PyPep8Naming
    def __init__(
        self, connection, payload_q, bcdb, name=None, payload_id=None,
    ):
        threading.Thread.__init__(self)
        assert not connection is None

        if not name is None:
            self.name = name
        if not payload_id is None:
            self.payload_id = payload_id
        self.connection = connection
        self.delay = 0.1
        self.terminate = False
        self.payload_queue = payload_q
        self.bcdb = bcdb

    def check_existence(self, hash: str):
        cond_string = f'hash == "{hash}"'
        # cond_string = f'hash == "{hash}" AND payload == "{payload}"'
        entry = self.bcdb.select_entry(cond_string)
        return bool(entry)

    def format_msg(self, msg: str) -> bytes:
        """ Format message to be sent over socket """
        b = len(msg).to_bytes(4, "big", signed=False) + bytes(msg, "utf-8")
        return b
    
    def send_message_to_client(self, msg):
        byte_msg = self.format_msg(msg)
        self.connection.send(byte_msg)

    def get_message_from_client(self):
        """Handles getting message.
        1. Blocks on receiving message length
        2. Blocks on receiving message
        3. Returns JSON or string
        """
        # Get message length
        byte_length = self.connection.recv(4)   # Blocks
        if byte_length == b"":
            raise Exception(f"> Connection closed. Socket:{self.connection}")
        try:
            # Get message length as integer
            length = int.from_bytes(byte_length, "big", signed=False)
        except Exception as e:
            verbose_print(">!! Failed to read length of message")
            return ""
        if length > BUFFER_SIZE:
            verbose_print(">!! Message size too large")
            return ""
        try:
            # Get the message data
            b = self.connection.recv(length)
        except Exception as e:
            verbose_print(">!! Failed to read message with:", e)
        try:
            json_msg = json.loads(b)
            return json_msg
        except:
            return ""

    def send_ack(self, payload=None):
        acc = json.dumps({"message_received": True, "payload_id": self.payload_id})
        try:
            verbose_print("Sending message_received ack")
            if payload:
                self.send_message_to_client(payload)
            else:
                self.send_message_to_client(acc)
        except Exception as e:  # should really be more specific
            verbose_print("exception", type(e), e)
            self.terminate = True
    
    def run(self):
        # After initial handshake.
        # Where service of the client request takes place
        vverbose_print(f"[CLIENT START]: The thread: {self.name}")
        # initial handshake with client
        msg = json.dumps({"Server": "Hello", "name": self.name})
        self.send_message_to_client(msg)
        # Only receive the first message. Use message length        
        data = self.get_message_from_client()
        self.name = data["name"]
        self.payload_id = data["payload_id"]
        self.send_ack()
        # Service client requests until client terminates
        while not self.terminate:
            try:
                d = self.get_message_from_client() # Blocks on waiting for data from client and loads into dict
            except Exception as e:  
                verbose_print("exception", type(e), e)
                self.terminate = True
                break
            if d["request_type"] == "verify":
                # payload = f"{d['name']},{d['request_type']},{d['payload']}"
                # if self.check_existence(d["hash"], payload):
                if self.check_existence(d["hash"]):
                    resp = json.dumps({"verified": True,})
                else:
                    resp = json.dumps({"verified": False,})
                self.send_message_to_client(resp)
            elif d["request_type"] == "read_chain":
                # Gets back chain in a list of dictionaries
                blockchain = self.bcdb.read_blocks(0, read_entire_chain=True)
                # Send back entire blockchain json object
                self.send_message_to_client(json.dumps(blockchain))
            else:   # "request_type == "block"
                # Add new message to payload queue and send back ACK
                self.payload_id = d["payload_id"]
                if type(d['payload']) == dict:
                    payload = json.dumps(d['payload']) # Take dict and turn to json
                else:
                    payload = f"{d['payload']}"    # If not dict, store unchanged string
                # Add new message to queue
                self.payload_queue.put((self.payload_id, payload))
                self.send_ack(payload)
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
        self.bcdb = bcdb

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            if LOCAL:
                self.s.bind((IPv4_addr, port))
            else:
                self.s.bind(("", port)) # Binds to any available IP Address
            self.s.listen(5)
        except Exception as e:
            verbose_print(
                "Error: Cannot setup socket - no point in continuing", type(e), e.args
            )
            raise

        verbose_print("Server started - listening at", IPv4_addr, ":", port)

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

        vverbose_print(
            "Handle Client",
            TCP_Server.NumConnections,
            "total threads",
            threading.active_count(),
        )
        try:
            thread = self.RequestHandlerClass(
                connection,
                self.payload_queue,
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
        assert not self.running
        self.__is_shut_down.clear()
        try:
            self.running = True
            while not self.__server_terminate:
                # Calls accept to get connection
                self.accept()   # Blocks on waiting for a new connection
        except Exception as e:
            verbose_print("Error:", type(e), e.args)
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
