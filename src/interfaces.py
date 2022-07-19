## How about having a "def" file that defines the abstract classes of concern
## https://www.python.org/dev/peps/pep-0484/

from threading import Thread, ThreadError
import inspect
#import json
import hashlib
import ast


#__test_interfaces = True
NoneType = type(None)

verbose = True
vverbose = True


def verbose_print(*s):
    if verbose:
        print(" ".join(map(str, s)))


def vverbose_print(*s):
    if vverbose:
        print(" ".join(map(str, s)))


def method_name():
    return inspect.currentframe().f_back.f_code.co_name


class ProtocolCommunication(Thread):
    """ Communicaiton module - responsible for: 
        a) Establishing and maintaining p2p network
        b) All comm related to the consensus protocol
        
        Simple API, send and receive, point-to-point or multi
        
        Implementation should redefine these functions, but honor the semantics

        Semantics:
            --- perhaps elaborate
    """

    def __init__(self, name: str):  # what are the natural arguments
        # # Constructor.
        Thread.__init__(self)
        if name is not None:
            self.name = name

    def send_msg(self, message, sent_to=None):
        # Accepts a message to be sent to "sent_to". If None, then broadcast to all
        # Takes responsibility for delivering the message.
        # Does not block? if so need a way to report the failure to the sender
        """ Accepts a message to be sent to "sent_to". If None, then broadcast to all
        Takes responsibility for delivering the message.
        Does not block? if so need a way to report the failure to the sender 
        
        Args:
            message (binary string): The message to be sent
            sent_to (remote host): destination "host". If None broadcast.

        Returns:
            no return value. 
            Exception if ...
        """
        pass

    def recv_msg(self, recv_from=None):
        # # receives a message from "recv_from". If None from all
        # possible semantics: request to receive the next message from "recv_from"
        #
        # Need to decide - when is the message received - if from all
        # If does not block, how to communicate when a message is available

        # pass

        # def recv_msg(recv_from=None):
        """ ## receives a message from "recv_from". If None from all
        
        possible semantics: request to receive the next message from "recv_from"
        
        Need to decide - when is the message received - if from all
        If does not block, how to communicate when a message is available
        """
        return "ERROR: Not properly implemented"

class i_Block:
    """ Creation and manipulation of a block that goes onto the blockchain.
        An attempt to encapsulate and figure out, what methods are really needed
        
        ## No body other than the protocol engine should need to use any method other than the constructor

        (
            prev_hash
            writerID,
            coordinatorID,
            winning_number,
            writer_signature,
            timestamp,
            this_hash,
            payload, 
        )    

    """

    def __init__(self, 
                prev_hash : str,
                writerID : int,
                coordinatorID : int,
                winning_number : int,
                writer_signature : str,
                timestamp : int,
                payload : str,
                ):

        pass

    #def block_from_tuple
    @classmethod
    def from_tuple(block_as_tuple : tuple):
        ## Creates a block from a tuple.
        pass

    def as_tuple(self):
        """ Returns the content of the block as a tuple 
        """
        return (self.prev_hash, self.writerID, self.coordinatorID, self.winning_number, self.writer_signature, 
                self.timestamp, self.this_hash, self.payload )



class BlockChainEngine:
    """ The Database engine operating the raw blockchain
        Only the protocol engine can add to the chain
        More entities probably need read access.

        loal_name = is nema of the file on the local file system (full path) 
                    The special path name ":memory:" can be provided to connect to a transient in-memory database:
    """

    # def __init__(self, dbconnection):
        ## initializing the database connection
    #    assert dbconnection is not None
    #    self.connection = dbconnection
    #    self.create_table()
    #    self.length = 0
    #    print("DB connection established")

    def __init__(self, db_path : str = ":memory:"):
        pass

    def __del__(self):
        # shutting down the database
        pass

    def create_table(self):
        pass

    def insert_block(
        self, block_id, block, overwrite=False
    ):  # needs defnintion of a block if to be used
        assert isinstance(block_id, int)    # The round
        #assert isinstance(block, i_Block)       

        print(method_name(), " not implemented")
    

    def select_entry(self, condition: str, col: str = "*"):
        """ Retrieve block with specific condition
        """
        # assert isinstance(condition, str)
        # query = f"SELECT {col} FROM chain WHERE {condition}"
        pass

    def read_blocks(self, begin, end=None, col="*", get_last_row=False, read_entire_chain=False):
        """ Retrieve blocks with from and including start to end
            If end is None, retrieve only the one block
            Returns a list of blocks retrieved

            What if none satisfies?
            What type of exceptions
        """
        #assert isinstance(begin, int)
        #assert isinstance(end, (int, NoneType))
        pass


