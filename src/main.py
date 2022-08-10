from operator import concat
import os
import argparse
from threading import Thread
import json
import random
import requests
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
from block import Block
from membershipData import MembershipData
from blockchainDB import BlockchainDB
from nodeAPI import app, NodeAPI, BCDB
# from NodeAPI.nodeAPI import app, NodeAPI, BCDB
# should put here some elementary command line argument processing
# EG. parameters for where the config file is, number of writers (for testing), and rounds
# Define explicitly the paths
RUN_WRITER_API = True   # If the api turns on, then it should be a reader of the blockchain
CWD = os.getcwd()
print("WORKING DIRECTORY: ", os.getcwd())
CONFIG_PATH = f"{CWD}/src"
LOCAL = True    # If True, use local file for private key and separate databases
if LOCAL:
    DB_PATH = f"{CWD}/src"
else:
    DB_PATH = f"{CWD}/src/db"

PRIV_KEY_PATH = f"{CWD}/src"

WRITER_API_PATH = "http://127.0.0.1:8000/"

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
     # Initialize the local database connection
    #   -- this is the local copy of the blockchain
    dbpath = f"{DB_PATH}/test_node_{id}/blockchain.db"
    print("::> Starting up Blockchain DB = using ", dbpath)
    bce = BlockchainDB(dbpath, WRITER_API_PATH)
    print("Local block chain database successfully initialized")
    mem_data = MembershipData(id, CONFIG_PATH, conf_file, WRITER_API_PATH, bce)
    data = mem_data.conf
    if RUN_WRITER_API and id == 3:  # Run the NodeAPI as a thread on a reader
        BCDB[0] = bce   # blockchain db object access for the node API process
        writer_api = NodeAPI(app)
        writer_api_thread = Thread(target=writer_api.run, name="WriterAPIThread")
        writer_api_thread.daemon = True
        writer_api_thread.start()
    with open(f"{CONFIG_PATH}/test_node_{id}/priv_key.json", "r") as f:
        priv_key = json.load(f)
    # Do not start participating until up to date
    print("Database up to date")
    # Start Communication Engine - maintaining the peer-to-peer network of writers
    print("::> Starting up peer-to-peer network engine with id ", id)
    pComm = ProtoCom(id, mem_data)  # Send in config file to protocom
    pComm.daemon = True
    pComm.start()
    print("Peer-to-peer network engine up  and running as:", pComm.name)   
    TCP_IP = mem_data.get_tcp_ip(id)
    TCP_PORT = mem_data.get_tcp_port(id)
    print(f"TCP PORT: {TCP_PORT}")
    print("::> Starting up ClientServer thread")
    # TCPServer: name, IPv4_addr, port, RequestHandlerClass, bcdb
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
    PE = ProtoEngine(id, tuple(keys), pComm, bce, clients, mem_data)
    PE.set_rounds(rounds)
    # Writers set to wait for connecting to until rounds start
    PEthread = Thread(target=PE.run_forever, name="ProtocolEngine")
    PEthread.start()
    print("Protocol Engine up and running as:", PEthread.name)
    # finalization and cleanup
    # PEthread is not a daemon
    PEthread.join() # MainThread awaits here for cleanup
    # Associated daemon threads are killed when the program ends
    
