import os
from protoengine import ProtoEngine
import sqlite3
import argparse
from threading import Thread
from interfaces import (
    BlockChainEngine,
    ClientServer,
)
import json
from tcpserver import TCP_Server, ClientHandler
from protocom import ProtoCom
import random

NUM_WRITERS = 2 # Can be 1-5. Starts up writers from config file
# should put here some elementary command line argument processing
# EG. parameters for where the config file is, number of writers (for testing), and rounds

if __name__ == "__main__":

    ap = argparse.ArgumentParser()
    # ap.add_argument('-file', help='input data file (default stdin)')
    """ap.add_argument(
       "configfile",
        nargs="?",
        type=argparse.FileType("r"),
        default=src/,
        help="input data file (default stdin)",
    )"""
    ap.add_argument("-myID", default=0, type=int,
                    help="ID fyrir skrifara, mandatory")
    ap.add_argument("-r", default=0, type=int, help="number of rounds")
    a = ap.parse_args()
    id = a.myID
    print("THE ID", id)
    rounds = a.r
    # Read config and other init stuff
    with open("./src/config.json", "r") as f:
        data = json.load(f)
    # Start Communication Engine - maintaining the peer-to-peer network of writers
    print("::> Starting up peer-to-peer network engine with id ", id)
    pComm = ProtoCom(id, data, NUM_WRITERS)
    pComm.daemon = True
    pComm.start()
    print("Peer-to-peer network engine up  and running as:", pComm.name)
    # Initialize database connection
    print("::> Starting up BlockChainEngine")
    dbpath = f"/src/db/blockchain{id}.db"
    print("Should print here")
    print("The os ", os.getcwd())
    connection = sqlite3.connect(os.getcwd() + dbpath, check_same_thread=False)
    print(connection)
    print(f"[DIRECTORY PATH] in main, path to db: {os.getcwd()+dbpath}")
    bce = BlockChainEngine(connection)

    print("running")
    # Start tcp_server thread for client requests
    # Since it selects a port on the computer, with a hard-coded TCP port, it can only start one 


    # if id == 1 or id == 2 or id == 3:
    print("THE ID IS 1. THE ID: ", id)
    # See config.json for active_writer_set
    TCP_IP = data["active_writer_set"][id - 1]["hostname"]
    # TCP_PORT = 5005 + id
    TCP_PORT = 5005 + id + random.randint(0,30)
    print(F"TCP PORT: {TCP_PORT}")
    print("::> Starting up ClientServer thread")
    # TCPServer: name, IPv4_addr, port, RequestHandlerClass, bcdb,
    clients = TCP_Server("the server", TCP_IP, TCP_PORT, ClientHandler, bce)
    # Socket listening to events
    # The Client Handler thread
    cthread = Thread(target=clients.run, name="ClientServerThread")
    cthread.daemon = True
    cthread.start()
    print("ClientServer up and running as:", cthread.name)
    # else:
    #     print("::> Starting up ClientServer thread")
    #     clients = ClientServer()
    #     cthread = Thread(target=clients.run_forever, name="ClientServerThread"+ str(id))
    #     cthread.daemon = True
    #     cthread.start()
    #     print("ClientServer up and running as:", cthread.name)

    # Start protocol engine
    print("::> Starting up BlockChainEngine")
    keys = data["active_writer_set"][id - 1]["priv_key"]
    PE = ProtoEngine(tuple(keys), pComm, bce, clients)
    PE.set_ID(id)
    PE.set_rounds(rounds)
    PE.set_conf(data)

    wlist = []
    
    # for i in range(len(data["active_writer_set"])):
    for i in range(NUM_WRITERS):
        if (i + 1) != id:
            wlist.append(i)
    PE.set_writers(wlist)

    PEthread = Thread(target=PE.run_forever, name="ProtocolEngine")
    PEthread.start()
    print("Protocol Engine up and running as:", PEthread.name)
    # bce.__del__()
    # finalization and cleanup
    PEthread.join()
    cthread.join()
    pComm.join()

    # finalization and cleanup
