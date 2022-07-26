
"""Local Copy of the Blockchain module implementing a local database abstraction."""

import os
import sqlite3
from sqlite3 import Error
import json

import interfaces
from interfaces import verbose_print, vverbose_print
from block import Block

class BlockchainDB(interfaces.BlockChainEngine):
    """ The Database engine operating the raw blockchain
        Only the protocol engine can add to the chain
        More entities probably need read access.
    """

    #def __init__(self, dbconnection):
    
    def __init__(self, db_path : str = ":memory:"):
        ## Missing conditionals and exceptions
        self.db_path = db_path
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

    def create_table(self):

        # drop_chain_table = """DROP TABLE IF EXISTS chain
        # # """

        create_chain_table = """CREATE TABLE IF NOT EXISTS chain (
            round integer PRIMARY KEY,
            prev_hash string NOT NULL,
            writerID integer NOT NULL,
            coordinatorID integer NOT NULL,
            winning_number integer NOT NULL,
            writer_signature string NOT NULL,
            timestamp integer NOT NULL,
            hash string NOT NULL,
            payload string
        );"""
        try:
            # self.cursor.execute(drop_chain_table)
            self.cursor.execute(create_chain_table)
            self.db_connection.commit()
        except Exception as e:
            print("Error creating chain table ", e)
            #raise e

    def insert_block(self, block_id : int, block : Block, overwrite=False ):  
        # TODO: Separate from blockchain length and thus degraded.
        assert isinstance(block_id, int)    # The round 
        assert isinstance(block, Block)    

        ## TODO: Remove DELETE = this is a blockchain, nothing should be deleted.        
        verbose_print(f"[INSERT BLOCK] added block with block id {block_id} and block {block}")
        try:
            if overwrite:
                self.cursor.execute(f"DELETE FROM chain WHERE round == {block_id}")
            self.cursor.execute("insert into chain values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [self.length, block.prev_hash, block.writerID, block.coordinatorID, block.winning_number, block.writer_signature, 
            block.timestamp, block.this_hash, block.payload]
            )
            self.db_connection.commit()
            if not overwrite:
                self.length += 1
            
        except Exception as e:
            print("Error inserting block to chain db ", e)

    def get_round_number(self):
        try:
            query = "SELECT MAX (round) FROM chain"
            last_round_id_query = self.cursor.execute(query)
            last_round_id = last_round_id_query.fetchall() 
            return last_round_id[0][0] + 1
        except:
            return 0

    def select_entry(self, condition: str, col: str = "*"):
        """ Retrieve block with specific condition
        """
        assert isinstance(condition, str)
        query = f"SELECT {col} FROM chain WHERE {condition}"
        try:
            retrived = self.cursor.execute(query)
        except Exception as e:
            print("Error retriving blocks from db :", e)
       
        return retrived.fetchall()

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

    def get_latest_block(self, dict_form=True, col="*"):    # Returns latest_block as list of one
        query = f"SELECT {col} FROM chain WHERE round >= {self.length - 1} ORDER BY round"
        latest_block = self.get_query(query, dict_form)  # Returns list of single dict
        if len(latest_block):
            return latest_block[0]
        return None

    def get_blockchain(self, dict_form=True):
        query = f"SELECT * FROM chain WHERE round >= {0} ORDER BY round"
        return self.get_query(query, dict_form)

    def get_range_of_blocks(self, begin, end=None, col="*", dict_form=True):
        """ Returns blocks within range """
        assert isinstance(begin ,int)
        if end is not None:
            assert isinstance(end, int)
        if end is None:
            query = f"SELECT {col} FROM chain WHERE round >= {begin} ORDER BY round"
        else:
            query = f"SELECT {col} FROM chain WHERE round >= {begin} AND round <= {end} ORDER BY round"
        return self.get_query(query, dict_form)

    def get_query(self, query, dict_form=False):
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

    def read_blocks(self, begin, end=None, col="*", get_last_row=False, read_entire_chain=False):
        """ Retrieve blocks with from and including start to end
            If end is None, retrieve only the one block
            Returns a list of blocks retrieved

            What if none satisfies?
            What type of exceptions
        """
        assert isinstance(begin ,int)
        if end is not None:
            assert isinstance(end, int)

        verbose_print("read_blocks ", begin, end, col, get_last_row, read_entire_chain)
        to_return = []

        if get_last_row:  # If discrepancy between round and length of list because of arbitrarypayload
            query = f"SELECT {col} FROM chain WHERE round >= {self.length - 1} ORDER BY round"
        elif read_entire_chain:   # Returns a list of tuples for each transaction
            query = f"SELECT * FROM chain WHERE round >= {0} ORDER BY round"
        elif end is None:
            query = f"SELECT {col} FROM chain WHERE round >= {begin} ORDER BY round"
        else:
            query = f"SELECT {col} FROM chain WHERE round >= {begin} AND round <= {end} ORDER BY round"
        try: 
            if read_entire_chain:     # Get back list of dictionary object for each block
                self.db_connection.row_factory = self.dict_factory  
            else:   # Send back list of tuples
                self.db_connection.row_factory = None
            cursor = self.db_connection.cursor()
            retrieved = cursor.execute(query)
            to_return = retrieved.fetchall()
        except Exception as e:
            print("Error retrieving blocks from db")
            print(e)        
        return to_return


def __test_localDB():

    CWD = os.getcwd()
    db_path = CWD + "/src/test_node_5/blockchain.db"
    print(f"[DIRECTORY PATH] {db_path}")

    blocks_db = BlockchainDB(db_path)

     
    the_block = Block("prev_hash", 1, 2, 0, "writer signature", 0, "the hash")
    # the_block = ("prev_hash", 1, 2, json.dumps({"the payload": 1}), 0, "writer signature", "the hash")

    #Block(prev_hash, writerID, coordinatorID, winning_number, signature, timestamp, payload )
    genesis_block = Block("0", 0, 0, 0, "0", 0,  json.dumps({"type": "genesis block"}),)
    blocks_db.insert_block(0, genesis_block)
    # blocks_db.insert_block(1, the_block)
    # blocks_db.insert_block(2, the_block)
    # blocks_db.insert_block(3, the_block)
    # blocks_db.insert_block(4, the_block)
    # blocks_db.insert_block(5, the_block)
    # blocks_db.insert_block(6, the_block)
    # reading_blocks = len(blocks_db.read_blocks(0, 4))
    # print(f"[MESSAGE READ BLOCKS 1-4] The message: {msg}")
    # import time
    # time.sleep(100)
    # msg_old = len(blocks_db.read_blocks(0, read_entire_chain=True))
    # msg_new = len(blocks_db.get_blockchain(True))
    # print("Blockchain length: ", msg_old==msg_new)
    # #to_json = msg[0]['payload']
    # msg_get_range_old = blocks_db.read_blocks(3000, 10)
    msg_get_range_new = blocks_db.get_range_of_blocks(1)
    print("Blockchain: ", msg_get_range_new)
    msg_get_latest_block = blocks_db.get_latest_block(dict_form=False)
    print(msg_get_latest_block, "THE LATEST BLOCK")




if __name__ == "__main__":

    print("Main: Local Blockchain DB - running elementary tests")
    __test_localDB()
