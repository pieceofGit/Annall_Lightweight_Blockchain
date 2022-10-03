import os
import argparse
from threading import Thread
import json
## Own modules imported
from protoengine import ProtoEngine
from interfaces import (
    #BlockChainEngine,
    #ClientServer,
    verbose_print
)
from tcpserver import TCP_Server, ClientHandler
from protocom import ProtoCom
from blockchainDB import BlockchainDB
# from annallWriterAPI import app, WriterAPI, BCDB, MEM_DATA
from membershipData import MembershipData
# from WriterAPI.annallWriterAPI import app, WriterAPI, BCDB
# should put here some elementary command line argument processing
# EG. parameters for where the config file is, number of writers (for testing), and rounds
# Define explicitly the paths
RUN_WRITER_API = True   # If the api turns on, then it should be a reader of the blockchain
CWD = os.getcwd()
print("WORKING DIRECTORY: ", os.getcwd())
CONFIG_PATH = f"{CWD}/src/"
DB_PATH = f"{CWD}/src"
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
    ap.add_argument("-conf", default="config-remote.json", type=str, help="config file for writers")
    ap.add_argument("-privKey", default="priv_key.json", type=str, help="private key file for writer under /src")
    ap.add_argument("-writerApiPath", default="http://127.0.0.1:8000/", type=str, help="private key file for writer under /src")
    a = ap.parse_args()
    id = a.myID
    rounds = a.r
    config_file = a.conf
    priv_key = a.privKey
    writer_api_path = a.writerApiPath
    verbose_print("[ID]", id, " [ROUNDS]", rounds)
     # Initialize the local database connection
    #   -- this is the local copy of the blockchain
    dbpath = f"{DB_PATH}/test_node_{id}/blockchain.db"
    print("::> Starting up Blockchain DB = using ", dbpath)
    bce = BlockchainDB(dbpath)
    print("Local block chain database successfully initialized")
    mem_data = MembershipData(id, CONFIG_PATH, config_file, writer_api_path, bce)
    # MEM_DATA[0] = mem_data
    # if RUN_WRITER_API and id == 1:  # Run the WriterAPI as a thread on a reader
    #     # The writer api needs access to the blockchain database for reading
    #     IS_WRITER_API = True
    #     BCDB[0] = bce
    #     writer_api = WriterAPI(app)
    #     writer_api_thread = Thread(target=writer_api.run, name="WriterAPIThread")
    #     writer_api_thread.daemon = True
    #     writer_api_thread.start()
    
    with open(f"{CONFIG_PATH}/test_node_{id}/priv_key.json", "r") as f:
        priv_key = json.load(f)
        keys = priv_key["priv_key"]

    # Start Communication Engine - maintaining the peer-to-peer network of writers
    print("::> Starting up peer-to-peer network engine with id ", id)
    pComm = ProtoCom(id, mem_data)
    pComm.daemon = True
    pComm.start()
    print("Peer-to-peer network engine up  and running as:", pComm.name)
    
    verbose_print("THE ID: ", id)
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
    # PE.set_conf(data)
    # Writers set to wait for connecting to until rounds start
    # PE.set_writers(data["writer_list"])
    # PE.set_readers(data["reader_list"])

    PEthread = Thread(target=PE.run_forever, name="ProtocolEngine")
    PEthread.start()
    print("Protocol Engine up and running as:", PEthread.name)
    # finalization and cleanup
    # PEthread is not a daemon
    PEthread.join() # MainThread awaits here for cleanup
    # Associated daemon threads are killed when the program ends
    
