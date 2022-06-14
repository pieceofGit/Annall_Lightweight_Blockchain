import sys
import socket
import time
import json
import argparse

from interfaces import verbose_print, vverbose_print
from protocom import pMsg, pMsgTyp, RemoteEnd

BUFFER_SIZE = 128
GameOn = 1

# secret used to verify when connecting
test_conf = {"writerlist": {}, "secret": "42"}
test_conf["writerlist"][0] = {"ip": "127.0.0.1", "port": 15000}
test_conf["writerlist"][1] = {"ip": "127.0.0.1", "port": 15001}
test_conf["writerlist"][2] = {"ip": "127.0.0.1", "port": 15002}
test_conf["writerlist"][3] = {"ip": "127.0.0.1", "port": 15003}
test_conf["writerlist"][4] = {"ip": "127.0.0.1", "port": 15004}

class mMsg(str):
    pass

def create_event(me, send_to):
    try:
        msg = input(
            "Enter the next event : "
        )  # input format Type Name Text - where Each are a single word
        # t, n, txt = m.split(" ")
    except KeyboardInterrupt:
        return json.dumps({name: {"type": "Error", "name": "N/A", "body": "Error"}})
    except Exception as e:
        print("ERROR:", type(e), e)
        raise

    event = f"{me}#{send_to}#{msg}"
    return pMsg.format_msg(event)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "configfile",
        nargs="?",
        type=argparse.FileType("r"),
        default="../testdata/config.writer",
        help="configuration file (default stdin)",
    )
    ap.add_argument("-me", default=1, type=int, help="ID fyrir skrifara, mandatory")
    ap.add_argument("-v", default=True, type=bool, help="verbose")
    ap.add_argument("-vv", default=False, type=bool, help="Very verbose")
    a = ap.parse_args()

    print("Running")
    verbose_print(sys.argv[0], "config: ", a.configfile, "me:", a.me, a.v, a.vv)
    verbose = a.v
    vverbose = a.vv
    verbose_print("")

    """
    read_data = a.configfile.read()
    config_list_of_peers = json.loads(read_data)
    verbose_print(config_list_of_peers)
    me = a.myID
    host = ''
    port = 0
    list_of_peers = {}
    for peer in config_list_of_peers:
        id = int(peer["id"])
        if id == a.myID:
            host = peer["host"] 
            port = int(peer["port"])
        else:
            paddr = peer["host"], int(peer["port"])
            list_of_peers[id] = paddr

    verbose_print(list_of_peers)
    """

    list_of_peers = {}
    for pid, peer in test_conf["writerlist"].items():
        id = int(pid)
        paddr = peer["ip"], int(peer["port"])
        list_of_peers[id] = paddr

    name = "TESTclient"
    # for pid, address in list_of_peers.items():
    #   if pid != a.me:
    r_pid = 0
    r_address = list_of_peers[r_pid]

    print("Connecting to :", r_address)
    host, port = r_address
    rpeer = RemoteEnd(r_pid, host, port)
    rpeer.connect()
    # s.settimeout(4)

    # Handshake initiate
    # msg = pMsg.verify_msg(a.me,r_pid)
    msg = pMsg.make_msg(pMsgTyp.c_request, a.me, r_pid, data="Geheimnis")
    bmsg = pMsg.format_msg(msg)
    print(bmsg)
    print(pMsg.make_msg(pMsgTyp.c_reply, a.me, r_pid, data="Geheimnis Reply"))
    rpeer.send_bytes(bmsg)
    # s.sendall(bmsg)

    # Handshake complete
    try:
        msg = rpeer.recv_bytes()
        print(msg)
    except KeyboardInterrupt:
        pass
    except socket.timeout as e:
        print("Error: Timeout - remote end hung up")  # , type(e), e.args)
    else:
        while True:
            """try:
                msg = pMsg.read_single_msg(s)
                #data = sock.recv(BUFFER_SIZE)
                print(msg)
            except KeyboardInterrupt:
                break
            except socket.timeout as e:
                print("Error: Timeout - remote end hung up")  #, type(e), e.args)
                break
            """
            # msg = data.decode()
            print("  -- Invite :", msg)

            event = create_event(a.me, r_pid)
            print(event)
            rpeer.send_bytes(event)
            time.sleep(2)

