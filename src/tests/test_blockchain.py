import pytest
import sys
import os, sys
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add the parent directory to the Python path
sys.path.insert(0, parent_dir)

# print("THE PATH", sys.path)
# sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from models.block import Block
from models.blockchainDB import BlockchainDB

import unittest

class TestBlockchain(unittest.TestCase):
    # Test add blocks and remove range based on round number
    def test_1(self):
        chain = BlockchainDB()
        # b = Block(str(prev_hash), int(writerID), int(coordinatorID), int(winning_number), writer_signature, int(timestamp), payload)
        block = Block("prev_hash", 1, 2, 1, "signature",1,"the_payload")
        chain.insert_block(0, block)
        assert(chain.length == 1)
        chain.remove_blocks(0)
        assert(chain.length == 0)
        chain.remove_blocks(0)
        assert(chain.length == 0)
        chain.insert_block(0, block)
        block.prev_hash = block.this_hash
        chain.insert_block(1, block)
        assert(chain.length == 2)
        chain.remove_blocks(1)
        assert(chain.length == 1)
        chain.remove_blocks(2)
        assert(chain.length == 1)
    
    # Test get block by round number
    def test_2(self):
        chain = BlockchainDB()
        block = Block("prev_hash", 1, 2, 1, "signature",1,"the_payload")
        chain.insert_block(0, block)
        block_hash = chain.get_block_by_round_number(round=chain.length-1, dict_form=False, col="hash")[0][0]
        assert(block_hash == block.this_hash)
        chain.remove_blocks(0)
        block_hash = chain.get_block_by_round_number(round=0, dict_form=False, col="hash")
        assert(block_hash == None)
        chain.insert_block(0, block)
        block_2 = block
        block_2.prev_hash = block.this_hash
        chain.insert_block(1, block_2)
        block_2_hash = chain.get_block_by_round_number(round=0, dict_form=False, col="hash")[0][0]
        assert(block_2_hash == block_2.this_hash)
        block_hash = chain.get_block_by_round_number(round=1, dict_form=False, col="hash")[0][0]
        assert(block_hash == block.this_hash)

    # Test that it generates exactly one genesis block

    # def test_1(self):
    #     chain = BlockchainDB()
    #     assert isinstance(chain.get_genesis_block(), Block)
    #     assert len(chain.blocks) == 1

    # # Test that the genesis block is in the correct format
    # def test_2(self):
    #     chain = BlockchainDB()
    #     genesis_block = chain.get_genesis_block()
    #     assert (
    #         genesis_block.prev_hash == -1
    #         and genesis_block.coordinatorID == -1
    #         and genesis_block.payload == "genesis block"
    #         and genesis_block.writer_signature == -1
    #     )

    # Test that a block is added using the add_block function
    # def test_3(self):
    #     chain = BlockchainDB()
    #     payload = "test payload"
    #     writer_id = 56
    #     coordinator_id = 89
    #     writer_signature = "Test signature"
    #     chain.insert_block(payload, writer_id, writer_signature, coordinator_id)
    #     assert len(chain.blocks) == 1

    # # Test that a block is created correctly using the add_block function
    # def test_4(self):
    #     chain = BlockchainDB()
    #     payload = "test payload"
    #     writer_id = 56
    #     coordinator_id = 89
    #     writer_signature = "Test signature"
    #     chain.add_block(payload, writer_id, writer_signature, coordinator_id)
    #     block = Block(
    #         chain.get_genesis_block().hash,
    #         writer_id,
    #         coordinator_id,
    #         payload,
    #         writer_signature,
    #     )
    #     assert chain.blocks[1].hash == block.hash

    # # Test that hashing is unique
    # def test_5(self):
    #     chain = BlockchainDB()
    #     payload = "test payload"
    #     writer_id = 56
    #     coordinator_id = 89
    #     writer_signature = "Test signature"
    #     chain.add_block(payload, writer_id, writer_signature, coordinator_id)
    #     block = Block(
    #         chain.get_genesis_block().hash, writer_id, 90, payload, writer_signature,
    #     )
    #     assert chain.blocks[1].hash != block.hash

    # # Test that the get_chain_payload function returns correct length
    # def test_6(self):
    #     chain = BlockchainDB()
    #     payload = "test payload"
    #     writer_id = 56
    #     coordinator_id = 89
    #     writer_signature = "Test signature"
    #     for i in range(4):
    #         chain.add_block(payload, writer_id, writer_signature, coordinator_id)
    #     assert len(chain.get_chain_payload()) == 5

    # # Test that hashing is unique if same block added multiple times
    # def test_7(self):
    #     chain = BlockchainDB()
    #     payload = "test payload"
    #     writer_id = 56
    #     coordinator_id = 89
    #     writer_signature = "Test signature"
    #     for i in range(10):
    #         chain.add_block(payload, writer_id, writer_signature, coordinator_id)
    #     for h in chain.get_chain_hash():
    #         assert h.hash != h.prev_hash

