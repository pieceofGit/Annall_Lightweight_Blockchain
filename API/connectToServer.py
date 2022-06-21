# Connection to blockchain writer
import sys
import socket
import time
import json

# secret used to verify when connecting
test_conf = {"writerlist": {}, "secret": "42"}
test_conf["writerlist"][0] = {"ip": "127.0.0.1", "port": 15000}
test_conf["writerlist"][1] = {"ip": "127.0.0.1", "port": 15001}
test_conf["writerlist"][2] = {"ip": "127.0.0.1", "port": 15002}
test_conf["writerlist"][3] = {"ip": "127.0.0.1", "port": 15003}
# test_conf["writerlist"][4] = {"ip": "127.0.0.1", "port": 15004}

class ServerConnection:
    def __init__(self, tcp_port):
        # On initialization, connect to server
        self.TCP_IP = '127.0.0.1'
        self.tcp_port = tcp_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.TCP_IP, self.tcp_port))
    # connection writer to API

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
        print(">", self.read_msg.__name__, "Received message of length:", length)
        if length == 0:
            return ""
        b = self.socket.recv(length)
        return b.decode("utf-8")

    def format_msg(self, msg: str) -> bytes:
        """ Format message to be sent over socket from string to bytes """
        print(">", self.format_msg.__name__, "Length: ", len(msg), "Message: ", msg)
        byte_msg = len(msg).to_bytes(4, "big", signed=False) + bytes(msg, "utf-8")
        print(">", self.format_msg.__name__, "Message in bytes: ", byte_msg)
        return byte_msg

    def verify_msg(self, block):
        """Verifies a block.
        Requires supplying the correct JSON object """
        # JSON: request_type="verify", name, body, hash
        block["request_type"] = "verify"
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


if __name__ == "__main__":
    # Connect as client to writer of ID 1
    print("[INPUT] you can input the TCP Port")
    TCP_IP = '127.0.0.1'
    TCP_PORT = 5019

    if len(sys.argv) > 1:
        TCP_PORT = int(sys.argv[1])
    print("Connecting to :", TCP_IP, ":", TCP_PORT)
    print()
    print()
    name = "TestClient"
    server = ServerConnection(TCP_PORT)
    # Initial handshake
    msg = server.read_msg()
    # msg_0 = data.decode()
    print(f"[MESSAGE RECEIVED BY CLIENT] {msg}")
    msg = json.dumps({"payload_id": 1, "name": name})
    print(f"[MESSAGE TO SERVER] confirmation message who we are: {msg}")
    ack = server.send_msg(msg)  # No ack here
    print(f"[ACK FROM SERVER] {ack}")
    # Send message to blockchain
    msg = json.dumps({"request_type": "block", "name": name, "body": "fjolnir1", "payload_id": 1})
    ack = server.send_msg(msg)
    print(f"[ACK FROM BLOCK ADDED] {ack}")
