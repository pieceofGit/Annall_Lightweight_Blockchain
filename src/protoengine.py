from queue import Queue
import hashlib


from queue import Queue
from threading import Thread
import struct
import time
from datetime import datetime
import ast

import sys
import argparse
import os
import json
from protocom import ProtoCom
from models.membershipData import MembershipData
from tcp_server import TCP_Server, ClientHandler
from blockBroker import BlockBroker
import interfaces
from interfaces import (
    ProtocolCommunication,
    ClientServer,
    ProtocolEngine,
    verbose_print,
    vverbose_print,
)
from models.blockchainDB import BlockchainDB
from models.block import Block

NoneType = type(None)

def bytes_to_long(s: str):
    """Convert a byte string to a long integer (big endian).
    In Python 3.2+, use the native method instead::
        >>> int.from_bytes(s, 'big')
    For instance::
        >>> int.from_bytes(b'\x00P', 'big')
        80
    This is (essentially) the inverse of :func:`long_to_bytes`.
    """
    acc = 0

    unpack = struct.unpack

    length = len(s)
    if length % 4:
        extra = 4 - length % 4
        s = b"\x00" * extra + s
        length = length + extra
    for i in range(0, length, 4):
        acc = (acc << 32) + unpack(">I", s[i : i + 4])[0]
    return acc


