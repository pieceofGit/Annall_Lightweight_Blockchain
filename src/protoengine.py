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
from downloader import Downloader
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
        self.downloader = Downloader(mem_data, blockchain)
                    
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

        if block is not None:
            writer = block.writerID
            payload = block.payload
            signature = int(block.writer_signature, 16)
            writer_pubkey = int(self.mem_data.conf["node_set"][int(writer) - 1]["pub_key"])  #TODO: Should not completely rely on id since the node_set is dynamic
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
        # ? How do nodes handle a new membership version when one is being proposed? 
        # TODO: Nodes only add at most one reader and one writer in a round. 
        # A coordinator can propose one new writer and reader to active set.
        # Any number of nodes can be proposed to be removed from the active set. 
        # New node continuously updates its current version while waiting and gets sent the current version number when added to consensus.
        ## TODO: More suspicious is, this seems to block if any of the writers is not connected.
        # Either program starting up or node is in waiting list
        while (len(self.comm.list_connected_peers()) / (len(self.mem_data.writer_list) + len(self.mem_data.reader_list))) < 0.5: # TODO: Needs more sophistication
            # Startup node means that the node is in the active list. 
            # Could have an empty list and wait until nodes are activated. 
            # Blockchain could be turned on and off. The last running nodes need to be the ones to startup the blockchain. 
            # Or the blockchain is stamped on the bitcoin network. What is the cost of that though?
            # The external party is controlling the membership statically. The nodes handle the dynamism of the membership management.
            # Assume there is an external api for signing up. It runs separately from the blockchain. On startup, nodes get some version of this active membership list.
            # The version number may be different. The coordinator shares the active list, round number, and the list version. 
            # The hash version should be signed by the external party for verification. 
            # Node 1: [1,2], Node 3: [1,2,3], Node 2: [1,2,3].
                # 1
                # Node 1 connects to node 2 and starts consensus.
                # Node 2 connects to node 1 and 3 and starts consensus.
                # Node 3 connects to node node 2 and waits to connect to node 1.
                # 2
                # Node 1 selects itself as coordinator
                # Node 2 selects node 3 as coordinator
            # ? How can this be fixed?
                # Connect the version number, the membership API, and node consensus about the current version
            # Idea: nodes communicate their version and fetch the latest version until all nodes agree. 
                # 1 Same as before
                # Node 1 and Node 2 communicate their version number.
                # Node 3 gets added by Node 1.
                # When node reach agreement with the version number, they start consensus round.
                # Coordinator fetches the membership config and proposes new version if it has changes.
                # Problem: Nodes do not fetch the same version number. 
            # ? How should change in membership be handled?
                # Either should fetch specific version or if proposing coordinator has the same proposed version when he is a proposer, it becomes the current version.
                # Every node has proposed the same version and the original proposer sets the new proposal as the new version.
                #  ? Effect on waiting node logic
                    # waiting node continues to update its version.
            # TODO: Simplest to propose a version number and other nodes fetch the same version
            # ? Nodes do not need to propose the latest version, only a later version number. Honest nodes eventually move everyone to latest version.
            # ? With fetch latest solution, malicious nodes could continuously activate and deactivate to increase the version number.
            
            if not self.mem_data.is_genesis_node:
                # Consensus is ongoing while node waits, and node needs to stay updated
                # 1. get new config
                self.mem_data.waiting_node_get_conf()
                # 2. get latest blocks
                self.downloader.download_db() # Problem with updating active set if not all up to date.
            time.sleep(1)
            print("WAITING TO CONNECT")
        print(f"ID={self.ID} -> connected and ready to build")
        return None
        # ? Connect to at least 51% and move on. Running nodes can at least start consensus and add unconnected nodes to penalty box.
        # Nodes should be able to run without being connected to everyone.
        # Node needs to ask for data from other nodes if it does not get the latest block. 
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
        if not self.mem_data.conf["is_local"]:
            latest_block = self.bcdb.get_latest_block()
            self.broker.publish_block(json.dumps(latest_block))
        
    def check_for_old_cancel_message(self, round):
        """Checks for cancel blocks of previous rounds and overwrites block with cancel block"""
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
        self.bcdb.insert_block(round, self.latest_block)    # Rounds in consensus different from stored in db

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
            # Node is winner
            # First check if the previous round was cancelled and I had not seen the message yet
            self.check_for_old_cancel_message(round)
            block = self.create_block(pad, coordinatorID, round)    # Returns false if payload queue is empty
            self.latest_block = block
            # Broadcast our newest block before writing into chain
            if not block:   # Winning writer had nothing to write
                self.broadcast("block", str(block), round, send_to_readers=True)  
                return
            self.broadcast("block", str(block.as_tuple()), round, send_to_readers=True)  

        elif winner_verified:
            # Wait for a block to verify
            # Node gets block, does not check for cancel block from others. 
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
            else:
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
            # Round failed verification. Round cancelled
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
        """Requests an update from the writer api to check if it should delete all blocks and restart the blockchain"""
        if self.mem_data.check_reset_chain():
            self.bcdb.truncate_table()

    def run(self):
        """
        """
        # Expects all active nodes to join. Program does not start until all active nodes are all connected
        
        # Waiting nodes connect to everyone and fetch missing blocks. They may be piggybacking on some node and getting the latest blocks
        # All nodes have a thread to periodically fetch the latest config file. A coordinator can push to proposing a new version of the config.
        # Then in the next round, a coordinator sees that a proposed version is the same as it fetches, and sets it as the current version.
        # In this round, the coordinator sends that we have moved to a different version and that there is a new current version.
        
        # Long-term, catch-up should happen before activation. If 20GB, then waiting for an hour if node is activated.
        # The node has access to all current nodes before it adds itself and should fetch through their client API for all blocks.
        # Get all blockchain from one node and check yourself with a signature on your latest block. If 51% agree, continue, else reset to next node.
        # After getting all blocks, continue fetching while not connected to all nodes.
        # The coordinator of a round is the first to open a connection to the new node. It should send the round number along when it was proposed to be added.
        # The node then knows the round number and knows that it is added in the next round and can get data up to that point and then wait for the next coordinator.
        # ? Next coordinator does not comply
        # It sends a cancel block to all nodes, but the round could be complete... the next one should comply and wait for the request by the new node.
        
        
        # 1. Node waits until it is activated
        while not self.mem_data.node_activated:
            time.sleep(1)
        # Node has successfully fetched blockchain and been added to the active node set
        # 2. Node attempts to connect to all active nodes
        
        # Could be round retry with different coordinator.
        # Both round robin rounds and within a round retry. 
        # A new node could wait for a specific coordinator to join. Could send request when all joined. 
        # Not possible for start of blockchain.
        # Rule: If not in preset node list, other nodes are waiting for it.
        # A node has to send a deactivate request to not end in penalty box.
        # Nodes don't need to have the same round number in the consensus to join.
        # Coordinator shares the round number in its request. 
        # New nodes set the round number after getting it from the coordinator.
        # On blockchain start, all nodes have an empty blockchain and they are not in the waiting list.
        # Nodes in the preset list do not go through the waiting list.
        
        # Node should just wait for a message from any coordinator to join. 
        self.join_writer_set()
        print("[ALL JOINED] all writers have joined the writer set")
        round = self.bcdb.length    
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
                if round > self.rounds and self.rounds:
                    break   # Stops the program
                round += 1
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
    w.run()
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
