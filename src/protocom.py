from PCommMsg import pMsg
from PCommMsg import pMsgTyp
import interfaces
from threading import Thread
import threading
import socket
from queue import Queue
import select
import selectors
import sys
import json
import argparse
import time
import random
import struct
import inspect


VERBOSE = True
DEBUG = True
# **********************************

# **********************************

"""
We use "#" as seperator so messages cannot contain this symbol
send
TODO: sys.exit() when catching ctrl-C
"""

linebreak = "***************************************"


class RemoteEnd:
    """ Remote peer in the p2p network

    Invariants:
        listen_address = is configured address where remote peer is listening
        socket : is None or an open socket connected to remote peer
        is_active : is true is socket is valid and open
    """

    max_try_conn = 10
    # if we reach max connection tries we wait 60 seconds until next try
    wait_conn = 60

    def __init__(self, rem_id: int, host: str, port: int, pub_key):
        self.rem_id = rem_id
        self.listen_address = (host, port)
        self.pub_key = pub_key
        self.is_active = False
        # Number of tries to connect to
        self.try_conn = 0
        # time_last is either time since connection tries reach max
        # or since last message received
        self.time_last = time.process_time()
        # socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket: socket.socket() = None
        # self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def connect(self):
        """ Check wether connection tries exceed max\n
            if not try to connect """
        self.try_conn += 1
        if self.try_conn == RemoteEnd.max_try_conn:
            self.time_last = time.process_time()
            raise Exception("Max tries reached")
        elif self.try_conn > RemoteEnd.max_try_conn:
            # if timeout for tryin to reconnect is reached
            if time.process_time() - self.time_last > RemoteEnd.wait_conn:
                # allow one more try
                self.try_conn = RemoteEnd.max_try_conn - 1
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(30)  # TODO: Find out the appropriate timeout
        self.socket.connect(self.listen_address)
        self.try_conn = 0
        self.time_last = time.process_time()
        return self.socket

    def connect_accept(self):
        """ Called to finalize connection set as active"""
        # self.socket = socket
        self.is_active = True
        self.time_last = time.process_time()

    def accept_from(self, socket):
        """ Accept socket """
        self.socket = socket
        self.time_last = time.process_time()
        # self.is_active = True

    def close(self, selec):
        """ Close socket """
        try:
            self.socket.close()
            if self.is_active:
                selec.unregister(self.socket)
            del self.socket
            self.socket = None
        except Exception as e:
            if DEBUG:
                print(f">!! Failed to close socket with exception {e}")
        finally:
            self.is_active = False

    def send_bytes(self, b_msg):
        """ Send bytes over socket """
        if self.socket is not None:
            print("send bytes..")
            self.socket.sendall(b_msg)
            print("bytes sent")
            self.time_last = time.process_time()
        else:
            raise Exception("Connection not active")

    def read_single_msg(self) -> str:
        """ Read a single message from socket\n
            assumes that socket is ready to read\n
            Raises exception if reads "" assumes connection is closed\n
            Returns "" if fails to convert to int
            @returns string
            """
        # TODO handle exception when int fails. Read all message buffer and throw away
        # if self.is_active:
        byte_length = self.socket.recv(4)
        # print("Read length:", byte_length)
        if byte_length == b"":
            raise Exception(f"> Connection closed. Socket:{self.socket}")
        try:
            length = int.from_bytes(byte_length, "big", signed=False)
            # print("Received message of length:", length)
        except Exception as e:
            if DEBUG:
                print(">!! Failed to read length of message")
            return ""
        try:
            # print("Reading message")
            b = self.socket.recv(length)
        except Exception as e:
            if DEBUG:
                print(">!! Failed to read message with:", e)
        decb = b.decode("utf-8")
        # print("> Received message:", decb)
        return decb
        # else:
        #    raise Exception("Connection not active")

    def recv_bytes(self) -> str:
        byte_length = self.socket.recv(4)
        length = int.from_bytes(byte_length, "big", signed=False)
        if not byte_length or length == 0:
            raise ConnectionAbortedError
        bmsg = self.socket.recv(length)
        if not bmsg:
            raise ConnectionAbortedError
        return bmsg.decode("utf-8")

    @staticmethod
    def static_read_single_msg(r_socket: socket.socket) -> str:
        """ Read a single message from socket\n
            assumes that socket is ready to read\n
            Raises exception if reads "" assumes connection is closed\n
            Returns "" if fails to convert to int
            @returns string
            """
        # TODO handle exception when int fails. Read all message buffer and throw away
        # if self.is_active:
        byte_length = r_socket.recv(4)
        if VERBOSE:
            print("Read length:", byte_length)
        if byte_length == b"":
            raise Exception(f"> Connection closed. Socket:{r_socket}")
        try:
            length = int.from_bytes(byte_length, "big", signed=False)
            # print("Received message of length:", length)
        except Exception as e:
            if DEBUG:
                print(">!! Failed to read length of message")
            return ""
        try:
            if VERBOSE:
                print("Reading message")
            b = r_socket.recv(length)
        except Exception as e:
            if DEBUG:
                print(">!! Failed to read message with:", e)
        decb = b.decode("utf-8")
        if VERBOSE:
            print("> Received message:", decb)
        return decb
        # else:
        #    raise Exception("Connection not active")

    @staticmethod
    def read_c_request(socket):
        """@returns ([rem_id],[self_id],[secret], opt []) """
        tries = 0
        while tries < 3:
            try:
                msg = RemoteEnd.static_read_single_msg(socket)
            except Exception as e:
                raise e
            # [type], [r_id], [self_id], [secret], optional [something]
            try:
                tokens = msg.split(pMsg.sep, maxsplit=3)
                if tokens[0] == pMsgTyp.c_request:
                    return tokens[1:]
            except Exception as e:
                if DEBUG:
                    print("Failed to split message", e)
            tries += 1
        raise Exception("Failed to read C-ACK")

    def read_c_reply(self):
        """@returns ([rem_id],[self_id],[secret], opt []) """
        tries = 0
        while tries < 3:
            try:
                msg = self.read_single_msg()
            except Exception as e:
                # raise e
                if DEBUG:
                    print("Failed to read message:", e)
            # [type], [r_id], [self_id], [secret], optional [something]
            # we cannot unpack because we dont know or assume number of splits
            try:
                tokens = msg.split(pMsg.sep, maxsplit=4)
                if tokens[0] == pMsgTyp.c_reply:
                    return tokens[1:]
            except Exception as e:
                if DEBUG:
                    print("Failed to split message", e)
            tries += 1
        raise Exception("Failed to read C-ACK")

    def read_c_ack(self):
        """@returns ([rem_id],[self_id]) """
        if VERBOSE:
            print(f"Reading C-ACK message from id: {self.rem_id}")
        tries = 0
        while tries < 3:
            try:
                msg = self.read_single_msg()
            except Exception as e:
                if DEBUG:
                    print("Failed with exception:", e)
                raise e
            # [type], [r_id], [self_id]
            if VERBOSE:
                print("Revieved:", msg)
            try:
                print(f"protocom splitting message: {msg}")
                tokens = msg.split(pMsg.sep, maxsplit=4)
                if tokens[0] == pMsgTyp.c_ack:
                    return tokens[1:]
            except Exception as e:
                if DEBUG:
                    print("Failed to split message", e)
            tries += 1
        raise Exception("Failed to read C-ACK")

    def __del__(self):
        # if self.socket is not None:
        #    del self.socket
        pass


    def __str__(self):
        return f'''\n
        ID: {self.rem_id}
        Address: {self.listen_address}
        Public Key: {self.pub_key}
        IsActivate: {self.is_active}\n
        '''

    def __repr(self):
        return f"<{self.rem_id}:{self.listen_address} is active: {self.is_active} {self.socket}>"


