
"""Local Copy of the Blockchain module implementing a local database abstraction."""

import os
import sqlite3
import json
import sys
sys.path.insert(0, '..')  # Add the parent directory to the Python path

import interfaces
from interfaces import verbose_print
from models.block import Block

class BlockchainDB(interfaces.BlockChainEngine):
    """ The Database engine operating the raw blockchain
        Only the protocol engine can add to the chain.
    """
    
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
        self.create_table()

    def truncate_table(self):
        truncate_chain_table = """DELETE FROM chain"""
        try:
            self.cursor.execute(truncate_chain_table)
            self.length = self.get_round_number()
            self.db_connection.commit()
        except Exception as e:
            print("Error truncating chain table ", e)

    def create_table(self):
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
            self.cursor.execute(create_chain_table)
            self.length = self.get_round_number()
            self.db_connection.commit()
        except Exception as e:
            print("Error creating chain table ", e)
            
    def remove_blocks(self, round_begin : int):
        """Removes blocks from round_begin and onwards"""
        try:
            self.cursor.execute(f"DELETE FROM chain WHERE round >={round_begin}")
            # Commit the changes
            self.length = self.get_round_number()
            self.db_connection.commit()
            return True
        except:
            return False

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

    def get_block_by_round_number(self, round, dict_form=True, col="*"):    # Returns latest_block as list of one tuple or dict
        query = f"SELECT {col} FROM chain WHERE round == {round} ORDER BY round"
        latest_block = self.get_query(query, dict_form)  # Returns list of single dict
        if len(latest_block):
            if dict_form:
                return latest_block[0]
            return latest_block
        return None
    
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