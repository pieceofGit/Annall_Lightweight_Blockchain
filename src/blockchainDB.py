
"""Local Copy of the Blockchain module implementing a local database abstraction."""

import os
import sqlite3
from sqlite3 import Error
import json

import interfaces
from interfaces import verbose_print

class BlockchainDB(interfaces.BlockChainEngine):
    """ The Database engine operating the raw blockchain
        Only the protocol engine can add to the chain
        More entities probably need read access.
    """

    #def __init__(self, dbconnection):
    
    def __init__(self, db_path : str = ":memory:"):
        ## Missing conditionals and exceptions
        self.db_path = db_path
        self.length = 0           # really a sequence number as primary key
        self.db_connection = sqlite3.connect(db_path, check_same_thread=False) # TODO: How can we circumvent check_same_thread?
        self.cursor = self.db_connection.cursor()
        self.initilize_table()
        print("DB: Local Blockchain ready for use")

    def __del__(self):
        # Missing conditionals and exceptions
        self.db_connection.commit()    # flushes transactions to disk
        self.db_connection.close()
        print("DB closed")

    def initilize_table(self):
        #TODO treat the case when the DB exists, and we want to continue.
        self.create_table()

    def create_table(self):

        drop_chain_table = """DROP TABLE IF EXISTS chain
        """

        create_chain_table = """CREATE TABLE IF NOT EXISTS chain (
            round integer PRIMARY KEY,
            prevHash string NOT NULL,
            writerID integer NOT NULL,
            coordinatorID integer NOT NULL,
            payload string,
            winningNumber integer NOT NULL,
            writerSignature string NOT NULL,
            timestamp integer NOT NULL,
            hash string NOT NULL
        );"""

        try:
            self.cursor.execute(drop_chain_table)
            self.cursor.execute(create_chain_table)
            self.db_connection.commit()
        except Exception as e:
            print("Error creating chain table ", e)
            #raise e

    def insert_block(
        self, block_id, block, overwrite=False
    ):  # needs defnintion of a block if to be used
        assert isinstance(block_id, int)    # The round
        assert isinstance(block[0], str)    # prevHash
        assert isinstance(block[1], int)    # writerID
        assert isinstance(block[2], int)    # coordinatorID
        assert isinstance(block[3], str)    # payload
        assert isinstance(block[4], int)    # winningNumber
        assert isinstance(block[5], str)    # writerSignature
        assert isinstance(block[6], int)    # timestamp
        assert isinstance(block[7], str)    # hash

        ## TODO: Remove DELETE = this is a blockchain, nothing should be deleted.
        if block[3] == "arbitrarypayload":  # Do not write into chain if empty message
            # TODO: Figure out what and why this is here = looks like crap
            return
        verbose_print(f"[CREATE BLOCK] added block with block id {block_id} and block {block}")
        try:
            if overwrite:
                self.cursor.execute(f"DELETE FROM chain WHERE round == {block_id}")
            # self.cursor.execute(insertion)
            self.cursor.execute("insert into chain values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [self.length, block[0], block[1], block[2], block[3], block[4], block[5], block[6], block[7]]
            )
            self.db_connection.commit()
            if not overwrite:   # Keep record of length for arbitrarypaylaod rounds
                self.length += 1
            
        except Exception as e:
            print("Error inserting block to chain db ", e)

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

    def dict_factory(self, row):
        d = {}
        for idx, col in enumerate(self.cursor.description):
            if col[0] == "payload" and row[idx] != "genesis block": 
                print(row, idx)
                print("[JSON THE PAYLOAD] ", row[idx])
                d[col[0]] = json.loads(row[idx])    # Loads payload dict to json 
            else: 
                d[col[0]] = row[idx]
        return d

    def read_blocks(self, begin, end=None, col="*", getLastRow=False, read_entire_chain=False):
        """ Retrieve blocks with from and including start to end
            If end is None, retrieve only the one block
            Returns a list of blocks retrieved

            What if none satisfies?
            What type of exceptions
        """
        assert isinstance(begin, int)
        if end is not None:
            assert isinstance(end, int)

        verbose_print("read_blocks ", begin, end, col, getLastRow, read_entire_chain)
        to_return = []

        if getLastRow:  # If discrepancy between round and length of list because of arbitrarypayload
            # TODO:  remove arbitrarypayload special treatment
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
            # cursor = self.db_connection.cursor()
            retrieved = self.cursor.execute(query)
            to_return = retrieved.fetchall()
        except Exception as e:
            print("Error retrieving blocks from db")
            print(e)
        
        print(f"[RETURN FROM READ BLOCKS] {to_return}")
        return to_return


def __test_localDB():


    # dbpath = r"/src/db/blockchain.db"
    #3connection = sqlite3.connect(os.getcwd() + dbpath)
    #print(connection)
    #print(f"[DIRECTORY PATH] {os.getcwd()+dbpath}")
    #bcdb = BlockChainEngine(connection)
    CWD = os.getcwd()
    db_path = CWD + "/src/db/test_blockchain.db"
    print(f"[DIRECTORY PATH] {db_path}")

    blocks_db = BlockchainDB(db_path)

     
    the_block = ("prevHash", 1, 2, json.dumps({"hello":{"sailor":"the sailor"}}), 0, "writer signature", 0, "the hash")
    # the_block = ("prevHash", 1, 2, json.dumps({"the payload": 1}), 0, "writer signature", "the hash")
    genesis_block = ("0", -1, 0,  "genesis block", 0, "0", -1, "0")
    blocks_db.insert_block(0, genesis_block)
    blocks_db.insert_block(1, the_block)
    blocks_db.insert_block(2, the_block)
    blocks_db.insert_block(3, the_block)
    msg = blocks_db.read_blocks(0, 4)
    print(f"[MESSAGE READ BLOCKS 1-4] The message: {msg}")
    # import time
    # time.sleep(100)
    msg = blocks_db.read_blocks(0, read_entire_chain=True)
    print("READING ENTIRE BLOCKCHAIN", msg, type(msg))
    #to_json = msg[0]["payload"]




if __name__ == "__main__":

    print("Main: Local Blockchain DB - running elementary tests")
    # __test_localDB()
