"""
    Implements class block

"""
import json
import hashlib
from interfaces import (
    i_Block,
    verbose_print,
    vverbose_print,
)


class Block(i_Block):
    '''
    Implementation of a block.
    '''
    def __init__(self, 
                prev_hash : str,
                writerID : int,
                coordinatorID : int,
                winning_number : int,
                writer_signature : str,
                timestamp : int,
                payload : str,
                round=""  # int
                ):
        ## Only invariant is that this_hash should be a valid hash_of the block

        assert isinstance(prev_hash, str)         # prevHash
        assert isinstance(writerID, int)          # writerID
        assert isinstance(coordinatorID, int)     # coordinatorID
        assert isinstance(winning_number, int)    # winningNumber
        assert isinstance(writer_signature, str)  # writerSignature = signs all fields except this_hash
        assert isinstance(timestamp, int)         # timestamp
        assert isinstance(payload, str)           # payload
        if not round == "":
            assert isinstance(round, int)           # payload
            self.round = round

        self.prev_hash = prev_hash
        self.writerID = writerID
        self.coordinatorID = coordinatorID
        self.payload = payload
        self.winning_number = winning_number
        self.writer_signature = writer_signature
        self.timestamp = timestamp
        self.this_hash = self._hash_block()

    def __eq__(self, other):
        a = (
        self.prev_hash == other.prev_hash and
        self.writerID == other.writerID  and
        self.coordinatorID == other.coordinatorID  and
        self.winning_number == other.winning_number  and
        self.writer_signature == other.writer_signature  and
        self.timestamp == other.timestamp  and
        self.this_hash == other.this_hash  and
        self.payload == other.payload )
        return a 
    
    def is_next(self, other):
        ''' returns true if other is the next block following self '''
        return self.this_hash == other.prev_hash

    def set_payload(self, payload):
        ''' edits payload and recreates hash '''
        assert isinstance(payload, str)
        self.payload = payload
        self.this_hash = self._hash_block()
    
    def as_tuple(self):
        ''' returns a tuple representation of the block '''
        return (
            self.prev_hash,
            self.writerID,
            self.coordinatorID,
            self.winning_number,
            self.writer_signature,
            self.timestamp,
            self.this_hash,
            self.payload
        )
        
    @classmethod 
    def from_any(cls, block):
        if isinstance(block, dict):
            return cls.from_dict(block)
        elif isinstance(block, Block):
            return block
        elif isinstance(block, list):
            return cls.from_tuple(tuple(block))
        elif isinstance(block, tuple):
            return cls.from_tuple(block)
        elif isinstance(block, str):
            loaded_block = json.loads(block)
            return cls.from_any(loaded_block)
        

    @classmethod
    def from_json_tuple(cls, json_block: str):
        """Takes in string json, loads, and returns tuple"""
        json_list = json.loads(json_block)
        return cls.from_tuple(tuple(json_list))
    
    @classmethod
    def from_tuple(cls, block_as_tuple : tuple): ## Factory to create a block from a tuple
        (
            prev_hash,
            writerID,
            coordinatorID,
            winning_number,
            writer_signature,
            timestamp,
            this_hash,
            payload
        ) = block_as_tuple
        b = Block(str(prev_hash), int(writerID), int(coordinatorID), int(winning_number), writer_signature, int(timestamp), payload)
        if this_hash == b.this_hash:    # Recreates and compares hash
            return b
        verbose_print("Error: trying to create an inconsistent Block - this_hash does not match")
        return None
    
    @classmethod
    def from_dict(cls, block : dict): ## Factory to create a block from a dict
        
        b = Block(str(block["prevHash"]), int(block["writerID"]), int(block["coordinatorID"]), int(block["winningNumber"]), block["writerSignature"], int(block["timestamp"]), block["payload"], int(block["round"]))
        if block["hash"] == b.this_hash:
            return b
        
        verbose_print("Error: trying to create an inconsistent Block - this_hash does not match")
        return None

    def _hash_block(self):
        '''
        Creates a hash for a given block
        '''
        # create a SHA-256 hash object
        key = hashlib.sha256()

        # The update is feeding the object with bytes-like objects (typically bytes)
        # Using update
        key.update(str(self.prev_hash).encode("utf-8"))
        key.update(str(self.writerID).encode("utf-8"))
        key.update(str(self.coordinatorID).encode("utf-8"))
        key.update(str(self.payload).encode("utf-8"))
        key.update(str(self.winning_number).encode("utf-8"))
        key.update(str(self.writer_signature).encode("utf-8"))
        key.update(str(self.timestamp).encode("utf-8"))
        
        return "0x" + key.hexdigest()

    """ Need to test:
        Create of block =
        Invariant maintained
        from_tuple()
        as_tuple()
    """




if __name__ == "__main__":

    priv_key = (
        102112530386709581147763754450150551811184989910838951048382139732065221861253,
        69262763159099467476945738510463449672430996893716133108303399418455764886583,
        65537
    )


    blockA = Block("prev_hash", 1 , 2 , 3 ,  ":signature:", 9, "Payload" )
    
    blocks = []
    block = Block("prev_hash", 1, 2, 3, ":signature:", 9, "Payload")
    blocks.append(block)
    first_block = block
    prev_block = block
    for i in range(10):
        block = Block(prev_block.this_hash, 1, 2, 3, ":signature:", 9, f"Payload{i}")
        blocks.append(block)
        prev_block = block

    prev_block = first_block
    for b in blocks[1:]:
        print(b.as_tuple())
        print(prev_block.is_next(b))
        prev_block = b

    print(blockA == first_block)
    print(blockA == prev_block)
    print()

    for b in blocks:
        tb = b.as_tuple()
        bback = Block.from_tuple(tb)
        if b != bback:
            print("ERROR")