class ProtoCom(interfaces.ProtocolCommunication):
    def __init__(self, self_id: int, conf: dict, num_writers=None):
        interfaces.ProtocolCommunication.__init__(
            self, "Protocall communication")
        # set up
        self.id = self_id
        self.conf = conf
        self.running = True
        self.conn_modulus = 0
        # lock is used to put on to and take off of msg_queue
        self.msg_lock = threading.RLock()
        # Define number of writers to attempt to connect to 
        if num_writers:
            self.num_writers = num_writers
        else:
            self.num_writers = len(conf["active_writer_set"])
        # print(">", self.name, "Number of writers: ", self.num_writers)
        self.rr_selector = None
        # set up lists and stuff
        # dictionary of connected sockets use for storing sockets and stuff
        self.peers = {}
        ip = None
        listen_port = None
        # Select out of the writers list who we want to connect to
        print("[PRINTING WRITERS IN SET NO_WRITERS]", conf["active_writer_set"][0:self.num_writers])
        for writer in conf["active_writer_set"][0:self.num_writers]:
            print("The writer set ")
            if writer["id"] != self.id:
                print("Inside if in 287 ")
                self.peers[writer["id"]] = RemoteEnd(
                    writer["id"], writer["hostname"], writer["port"], writer["pub_key"]
                )
            elif writer["id"] == self.id:
                ip = writer["hostname"]
                listen_port = writer["port"]
                self.pub_key = writer["pub_key"]
        # set up listening socket
        # Making sure to not run this if either are undefined, unless it crashes
        if (ip != None) or (listen_port != None):
            self.listen_sock = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            # Prevents error Address already in use. Socket not in TIME_WAIT state
            self.listen_sock.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listen_sock.setblocking(False)
            print(f"Listening on port: {listen_port}")
            self.listen_sock.bind((ip, listen_port))
            # TODO decide what number - lets not decide and just make it big
            self.listen_sock.listen(100)
            # TODO for all sockets conn.setblocking(False) when using selectors
            # ready read selector
            self.rr_selector = selectors.DefaultSelector()
            self.rr_selector.register(
                self.listen_sock, selectors.EVENT_READ, self.id)

            # Received messages are added to this queue and removed when recv_msg() is called
            self.msg_queue = []

    def accept_con(self, listen_sock: socket.socket):
        """ callback method for listening socket

            Accept procedure
            1. accept from listensock
            2. receive msg. if not C-request try to read again. if verify fails send C-refuse
            3. send C-reply.
            4. wait for C-ack
            5 accept connection
        """
        if VERBOSE:
            print(" Revceived incoming connection ",
                  self.list_connected_peers())
        in_conn, in_addr = listen_sock.accept()
        in_conn.settimeout(4)  # Only for accepting
        # tmpRemoteEnd = RemoteEnd(None, in_addr[0], in_addr[1])
        # tmpRemoteEnd.accept(in_conn)
        try:
            tokens = RemoteEnd.read_c_request(in_conn)
        except Exception as e:
            if DEBUG:
                print("Failed to read c-request with exception:", e)
            return
        if len(tokens) == 4:
            if VERBOSE:
                print("Received data: ", tokens[3])
        if VERBOSE:
            print("Received:", tokens)
        rem_id, self_id, secret = tokens[0:3]
        rem_id = int(rem_id)
        # Verifies the message by comparing its public key to the message's public key
        if pMsg.verify_con_msg(
            tokens[0:3], self.id, rem_id, self.peers[rem_id].pub_key
        ):
            if VERBOSE:
                print("Verification Complete")
                print(" Received incoming connection from id:", rem_id)
            if not self.peers[rem_id].is_active:
                if VERBOSE:
                    print("Sending verification")
                # sends back message of type C-REPLY
                repl_msg = pMsg.con_repl_msg(
                    self.id, rem_id, self.list_connected_peers(), self.pub_key
                )
                # Sets the socket for remote connection
                self.peers[rem_id].accept_from(in_conn)
                try:
                    # Sends all bytes in buffer to remote writer
                    in_conn.sendall(repl_msg)
                except Exception as e:
                    if DEBUG:
                        print("Failed to send reply", e)
                    in_conn.close()
                    return
                time.sleep(2)
                try:
                    tokens = self.peers[rem_id].read_c_ack()
                    # rem_id, self_id = tokens[0:1]
                    if VERBOSE:
                        print(f"Received c-ack message: {tokens}")
                except Exception as e:
                    if DEBUG:
                        print("Failed to read ack message closing connection:", e)
                    self.peers[rem_id].close(self.rr_selector)
                    return
                try:
                    in_conn.setblocking(False)
                    self.rr_selector.register(
                        in_conn, selectors.EVENT_READ, rem_id)
                    self.peers[rem_id].connect_accept()
                    if VERBOSE:
                        print("Accept incoming connection",
                              self.list_connected_peers())
                except Exception as e:
                    if DEBUG:
                        print("Failed to store connection", e)
            else:
                # TODO: send to other connection refused because already have connection
                if VERBOSE:
                    print("Already have connection so we close the new one")
                in_conn.close()
        else:
            if VERBOSE:
                print("Verification failed")
            # TODO send refused
            in_conn.close()

    def init_con_all(self):
        """ Attempt to connect to ONE unconnected writers

            Iterates through one writer on each call

            Connect procedure
            1. Send C-request
            2. receive msg. if not C-reply try to read again. if verify fails send C-refuse
            3. send C-ack.
            4. accept connection
        """
        # make list of writers, set random start index, loop through all
        w_list = list(self.peers.keys())
        # n = random.randrange(start=0, stop=len(self.peers.keys()))
        # rearrange list such that it starts on index n
        w_list = list(set(w_list) - set(self.list_connected_peers()))
        if len(w_list) == 0:
            self.conn_modulus = 0
            # print("All peers connected")
            return
        self.conn_modulus += 1
        if self.conn_modulus >= len(w_list):
            self.conn_modulus = 0
        r_id = w_list[self.conn_modulus]
        # for r_id in w_list:
        # NB only connect to those with higher number
        if r_id > self.id and not self.peers[r_id].is_active:
            if VERBOSE:
                print(">", "Attempting to connect to id: ", r_id)
            try:
                self.peers[r_id].connect()
                if VERBOSE:
                    print("Connected to id:", r_id)
            except Exception as e:
                if DEBUG:
                    print(f">!! Failed to connect with exception: {e}")
                self.peers[r_id].close(self.rr_selector)
                return
            try:
                req_msg = pMsg.con_requ_msg(self.id, r_id, self.pub_key)
                self.peers[r_id].send_bytes(req_msg)
            except Exception as e:
                if DEBUG:
                    print(
                        f">!! Failed to send connection request with exception: {e}")
                self.peers[r_id].close(self.rr_selector)
                return
            # time.sleep(1) might as well wait on the socket
            # read_c_reply reads from socket until a read_c_reply message is read
            try:
                repl_msg = self.peers[r_id].read_c_reply()
                if VERBOSE:
                    print("Revieved verification", repl_msg)
            except Exception as e:
                if DEBUG:
                    print(
                        f">!! Failed to receive reply message with exception {e}")
                self.peers[r_id].close(self.rr_selector)
                return
            if pMsg.verify_con_msg(
                repl_msg[:3], self.id, r_id, self.peers[r_id].pub_key
            ):
                self.peers[r_id].send_bytes(
                    pMsg.con_ack_msg(
                        self.id, r_id, self.list_connected_peers())
                )
                if VERBOSE:
                    print("Verification Complete")
                self.peers[r_id].socket.setblocking(False)
                self.rr_selector.register(
                    self.peers[r_id].socket, selectors.EVENT_READ, r_id
                )
                self.peers[r_id].connect_accept()
                if VERBOSE:
                    print(">", "Connected to:", r_id)
            else:
                if VERBOSE:
                    print(">", "Verification failed. Closing connection")
                self.peers[r_id].close(self.rr_selector)

    def read_con(self, r_id, r_sock):
        """ callback method for remote connection socket\n
            Reads a single message from the socket and puts it on the message queue

            Read procedure
            1. Read a single message
            2. check type. If Data put data on message queue.
            3. send appropriate response
        """
        # print("Reading from id:", r_id)
        try:
            print("BEFORE - read single msg")
            msg = self.peers[r_id].read_single_msg()
            print(msg)
            print("AFTER - read single msg")
        except Exception as e:
            if DEBUG:
                print(">!! ", "Failed to read from socket")
            # this means connection is closed
            # close socket here do not put on a removelist
            try:
                if VERBOSE:
                    print(">", "Removing connection to id: ", r_id)
                self.peers[r_id].close(self.rr_selector)
            except Exception as e:
                if DEBUG:
                    print(">!! ", "Failed to close socket")
                    print(">!! ", "with exception: ", type(e), e)
            return
        if msg == "":
            # we received a bad message (maybe add some error counter)
            # (and close bad connections)
            return
        # [type], [r_id], [self_id], optional [data]
        msg_typ, rem_id, self_id, msg_data = msg.split(pMsg.sep, maxsplit=3)
        print(msg_typ, rem_id,self_id,msg_data)
        """try:
            rem_id = int(rem_id)
            assert rem_id == r_id
            self_id = int(self_id)
            assert self_id == self.id
            # test wether ids match up with expected from connection
        except Exception as e:
            pass """
        # TODO what if msg_type is data_ack ???
        # TODO When reviece ECHO request reply with ECHO reply
        # if request contains data reply with that data else send list of connected ids
        if msg_typ == pMsgTyp.data:
            print("data == data")
            with self.msg_lock:
                print("adding to queue")
                self.msg_queue.append((r_id, msg_data))
            rep_msg = pMsg.data_ack_msg(self.id, r_id)
        elif msg_typ == pMsgTyp.data_ack:
            # ? put on some special queue
            # ? advance some counter or something in the RemoteHost object
            if VERBOSE:
                print("Received ACK for recieving data from me")
        elif msg_typ == pMsgTyp.echo_request:
            if len(msg_data) > 0:
                rep_m = pMsg.echo_repl_msg(self.id, r_id, msg_data)
            else:
                peers = list(map(str, self.list_connected_peers()))
                peers = ", ".join(peers)
                rep_m = pMsg.echo_repl_msg(self.id, r_id, peers)
            self.peers[r_id].send_bytes(rep_m)
        elif msg_typ == pMsgTyp.echo_reply:
            if VERBOSE:
                print("Received ECHO reply from",
                      r_id, "with message: ", msg_data)

    def run(self):
        """ The run method. Runs until request_stop is called. """
        # TODO add some checks for time since last revieved
        while self.running:
            # print(
            #    ">>> running - connected peers:", self.list_connected_peers(),
            # )
            if self.rr_selector != None:
                events = self.rr_selector.select(timeout=2)
                for key, mask in events:
                    print("initial run")
                    # The listening socket is registered on our id
                    if key.data == self.id:
                        self.accept_con(key.fileobj)
                    # all other ids are remote connections
                    else:
                        self.read_con(key.data, key.fileobj)
                self.init_con_all()
                time.sleep(random.random() * 0.1)  # 0-0.1 s

    def request_stop(self):
        """ Set the running boolean flag to false casing the thread to exit on completing the current loop"""
        self.running = False

    def num_connection(self):
        return len(self.list_connected_peers())
        # return len(self.peers)

    def list_connected_peers(self):
        c_p = []
        # print(self.peers.values())
        for peer in self.peers.values():
            # print(peer)
            # print(peer.is_active)
            if peer.is_active:
                c_p.append(peer.rem_id)
        return c_p

    def send_msg(self, message: str, send_to: int = None) -> list:
        """ Send message\n
            Does nothing if specified send_to id is not connected\n
            If send_to is None the message is broadcast to all connected writers\n
            @returns list of ids to which the message was succesfully sent

            Send procedure
            1. Send a single message with type Data
            2. Wait for data acknowledge
            3. confirm successfull send
            """
        print("broadcast")
        if send_to is None:
            print("send_to None")
            id_list = []
            # print(">", self.send_msg.__name__, "Broadcasting")
            for rem_id in self.peers:
                if self.peers[rem_id].is_active:
                    try:
                        data = pMsg.data_msg(self.id, rem_id, message)
                        print(">", "Sending: ", data, " to id: ", rem_id)
                        print(">", "Connection:", self.peers[rem_id])
                        
                        # TODO: you dont work
                        self.peers[rem_id].send_bytes(data)

                        for p in self.peers.values():
                            print(p)
                        # TODO Listen for Acks???
                        id_list.append(rem_id)
                    except Exception as e:
                        if DEBUG:
                            print(linebreak)
                            print(">!!", "Failed to send to id: ", rem_id)
                            print(">!!", "Whith exception: ", type(e), e)
                        continue
            return id_list
        else:
            print("send_to", send_to)
            if self.peers[send_to].is_active:
                try:
                    data = pMsg.data_msg(self.id, send_to, message)
                    # print(">", "Sending: ", data, " to id: ", s)
                    # print(">", "Connection:", self.peers[s])
                    self.peers[send_to].send_bytes(data)
                    # TODO Listen for Acks???
                    return [send_to]
                except Exception as e:
                    if DEBUG:
                        print(linebreak)
                        print(">!!", "Failed to send to id: ", send_to)
            return []

    def recv_msg(self, recv_from: int = None) -> list:
        """ returns a list of tuples of ([id]: int, [msg]: string) """
        if recv_from is None:
            # return all messages
            with self.msg_lock:
                tmpl = self.msg_queue.copy()
                self.msg_queue.clear()
            return tmpl
        else:
            # search through msg_queue and return what fits with recv_from
            with self.msg_lock:
                rl = [(i, m) for i, m in self.msg_queue if i == recv_from]
                for m in rl:
                    self.msg_queue.remove(m)
            return rl


