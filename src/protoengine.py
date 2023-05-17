from queue import Queue
import hashlib


from queue import Queue
from threading import Thread
import struct
import time
from datetime import datetime
import ast
import math
import sys
import argparse
import os
import json
from protocom import ProtoCom
from models.membershipData import MembershipData
from models.message import Message
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

        self.id = id
        self.keys = keys    # Private keys
        self.mem_data = mem_data
        self.update_num = 0
        # Defining e
        self.modulus = 65537
        # For how many rounds the blockchain should run for
        self.rounds = None        
        self.cancel_seq_num = 0
        # Messages in our writer's queue
        self.message_queue = Queue()
        self.cancel_message_queue = Queue()
        self.latest_block = None
        # maintain a payload
        self.stashed_payload = None
        # PubSub queue and exchange
        self.broker = BlockBroker()       
        self.downloader = Downloader(mem_data, blockchain)  # For periodically checking for new blocks while waiting to join
                    
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
        self.mem_data.ma_writer_list = writers
    
    def set_readers(self, readers: list):
        for r in readers:
            assert isinstance(r, int)
        self.mem_data.ma_reader_list = readers
    
    def get_timestamp(self):
        # Returns time in Unix epoch time 
        return round(datetime.timestamp(datetime.now()))

    def get_prev_hash(self, round=None):
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
        # assert isinstance(msg, (int, str, list))
        assert isinstance(round, int)
        return self._send_msg(round=round, type=msg_type, message=msg, sent_to=None, send_to_readers=send_to_readers)

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
            return "Writer had nothing to write"
        else:
            payload = queue.get()
            vverbose_print(f"INSERTING PAYLOAD TO CHAIN \n", payload)
            self.stashed_payload = payload
            return payload[1]

    def get_coordinatorID(self, round: int):  # TODO: See comments below
        """Decides the coordinator for the round
        """
        assert isinstance(round, int)
        ## TODO not clear if this really works, e.g. in the case if some node dies, or if the set of writers changes
        # IDs sorted by ascending ID number. Returns index in writer list
        self.mem_data.round_writer_list.sort()
        coordinator_index = (round - 1) % (len(self.mem_data.round_writer_list))
        # Separate list for round and list for connections.
        if self.mem_data.round_writer_list[coordinator_index] == 3:
            return 2
        else:
            return self.mem_data.round_writer_list[coordinator_index]

    def get_cancel_coordinatorID(self):
        """Decides the coordinator for a cancel round in the membership protocol.
        Should only change when there is a view-change in the cancellation."""
        return self.mem_data.round_writer_list[0]

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
        # TODO: Nodes only add at most one reader and one writer in a round. Why? 
        # A coordinator can propose one new writer and reader to active set.
        # Any number of nodes can be proposed to be removed from the active set. 
        # New node continuously updates its current version while waiting and gets sent the current version number when added to consensus.
        ## TODO: More suspicious is, this seems to block if any of the writers is not connected.
        # TODO: Should not block indefinitely if writers are down
        wait = 0
        while (len(self.comm.list_connected_peers()) / (len(self.mem_data.ma_writer_list) + len(self.mem_data.round_reader_list))) < 0.5:
            if not self.mem_data.is_genesis_node:
                # Consensus is ongoing while node waits, and node needs to stay updated
                # 1. get new config
                self.mem_data.waiting_node_get_conf()
                # 2. get latest blocks
                self.downloader.download_db() # Problem with updating active set if not all up to date.
            if wait == 0:
                print("WAITING TO CONNECT")
            wait += 1
            time.sleep(1)
        print(f"ID={self.id} -> connected and ready to build")
        return None

    def cancel_round(self, faulty_node: int, round: int):
        """
        Cancel the round, send cancel message to everybody with the reason for the cancellation, and write cancel block.
        Either the majority agrees with the cancellation and adds the faulty node to the penalty box or the cancelling node is sent to the penalty box.
        """
        # Can't write cancel block unless waited for everyone to respond, either cancel because of cancelling node or in agreement.
        payload = self.get_cancel_block_payload(round=round)
        msg = self.broadcast("cancel", payload, round, send_to_readers=True)
        self.create_cancel_block(Message.from_json(msg))


    def create_block(self, pad: int, coordinatorID: int, round):
        assert isinstance(pad, int)
        assert isinstance(coordinatorID, int)
        payload = self.get_payload(round)    # If returns False, should skip the round
        if not payload: # Writer had nothing to write
            return False
        if round == 0:
            prev_hash = 0
        else:
            prev_hash = self.get_prev_hash(round=round)
        prev_hash = str(prev_hash)  # Hash of latest block as the previous hash for new block
        # Returns payload of writer or arbitrary string if there is no payload
        vverbose_print(f"[PAYLOAD] the payload is: {payload} from the TCP server payload_queue")
        signature = self.sign_payload(payload)
        winning_number = pad
        coordinatorID = coordinatorID
        writerID = self.id
        timestamp = self.get_timestamp()

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
    
    def insert_cancel_block(self, round, cancel_round, accuser_id):
        """Synchronizes the node on the round to insert the block by catching up or removing invalid blocks, and inserts the cancel block"""
        if cancel_round == round + 1: # Cancel block is in next round 
            # Check for any blocks received in the meantime, else try to catch up.
            block = self._recv_msg(type="block", round=round)  
            if block:
                self.bcbd.insert_block(round, block)
                # Insert block in next round
                # Received block, insert cancel block in current round
                self.create_cancel_block(accuser=accuser_id, round=cancel_round)
                self.bcdb.insert_block(round, self.latest_block)
                self.publish_block(cancel_round)
            else:
                self.downloader.download_db()
        elif cancel_round < round:  # Cancel block is in prior round
            # Remove all blocks from round to cancel_round. #TODO: Should not accept further than f+1 rounds back
            self.bcdb.remove_blocks(round_begin=round)
        elif cancel_round > round + 1:    # Cancel block is in much later round
            self.downloader.download_db()
        self.create_cancel_block(accuser=accuser_id, round=cancel_round)
        self.bcdb.insert_block(round, self.latest_block)
        self.publish_block(cancel_round)

    def create_cancel_block(self, accuser: int, round: int):
        """ Generates a cancel block """
        # assert isinstance(message, Message)
        canceller = accuser
        round = round
        coor_id = self.get_coordinatorID(round)
        prev_hash = self.get_prev_hash(round=round)
        prev_hash = str(prev_hash)
        timestamp = 0   # Can't sync on timestamp if everyone creates their own cancel block
        cancel_block = Block(
            prev_hash=prev_hash, 
            writerID=canceller, 
            coordinatorID=coor_id, 
            winning_number=0,
            writer_signature="0",   #? Should this not be signed
            timestamp=timestamp,
            payload=json.dumps({"type": "cancel", "payload": json.dumps((self.mem_data.round_disconnect_list, self.cancel_seq_num))}))
        self.latest_block = cancel_block
        return cancel_block

    def publish_block(self, round: int):
        """Winning writer fetches latest block in chain and publishes it to queue"""
        if not self.mem_data.conf["is_local"]:
            # latest_block = self.bcdb.get_block_by_round_number(round)
            self.broker.publish_block(json.dumps(self.latest_block.as_tuple()))
            
    def get_cancel_block_payload(self, round):
        return json.dumps({"type": "cancel", "faulty_node": self.mem_data.round_disconnect_list, "cancel_seq_num": self.cancel_seq_num, "prev_hash": self.get_prev_hash(round=round), "round": round})
        
    def check_for_old_cancel_message(self, round):
        """Checks for cancel blocks of previous rounds and overwrites block with cancel block"""
        message = self._recv_msg(type="cancel")
        if message is not None:
            cancel_block = self.create_cancel_block(message)
            if int(message.round) != round:
                self.bcdb.insert_block(int(message.round), cancel_block, overwrite=True)
            
    def propose_cancel(self, faulty_node: int, round: int):
        """Broadcasts a round cancellation proposal"""
        # Need a unique identifier to differentiate between old and current cancel messages
        # Nodes do also not have a consensus on the prev_hash.
        payload = json.dumps({"type": "propose_cancel", "prev_hash": self.get_prev_hash(), "cancel_seq_num": self.cancel_seq_num, "faulty_node": faulty_node})
        msg = self.broadcast("propose_cancel", payload, round, send_to_readers=True)
        
    def get_propose_cancel(self, round):
        """Checks for propose_cancel message and returns round of propose_cancel, and the accuser and accusee id"""
        for round_i in range(round-math.floor((len(self.mem_data.round_writer_list)-1)/3)-1, round+1):
            propose_message = self._recv_msg(type="propose_cancel", round=round_i, cancel_msg=True)
            # What does the node do about duplicate propose_cancel messages?
            # TODO: Need to differentiate between old and current cancel messages
            # It should be the prev_hash, because a cancelled round has a prev_hash.
            # If a round was successfully cancelled, all honest nodes should have had the same prev_hash. No, not if a node was behind and threw a propose_cancel message.
            # All honest nodes should have the same lates prev_hash, if a round was cancelled. That should hold.
            # But if it is a round that was not cancelled, the nodes can have a different prev_hash.
            if propose_message:
                payload = json.loads(propose_message.payload)   
                if payload["cancel_seq_num"] >= self.cancel_seq_num:    # Only check new cancel messages
                    faulty_node = payload["faulty_node"]
                    return propose_message.round, propose_message.from_id, faulty_node
        return round, None, None
 
    def vote_cancel(self, faulty_node: int, round: int):
        """Broadcasts a round cancellation vote"""
        payload = json.dumps({"type": "vote_cancel", "faulty_node": faulty_node})
        msg = self.broadcast("vote_cancel", payload, round, send_to_readers=True)
    
    def request_cancel(self, vote: tuple, round: int):
        """Broadcasts a round cancellation vote"""
        payload = json.dumps({"type": "request_cancel", "vote": vote})
        msg = self.broadcast("request_cancel", payload, round, send_to_readers=True)
    
    def get_request_cancel(self, round):
        """Blocks for request cancel message and returns accuser and accusee id"""
        request_cancel_message = None
        while request_cancel_message is None:   # May not be its own vote proposal
            request_cancel_message = self._recv_msg(type="request_cancel", round=round, cancel_msg=True)
            if request_cancel_message:
                payload = json.loads(request_cancel_message.payload)
                accuser_id = payload["vote"][0]     # From coordinator, accuser is the one who proposed the cancellation
                accusee_id = payload["vote"][1]     # From coordinator, accusee is the one who is being accused
            time.sleep(0.01)
        return accuser_id, accusee_id

    def get_vote_ballot(self, accuser_id, accusee_id, round, vote_for_accusee):
        """Blocks for vote messags, waits for consensus, and adds nodes to round_disconnect_list"""
        votes = []
        consensus = False
        vote_accuser = 0
        vote_accusee = 0
        if vote_for_accusee:
            vote_accusee += 1
            votes.append(accusee_id)
        else:
            vote_accuser += 1
            votes.append(accuser_id)
        while len(votes) < len(self.mem_data.round_writer_list) + len(self.mem_data.round_reader_list) and not consensus:
            message = self._recv_msg(type="vote_cancel", round=round, cancel_msg=True)
            if message is not None:
                payload = json.loads(message.payload)
                if payload["faulty_node"] == accuser_id:
                    vote_accuser += 1
                elif payload["faulty_node"] == accusee_id:
                    vote_accusee += 1
                else:
                    pass
                votes.append(payload["faulty_node"])
                # Check if consensus reached
                # TODO: Nodes in penalty box are not a part of the consensus
                if vote_accuser > len(self.mem_data.round_writer_list) / 2 or vote_accusee > len(self.mem_data.round_writer_list) / 2:
                    consensus = True
            time.sleep(0.01)
        # Majority voted for accuser
        if vote_accuser > len(self.mem_data.round_writer_list) / 2:
            # Both nodes sanctioned from consensus
            self.mem_data.round_disconnect_list.append(accuser_id)
            self.mem_data.round_disconnect_list.append(accusee_id)
        else:
            # Accusee sanctioned from consensus
            self.mem_data.round_disconnect_list.append(accusee_id)
        self.cancel_seq_num += 1

    def vote(self, accuser_id, accusee_id, round):
        if accusee_id in self.mem_data.disconnected_nodes:
            self.vote_cancel(faulty_node=accusee_id, round=round)
            self.get_vote_ballot(accuser_id, accusee_id, round, vote_for_accusee=True)    # Blocks on receiving all votes
        else:
            self.vote_cancel(faulty_node=accuser_id, round=round)
            self.get_vote_ballot(accuser_id, accusee_id, round, vote_for_accusee=False)    # Blocks on receiving all votes
        
    def node_check_round_cancelled(self, round: int):
        """Helper function for checking if round is cancelled"""
        if self.get_cancel_coordinatorID() == self.id:
            return self.coordinator_round_cancelled(round)
        else:
            return self.writer_round_cancelled(round)
    
    def writer_round_cancelled(self, round) -> tuple:
        """Checks for round cancellation messages for the current round and proposes a cancellation if it has not been proposed yet"""
        cancel_round = round
        cancel_round, accuser_id, accusee_id = self.get_propose_cancel(round)
        peer_disconnected =  self.comm.peers_disconnected()
        if  peer_disconnected and not accusee_id:  # Check and returns true if any node has disconnected
            accusee_id = self.mem_data.disconnected_nodes[0]
        if accusee_id:
            # Broadcast own cancel message proposal, calculate votes, and set cancel block
            self.propose_cancel(faulty_node=accusee_id, round=cancel_round)   # Broadcasts own cancel block proposal
            # Waits for request_cancel from coordinator
            accuser_id, accusee_id = self.get_request_cancel(cancel_round)
            # Broadcast own vote
            self.vote(accuser_id, accusee_id, cancel_round)
            # Given that coordinator is not faulty node, nodes are synced on vote
            # Create cancel block and moves on. Each node creates its own cancel block. Payload is the disconnect list
            self.insert_cancel_block(round, cancel_round, accuser_id)
            # Now the last f+1 rounds may be cancelled due to the cancellation.
            # If the round cancellation is for a later round, the node should catch up. given, that there were no cancellations there.
            return True, cancel_round
        return False, cancel_round
     
    def coordinator_round_cancelled(self, round) -> tuple:
        """Checks for round cancellation messages for the current round and proposes a cancellation if it has not been proposed yet"""
        cancel_round = round
        # Check for received propose_cancel
        cancel_round, accuser_id, accusee_id = self.get_propose_cancel(round)
        if self.comm.peers_disconnected() and not accusee_id:  # Check and returns true if any node has disconnected
            accusee_id = self.mem_data.disconnected_nodes[0]
        if accusee_id:
            if not accuser_id:
                accuser_id = self.id
            self.propose_cancel(faulty_node=accusee_id, round=cancel_round)   # Broadcasts own cancel block proposal
            self.request_cancel((accuser_id, accusee_id), cancel_round)
            self.vote(accuser_id, accusee_id, cancel_round)
            # Create cancel block and moves on. Each node creates its own cancel block. Payload is the disconnect list
            self.create_cancel_block(accuser=accuser_id, round=cancel_round)
            return True, cancel_round
        return False, cancel_round
            
    # Consensus protocol messages
    def get_request_msg(self, id: int, round: int) -> tuple:
        """Blocks for request message and sends back message object and boolean for round cancellation"""
        message = None
        while message is None:
            message = self._recv_msg(type="request", recv_from=id)
            time.sleep(0.01)
            round_cancelled, cancel_round = self.node_check_round_cancelled(round)
            if round_cancelled:
                return None, cancel_round
        return message, None
    
    def get_announce_msg(self, id, round) -> tuple:
        """Blocks for announce message and sends back message object and boolean for round cancellation"""
        message = None
        while message is None:
            message = self._recv_msg("announce", recv_from=id, round=round)
            time.sleep(0.01)            
            round_cancelled, cancel_round = self.node_check_round_cancelled(round)
            if round_cancelled:
                return None, cancel_round
        return message, None
    
    def get_otp_numbers(self, round) -> tuple:
        """Blocks OTP nubmers from all active nodes and returns list of numbers and boolean for round cancellation"""
        numbers = []
        no_recv_messages = 0
        while no_recv_messages < len(self.mem_data.round_writer_list) + len(self.mem_data.round_reader_list) - 1:
            message = self._recv_msg(type="reply", round=round)
            if message is not None:
                no_recv_messages += 1
                if message.from_id in self.mem_data.round_writer_list:
                    numbers.append([message.from_id, message.payload])    #(id, otp)
            round_cancelled, cancel_round = self.node_check_round_cancelled(round)
            if round_cancelled:
                return None, cancel_round
            time.sleep(0.01)
        return numbers, None
    
    def receive_block(self, winner_id: int, round: int) -> tuple:
        message = None
        while message is None:
            message = self._recv_msg(type="block", recv_from=winner_id, round=round)    # Gets back tuple block
            round_cancelled, cancel_round = self.node_check_round_cancelled(round)
            if round_cancelled:
                return None, cancel_round
            time.sleep(0.01)
        # if not json.loads(message.payload):   # Winner had nothing to write. Round skipped
        #     return None, None
        # Receives json payload
        block = Block.from_json(message.payload) # Converts tuple block to block object
        if not self.verify_block(block):
            self.cancel_round(faulty_node=winner_id,round=round)   # Sets latest block as cancel block 
        else:
            # Check if other writer cancelled block
            message = self._recv_msg(type="cancel")
            if message is not None:
                cancel_block = self.create_cancel_block(message)    # Block object
                if message.round != round: # Overwrite block in prior round
                    self.bcdb.insert_block(message.round, cancel_block, overwrite=True) # Overwrites prior round but adds new block at end
                    self.latest_block = block
                else:
                    # The block does not belong to this round
                    # We assign the latest round as a cancel block
                    self.latest_block = cancel_block
            else:   # Winner and block verified
                self.latest_block = block
        return block, None

    def reader_round(self, round: int, coordinator_id: int) :
        # Readers trust the chain and only listen for blocks including cancel blocks
        assert isinstance(round, int)
        assert isinstance(coordinator_id, int)
        # Step 1 - Receive request from Coordinator
        message  = self.get_request_msg(coordinator_id)
        success = self.check_membership_version_update(message.version)
        if not success:
            self.cancel_round(faulty_node=coordinator_id, round=round)   # Sets latest block as cancel block
        # Step 2 - Generate next number and transmit to Coordinator
        pad = self.generate_pad()
        self._send_msg(round, "reply", pad, sent_to=coordinator_id)

        # Step 3 - Waiting for annoucement from the Coordinator
        message = self.get_announce_msg(coordinator_id)
        winner = message.payload
        winner_id = winner[2]
        received_block = self.receive_block(winner_id, round)
        if not received_block:
            return
        self.bcdb.insert_block(round, self.latest_block)    # Rounds in consensus different from stored in db

    def writer_round(self, round: int, coordinator_id: int):
        """Writers in lottery win contention for a round"""
        assert isinstance(round, int)
        assert isinstance(coordinator_id, int)
        # Step 1 - Receive request from Coordinator
        message, cancel_round  = self.get_request_msg(coordinator_id, round)
        if not message: # Round cancelled
            return cancel_round
        # Step 1.1 - Check for new membership version based on message
        is_valid_version = self.check_membership_version_update(message.version)
        # Throw cancel block if not valid membership version
        # if not is_valid_version:
        #     self.cancel_round(faulty_node=coordinator_id, round=round)   # Sets latest block as cancel block
        # Step 2 - Generate next number and transmit to Coordinator
        pad = self.generate_pad()
        self._send_msg(round, "reply", pad, sent_to=coordinator_id)
        # Step 3 - Waiting for announcement from the Coordinator
        message, cancel_round = self.get_announce_msg(coordinator_id, round)
        if not message: # Round cancelled
            return cancel_round
        # Step 4 - Verify new block from winner or add a cancel block
        winner = message.payload
        winner_verified = self.verify_round_winner(winner, pad)
        winner_id = winner[2]
        if self.id == winner_id and winner_verified:    # Node is winning writer
            # First check if the previous round was cancelled and I had not seen the message yet
            self.check_for_old_cancel_message(round)
            block = self.create_block(pad, coordinator_id, round)    # Returns false if payload queue is empty
            self.latest_block = block
            # if not block:   # Node has nothing to write
            #     self.broadcast("block", json.dumps(block), round, send_to_readers=True)  
            #     return round
            self.broadcast("block", json.dumps(block.as_tuple()), round, send_to_readers=True)  
        elif winner_verified:   # Node receives block from winner
            received_block, cancel_round = self.receive_block(winner_id, round)
            if self.mem_data.round_disconnect_list:
                # Round was cancelled
                return cancel_round
            elif not received_block:
                return round
        else:   # Round failed verification
            self.cancel_round(faulty_node=winner_id, round=round)
        vverbose_print(f"[LATEST BLOCK] the latest block is: {self.latest_block}")
        self.bcdb.insert_block(round, self.latest_block)
        self.publish_block(round)
        return round

    def coordinator_round(self, round: int):
        vverbose_print(f"Round: {round} and ID={self.id}")
        assert isinstance(round, int)
        self.check_for_old_cancel_message(round=round)  #TODO: Clear up cancel blocks
        # Step 0 - Fetch latest membership configuration file from MA
        self.mem_data.get_remote_conf()
        # Step 1 - Request OTP number from writers. Piggyback version number on message
        self.broadcast(msg_type="request", msg=round, round=round, send_to_readers=True)
        # Step 2 - Wait for numbers reply from all
        numbers, cancel_round = self.get_otp_numbers(round)
        if not numbers: # Round cancelled
            return cancel_round
        # Step 3 - Declare and announce winner.
        winner = self.calculate_sum(numbers)
        self.broadcast(msg_type="announce", msg=winner, round=round, send_to_readers=True)
        winner_id = winner[2]
        # Step 4 - Receive new block (from winner)
        received_block, cancel_round = self.receive_block(winner_id, round)
        if self.mem_data.round_disconnect_list: # Round cancelled
            return cancel_round
        elif not received_block:
            return round
        self.bcdb.insert_block(round, self.latest_block)
        return round

    def check_for_chain_reset(self):
        """Requests an update from the writer api to check if it should delete all blocks and restart the blockchain"""
        if self.mem_data.check_reset_chain():
            self.bcdb.truncate_table()
            
    def check_membership_version_update(self, version: int) -> bool:
        """Attempts to update membership version and returns its success boolean"""
        if version > self.mem_data.current_version:
            update_complete = self.mem_data.get_membership_version(version)
            if update_complete:
                return True
            else:
                return False
        elif version < self.mem_data.current_version:
            return False
        else:
            return True
            
    def run(self):
        """
        """
        # Expects all active nodes to join. Program does not start until all active nodes are all connected
        while not self.mem_data.node_activated:
            time.sleep(1)
        self.mem_data.downloader_clean_up() # Clean up downloader thread
        # Node has successfully fetched blockchain and been added to the active node set
        # 2. Node attempts to connect to all active nodes
        self.join_writer_set()
        # Nodes should receive the current round number on startup
        print("[ALL JOINED] all writers have joined the writer set")
        round = self.bcdb.length    #TODO: Node should get the round number from running nodes, if not genesis node
        print("ROUND: ", round)
        if self.mem_data.is_writer:
            while True:
                if self.mem_data.round_disconnect_list:
                    print("FINISHED ROUND: ", round, "PENALTY BOX: ", self.mem_data.penalty_box)
                self.mem_data.set_round_lists(round) # Update penalty box, disconnect list and active node lists
                self.check_for_chain_reset()
                if self.mem_data.proposed_version > self.mem_data.current_version:
                    self.mem_data.update_version()
                    self.comm.set_active_nodes() # Sets up socket connection for incoming node
                    self.join_writer_set()
                    round = self.bcdb.length    #TODO: Should never reset the consensus round number. Perhaps has effect on penalty box.
                    # time.sleep(2)   # New nodes need time to connect, otherwise they are registered as disconnected.
                coordinator = self.get_coordinatorID(round)
                vverbose_print(f"ID: {self.id}, CordinatorId: {coordinator}", coordinator == self.id)
                if coordinator == self.id:
                    curr_round = self.coordinator_round(round)
                else:
                    curr_round = self.writer_round(round, coordinator)
                vverbose_print(f"[ROUND COMPLETE] round {round} finished with writer with ID {coordinator} as  the coordinator")
                if curr_round > round:
                    # Round was cancelled and node needs to catch up
                    # Should do that before it adds the cancel block
                    ...
                elif curr_round < round:
                    # Round was cancelled in a prior round, node needs to delete later blocks
                    ...
                round = curr_round
                self.mem_data.decrease_penalty_box_counters()
                self.mem_data.add_to_penalty_box(round)
                round += 1
                if round > self.rounds and self.rounds:
                    break   # Stops the program
        else:
            while True:
                self.check_for_chain_reset()
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
        msg = Message.create_msg(round=round, from_id=self.id, message=message, type=type, version=self.mem_data.get_version())
        self.comm.send_msg(message=msg, send_to=sent_to, send_to_readers=send_to_readers)
        return msg

    def add_messages_to_queue(self, messages):
        normal_msg_types = ["request", "reply", "announce", "block", "cancel"]
        cancel_msg_types = ["propose_cancel", "vote_cancel", "request_cancel"]
        for msg in messages:
            msg = Message.from_json(msg[1]) # Takes msg json and loads into object
            if msg:
                if msg.type in normal_msg_types:
                    self.message_queue.put(msg)
                elif msg.type in cancel_msg_types:
                    self.cancel_message_queue.put(msg)

    # MSG FORMAT <round nr>-<from id>-<to id>-<msg type>-<msg body>
    def _recv_msg(self, type=None, recv_from=None, round=None, cancel_msg=False):
        assert isinstance(type, (str, NoneType))
        assert isinstance(recv_from, (int, NoneType))
        assert isinstance(round, (int, NoneType))
        # implements a remote procedure call wrt protocolCommunication
        messages = self.comm.recv_msg()  # Checks for new messages from other writers and adds them to the queue
        self.add_messages_to_queue(messages)        
        if self.message_queue.empty() and not cancel_msg:
            vverbose_print("message queue empty")
            return None
        elif self.cancel_message_queue.empty() and cancel_msg:
            vverbose_print("cancel message queue empty")
            return None
        if cancel_msg:
            msg = self.cancel_message_queue.get() # Reader checks for cancel messages
        else:
            msg = self.message_queue.get() # Reader checks for cancel messages and takes request message
        if not msg:
            self.message_queue.put(msg)
            return None
        type_check = True
        from_check = True
        round_check = True
        if type:
            type_check = msg.type == type
        if recv_from:
            from_check = msg.from_id == recv_from
        if round:
            round_check = msg.round == round
        if type_check and from_check and round_check:
            return msg  # Returns msg object if all is true
        else:   
            if cancel_msg:
                self.cancel_message_queue.put(msg)
            else:
                self.message_queue.put(msg)    # Message added back. Was not supposed to be taken off of the queue
        return None