class ClientServer:
    """ Communication with external clients/services, collecting client requests, 
        and queuing them until the the protocolEngine consumes them
        Returns a confirmation to the client when request has been committed
    """

    def __init__(self):  # what are the natural arguments
        pass

    def run_forever(self):
        pass

    def retrieve_request(self):
        # Returns the ´next´client request to be written into the chain, if one exists
        # Does not block. If no request, returns None
        # Request is of the form {request_id, body}
        return None

    def notify_commit(self, request_id: str):
        # Used by protocol server, to notify that request_id has been committed into the chain
        pass


class ProtocolEngine:
    """ Executes the consensus protocol 
        Communincates with protocolCommunication, via RPC to send and receive messages
        Need to determine who blocks and where 
    """

    def __init__(
        self,
        id : int,
        comm: ProtocolCommunication,
        blockchain: BlockChainEngine,
        clients: ClientServer,
    ):
        """ Constructor - 
            Depends on service classes, for a) communication, b) blockchain, and c) client requests
        """
        assert isinstance(id, int)
        assert isinstance(comm, ProtocolCommunication)
        assert isinstance(blockchain, BlockChainEngine)
        assert isinstance(clients, ClientServer)
        self.ID = id
        self.comm = comm
        self.bcdb = blockchain
        self.clients = clients

    def run_forever(self):
        pass

    def run():
        print("ERROR = not implemented")

    def _send_msg(self, type, message, send_to=None):
        # implements a remote procedure call wrt protocolCommuincation
        pass

    def _recv_msg(self, type, recv_from=None):
        pass



# ## what follows does not belong here, is prototyping and testcode
def __test_interfaces():
    """ test code here
    """
    print("Elementary Testing of Interfaces")

    print("Testing creating a ProtocolCommunications")
    pComm = ProtocolCommunication("comm")
    pComm.start()
    print("running")
    print(pComm)


    print("Testing Database")
    import os
#    import sqlite3
    from sqlite3 import Error



    dbpath = r"/src/db/blockchain.db"
    dbpath = os.getcwd() + dbpath
    print(f"[DIRECTORY PATH] {dbpath}")
    bcdb = BlockChainEngine(dbpath)
    # insertion = f'INSERT INTO chain(round,prevHash,writerID,coordinatorID,payload,winningNumber,writerSignature,hash) VALUES({block_id},"{block[0]}",{block[1]},{block[2]},"{block[3]}",{block[4]},"{block[5]}","{block[6]}");'
    import json
    print(json.dumps({"insurance":"john"}))

    #the_block = Block(prev_hash, writerID, coordinatorID, winning_number, signature, timestamp, payload )

    the_block = i_Block("prevHash", 1, 2, 0, "writer signature", 0, json.dumps({"hello":{"sailor":"the sailor"}}),)
   
    genesis_block = i_Block("0", 0, 0, 0, "0", 0, "genesis block",)
    bcdb.insert_block(0, genesis_block)
    bcdb.insert_block(1, the_block)
    bcdb.insert_block(2, the_block)
    bcdb.insert_block(3, the_block)
    msg = bcdb.read_blocks(0, 4)
    print(f"[MESSAGE READ BLOCKS 1-4] The message: {msg}")
    # import time
    # time.sleep(100)
    msg = bcdb.read_blocks(0, read_entire_chain=True)
    print("READING ENTIRE BLOCKCHAIN", msg, type(msg))
    if msg != None:
        to_json = msg[0]['payload']
    # print(type(to_json))
    # print(type(json.loads(to_json)))

    print("Testing ClientServer")
    clients = ClientServer()
    cthread = Thread(target=clients.run_forever)
    cthread.start()
    print("ClientServer up and running in thread:", cthread.name)
    if clients.retrieve_request() is not None:
        print("surprise - client is a real thing")
    else:
        print("nothing to process")
    clients.notify_commit("RID:4")

    print("testing setting up ProtocolEngine")

    PE = ProtocolEngine(1, pComm, bcdb, clients)
    PEthread = Thread(target=PE.run_forever)
    PEthread.start()
    print("Protocol Engine up and running in thread:", PEthread.name)

    pComm.join()
    PEthread.join()
    cthread.join()


if __name__ == "__main__":

    print("Main: Interfaces")
    __test_interfaces()