def egcd(a, b):
    if a == 0:
        return (b, 0, 1)
    else:
        g, y, x = egcd(b % a, a)
        return (g, x - (b // a) * y, y)


def mod_inverse(a, m):
    g, x, _ = egcd(a, m)
    if g != 1:
        raise Exception("modular inverse does not exist")
    else:
        return x % m


# calculates the hash for a given block
def hash_block(block: tuple):
    '''
    Creates a hash for a given block
    
    Block is a 8 item tuple containing the following attributes:
        prev_hash,
        writerID,
        coordinatorID,
        payload,
        winning_number,
        writer_signature,
        timestamp,
        _ (current hash?)
    '''
    assert isinstance(block, tuple)
    assert len(block) == 8  # Added timestamp
    # create a SHA-256 hash object
    key = hashlib.sha256()

    # Extract these variables from block
    (
        prev_hash,
        writerID,
        coordinatorID,
        payload,
        winning_number,
        writer_signature,
        timestamp,
        _,
    ) = block
    # The update is feeding the object with bytes-like objects (typically bytes)
    # Using update
    key.update(str(prev_hash).encode("utf-8"))
    key.update(str(writerID).encode("utf-8"))
    key.update(str(coordinatorID).encode("utf-8"))
    key.update(str(payload).encode("utf-8"))
    key.update(str(winning_number).encode("utf-8"))
    key.update(str(writer_signature).encode("utf-8"))
    key.update(str(timestamp).encode("utf-8"))
    # 0x + the key hex string
    return "0x" + key.hexdigest()


class ProtoEngine(ProtocolEngine):
    # Executes the consensus protocol
    # Communincates with protocolCommunication, via RPC to send and receive messages
    # Need to determine who blocks and where

    def __init__(
        self,
        id: int, 
        keys: tuple,    
        comm: ProtocolCommunication,
        blockchain: interfaces.BlockChainEngine,
        clients: ClientServer,
        mem_data: MembershipData

    ):  # what are the natural arguments
        assert isinstance(keys, tuple)
        assert len(keys) == 3
        # The interface initiates the following attributes
        ProtocolEngine.__init__(self, id, comm, blockchain, clients)

        self.ID = id
        self.keys = keys    # Private keys
        self.mem_data = mem_data
        self.update_num = 0        
        # Defining e
        self.modulus = 65537
        # For how many rounds the blockchain should run for
        self.rounds = None        
        # Messages in our writer's queue
        self.message_queue = Queue()
        self.latest_block = None
        # maintain a payload
        self.stashed_payload = None
        # PubSub queue and exchange
        self.broker = BlockBroker()        
                    
    def set_rounds(self, round: int):
        ''' A round is a minting of a block, this defines for how many rounds the blockchain runs for'''
        assert isinstance(round, int)
        self.rounds = round

    def sign_payload(self, payload: str):
        # keys of form [p, q, e]
        '''Creates a signature of the payload'''
        assert isinstance(payload, str)
        p, q, e = self.keys
        N = p * q
        d = mod_inverse(e, (p - 1) * (q - 1))
        D = bytes_to_long(payload.encode("utf-8"))
        signature = pow(D, d, N)
        return hex(signature % N)

    def set_writers(self, writers: list):
        for w in writers:
            assert isinstance(w, int)
        self.mem_data.writer_list = writers
    
    def set_readers(self, readers: list):
        for r in readers:
            assert isinstance(r, int)
        self.mem_data.reader_list = readers
    
    def get_timestamp(self):
        # Returns time in Unix epoch time 
        return round(datetime.timestamp(datetime.now()))

    def get_prev_hash(self):
        if self.bcdb.length == 0:
            return str(0)
        else:
            prev_hash = self.bcdb.get_latest_block(dict_form=False, col="hash")[0][0]
            return str(prev_hash)

    def verify_block(self, block: Block):
        '''
        To verify a block both the signature and hash of the block must be correct
        '''
        assert isinstance(block, Block)

        # new_block = Block.from_tuple(block)
        if block is not None:
            writer = block.writerID
            payload = block.payload
            signature = int(block.writer_signature, 16)
            writer_pubkey = self.mem_data.conf["node_set"][int(writer) - 1]["pub_key"]
            D = bytes_to_long(payload.encode("utf-8")) % writer_pubkey
            res = pow(signature, self.keys[2], writer_pubkey)
            res = res % writer_pubkey
            
            # Get the hash based on what is in the block
            # hash = hash_block(block)  - invariant, part of block construction
            signature_correct = res == D
            return signature_correct
        else:
            # Only reason new_block is None is that the hash does not match
            return False ## only reason block was not created


    def broadcast(self, msg_type: str, msg, round: int, send_to_readers=False):
        assert isinstance(msg_type, str)
        assert isinstance(msg, (int, str, list))
        assert isinstance(round, int)
        self._send_msg(round=round, type=msg_type, message=msg, sent_to=None, send_to_readers=send_to_readers)

    def generate_pad(self):
        ''' Generates a number '''
        # TODO: This needs to be changed to use an already generated pad
        assert self.modulus > 0
        x = os.urandom(8)
        number = struct.unpack("Q", x)[0]
        return number % self.modulus

    def verify_round_winner(self, numbers: list, my_number: int):
        """Verifies if the round winner is the writer
        Verifies that all details are correct. 
        """
        assert isinstance(numbers, list)
        assert len(numbers) == 3
        assert isinstance(my_number, int)
        # Calculate the sum to check if we have the correct results
        verified_results = self.calculate_sum(numbers[0])
        # Checking if we are using the same OTP
        same_pad = verified_results[1] == numbers[1]
        # Checking if the use the same winner for the calculation
        same_winner = verified_results[2] == numbers[2]
        # Check if all the entries match up for each
        my_numb_exists = any([my_number == entry[1] for entry in numbers[0]])
        # correct case here would return True, True, True
        return same_pad and same_winner and my_numb_exists

    def get_payload(self, round: int):
        """Retrieves payload from the client server part
        """
        # Get the queue we have from the clients
        # These are the transactions the client 
        # Has sent to our writer
        if round == 0:    # Write genesis block
            genesis_block = {
                "name": "Annáll Blockchain",
                "owners": "Reykjavík University and Gísli Hjálmtýsson",
                "purpose": "A lightweight and secure blockchain for whatever you want"
            }
            return json.dumps(genesis_block)
        queue = self.clients.payload_queue
        if queue.empty():        
            vverbose_print("[PAYLOAD QUEUE ] empty")
            # If empty we just return anything
            return False
        else:
            payload = queue.get()
            vverbose_print(f"INSERTING PAYLOAD TO CHAIN \n", payload)
            self.stashed_payload = payload
            return payload[1]

    def get_coordinatorID(self, round: int):  # TODO: See comments below
        """Decides the coordinator for the round
        """
        assert isinstance(round, int)
        ## NOT SURE WHY THIS IS HERE:  8 - 1 % (3+1) # 7 % 4 = 3
        ## TODO not clear if this really works, e.g. in the case if some node dies, or if the set of writers changes
        coordinator = (round - 1) % (len(self.mem_data.writer_list))
        return coordinator + 1

    def calculate_sum(self, numbers: list):
        """Numbers is a list of <ID, number> pairs. This function calculates the pad for the round from the numbers using xor
        then it calculates which ID corresponds to the number 'closest' to the pad. Returns a list of length 3, containing
        [<id number pairs>, <pad>, <winner_id>]
        Tiebreaker decided by lower ID number
        """
        assert isinstance(numbers, list)

        pad = 0
        for number in numbers:
            pad ^= number[1]
        # Same as pad = pad%self.modulus
        pad %= self.modulus
        # calculate winner, finds the minimum difference for all submitted numbers from the calculated pad.
        winner, number = min(
            numbers,
            key=lambda x: [
                min((x[1] - pad) % self.modulus, (pad - x[1]) % self.modulus),
                x[0],
            ],
        )
        return [numbers, pad, winner]

    def join_writer_set(self):
        """Bootstrap to the writerset, using comm module
        """
        ## TODO: More suspicious is, this seems to block if any of the writers is not connected.
        while len(self.comm.list_connected_peers()) != len(self.mem_data.writer_list) + len(self.mem_data.reader_list) - 1: # TODO: Needs more sophistication
            time.sleep(1)
            print("WAITING TO CONNECT")
        print(f"ID={self.ID} -> connected and ready to build")
        return None

    def cancel_round(self, cancel_log: str, round: int):
        """
        Cancel the round, send cancel message to errbody and write cancel block
        """
        self.broadcast("cancel", cancel_log, round, send_to_readers=True)
        fake_message = f"{round}-{self.ID}-0-cancel-hehe"
        self.create_cancel_block(fake_message)

    def create_block(self, pad: int, coordinatorID: int, round):
        assert isinstance(pad, int)
        assert isinstance(coordinatorID, int)
        payload = self.get_payload(round)    # If returns False, should skip the round
        if not payload: # Writer had nothing to write
            return False
        if round == 0:
            prev_hash = 0
        else:
            prev_hash = self.get_prev_hash()
        prev_hash = str(prev_hash)  # Hash of latest block as the previous hash for new block
        # Returns payload of writer or arbitrary string if there is no payload
        vverbose_print(f"[PAYLOAD] the payload is: {payload} from the TCP server payload_queue")
        signature = self.sign_payload(payload)
        winning_number = pad
        coordinatorID = coordinatorID
        writerID = self.ID
        timestamp = self.get_timestamp() ### hmmmm

        block = Block( 
            prev_hash=prev_hash,
            writerID=writerID,
            coordinatorID=coordinatorID,
            winning_number=winning_number,
            writer_signature=signature,
            timestamp=timestamp,
            payload=payload,
        )
        return block

    def create_cancel_block(self, message: str):
        ''' Generates a cancel block '''
        assert isinstance(message, str)
        parsed_message = message.split("-")
        canceller = int(parsed_message[1])
        round = int(parsed_message[0])
        coor_id = self.get_coordinatorID(round)
        prev_hash = self.get_prev_hash()
        prev_hash = str(prev_hash)
        timestamp = self.get_timestamp()
         
        cancel_block = Block(
            prev_hash=prev_hash, 
            writerID=canceller, 
            coordinatorID=coor_id, 
            winning_number=0,
            writer_signature="0",
            timestamp=timestamp,
            payload=f"round {round} cancelled by {canceller}")

        self.latest_block = cancel_block
        return cancel_block

    def publish_block(self):
        """Winning writer fetches latest block in chain and publishes it to queue"""
        latest_block = self.bcdb.get_latest_block()
        self.broker.publish_block(json.dumps(latest_block))
        
    def check_for_old_cancel_message(self, round):
        message = self._recv_msg(type="cancel")
        if message is not None:
            parsed_message = message.split("-")
            cancel_block = self.create_cancel_block(message)
            if int(parsed_message[0]) != round:
                self.bcdb.insert_block(
                    int(parsed_message[0]), cancel_block, overwrite=True
                )

    def reader_round(self, round: int, coordinatorID: int):
        # Readers trust the chain and only listen for blocks including cancel blocks
        assert isinstance(round, int)
        assert isinstance(coordinatorID, int)
        message = None
        while message is None:  #TODO: Clean up messaging
            message = self._recv_msg("request", recv_from=coordinatorID)
            time.sleep(0.01)
        # Step 2 - Generate next number and transmit to Coordinator
        pad = self.generate_pad()
        # pad = -1    # Send negative number since others always give a positive number
        self._send_msg(round, "reply", pad, sent_to=coordinatorID)

        # Step 3 - Waiting for annoucement from the Coordinator
        message = None
        while message is None:
            message = self._recv_msg("announce", recv_from=coordinatorID)
        # Step 4 - Verify and receive new block from winner
        parsed_message = message.split("-")
        winner = ast.literal_eval(parsed_message[4])
        message = None
        while message is None:  # Gets stuck here in round 4. Message queue empty. Maybe that reader won round.
            message = self._recv_msg(type="block", recv_from=winner[2], round=round)    # Gets back tuple block
            time.sleep(0.01)
        parsed_message = message.split("-")
        parsed_message = message.split("-")
        payload = ast.literal_eval(parsed_message[4])   # Gets back the unstringed value
        if not payload:
            return
        block = Block.from_tuple(payload) # Converts tuple block to block object
        if not block:   # Winner had nothing to write. Round skipped
            return
        else:   # Block ok on our end
            # Check if other writer cancelled block
            message = self._recv_msg(type="cancel") 
            if message is not None:
                verbose_print("[ROUND CANCEL] the round was cancelled by another node")
                parsed_message = message.split("-")
                cancel_block = self.create_cancel_block(message)    # Block object
                if int(parsed_message[0]) != round: # Overwrite block in prior round
                    self.bcdb.insert_block(
                        int(parsed_message[0]), cancel_block, overwrite=True # Overwrites prior round but adds new block at end
                    )
                    self.latest_block = block
                else:
                    # The block does not belong to this round
                    # We assign the latest round as a cancel block
                    verbose_print("[ROUND CANCEL] a previous round was cancelled because of cancel message\n", parsed_message)
                    self.latest_block = cancel_block
            else:   # Winner and block verified
                self.latest_block = block
        vverbose_print(f"[LATEST BLOCK] the latest block is: {self.latest_block}")
        self.bcdb.insert_block(round, self.latest_block)

    # The round for the writer when you are not coordinator
    def writer_round(self, round: int, coordinatorID: int):
        assert isinstance(round, int)
        assert isinstance(coordinatorID, int)

        # Step 1 - Receive request from Coordinator
        message = None
        while message is None:
            message = self._recv_msg("request", recv_from=coordinatorID)    # Gets stuck here if reconnected sometimes
            vverbose_print("[REQUEST MESSAGE] Received message of request for OTP from coordinator")
            time.sleep(0.01)
        
        # Step 2 - Generate next number and transmit to Coordinator
        pad = self.generate_pad()
        self._send_msg(round, "reply", pad, sent_to=coordinatorID)

        # Step 3 - Waiting for announcement from the Coordinator
        message = None
        while message is None:
            message = self._recv_msg("announce", recv_from=coordinatorID)
            time.sleep(0.01)        
        # Step 4 - Verify and receive new block from winner
        parsed_message = message.split("-")
        winner = ast.literal_eval(parsed_message[4])
        winner_verified = self.verify_round_winner(winner, pad)
        vverbose_print(f"[WINNER WRITER] writer with ID {winner[2]} won the round")
        
        if winner_verified and self.ID == winner[2]:
            # I WON
            # First check if the previous round was cancelled and I had not seen the message yet
            self.check_for_old_cancel_message(round)    #TODO: Should probably be in reader_round
            block = self.create_block(pad, coordinatorID, round)    # Returns false if payload queue is empty
            self.latest_block = block
            # Broadcast our newest block before writing into chain
            if not block:   # Winning writer had nothing to write
                self.broadcast("block", str(block), round, send_to_readers=True)  
                return
            self.broadcast("block", str(block.as_tuple()), round, send_to_readers=True)  

        elif winner_verified:
            # Wait for a block to verify
            message = None
            while message is None:
                message = self._recv_msg(type="block", recv_from=winner[2], round=round)    # Gets back tuple block
                time.sleep(0.01)
            parsed_message = message.split("-")
            block = Block.from_tuple(ast.literal_eval(parsed_message[4])) # Converts tuple block to block object
            if not block:   # Winner had nothing to write. Round skipped
                return
            if not self.verify_block(block):
                self.cancel_round("Block not correct", round)   # Sets latest block as cancel block
            else:   # Block ok on our end
                # Check if other writer cancelled block
                message = self._recv_msg(type="cancel")
                if message is not None:
                    verbose_print("[ROUND CANCEL] the round was cancelled by another node")
                    parsed_message = message.split("-")
                    cancel_block = self.create_cancel_block(message)    # Block object
                    if int(parsed_message[0]) != round: # Overwrite block in prior round
                        self.bcdb.insert_block(
                            int(parsed_message[0]), cancel_block, overwrite=True # Overwrites prior round but adds new block at end
                        )
                        self.latest_block = block
                    else:
                        # The block does not belong to this round
                        # We assign the latest round as a cancel block
                        verbose_print("[ROUND CANCEL] a previous round was cancelled because of cancel message\n", parsed_message)
                        self.latest_block = cancel_block
                else:   # Winner and block verified
                    self.latest_block = block
        else:
            # Round is not verified
            # Cancel the round
            verbose_print("[ROUND CANCEL] round was cancelled because it was not verified")
            self.cancel_round("Round not verified", round)
        vverbose_print(f"[LATEST BLOCK] the latest block is: {self.latest_block}")
        self.bcdb.insert_block(round, self.latest_block)
        self.publish_block()


    def coordinator_round(self, round: int):
        
        vverbose_print(f"Round: {round} and ID={self.ID}")

        assert isinstance(round, int)

        # Step 1 -
        self.check_for_old_cancel_message(round=round)
        self.broadcast(msg_type="request", msg=round, round=round, send_to_readers=True)

        # Step 2 - Wait for numbers reply from all
        numbers = []
        no_recv_messages = 0
        # Currently waiting for a number from all active writers
        # MSG FORMAT <round nr>-<from id>-<to id>-<msg type>-<msg body>
        while no_recv_messages < len(self.mem_data.writer_list) + len(self.mem_data.reader_list) - 1:
            message = self._recv_msg(type="reply")
            if message is not None:
                parsed_message = message.split("-")
                from_id = ast.literal_eval(parsed_message[1])
                no_recv_messages += 1
                if from_id in self.mem_data.writer_list:
                    numbers.append([int(parsed_message[1]), int(parsed_message[4])])    #(id, otp)
            time.sleep(0.01)

        # Step 3 - Declare and announce winner
        winner = self.calculate_sum(numbers)    
        self.broadcast("announce", winner, round, send_to_readers=True)
        winner_id = winner[2]

        # Step 4 - Receive new block (from winner)
        message = None
        while message is None:
            message = self._recv_msg(type="block", recv_from=winner_id, round=round)
            time.sleep(0.01)
        parsed_message = message.split("-")
        payload = ast.literal_eval(parsed_message[4])
        if not payload: # Winner had nothing to write
            return
        block = Block.from_tuple(payload)
        if not self.verify_block(block):
            self.cancel_round("Round not verified", round)  #Sets latest block as cancel block
            verbose_print("ERROR, NOT CORRECT BLOCK")
        else:
            # Finally - write new block to the chain (DB)
            message = self._recv_msg(type="cancel") # Check if cancelled round
            if message is not None:
                parsed_message = message.split("-")
                cancel_block = self.create_cancel_block(message)
                if int(parsed_message[0]) != round:
                    self.bcdb.insert_block(
                        int(parsed_message[0]), cancel_block, overwrite=True
                    )
                    self.latest_block = block
                else:
                    self.latest_block = cancel_block
            else:
                self.latest_block = block

        self.bcdb.insert_block(round, self.latest_block)

    def check_for_updates(self):
        """Requests an update from the writer api to check if delete blocks"""
        if self.mem_data.check_delete_blocks():
            self.bcdb.truncate_table()

    def run_forever(self):
        """
        """
        # Expects all writers to join. Program does not start until all writers are all connected
        # TODO: Define a Quorate set, cannot insist on all writers being present
        #       Note: most likely need a consensus on which writers are present
        self.join_writer_set()
        print("[ALL JOINED] all writers have joined the writer set")
        round = self.bcdb.length    # TODO: Not possible for catch-up node
        print("ROUND: ", round)
        if self.comm.is_writer:
            while True:
                self.check_for_updates()
                coordinator = self.get_coordinatorID(round)
                vverbose_print(f"ID: {self.ID}, CordinatorId: {coordinator}", coordinator == self.ID)
                if coordinator == self.ID:
                    self.coordinator_round(round)
                else:
                    self.writer_round(round, coordinator)
    
                vverbose_print(f"[ROUND COMPLETE] round {round} finished with writer with ID {coordinator} as  the coordinator")
                round += 1
                if round > self.rounds and self.rounds:
                    break   # Stops the program
        else:
            while True:
                self.check_for_updates()
                coordinator = self.get_coordinatorID(round)
                self.reader_round(round, coordinator)
                round += 1
                if round > self.rounds and self.rounds:
                    break   # Stops the program
                vverbose_print(f"[ROUND COMPLETE] round {round} finished with writer with ID {coordinator} as  the coordinator")


    # MSG FORMAT <round nr>-<from id>-<to id>-<msg type>-<msg body>
    def _send_msg(self, round: int, type: str, message, sent_to=None, send_to_readers=False):
        assert isinstance(sent_to, (int, NoneType))
        assert isinstance(type, (str, NoneType))
        # implements a remote procedure call wrt protocolCommunication
        self.comm.send_msg(f"{round}-{self.ID}-{100}-{type}-{message}", send_to=sent_to, send_to_readers=send_to_readers)

    # MSG FORMAT <round nr>-<from id>-<to id>-<msg type>-<msg body>
    def _recv_msg(self, type=None, recv_from=None, round=None):
        assert isinstance(recv_from, (int, NoneType))
        assert isinstance(type, (str, NoneType))
        assert isinstance(round, (int, NoneType))
        # implements a remote procedure call wrt protocolCommunication
        rec = self.comm.recv_msg()  # Checks for new messages from other writers and adds them to the queue
        for message in rec: 
            self.message_queue.put(message[1])
        
        if self.message_queue.empty():
            
            vverbose_print("message queue empty")
            return None
        mess = self.message_queue.get() # Reader checks for cancel messages and takes request message
        parsed_message = mess.split("-")
        type_check = True
        from_check = True
        round_check = True

        if type:
            type_check = parsed_message[3] == type
        if recv_from:
            from_check = int(parsed_message[1]) == recv_from
        if round:
            round_check = int(parsed_message[0]) == round

        if type_check and from_check and round_check:
            return mess
        else:
            self.message_queue.put(mess)    # Message added back. Was not supposed to be taken off of the queue
        
        return None


global_list = []


def verify_chain(chain):
    correct_hash_chain = True
    for index in range(len(chain)):
        if index != 0:
            if chain[index][1] != chain[index - 1][7]:
                print("Incorrect part in chain 1/2" , chain[index][1])
                print("Incorrect part in chain 2/2" , chain[index - 1][7])
                correct_hash_chain = False

    same_writer_coord = not any(block[2] == block[3] for block in chain[1:])

    correctly_hashed = all(hash_block(block[1:]) == block[7] for block in chain[1:])

    return correct_hash_chain and same_writer_coord and correctly_hashed


def test_engine(id: int, rounds: int, no_writers: int):
    with open("./src/config-l2.json", "r") as f:
        data = json.load(f)


    # bce, blockchain writer to db
    CWD = os.getcwd()
    dbpath = f"/src/db/blockchain{id}.db"
    dbpath = CWD + dbpath
    print(f"[DIRECTORY PATH] {dbpath}")
    bce = BlockchainDB(dbpath)

    # p2p network
    pcomm = ProtoCom(id, data)
    pcomm.daemon = True
    pcomm.start()

    # client server thread
    if id == 1:
        TCP_IP = data["node_set"][id - 1]["hostname"]
        TCP_PORT = 15005
        print("::> Starting up ClientServer thread")
        clients = TCP_Server("the server", TCP_IP, TCP_PORT, ClientHandler, bce)
        cthread = Thread(target=clients.run, name="ClientServerThread")
        cthread.daemon = True
        cthread.start()
        print("ClientServer up and running as:", cthread.name)
    else:
        clients = ClientServer()

    keys = data["node_set"][id - 1]["priv_key"]

    # run the protocol engine, with all the stuff
    w = ProtoEngine(id, tuple(keys), pcomm, bce, clients,)
    w.set_rounds(rounds)
    w.set_conf(data)

    wlist = []
    for i in range(no_writers):
        if (i + 1) != id:
            wlist.append(i + 1)
    w.set_writers(wlist)
    w.run_forever()
    time.sleep(id)
    global_list.append(w.bcdb.read_blocks(0, 10))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-w", default=5, type=int, help="number of writers")
    ap.add_argument(
        "-r", default=10, type=int, help="number of rounds, 0 = run forever"
    )
    a = ap.parse_args()
    print(sys.argv[0], a.w, a.r)
    no_writers = a.w
    rounds = a.r
    threads = []

    for i in range(no_writers):
        thread = Thread(target=test_engine, args=[i + 1, rounds, no_writers])
        threads.append(thread)

    for t in threads:
        t.start()

    for t in threads:
        t.join()
    # Here we verify if the chain is stil lintact
    correctness = all(verify_chain(chain) for chain in global_list)
    if correctness:
        print("THE CHAIN IS INTACT")
    else:
        print("The chain failed somewhere")
        for chain in global_list:
            print(chain)