def main_1():
    r"""
    In order to test this. Run in two different consoles
    cd C:\Users\thors\Documents\GitHub\Lightweight-Blockchain
    .venv\Scripts\activate.bat
    src\protocom.py -myID 1
    src\protocom.py -myID 2
    src\protocom.py -myID 3
    src\protocom.py -myID 4
    """
    ap = argparse.ArgumentParser()
    # ap.add_argument('-file', help='input data file (default stdin)')
    # ap.add_argument('configfile', nargs='?', type=argparse.FileType('r'),
    #               default=sys.stdin, help='input data file (default stdin)')
    ap.add_argument("-me", default=1, type=int,
                    help="ID fyrir skrifara, mandatory")
    a = ap.parse_args()
    print(sys.argv[0], "me:", a.me)
    # print(sys.argv[0], "config: ", a.configfile, "MyID:", a.myID)
    print()

    # read_data = a.configfile.read()
    # test_data = json.loads(read_data)

    # secret used to verify when connecting
    # test_conf = {"active_writer_set": {}, "secret": "42"}
    # test_conf["active_writer_set"][0] = {"ip": "127.0.0.1", "port": 15000}
    # test_conf["active_writer_set"][1] = {"ip": "127.0.0.1", "port": 15001}
    # test_conf["active_writer_set"][2] = {"ip": "127.0.0.1", "port": 15002}
    # test_conf["active_writer_set"][3] = {"ip": "127.0.0.1", "port": 15003}
    # test_conf["active_writer_set"][4] = {"ip": "127.0.0.1", "port": 15004}

    # using
    with open("config.json", "r") as f:
        test_conf = json.load(f)

    print(repr(test_conf["active_writer_set"]))
    num_writers = len(test_conf["active_writer_set"])
    pc = ProtoCom(a.me, test_conf)

    # time.sleep(2 + random.random() * 2)

    pc.start()
    # make the thread do something in a loop
    i = 0
    time_to_connect = 60
    while pc.num_connection() < 1 and i < time_to_connect:
        time.sleep(1)
        i += 1

    # return

    time.sleep(2)
    success_msg = 0
    success_send = 0
    if pc.num_connection() == num_writers - 1:
        for i in range(10):
            print(linebreak)
            print(">> Test: ", i)
            # send # None means broadcast
            s = pc.send_msg(message="Hello world! : " + str(i), send_to=None)
            success_send += len(s)
            time.sleep(3)
            # receive
            r = pc.recv_msg()
            if len(r) == 0:
                time.sleep(4)
            else:
                success_msg += len(r)
                print(">> Received: ", r)
            time.sleep(1)
            # something / anything
    # succesfull should be (len(conf["writerlist"])-1) * 10 [num messages]
    print(linebreak)
    print(">> Number of succesfull messages sent    : ", success_send)
    print(">> Number of succesfull messages received: ", success_msg)
    print(linebreak)
    pc.request_stop()
    pc.join()
    del pc
    input()


if __name__ == "__main__":
    main_1()
