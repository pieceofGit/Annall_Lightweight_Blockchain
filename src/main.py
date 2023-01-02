import os
import argparse
from threading import Thread
import json
## Own modules imported
from protoengine import ProtoEngine
from interfaces import (
    verbose_print
)
from tcp_server import TCP_Server, ClientHandler
from protocom import ProtoCom
from downloader import Downloader
from models.blockchainDB import BlockchainDB
from models.membershipData import MembershipData
CWD = os.getcwd()
CONFIG_PATH = f"{CWD}/src/"
PRIV_KEY_PATH = f"{CWD}/src"

if __name__ == "__main__":
    print("MAIN STARTED")
    ap = argparse.ArgumentParser()
    ap.add_argument("-myID", default=0, type=int,
                    help="ID fyrir skrifara, mandatory")
    ap.add_argument("-r", default=0, type=int, help="number of rounds")
    ap.add_argument("-conf", default="config-remote.json", type=str, help="config file for writers")
    ap.add_argument("-privKey", default="priv_key.json", type=str, help="private key file for writer under /src")
    ap.add_argument("-db", default=None, type=str, help="Set if shared db in docker")
    ap.add_argument("-isWriter", default=True, type=bool, help="Set if shared db in docker")
    
    a = ap.parse_args()
    id = a.myID
    rounds = a.r
    config_file = a.conf
    priv_key = a.privKey
    db_path = a.db
    is_writer = a.isWriter
    verbose_print("[ID]", id, " [ROUNDS]", rounds)
     # Initialize the local database connection
    #   -- this is the local copy of the blockchain
    if not db_path:
        db_path = f"src/testNodes/test_node_{id}/blockchain.db"
    print("::> Starting up Blockchain DB = using ", db_path)
    bce = BlockchainDB(db_path)
    print("Local block chain database successfully initialized")
    mem_data = MembershipData(id, CONFIG_PATH, config_file, bce, is_writer)
    # Fetch blocks until all stored in database to prevent timeout on node activation and the wrong data
    # Tells membershipdata thread to activate node when all data fetched
    downloader = Downloader(mem_data, bce)

    with open(f"{CONFIG_PATH}/testNodes/test_node_{id}/priv_key.json", "r") as f:
        priv_key = json.load(f)
        keys = priv_key["priv_key"]
    # Start Communication Engine - maintaining the peer-to-peer network of writers
    print("::> Starting up peer-to-peer network engine with id ", id)
    pComm = ProtoCom(id, mem_data)
    pComm.daemon = True
    pComm.start()
    print("Peer-to-peer network engine up  and running as:", pComm.name)
    
    verbose_print("THE ID: ", id)
    # Get ip and port to bind to for clients
    TCP_IP = mem_data.get_tcp_ip(id)
    TCP_PORT = mem_data.get_tcp_port(id)
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
    PE = ProtoEngine(id, tuple(keys), pComm, bce, clients, mem_data)
    PE.set_rounds(rounds)

    PEthread = Thread(target=PE.run, name="ProtocolEngine")
    PEthread.start()
    print("Protocol Engine up and running as:", PEthread.name)
    # finalization and cleanup
    # PEthread is not a daemon
    PEthread.join() # MainThread awaits here for cleanup
    # Associated daemon threads are killed when the program ends
    
