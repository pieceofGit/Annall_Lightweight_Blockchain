
"""Local Copy of the Blockchain module implementing a local database abstraction."""

import os
import sqlite3
from sqlite3 import Error
import json

import interfaces
from interfaces import verbose_print
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

    def insert_block(self, block_id : int, block : Block, overwrite=False ):  
    
        assert isinstance(block_id, int)    # The round
        assert isinstance(block, Block)    

        ## TODO: Remove DELETE = this is a blockchain, nothing should be deleted.
        
        if block.payload == "arbitrarypayload":  # Do not write into chain if empty message
            # TODO: Figure out what and why this is here = looks like crap
            return
        verbose_print(f"[INSERT BLOCK] added block with block id {block_id} and block {block}")
        # insertion = f'INSERT INTO chain(round,prevHash,writerID,coordinatorID,payload,winningNumber,writerSignature,hash) VALUES({self.length},"{block[0]}",{block[1]},{block[2]},"{block[3]}",{block[4]},"{block[5]}","{block[6]}");'
        try:
            if overwrite:
                self.cursor.execute(f"DELETE FROM chain WHERE round == {block_id}")
           
            self.cursor.execute("insert into chain values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            #[self.length, self.prev_hash, self.writerID, self.coordinatorID, self.winning_number, self.writer_signature,
            #    self.timestamp, self.this_hash, self.payload]
            [self.length, block.prev_hash, block.writerID, block.coordinatorID, block.winning_number, block.writer_signature,
            block.timestamp, block.this_hash, block.payload]
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
            cursor = self.db_connection.cursor()
            retrieved = cursor.execute(query)
            to_return = retrieved.fetchall()
        except Exception as e:
            print("Error retrieving blocks from db")
            print(e)
        
        print(f"[RETURN FROM READ BLOCKS] {to_return}")
        return to_return


def __test_localDB():

    CWD = os.getcwd()
    db_path = CWD + "/src/db/test_blockchain.db"
    print(f"[DIRECTORY PATH] {db_path}")

    blocks_db = BlockchainDB(db_path)

     
    the_block = Block("prevHash", 1, 2, 0, "writer signature", 0, "the hash")
    # the_block = ("prevHash", 1, 2, json.dumps({"the payload": 1}), 0, "writer signature", "the hash")

    #Block(prev_hash, writerID, coordinatorID, winning_number, signature, timestamp, payload )
    genesis_block = Block("0", 0, 0, 0, "0", 0,  json.dumps({"type": "genesis block"}),)
    blocks_db.insert_block(0, genesis_block)
    blocks_db.insert_block(1, the_block)
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
    __test_localDB()
