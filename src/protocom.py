from p_comm_msg import pMsg, pMsgTyp
#import interfaces
import threading
import socket
import selectors
import sys
import json
import argparse
import time
import random

from interfaces import ( 
    ProtocolCommunication,
    verbose_print, 
    vverbose_print
)
from models.membershipData import MembershipData

VERBOSE = False
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

    def __init__(self, rem_id: int, host: str, port: int, pub_key, is_writer: bool):
        self.rem_id = rem_id
        self.listen_address = (host, port)
        self.pub_key = pub_key
        self.is_active = False
        self.is_writer = is_writer
        # Number of tries to connect to
        self.try_conn = 0
        # time_last is either time since connection tries reach max
        # or since last message received
        self.time_last = time.process_time()
        # socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket: socket.socket() = None
        # self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def connect(self):
        """ Check whether connection tries exceed max\n
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
            verbose_print(f">!! Failed to close socket with exception {e}")
        finally:
            self.is_active = False

    def send_bytes(self, b_msg):
        """ Send bytes over socket """
        if self.socket is not None:
            self.socket.sendall(b_msg)
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
        if byte_length == b"":
            raise Exception(f"> Connection closed. Socket:{self.socket}")
        try:
            length = int.from_bytes(byte_length, "big", signed=False)
        except Exception as e:
            verbose_print(">!! Failed to read length of message")
            return ""
        try:
            b = self.socket.recv(length)
        except Exception as e:
            verbose_print(">!! Failed to read message with:", e)
        decb = b.decode("utf-8")
        return decb

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
        byte_length = r_socket.recv(4)
        vverbose_print("Read length:", byte_length)
        if byte_length == b"":
            raise Exception(f"> Connection closed. Socket:{r_socket}")
        try:
            length = int.from_bytes(byte_length, "big", signed=False)
        except Exception as e:
            verbose_print(">!! Failed to read length of message")
            return ""
        try:
            verbose_print("Reading message")
            b = r_socket.recv(length)
        except Exception as e:
            verbose_print(">!! Failed to read message with:", e)
        decb = b.decode("utf-8")
        return decb

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
                verbose_print("Failed to split message", e)
            tries += 1
        raise Exception("Failed to read C-ACK")

    def read_c_reply(self):
        """@returns ([rem_id],[self_id],[secret], opt []) """
        tries = 0
        while tries < 3:
            try:
                msg = self.read_single_msg()
            except Exception as e:
                verbose_print("Failed to read message:", e)
            # [type], [r_id], [self_id], [secret], optional [something]
            # we cannot unpack because we dont know or assume number of splits
            try:
                tokens = msg.split(pMsg.sep, maxsplit=4)
                if tokens[0] == pMsgTyp.c_reply:
                    return tokens[1:]
            except Exception as e:
                verbose_print("Failed to split message", e)
            tries += 1
        raise Exception("Failed to read C-ACK")

    def read_c_ack(self):
        """@returns ([rem_id],[self_id]) """
        vverbose_print(f"Reading C-ACK message from id: {self.rem_id}")
        tries = 0
        while tries < 3:
            try:
                msg = self.read_single_msg()
            except Exception as e:
                verbose_print("Failed with exception:", e)
                raise e
            # [type], [r_id], [self_id]
            try:
                tokens = msg.split(pMsg.sep, maxsplit=4)
                if tokens[0] == pMsgTyp.c_ack:
                    return tokens[1:]
            except Exception as e:
                verbose_print("Failed to split message", e)
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


class ProtoCom(ProtocolCommunication):
    def __init__(self, self_id: int, mem_data: MembershipData, name: str = "P2P : Protocol communication" ):
        ProtocolCommunication.__init__(
            self, name)
        # set up
        self.id = self_id
        self.mem_data = mem_data
        self.running = True
        self.conn_modulus = 0
        # lock is used to put on to and take off of msg_queue
        self.msg_lock = threading.RLock()
        # Define number of writers to connect to
        self.rr_selector = None
        # set up lists and stuff    
        # dictionary of connected sockets use for storing sockets and stuff
        self.peers = {}
        self.ip = self.mem_data.conf["node_set"][self.id-1]["hostname"]
        self.listen_port = self.mem_data.conf["node_set"][self.id-1]["protocol_port"]
        self.pub_key = self.mem_data.conf["node_set"][self.id-1]["pub_key"]
        # Setup remote_end object for communication with active writers and readers
        self.set_active_nodes()  # ? Node fetches a config where it is not active, thus no ip and listen_port
        verbose_print(f"[IS WRITER] node with id: {self.id} is a writer: {self.mem_data.is_writer}")
        # set up listening socket
        # Making sure to not run this if either are undefined, unless it crashes
        if (self.ip != None) or (self.listen_port != None):
            self.listen_sock = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            # Prevents error Address already in use. Socket not in TIME_WAIT state
            self.listen_sock.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listen_sock.setblocking(False)
            verbose_print(f"Listening on port: {self.listen_port}")
            self.listen_sock.bind(("", self.listen_port))
            # TODO decide what number - lets not decide and k make it big
            self.listen_sock.listen(100)
            # TODO for all sockets conn.setblocking(False) when using selectors
            # ready read selector
            self.rr_selector = selectors.DefaultSelector()
            self.rr_selector.register(
                self.listen_sock, selectors.EVENT_READ, self.id)
            # Received messages are added to this queue and removed when recv_msg() is called
            self.msg_queue = []

    def set_active_nodes(self):
        """Setup RemoteEnd object for all unconnected active writers and readers"""
        try:
            active_node_list = self.mem_data.ma_writer_list + self.mem_data.ma_reader_list
            for i in active_node_list:
                node = self.mem_data.conf["node_set"][i-1]
                if i != self.id and i not in self.peers:    # TODO: Does not handle case for reconnecting writer
                    self.peers[i] = RemoteEnd(
                    node["id"], node["hostname"], node["protocol_port"], node["pub_key"], self.check_if_writer(node["id"])
                    )
            peer_keys = list(self.peers.keys())
            for i in peer_keys:
                if i not in active_node_list:
                    self.peers[i].close(self.rr_selector)
                    self.peers.pop(i)
        except Exception as e:
            print("FAILED IN CONNECT TO ACTIVE NODES", e)
            return
    
    def peers_disconnected(self):
        """Checks for disconnected nodes and adds them to the round disconnect list if they are not in the penalty box."""
        # return False
        for node in self.peers.values():
            if not node.is_active:
                # Do not add node to disconnected_nodes if it is in the penalty box for the current round
                node_in_penalty_box_dict = self.mem_data.penalty_box.get(self.mem_data.get_pub_key_by_id(node.rem_id), None)
                if not node_in_penalty_box_dict and not node.rem_id in self.mem_data.disconnected_nodes:    # Key does not exist in penalty box
                    self.mem_data.disconnected_nodes.append(node.rem_id)
                elif not node_in_penalty_box_dict["in_penalty_box"] and not node.rem_id in self.mem_data.disconnected_nodes:    # Key exists in penalty box but is not in penalty box
                    self.mem_data.disconnected_nodes.append(node.rem_id)
        if len(self.mem_data.disconnected_nodes) > 0:
            return True
        return False

    def check_if_writer(self, id):
        """Returns boolean for if reader or writer node"""
        if id == self.id:
            return self.mem_data.is_writer
        for i in self.mem_data.conf["writer_list"]:
            if i == id:
                return True
        return False

    def accept_con(self, listen_sock: socket.socket):
        """ callback method for listening socket

            Accept procedure
            1. accept from listensock
            2. receive msg. if not C-request try to read again. if verify fails send C-refuse
            3. send C-reply.
            4. wait for C-ack
            5 accept connection
        """
        verbose_print(" Received incoming connection ",
                  self.list_connected_peers())
        in_conn, in_addr = listen_sock.accept()
        in_conn.settimeout(4)  # Only for accepting
        try:
            tokens = RemoteEnd.read_c_request(in_conn)
        except Exception as e:
            verbose_print("Failed to read c-request with exception:", e)
            return
        if len(tokens) == 4:
            verbose_print("Received data: ", tokens[3])
        rem_id, self_id, secret = tokens[0:3]
        rem_id = int(rem_id)
        # Verifies the message by comparing its public key to the message's public key
        if pMsg.verify_con_msg(
            tokens[0:3], self.id, rem_id, self.peers[rem_id].pub_key
        ):
            vverbose_print("Verification Complete")
            vverbose_print(" Received incoming connection from id:", rem_id)
            if not self.peers[rem_id].is_active:
                vverbose_print("Sending verification")
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
                    verbose_print("Failed to send reply", e)
                    in_conn.close() # Closes connection
                    return
                time.sleep(2)
                try:
                    tokens = self.peers[rem_id].read_c_ack()
                    # rem_id, self_id = tokens[0:1]
                    vverbose_print(f"Received c-ack message: {tokens}")
                except Exception as e:
                    verbose_print("Failed to read ack message closing connection:", e)
                    self.peers[rem_id].close(self.rr_selector)
                    return
                try:
                    in_conn.setblocking(False)
                    self.rr_selector.register(
                        in_conn, selectors.EVENT_READ, rem_id)
                    self.peers[rem_id].connect_accept()
                    verbose_print("Accept incoming connection",
                              self.list_connected_peers())
                except Exception as e:
                    verbose_print("Failed to store connection", e)
            else:
                # TODO: send to other connection refused because already have connection
                verbose_print("Already have connection so we close the new one")
                in_conn.close()
        else:
            verbose_print("Verification failed")
            # TODO send refused
            in_conn.close()

    def init_con_all(self):
        """ Attempts to connect to ONE unconnected writer

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
        if len(w_list) == 0:    # Node is Connected to all nodes in network
            self.conn_modulus = 0
            return
        self.conn_modulus += 1
        if self.conn_modulus >= len(w_list):
            self.conn_modulus = 0
        r_id = w_list[self.conn_modulus]    # Selects a node to connect to round robin with modulus
        # for r_id in w_list:
        # NB only connect to those with higher number
        #? Why only connect to those with higher number?
        if r_id > self.id and not self.peers[r_id].is_active:
            vverbose_print(">", "Attempting to connect to id: ", r_id)
            try:
                self.peers[r_id].connect()
                vverbose_print("Connected to id:", r_id)
            except Exception as e:
                vverbose_print(f">!! Failed to connect with exception: {e}")
                self.peers[r_id].close(self.rr_selector)
                return
            try:
                req_msg = pMsg.con_requ_msg(self.id, r_id, self.pub_key)
                self.peers[r_id].send_bytes(req_msg)
            except Exception as e:
                verbose_print(
                        f">!! Failed to send connection request with exception: {e}")
                self.peers[r_id].close(self.rr_selector)
                return
            # time.sleep(1) might as well wait on the socket
            # read_c_reply reads from socket until a read_c_reply message is read
            try:
                repl_msg = self.peers[r_id].read_c_reply()
                vverbose_print("Received verification", repl_msg)
            except Exception as e:
                verbose_print(
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
                self.peers[r_id].socket.setblocking(False)
                self.rr_selector.register(
                    self.peers[r_id].socket, selectors.EVENT_READ, r_id
                )
                self.peers[r_id].connect_accept()
                vverbose_print(">", "Connected to:", r_id)
            else:
                verbose_print(">", "Verification failed. Closing connection")
                self.peers[r_id].close(self.rr_selector)

    def read_con(self, r_id, r_sock):
        """ callback method for remote connection socket\n
            Reads a single message from the socket and puts it on the message queue

            Read procedure
            1. Read a single message
            2. check type. If Data put data on message queue.
            3. send appropriate response
        """
        try:
            msg = self.peers[r_id].read_single_msg()
        except Exception as e:
            verbose_print(">!! ", "Failed to read from socket ", e)
            # Connection is closed. Remove socket
            try:
                self.peers[r_id].close(self.rr_selector)  #TODO: Removing the peer prior from dict, makes this faulty
            except Exception as e:
                verbose_print(">!! ", "Failed to close socket with exception: ", type(e), e)
            return
        if msg == "":
            # we received a bad message (maybe add some error counter)
            # (and close bad connections)
            return
        # [type], [r_id], [self_id], optional [data]
        msg_typ, rem_id, self_id, msg_data = msg.split(pMsg.sep, maxsplit=3)
        """try:
            rem_id = int(rem_id)
            assert rem_id == r_id
            self_id = int(self_id)
            assert self_id == self.id
            # test wether ids match up with expected from connection
        except Exception as e:
            pass """
        # TODO what if msg_type is data_ack ???
        # TODO When receive ECHO request reply with ECHO reply
        #TODO Nothing that seems to stop a node outside of the whitelisted nodes, to join the network
        # if request contains data reply with that data else send list of connected ids
        if msg_typ == pMsgTyp.data:
            with self.msg_lock:
                vverbose_print("Received data from", r_id, ":", msg_data)
                self.msg_queue.append((r_id, msg_data))
            rep_msg = pMsg.data_ack_msg(self.id, r_id)
        elif msg_typ == pMsgTyp.data_ack:
            # ? put on some special queue
            # ? advance some counter or something in the RemoteHost object
            vverbose_print("Received ACK for receiving data from me")
        elif msg_typ == pMsgTyp.echo_request:
            if len(msg_data) > 0:
                rep_m = pMsg.echo_repl_msg(self.id, r_id, msg_data)
            else:
                peers = list(map(str, self.list_connected_peers()))
                peers = ", ".join(peers)
                rep_m = pMsg.echo_repl_msg(self.id, r_id, peers)
            self.peers[r_id].send_bytes(rep_m)
        elif msg_typ == pMsgTyp.echo_reply:
            vverbose_print("Received ECHO reply from",
                      r_id, "with message: ", msg_data)

    def run(self):
        """ The run method. Runs until request_stop is called. """
        # TODO add some checks for time since last revieved
        connected_peers = 0
        while self.running:
            if connected_peers != len(self.list_connected_peers()):
                verbose_print(
                ">>> running - connected peers:", self.list_connected_peers(),
                )
                connected_peers = len(self.list_connected_peers())

            if self.rr_selector != None:
                events = self.rr_selector.select(timeout=2)
                for key, mask in events:
                    # The listening socket is registered on our id
                    if key.data == self.id:
                        self.accept_con(key.fileobj)
                    # all other ids are remote connections
                    else:
                        self.read_con(key.data, key.fileobj)
                self.init_con_all() # Connects to unconnected writers
                time.sleep(random.random() * 0.1)  # 0-0.1 s

    def request_stop(self):
        """ Set the running boolean flag to false casing the thread to exit on completing the current loop"""
        self.running = False

    def num_connection(self):
        """Returns number of connected peers"""
        return len(self.list_connected_peers())

    def list_connected_peers(self):
        """Returns a list of node peers"""
        c_p = []
        for peer in self.peers.values():
            if peer.is_active:
                c_p.append(peer.rem_id)
        return c_p
    
    def send_msg_to_remote_end(self, rem_id, message, send_to_readers): 
        # Send message to single remote end
        if not send_to_readers and not self.peers[rem_id].is_writer:    
            return  # Message is not for reader
        data = pMsg.data_msg(self.id, rem_id, message)
        vverbose_print(">", "Sending: ", data, " to id: ", rem_id)
        vverbose_print(">", "Connection:", self.peers[rem_id])
        self.peers[rem_id].send_bytes(data)

    def send_msg(self, message: str, send_to: int = None, send_to_readers: bool = None) -> list:
        """ Send message\n
            Does nothing if specified send_to id is not connected\n
            If send_to is None the message is broadcast to all connected writers\n
            @returns list of ids to which the message was succesfully sent

            Send procedure
            1. Send a single message with type Data
            2. Wait for data acknowledge
            3. confirm successful send
            """
        if send_to is None: # Broadcast message
            
            id_list = []
            for rem_id in self.peers:
                if self.peers[rem_id].is_active:
                    try:
                        self.send_msg_to_remote_end(rem_id, message, send_to_readers)
                        id_list.append(rem_id)
                    except Exception as e:
                        verbose_print(">!!", "Failed to send to id: ", rem_id, "With exception: ", type(e), e)
                        continue
                vverbose_print("Sent message to", id_list, "with message:", message, "is_active: ", self.peers[rem_id].is_active)
            return id_list
        else:
            if self.peers[send_to].is_active:
                try:
                    data = pMsg.data_msg(self.id, send_to, message)
                    self.peers[send_to].send_bytes(data)
                    return [send_to]
                except Exception as e:
                    verbose_print(">!!", "Failed to send to id: ", send_to)
            return [] # TODO: should this not be [sent_to]
 
    def recv_msg(self, recv_from: int = None) -> list:
        """ returns a list of tuples of ([id]: int, [msg]: string) """
        # return all messages
        if recv_from is None:
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


def test_protocom_1():
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

    # using
    with open("./src/config-local.json", "r") as f:
        test_conf = json.load(f)    #TODO: The test is broken with the changes

    print(repr(test_conf["node_set"]))
    num_writers = len(test_conf["node_set"])
    pc = ProtoCom(a.me, test_conf)
    pc.start()
    
    input("Connectivity test. Hit any key to progress")
    
    print("Testing some elementary send and recieve")
    
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
    input("Message exchange done. Hit any key to progress")


if __name__ == "__main__":
    test_protocom_1()
