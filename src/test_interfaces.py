from threading import Thread, ThreadError
import inspect
import time
import json
import os
import sqlite3
from sqlite3 import Error
from interfaces import  (
    ProtocolCommunication,
    BlockChainEngine,
    ClientServer,
    ProtocolEngine,
    verbose_print
)
from protoengine import ProtoEngine

print("Testing creating a ProtocolCommunications")
pComm = ProtocolCommunication("comm")
pComm.start()
print("running")

print("Testing Database")
DB_PATH = f"{os.getcwd()}/src/db/test_blockchain.db"
print("[DB DIRECTORY] ",DB_PATH)
connection = sqlite3.connect(DB_PATH)
bcdb = BlockChainEngine(connection)

the_block = ("prevHash", 1, 2, json.dumps({"hello":{"sailor":"the sailor"}}), 0, "writer signature", 1223123124134, "the hash")
genesis_block = ("0", 0, 0,  "genesis block", 0, "0", 13413413434, "0")
bcdb.insert_block(0, genesis_block)
bcdb.insert_block(1, the_block)
bcdb.insert_block(2, the_block)
bcdb.insert_block(3, the_block)
msg = bcdb.read_blocks(0, 4)
print(f"[MESSAGE READ BLOCKS 1-4] The message: {msg}")
# time.sleep(100)
msg = bcdb.read_blocks(0, read_entire_chain=True)
print("READING ENTIRE BLOCKCHAIN", msg, type(msg))
to_json = msg[0]["payload"]
# print(type(to_json))
# print(type(json.loads(to_json)))

# print("Testing ClientServer")
# clients = ClientServer()
# cthread = Thread(target=clients.run_forever)
# cthread.start()
# print("ClientServer up and running in thread:", cthread.name)
# if clients.retrieve_request() is not None:
#     print("surprise - client is a real thing")
# else:
#     print("nothing to process")
# clients.notify_commit("RID:4")

# print("testing setting up ProtocolEngine")

# PE = ProtocolEngine(pComm, bcdb, clients)
# PEthread = Thread(target=PE.run_forever)
# PEthread.start()
# print("Protocol Engine up and running in thread:", PEthread.name)

# pComm.join()
# PEthread.join()
# cthread.join()