if "__main__" == __name__:
    unittest.main()
    
    
    

# def __test_localDB():

#     CWD = os.getcwd()
#     db_path = CWD + "/testNodes/test_node_3/blockchain.db"
#     print(f"[DIRECTORY PATH] {db_path}")

#     blocks_db = BlockchainDB(db_path)
#     the_block = Block("prevHash", 1, 2, 0, "writer signature", 0, "the hash")
#     #Block(prev_hash, writerID, coordinatorID, winning_number, signature, timestamp, payload )
#     genesis_block = Block("0", 0, 0, 0, "0", 0,  json.dumps({"type": "genesis block"}),)
#     second_block = Block("0", 0, 0, 0, "0", 0,  json.dumps({"type": "second block"}),)
#     third_block = Block("0", 0, 0, 0, "0", 0,  json.dumps({"type": "third block"}),)
#     fourth_block = Block("0", 0, 0, 0, "0", 0,  json.dumps({"type": "fourth block"}),)
#     print(blocks_db.remove(3))
#     # blocks_db.insert_block(0, genesis_block)
#     # blocks_db.insert_block(0, second_block)
#     # blocks_db.insert_block(0, third_block)
#     # blocks_db.insert_block(0, fourth_block)
#     # the_block = Block("correct prevHash", 1, 2, 0, "writer signature", 0, "the hash")
#     # blocks_db.insert_block(6, the_block)
#     # prev_hash = blocks_db.get_latest_block(dict_form=False, col="hash")[0][0]
#     # print(prev_hash == "correct prevHash")
#     # print(blocks_db.get_blockchain(True))
#     # reading_blocks = len(blocks_db.read_blocks(0, 4))
#     # print(f"[MESSAGE READ BLOCKS 1-4] The message: {msg}")
#     # import time
#     # time.sleep(100)
#     # msg_old = len(blocks_db.read_blocks(0, read_entire_chain=True))
#     # msg_new = len(blocks_db.get_blockchain(True))
#     # print("Blockchain length: ", msg_old==msg_new)
#     # #to_json = msg[0]['payload']
#     # msg_get_range_old = blocks_db.read_blocks(3000, 10)
#     # msg_get_range_new = blocks_db.get_range_of_blocks(1)
#     # print("Blockchain: ", msg_get_range_new)
#     # blocks_db.truncate_table()
#     # prev_hash = blocks_db.get_latest_block(dict_form=False, col="hash")[0][0]
#     # print("BEFORE FIRST ROW INSERTION",prev_hash)
#     # genesis_block = Block("0", 0, 0, 0, "0", 0,  json.dumps({"type": "genesis block"}),)
#     # blocks_db.insert_block(0, genesis_block)
#     # blocks_db.insert_block(0, genesis_block)
#     # blocks_db.insert_block(0, genesis_block)
#     # blocks_db.insert_block(0, genesis_block)
#     # msg_get_range_new = blocks_db.get_range_of_blocks(1)
#     # prev_hash = blocks_db.get_latest_block(dict_form=False, col="hash")[0][0]
#     # print("AFTER FIRST ROW INSERTION",prev_hash)
#     print(blocks_db.get_missing_blocks("0xb76ab6fc1949fec304292ef76892002699e9d15fa279b32d085ae43904787380", True))





# if __name__ == "__main__":

#     print("Main: Local Blockchain DB - running elementary tests")
#     __test_localDB()
