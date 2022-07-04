import os
import time
from protoengine import ProtoEngine
import sqlite3
from sqlite3 import Error
import sys
import argparse
from threading import Thread
from interfaces import (
    ProtocolCommunication,
    BlockChainEngine,
    ClientServer,
    ProtocolEngine,
)
from queue import Queue
import json
from tcpserver import TCP_Server, ClientHandler
from protocom import ProtoCom

## should put here some elementary command line argument processing
#
# EG. parameters for where the config file is, number of writers (for testing), and rounds


def run_writer_thread(id: int, rounds: int, writers: int):

    with open("./src/config.json", "r") as f:
        data = json.load(f)

    # Start Communication Engine - maintaining the peer-to-peer network of writers
    print("::> Starting up peer-to-peer network engine")
    pComm = ProtoCom(id, data)
    pComm.daemon = True
    pComm.start()
    print("Peer-to-peer network engine up  and running as:", pComm.name)

    # Initialize database connection
    print("::> Starting up BlockChainEngine")

    dbpath = f"/src/db/blockchain{id}.db"
    connection = sqlite3.connect(os.getcwd() + dbpath, check_same_thread=False)
    bce = BlockChainEngine(connection)
    print("running")

    # Start tcp_server thread for client requests

    if id == 1:
        TCP_IP = data["active_writer_set"][id - 1]["hostname"]
        TCP_PORT = 5005
        print("::> Starting up ClientServer thread")
        clients = TCP_Server("the server", TCP_IP, TCP_PORT, ClientHandler, bce)
        cthread = Thread(target=clients.run, name="ClientServerThread")
        cthread.daemon = True
        cthread.start()
        print("ClientServer up and running as:", cthread.name)
    else:
        TCP_IP = data["active_writer_set"][id - 1]["hostname"]
        TCP_PORT = 6000 + id
        print("::> Starting up ClientServer thread")
        clients = TCP_Server("the server", TCP_IP, TCP_PORT, ClientHandler, bce)
        cthread = Thread(target=clients.run, name="ClientServerThread")
        cthread.daemon = True
        cthread.start()
        print("ClientServer up and running as:", cthread.name)

    # Start protocol engine
    print("::> Starting up ProtocolEngine")
    keys = data["active_writer_set"][id - 1]["priv_key"]
    PE = ProtoEngine(tuple(keys), pComm, bce, clients)
    PE.set_ID(id)
    PE.set_rounds(rounds)
    PE.set_conf(data)

    wlist = []
    for i in range(writers):
        if (i + 1) != id:
            wlist.append(i + 1)
    PE.set_writers(wlist)

    PEthread = Thread(target=PE.run_forever, name="ProtocolEngine")
    # PEthread.start()
    print("Protocol Engine up and running as:", PEthread.name)

    # finalization and cleanup
    # PEthread.join()

    # cthread.join()
    # pComm.join()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-w", default=5, type=int, help="number of writers")
    ap.add_argument(
        "-r", default=10, type=int, help="number of rounds, 0 = run forever"
    )
    a = ap.parse_args()
    no_writers = a.w
    rounds = a.r
    threads = []
    queues = []

    for i in range(no_writers):
        queues.append(Queue())

    for i in range(no_writers):
        thread = Thread(target=run_writer_thread, args=[i + 1, rounds, no_writers])
        threads.append(thread)
        print("Starting new thread")
     
        

    for t in threads:
        t.start()

    for t in threads:
        t.join()

