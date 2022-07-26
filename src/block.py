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
                ):
        ## Only invariant is that this_hash should be a valid hash_of the block

        assert isinstance(prev_hash, str)         # prev_hash
        assert isinstance(writerID, int)          # writerID
        assert isinstance(coordinatorID, int)     # coordinatorID
        assert isinstance(winning_number, int)    # winning_number
        assert isinstance(writer_signature, str)  # writer_signature = signs all fields except this_hash
        assert isinstance(timestamp, int)         # timestamp
        assert isinstance(payload, str)           # payload

        self.prev_hash = prev_hash
        self.writerID = writerID
        self.coordinatorID = coordinatorID
        self.payload = payload  #TODO: move payload to be the last field
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
        b = Block(prev_hash, int(writerID), int(coordinatorID), int(winning_number), writer_signature, int(timestamp), payload )
        if this_hash == b.this_hash:
            return b
        
        verbose_print("Error: trying to create an inconsistent Block - this_hash does not match")
        return None

    @classmethod
    def from_dict(cls, d_block : dict): ## Factory to create a block from a dictionary
        b = Block(str(d_block["prev_hash"]), int(d_block["writerID"]), int(d_block["coordinatorID"]), 
            int(d_block["winning_number"]), d_block["writer_signature"], int(d_block["timestamp"]), 
            json.dumps(d_block["payload"]))
        if d_block["hash"] == b.this_hash:
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



