import sys
import socket
import time
import json

BUFFER_SIZE = 128
GameOn = 1


# secret used to verify when connecting
test_conf = {"writerlist": {}, "secret": "42"}
test_conf["writerlist"][0] = {"ip": "127.0.0.1", "port": 15000}
test_conf["writerlist"][1] = {"ip": "127.0.0.1", "port": 15001}
test_conf["writerlist"][2] = {"ip": "127.0.0.1", "port": 15002}
test_conf["writerlist"][3] = {"ip": "127.0.0.1", "port": 15003}
# test_conf["writerlist"][4] = {"ip": "127.0.0.1", "port": 15004}


def format_msg(msg: str) -> bytes:
    """ Format message to be sent over socket """
    # bmsg = bytearray()
    # >I = int 4 bytes big endian, s = string (char array)
    # bmsg.append(len(msg + 1).to_bytes(4, "big", signed=False))
    # bmsg.append(bytes(msg, "utf-8"))
    # return bmsg
    print(">", format_msg.__name__, "Length: ", len(msg), "Message: ", msg)
    # b = struct.pack(">I", len(msg)) + bytes(msg, "utf-8")
    b = len(msg).to_bytes(4, "big", signed=False) + bytes(msg, "utf-8")
    print(">", format_msg.__name__, "Message in bytes: ", b)
    return b

def verify_msg(me, rem_id):
        """ Construct verification message """
        return "#".join(
            [str(me), str(rem_id), str(test_conf.get("secret", "Geheimnis"))]
        )


def read_single_msg(socket: socket.socket) -> str:
        """ Read a single message from socket\n
            assumes that socket is ready to read """
        byte_length = socket.recv(4)
        length = int.from_bytes(byte_length, "big", signed=False)
        print(">", read_single_msg.__name__, "Received message of length:", length)
        if length == 0:
            return ""
        b = socket.recv(length)
        return b.decode("utf-8")

def create_event(name):
    try: 
        # type - name - body
        m = input('Enter the next event (request_type, name, text) : ')  # input format Type Name Text - where Each are a single word
        req_type, name, body = m.split(" ")
    except KeyboardInterrupt:
        return json.dumps({ name: {'request_type': 'Error', 'name': 'N/A', 'body': 'Error'}})
    except Exception as e:
        print("ERROR:", type(e), e)
        raise

    event = f"{name}: {m}"
    print("Event: ", event)

    m_format = json.dumps({'request_type': req_type, 'name': name, "body": body, "payload_id": 1})
    return m_format.encode()
    


if __name__ == "__main__":
    # Connect as client to writer of ID 1
    print("[INPUT] you can input the TCP Port")
    TCP_IP = '127.0.0.1'
    TCP_PORT = 5023

    if len(sys.argv) > 1:
        TCP_PORT = int(sys.argv[1])
        
    #server_address = ('127.0.0.1', 5005)
    print("Connecting to :", TCP_IP, ":", TCP_PORT)
    print()
    print()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((TCP_IP, TCP_PORT))
    
    # Initial handshake
    data = sock.recv(BUFFER_SIZE)
    msg = data.decode()
    print("[SERVER MESSAGE] From server :", msg) # Should be: {"Server": "Hello", "Name": name}
    print()
    print()
    d = json.loads(msg)
    name = "TESTclient" #d["Name"]
    print("[SENDING MESSAGE] sending to server name and payload id")
    msg = json.dumps({"name": name, "payload_id": 1})   # Confirmation who we are before loop
    print(f"[MESSAGE TO SERVER] confirmation message who we are: {msg}")
    sock.sendall(msg.encode())

    # msg = verify_msg(1,0)
    print()
    print()
    msg = json.dumps({"request_type": "block", "name": name, "body": "fjolnir", "payload_id": 3})
    print()
    print()

    # bmsg = format_msg(msg)
    print("[SENDING MESSAGE] message for blockchain")
    sock.sendall(msg.encode())

    sock.settimeout(2.0)
    time.sleep(3)
    while True:
        try:
            # msg = read_single_msg(sock)
            data = sock.recv(BUFFER_SIZE)
        except KeyboardInterrupt:
            break
        except socket.timeout as e:
            print("Error: Timeout - remote end hung up")  #, type(e), e.args)
            # break
        
        msg = data.decode()
        print("  -- Invite :", msg)
        
        event = create_event(name)
        sock.sendall(event)
        
        time.sleep(1)  ## perhaps  randomize
