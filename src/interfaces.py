## How about having a "def" file that defines the abstract classes of concern
## https://www.python.org/dev/peps/pep-0484/

from threading import Thread, ThreadError
import inspect
import time

__test_interfaces = False
NoneType = type(None)

verbose = True
vverbose = False


def verbose_print(*s):
    if verbose:
        print(" ".join(map(str, s)))


def vverbose_print(*s):
    if vverbose:
        print(" ".join(map(str, s)))


def method_name():
    return inspect.currentframe().f_back.f_code.co_name


class ProtocolCommunication(Thread):
    """ Communicaiton module - responsible for all comm related to the consensus protocol
        Implementation should redefine these functions, but honor the semantics
    
        Semantics:
            if not thre
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
        pass

    def recv_msg(self, recv_from=None):
        # # receives a message from "recv_from". If None from all
        # possible semantics: request to receive the next message from "recv_from"
        #
        # Need to decide - when is the message received - if from all
        # If does not block, how to communicate when a message is available
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
        # pass

        # def recv_msg(recv_from=None):
        """ ## receives a message from "recv_from". If None from all
        
        possible semantics: request to receive the next message from "recv_from"
        
        Need to decide - when is the message received - if from all
        If does not block, how to communicate when a message is available
        """
        return "ERROR: Not properly implemented"


class BlockChainEngine:
    """ The Database engine operating the raw blockchain
        Only the protocol engine can add to the chain
        More entities probably need read access.
    """

    def __init__(self, dbconnection):
        ## Missing conditionals and exceptions
        assert dbconnection is not None
        self.connection = dbconnection
        self.create_table()
        print("DB connection established")

    def __del__(self):
        # Missing conditionals and exceptions
        self.connection.commit()
        self.connection.close()  # perhaps this should be out of the class
        print("DB closed")

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
            hash string NOT NULL
        );"""

        try:
            cursor = self.connection.cursor()
            cursor.execute(drop_chain_table)
            cursor.execute(create_chain_table)
        except Exception as e:
            print("Error creating chain table")
            print(e)

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
        assert isinstance(block[6], str)    # hash
        print(f"[CREATE BLOCK] added block with block id {block_id} and block {block}")
        insertion = f'INSERT INTO chain(round,prevHash,writerID,coordinatorID,payload,winningNumber,writerSignature,hash) VALUES({block_id},"{block[0]}",{block[1]},{block[2]},"{block[3]}",{block[4]},"{block[5]}","{block[6]}");'
        try:
            cursor = self.connection.cursor()
            if overwrite:
                cursor.execute(f"DELETE FROM chain WHERE round == {block_id}")
            cursor.execute(insertion)
        except Exception as e:
            print("Error inserting block to chain db")
            print(e)
            print(insertion)

    def select_entry(self, condition: str, col: str = "*"):
        """ Retrieve block with specific condition
        """
        assert isinstance(condition, str)
        query = f"SELECT {col} FROM chain WHERE {condition}"
        try:
            cursor = self.connection.cursor()
            retrived = cursor.execute(query)
        except Exception as e:
            print("Error retriving blocks from db")
            print(e)
        return retrived.fetchall()

    def read_blocks(self, begin, end=None, col="*"):
        """ Retrieve blocks with from and including start to end
            If end is None, retrieve only the one block
            Returns a list of blocks retrieved

            What if none satisfies?
            What type of exceptions
        """
        assert isinstance(begin, int)
        assert isinstance(end, (int, NoneType))
        if end is None:
            query = f"SELECT {col} FROM chain WHERE round >= {begin} ORDER BY round"
        else:
            query = f"SELECT {col} FROM chain WHERE round >= {begin} AND round <= {end} ORDER BY round"
        try:
            cursor = self.connection.cursor()
            retrived = cursor.execute(query)
        except Exception as e:
            print("Error retriving blocks from db")
            print(e)
        return retrived.fetchall()


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
        comm: ProtocolCommunication,
        blockchain: BlockChainEngine,
        clients: ClientServer,
    ):
        """ Constructor - 
            Depends on service classes, for a) communication, b) blockchain, and c) client requests
        """
        assert isinstance(comm, ProtocolCommunication)
        assert isinstance(blockchain, BlockChainEngine)
        assert isinstance(clients, ClientServer)
        self.comm = comm
        self.bcdb = blockchain
        self.clients = clients

    def run_forever(self):
        pass

    def _send_msg(self, type, message, send_to=None):
        # implements a remote procedure call wrt protocolCommuincation
        pass

    def _recv_msg(self, type, recv_from=None):
        pass


### what follows does not belong here, is prototyping and testcode

# ## what follows does not belong here, is prototyping and testcode
if __test_interfaces:
    """ test code here
    """
    print("Elementary Testing of Interfaces")

    print("Testing creating a ProtocolCommunications")
    pComm = ProtocolCommunication("comm")
    pComm.start()
    print("running")

    print("Testing Database")
    import os
    import sqlite3
    from sqlite3 import Error

    dbpath = r"/src/db/blockchain.db"
    connection = sqlite3.connect(os.getcwd() + dbpath)
    print(connection)
    print(f"[DIRECTORY PATH] {os.getcwd()+dbpath}")
    bcdb = BlockChainEngine(connection)
    # insertion = f'INSERT INTO chain(round,prevHash,writerID,coordinatorID,payload,winningNumber,writerSignature,hash) VALUES({block_id},"{block[0]}",{block[1]},{block[2]},"{block[3]}",{block[4]},"{block[5]}","{block[6]}");'
    the_block = ["prevHash", 1, 2, "the payload", 1, "writer signature", "the hash"]
    genesis_block = ("0", 0, 0, "genesis block", 0, "0", "0")
    bcdb.insert_block(0, genesis_block)
    # bcdb.insert_block(1, the_block)
    # bcdb.insert_block(2, the_block)
    # bcdb.insert_block(3, the_block)
    msg = bcdb.read_blocks(0, 4)
    print(f"[MESSAGE READ BLOCKS 1-4] The message: {msg}")
    time.sleep(100)
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


if __name__ == "__main__":

    print("Main: Interfaces")
