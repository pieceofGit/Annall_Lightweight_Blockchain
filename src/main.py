from operator import concat
import os
import argparse
from threading import Thread
import json
import random

## Own modules imported
from protoengine import ProtoEngine
from interfaces import (
    #BlockChainEngine,
    #ClientServer,
    verbose_print,
    vverbose_print
)
from tcpserver import TCP_Server, ClientHandler
from protocom import ProtoCom
from blockchainDB import BlockchainDB


# should put here some elementary command line argument processing
# EG. parameters for where the config file is, number of writers (for testing), and rounds
# Define explicitly the paths
CWD = os.getcwd()
CONFIG_PATH = f"{CWD}/src"
LOCAL = True    # If True, use local file for private key and separate databases
if LOCAL:
    DB_PATH = f"{CWD}/src"
else:
    DB_PATH = f"{CWD}/src/db"

PRIV_KEY_PATH = f"{CWD}/src"
if __name__ == "__main__":
    print("MAIN STARTED")
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
    ap.add_argument("-conf", default="config-local.json", type=str, help="config file for writers")
    ap.add_argument("-privKey", default="priv_key.json", type=str, help="private key file for writer under /src")
    a = ap.parse_args()
    id = a.myID
    rounds = a.r
    conf_file = a.conf
    priv_key = a.privKey
    verbose_print("[ID]", id, " [ROUNDS]", rounds, " [conf]", a.conf, " [privKey]", priv_key)
    
    # Read config and other init stuff
    with open(f"{CONFIG_PATH}/{conf_file}", "r") as f:
        data = json.load(f)
    if LOCAL:
        with open(f"{CONFIG_PATH}/test_node_{id}/priv_key.json", "r") as f:
            priv_key = json.load(f)
    
    # Start Communication Engine - maintaining the peer-to-peer network of writers
    print("::> Starting up peer-to-peer network engine with id ", id)
    pComm = ProtoCom(id, data)
    pComm.daemon = True
    pComm.start()
    print("Peer-to-peer network engine up  and running as:", pComm.name)
    
    # Initialize the local database connection
    #   -- this is the local copy of the blockchain
    dbpath = f"{DB_PATH}/test_node_{id}/blockchain.db"
    print("::> Starting up Blockchain DB = using ", dbpath)
    bce = BlockchainDB(dbpath)
    print("Local block chain database successfully initialized")
    verbose_print("THE ID: ", id)
    # See config.json for writer_set
    TCP_IP = data["writer_set"][id - 1]["hostname"]
    TCP_PORT = data["writer_set"][id-1]["client_port"] 
    print(f"TCP PORT: {TCP_PORT}")
    print("::> Starting up ClientServer thread")
    # TCPServer: name, IPv4_addr, port, RequestHandlerClass, bcdb,
    clients = TCP_Server("the server", TCP_IP, TCP_PORT, ClientHandler, bce)    # ClientHandler uses the bce object to read db
    # Socket listening to events
    # The Client Handler thread
    cthread = Thread(target=clients.run, name="TCPServerThread")
    cthread.daemon = True
    cthread.start()
    print("ClientServer up and running as:", cthread.name)
    # Start protocol engine
    print("::> Starting up BlockChainEngine")
    keys = priv_key["priv_key"]
    PE = ProtoEngine(id, tuple(keys), pComm, bce, clients)
    PE.set_rounds(rounds)
    PE.set_conf(data)

    # Writers set to wait for connecting to until rounds start
    ## TODO: What is the point of this?
    wlist = []
    for i in range(data["no_active_writers"]):
        if (i + 1) != id:
            wlist.append(i)
    print(wlist)
    PE.set_writers(wlist)

    PEthread = Thread(target=PE.run_forever, name="ProtocolEngine")
    PEthread.start()
    print("Protocol Engine up and running as:", PEthread.name)
    # finalization and cleanup
    # PEthread is not a daemon
    PEthread.join() # MainThread awaits here for cleanup
    # Associated daemon threads are killed when the program ends
    
