# Connection to blockchain writer
import sys
import socket
import json
import time

# secret used to verify when connecting
test_conf = {"writerlist": {}, "secret": "42"}
test_conf["writerlist"][0] = {"ip": "127.0.0.1", "protocol_port": 15000}
test_conf["writerlist"][1] = {"ip": "127.0.0.1", "protocol_port": 15001}
test_conf["writerlist"][2] = {"ip": "127.0.0.1", "protocol_port": 15002}
test_conf["writerlist"][3] = {"ip": "127.0.0.1", "protocol_port": 15003}
TEST_SERVER_CONNECTION = False

class ServerConnection:
    def __init__(self, ip_addr=None, tcp_port=None):
        # On initialization, connect to server
        self.TCP_IP = ip_addr  # Linode server
        self.tcp_port = tcp_port    # Not doing port forwarding
        # Try ten times to connect to writer
        self.connect_to_writer()
    def set_port(self, port):
        self.tcp_port = port
    
    def set_ip(self, ip):
        self.TCP_IP = ip

    # connection writer to ClientAPI and retry 
    def connect_to_writer(self):
        running = False
        count = 0
        while not running:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # connect to writer
                self.socket.connect((self.TCP_IP, self.tcp_port))
                # Initial handshake
                msg = self.read_msg() # Server sends back who he is
                # We send back who we are and server sends ACK back
                ack = self.send_msg(json.dumps({"payload_id": 1, "name": "Client"}))
                print(f"Connection with writer established at: {self.TCP_IP}:{self.tcp_port}")   
                running = True
            except Exception as e:
                print("Exception occured: ", e)
                count += 1
                if count == 10:
                    print(f"Tried connecting {count} times to writer")
                    break
                time.sleep(1)

    def send_data_msg(self, msg: str):
        """ Formats message to bytes and sends to server and replies with data"""
        self.socket.sendall(self.format_msg(msg))
        # Wait for acknowledgement and return
        return self.read_data_msg()


    def read_data_msg(self) -> str:
        """ Reads messages from socket while buffer is not empty\n
            assumes that socket is ready to read """
        self.socket.settimeout(3)
        byte_length = self.socket.recv(4)
        self.socket.settimeout(None)
        buffer = 4096
        b_arr = bytearray(byte_length)
        pos = 0
        msg_len = int.from_bytes(byte_length, "big", signed=False)
        while pos < msg_len:
            self.socket.settimeout(3)
            b_arr[pos:pos+buffer] = self.socket.recv(buffer)
            self.socket.settimeout(None)
            pos += buffer
        return bytes(b_arr).decode("utf-8")

    def send_msg(self, msg: str):
        """ Formats message to bytes and sends to server and replies with ACK"""
        self.socket.sendall(self.format_msg(msg))
        # Wait for acknowledgement and return
        return self.read_msg()
    
    def read_msg(self) -> str:
        """ Read a single message from socket\n
            assumes that socket is ready to read """
        byte_length = self.socket.recv(4)
        length = int.from_bytes(byte_length, "big", signed=False)
        # print(">", self.read_msg.__name__, "Received message of length:", length)
        if length == 0:
            return ""
        b = self.socket.recv(length)
        return b.decode("utf-8")

    def format_msg(self, msg: str) -> bytes:
        """ Format message to be sent over socket from string to bytes """
        # verbose_print(">", self.format_msg.__name__, "Length: ", len(msg), "Message: ", msg)
        byte_msg = len(msg).to_bytes(4, "big", signed=False) + bytes(msg, "utf-8")
        # verbose_print(">", self.format_msg.__name__, "Message in bytes: ", byte_msg)
        return byte_msg

    def verify_msg(self, block):
        """Verifies a block.
        Requires supplying the correct JSON object """
        # JSON: request_type="verify", name, body, hash
        try:
            # Send block
            self.send_msg(block)
            # Wait for ack
            ack_msg = self.read_msg()
            if ack_msg["verified"] == True:
                return True
        except Exception as e:
            print("exception", type(e), e)
        return False


if TEST_SERVER_CONNECTION:
    # Connect as client to writer of ID 1
    print("[INPUT] you can input the TCP Port")
    TCP_IP = '127.0.0.1'
    TCP_PORT = 5031

    if len(sys.argv) > 1:
        TCP_PORT = int(sys.argv[1])
    print("Connecting to :", TCP_IP, ":", TCP_PORT)
    print()
    print()
    name = "TestClient"
    server = ServerConnection(TCP_PORT)
    # Initial handshake
    msg = server.read_msg()
    print(f"[MESSAGE RECEIVED BY CLIENT] {msg}")
    msg = json.dumps({"payload_id": 1, "name": name})
    print(f"[MESSAGE TO SERVER] confirmation message who we are: {msg}")
    ack = server.send_msg(msg)  # No ack here
    print(f"[ACK FROM SERVER] {ack}")
    # Send message to blockchain
    msg = json.dumps({"request_type": "block", "name": name, "payload": "fjolnir1", "payload_id": 1})
    ack = server.send_msg(msg)
    print(f"[ACK FROM BLOCK ADDED] {ack}")
    msg = json.dumps({"request_type": "read_chain", "name": name, "payload": "fjolnir1", "payload_id": 1})
    chain = server.send_msg(msg)
    print(chain)
    # Verification message only sent after asking for something
    # msg = server.read_msg()
    # print(f"[MESSAGE VERIFICATION REPLY] {msg}")
    # msg = json.dumps({"request_type": "verify", "name": name, "payload": "fjolnir1", "payload_id": 3})
    # print(server.verify_msg(msg))

