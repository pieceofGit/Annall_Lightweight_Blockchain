import sys
import socket
import time
import string
import json
import random
import argparse


BUFFER_SIZE = 256
GameOn = 1


def create_event(name: str, req):
    """ Creates event to be sent to the server
        if argument req is None, invites (and waits for) input from console
        Arguments:
            name - string, name of client
            req  - is the request
    """
    if req is None:
        try:
            m = input(
                "Enter the next event : "
            )  # input format Type Name Text - where Each are a single word
            # type, name, body
            t, n, txt = m.split(" ")
        except KeyboardInterrupt:
            return json.dumps({name: {"type": "Error", "name": "N/A", "body": "Error"}})
        except Exception as e:
            print("ERROR:", type(e), e)
            raise
        else:
            event = {name: {"type": t, "name": n, "body": txt}}
    else:
        event = req

    emsg = json.dumps(event)
    return emsg


## add name of host and host sequence number to request


def client_handshake():
    pass


if __name__ == "__main__":

    ap = argparse.ArgumentParser()
    # ap.add_argument('-file', help='input data file (default stdin)')
    ap.add_argument(
        "infile",
        nargs="?",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="input data file (default stdin)",
    )
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
    ap.add_argument("-verbose", default=False, type=bool, help="additional printouts)")
    a = ap.parse_args()

    TCP_IP = a.host
    TCP_PORT = a.port

    if a.verbose:
        print(
            sys.argv[0],
            " infile: ",
            a.infile,
            "host: ",
            a.host,
            "port:",
            a.port,
            "verbose:",
            a.verbose,
        )
        print()

    read_data = a.infile.read()
    test_data = json.loads(read_data)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((TCP_IP, TCP_PORT))

    # Initial handshake
    # data = sock.recv(BUFFER_SIZE)
    # msg = data.decode()
    # print("From server :", msg)  # Should be: {"Server": "Hello", "Name": name}
    # d = json.loads(msg)
    # name = d["Name"]

    # msg = json.dumps({'Client': "Hello", 'Name': name})
    # if a.verbose:
    #     print("     Reply  :", msg)
    # sock.sendall(msg.encode())
    # print(test_data)
    # do service reqest
    for req in test_data:
        if a.verbose:
            print(req)
        try:
            data = sock.recv(BUFFER_SIZE)
        except KeyboardInterrupt:
            break
        except socket.timeout as e:
            print("Error: Timeout - remote end hung up")  # , type(e), e.args)
            break

        msg = data.decode()
        if a.verbose:
            print("  -- Invite :", msg)

        event = create_event("name", req)
        sock.sendall(event.encode())

        time.sleep(random.uniform(1, 5))

