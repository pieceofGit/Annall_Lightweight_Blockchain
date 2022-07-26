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

clean_block = ("prev_hash", 1, 2, json.dumps({"hello":{"sailor":"the sailor"}}), 0, "writer signature", 1223123124134, "the hash")
genesis_block = ("0", 0, 0,  "genesis block", 0, "0", 13413413434, "0")
incorrect_type_block = ("prev_hash", 1, 2, json.dumps({"hello":{"sailor":"the sailor"}}), 0, "writer signature", "1223123124134", "the hash")
missing_field_block = ("prev_hash", 1, 2, json.dumps({"hello":{"sailor":"the sailor"}}), 0, "writer signature", 1223123124134)
non_json_block = ("prev_hash", 1, 2, "string", 0, "writer signature", 1223123124134, "the hash")
bcdb.insert_block(0, genesis_block)
bcdb.insert_block(1, clean_block)
bcdb.insert_block(2, incorrect_type_block)
bcdb.insert_block(3, missing_field_block)
bcdb.insert_block(3, non_json_block)
msg = bcdb.read_blocks(0, 4)
print(f"[MESSAGE READ BLOCKS 1-4] The message: {msg}")
# time.sleep(100)
msg = bcdb.read_blocks(0, read_entire_chain=True)
print("READING ENTIRE BLOCKCHAIN", msg, type(msg))
to_json = msg[0]['payload']
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

import unittest

class TestBlockChainEngine(unittest.TestCase):
    
    def test_insert_block():
        ...
    
    def test_read_blocks():
        ...

    def test_some():
        ...