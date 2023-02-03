
"""Local Copy of the Blockchain module implementing a local database abstraction."""

import os
import sqlite3
import json

import interfaces
from interfaces import verbose_print
from models.block import Block

class BlockchainDB(interfaces.BlockChainEngine):
    """ The Database engine operating the raw blockchain
        Only the protocol engine can add to the chain
        More entities probably need read access.
    """

    #def __init__(self, dbconnection):
    
    def __init__(self, db_path : str = ":memory:"):
        ## Missing conditionals and exceptions
        self.db_path = db_path
        print(db_path)
        self.db_connection = sqlite3.connect(db_path, check_same_thread=False) # TODO: How can we circumvent check_same_thread?
        self.cursor = self.db_connection.cursor()
        self.initilize_table()
        print("DB: Local Blockchain ready for use")
        self.length = self.get_round_number()           # really a sequence number as primary key


    def __del__(self):
        # Missing conditionals and exceptions
        self.db_connection.commit()    # flushes transactions to disk
        self.db_connection.close()
        print("DB closed")

    def initilize_table(self):
        #TODO treat the case when the DB exists, and we want to continue.
        self.create_table()
        # If database exists, set self.length and initialize db

    def truncate_table(self):
        truncate_chain_table = """DELETE FROM chain"""
        try:
            self.cursor.execute(truncate_chain_table)
            self.length = self.get_round_number()
            self.db_connection.commit()
        except Exception as e:
            print("Error truncating chain table ", e)

    def create_table(self):

        # drop_chain_table = """DROP TABLE IF EXISTS chain"""

        create_chain_table = """CREATE TABLE IF NOT EXISTS chain (
            round integer PRIMARY KEY,
            prevHash string NOT NULL,
            writerID integer NOT NULL,
            coordinatorID integer NOT NULL,
            winningNumber integer NOT NULL,
            writerSignature string NOT NULL,
            timestamp integer NOT NULL,
            hash string NOT NULL,
            payload string
        );"""
        try:
            # self.cursor.execute(drop_chain_table)
            self.cursor.execute(create_chain_table)
            self.length = self.get_round_number()
            self.db_connection.commit()
        except Exception as e:
            print("Error creating chain table ", e)
            #raise e

    def insert_block(self, block_id : int, block : Block, overwrite=False ):  
        # TODO: Separate from blockchain length and thus degraded.
        assert isinstance(block_id, int)    # The round of the consensus, not the blockchain length.
        assert isinstance(block, Block)    

        ## TODO: Remove DELETE = this is a blockchain, nothing should be deleted.        
        verbose_print(f"[INSERT BLOCK] added block with block id {block_id} and block {block}")
        try:
            if overwrite:   #TODO: Handle case for round of cancel block.
                self.cursor.execute(f"DELETE FROM chain WHERE round == {block_id}")
                
            self.cursor.execute("insert into chain values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [self.length, block.prev_hash, block.writerID, block.coordinatorID, block.winning_number, block.writer_signature, 
            block.timestamp, block.this_hash, block.payload]
            )
            self.db_connection.commit()
            if not overwrite:   # Keep record of length for arbitrarypaylaod rounds
                self.length += 1
            
        except Exception as e:
            print("Error inserting block to chain db ", e)

    def get_missing_blocks(self, hash: str, dict_form=True):
        """Should return blocks after hash. Returns latest block if equal length"""
        cond_string = f'hash == "{hash}"'
        entry = self.select_entry(cond_string, dict_form=True)
        if entry:
            return self.get_range_of_blocks(begin=entry[0]["round"])
        else:
            # Hash not in blockchain, return full blockchain
            return self.get_blockchain()


    def get_round_number(self):
        try:
            query = "SELECT MAX (round) FROM chain"
            last_round_id_query = self.cursor.execute(query)
            last_round_id = last_round_id_query.fetchall() 
            return last_round_id[0][0] + 1
        except:
            return 0

    def select_entry(self, condition: str, col: str = "*", dict_form=False):
        """ Retrieve block with specific condition
        """
        assert isinstance(condition, str)
        query = f"SELECT {col} FROM chain WHERE {condition}"

        try:
            return self.get_query(query=query, dict_form=dict_form)
        except Exception as e:
            print("Error retrieving blocks from db :", e)

    def dict_factory(self, cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            if col[0] == "payload" and row[idx] != "genesis block": 
                try:
                    d[col[0]] = json.loads(row[idx])    # Loads payload dict to json if json
                except:
                    d[col[0]] = row[idx]
            else:
                d[col[0]] = row[idx]
        return d

    def get_blockchain(self, dict_form=True):
        query = f"SELECT * FROM chain WHERE round >= {0} ORDER BY round"
        return self.get_query(query, dict_form)

    def get_range_of_blocks(self, begin, end=None, col="*", dict_form=True):
        """Returns blocks within given range"""
        assert isinstance(begin ,int)
        if end is not None:
            assert isinstance(end, int)
        if end is None:
            query = f"SELECT {col} FROM chain WHERE round >= {begin} ORDER BY round"
        else:
            query = f"SELECT {col} FROM chain WHERE round >= {begin} AND round <= {end} ORDER BY round"
        return self.get_query(query, dict_form)

    def get_latest_block(self, dict_form=True, col="*"):    # Returns latest_block as list of one tuple or dict
        query = f"SELECT {col} FROM chain WHERE round >= {self.length - 1} ORDER BY round"
        latest_block = self.get_query(query, dict_form)  # Returns list of single dict
        if len(latest_block):
            if dict_form:
                return latest_block[0]
            return latest_block
        return None
    
    def get_blockchain(self, dict_form=True):
        query = f"SELECT * FROM chain WHERE round >= {0} ORDER BY round"
        return self.get_query(query, dict_form)

    def get_query(self, query, dict_form=False):
        """Helper function for all queries"""
        to_return = []
        try: 
            if dict_form:
                self.db_connection.row_factory = self.dict_factory  
            else:
                self.db_connection.row_factory = None
            cursor = self.db_connection.cursor()
            retrieved = cursor.execute(query)
            to_return = retrieved.fetchall()
        except Exception as e:
            verbose_print("Error retrieving blocks from db")
        return to_return

def __test_localDB():

    CWD = os.getcwd()
    db_path = CWD + "/src/testNodes/test_node_3/blockchain.db"
    print(f"[DIRECTORY PATH] {db_path}")

    blocks_db = BlockchainDB(db_path)

     
    the_block = Block("prevHash", 1, 2, 0, "writer signature", 0, "the hash")
    #Block(prev_hash, writerID, coordinatorID, winning_number, signature, timestamp, payload )
    genesis_block = Block("0", 0, 0, 0, "0", 0,  json.dumps({"type": "genesis block"}),)
    second_block = Block("0", 0, 0, 0, "0", 0,  json.dumps({"type": "second block"}),)
    third_block = Block("0", 0, 0, 0, "0", 0,  json.dumps({"type": "third block"}),)
    fourth_block = Block("0", 0, 0, 0, "0", 0,  json.dumps({"type": "fourth block"}),)
    # blocks_db.insert_block(0, genesis_block)
    # blocks_db.insert_block(0, second_block)
    # blocks_db.insert_block(0, third_block)
    # blocks_db.insert_block(0, fourth_block)
    # the_block = Block("correct prevHash", 1, 2, 0, "writer signature", 0, "the hash")
    # blocks_db.insert_block(6, the_block)
    # prev_hash = blocks_db.get_latest_block(dict_form=False, col="hash")[0][0]
    # print(prev_hash == "correct prevHash")
    # print(blocks_db.get_blockchain(True))
    # reading_blocks = len(blocks_db.read_blocks(0, 4))
    # print(f"[MESSAGE READ BLOCKS 1-4] The message: {msg}")
    # import time
    # time.sleep(100)
    # msg_old = len(blocks_db.read_blocks(0, read_entire_chain=True))
    # msg_new = len(blocks_db.get_blockchain(True))
    # print("Blockchain length: ", msg_old==msg_new)
    # #to_json = msg[0]['payload']
    # msg_get_range_old = blocks_db.read_blocks(3000, 10)
    # msg_get_range_new = blocks_db.get_range_of_blocks(1)
    # print("Blockchain: ", msg_get_range_new)
    # blocks_db.truncate_table()
    # prev_hash = blocks_db.get_latest_block(dict_form=False, col="hash")[0][0]
    # print("BEFORE FIRST ROW INSERTION",prev_hash)
    # genesis_block = Block("0", 0, 0, 0, "0", 0,  json.dumps({"type": "genesis block"}),)
    # blocks_db.insert_block(0, genesis_block)
    # blocks_db.insert_block(0, genesis_block)
    # blocks_db.insert_block(0, genesis_block)
    # blocks_db.insert_block(0, genesis_block)
    # msg_get_range_new = blocks_db.get_range_of_blocks(1)
    # prev_hash = blocks_db.get_latest_block(dict_form=False, col="hash")[0][0]
    # print("AFTER FIRST ROW INSERTION",prev_hash)
    print(blocks_db.get_missing_blocks("0xb76ab6fc1949fec304292ef76892002699e9d15fa279b32d085ae43904787380", True))





if __name__ == "__main__":

    print("Main: Local Blockchain DB - running elementary tests")
    __test_localDB()
