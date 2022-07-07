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
)
from tcpserver import TCP_Server, ClientHandler
from protocom import ProtoCom
from blockchainDB import BlockchainDB


# should put here some elementary command line argument processing
# EG. parameters for where the config file is, number of writers (for testing), and rounds
DEBUG = False   # If true, adds randomization to TCP_PORT == How does that make sense??

# Define explicitly the paths
CWD = os.getcwd()
CONFIG_PATH = f"{CWD}/src"
DB_PATH = f"{CWD}/src/db"

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
    a = ap.parse_args()
    id = a.myID
    rounds = a.r
    conf_file = a.conf
    verbose_print("[ID]", id, " [ROUNDS]", rounds, " [conf]", a.conf)

    # Read config and other init stuff
    with open(f"{CONFIG_PATH}/{conf_file}", "r") as f:
        data = json.load(f)
    
    # Start Communication Engine - maintaining the peer-to-peer network of writers
    print("::> Starting up peer-to-peer network engine with id ", id)
    pComm = ProtoCom(id, data)
    #pCommThread = Thread(target=pComm.run, name="ProtoComThread")   # NOT IN ORIGINAL CODE
    #pCommThread.daemon = True
    #pCommThread.start()
    pComm.daemon = True
    pComm.start()
    print("Peer-to-peer network engine up  and running as:", pComm.name)
    
    # Initialize the local database connection
    #   -- this is the local copy of the blockchain
    dbpath = f"{DB_PATH}/blockchain{id}.db"
    print("::> Starting up Blockchain DB = using ", dbpath)
    bce = BlockchainDB(dbpath)
    print("    Local block chain database successfully initialized")
    verbose_print("   ", bce)
 
 
    # Start tcp_server thread for client requests
    # Since it selects a port on the computer, with a hard-coded TCP port, it can only start one 
    # if id == 1 or id == 2 or id == 3:
    print("THE ID IS 1. THE ID: ", id)
    # See config.json for active_writer_set
    TCP_IP = data["active_writer_set"][id - 1]["hostname"]
    TCP_PORT = 5000 + id 
    if DEBUG:
        TCP_PORT += random.randint(0,30)
    print(F"TCP PORT: {TCP_PORT}")
    print("::> Starting up ClientServer thread")
    # TCPServer: name, IPv4_addr, port, RequestHandlerClass, bcdb,
    clients = TCP_Server("the server", TCP_IP, TCP_PORT, ClientHandler, bce)
    # Socket listening to events
    # The Client Handler thread
    cthread = Thread(target=clients.run, name="TCPServerThread")
    cthread.daemon = True
    cthread.start()
    print("ClientServer up and running as:", cthread.name)
    
    # Start protocol engine
    print("::> Starting up BlockChainEngine")
    keys = data["active_writer_set"][id - 1]["priv_key"]
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
    
