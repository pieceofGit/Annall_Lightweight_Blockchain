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
        # Messages in our writer's queue
        self.message_queue = Queue()
        self.cancel_message_queue = Queue()
        self.view_change_message_queue = Queue()
        self.latest_block = None
        # maintain a payload
        self.stashed_payload = None
        # PubSub queue and exchange
        self.broker = BlockBroker()       
        self.downloader = Downloader(mem_data, blockchain)  # For periodically checking for new blocks while waiting to join
        self.timeout = 10
        self.cancel_number = 0     # Incremented on receiving propose_cancel message
        self.view = 0

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
        
    def verify_message(self, payload, signature, sender_id: int):
        if payload is not None:
            signature = int(signature, 16)
            writer_pubkey = int(self.mem_data.conf["node_set"][sender_id - 1]["pub_key"])  #TODO: Should not completely rely on id since the node_set is dynamic
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

    def broadcast(self, msg_type: str, msg, round: int, view, send_to_readers=False):
        assert isinstance(msg_type, str)
        # assert isinstance(msg, (int, str, list))
        assert isinstance(round, int)
        return self._send_msg(round=round, type=msg_type, message=msg, sent_to=None, send_to_readers=send_to_readers, view=view)

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
        # IDs sorted by ascending ID number. Returns index in writer list
        self.mem_data.round_writer_list.sort()
        coordinator_index = (round - 1) % (len(self.mem_data.round_writer_list))
        # Separate list for round and list for connections.
        return self.mem_data.round_writer_list[coordinator_index]

    def get_cancel_coordinatorID(self, view_change_num: int = None):
        """Decides the coordinator for a cancel round in the membership protocol.
        Should only change when there is a view-change in the cancellation."""
        sorted_nodes = sorted(self.mem_data.penalty_box.values(), key=lambda x: (x["honesty_counter"], -x["id"]), reverse=True)
        coordinator_id = sorted_nodes[view_change_num]["id"]
        return coordinator_id

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
        while (len(self.comm.list_connected_peers()) < (len(self.mem_data.ma_writer_list) + len(self.mem_data.round_reader_list)-1)):
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
        msg = self.broadcast("cancel", payload, round, view=self.view, send_to_readers=True)
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
    
    def insert_cancel_block(self, cancel_round, accuser_id):
        """Synchronizes the node on the round to insert the block by catching up or removing invalid blocks, and inserts the cancel block"""
        # if cancel_round == round + 1: # Cancel block is in next round 
        #     # Check for any blocks received in the meantime, else try to catch up.
        #     block = self._recv_msg(type="block", round=round)  
        #     if block:
        #         self.bcbd.insert_block(round, block)
        #         # Insert block in next round
        #         # Received block, insert cancel block in current round
        #         self.create_cancel_block(accuser=accuser_id, round=cancel_round)
        #         self.bcdb.insert_block(self.bcdb.get_round_number()+1, self.latest_block)
        #         self.publish_block()
        #     else:
        #         self.downloader.download_db()
        # elif cancel_round < round:  # Cancel block is in prior round
        #     # Remove all blocks from round to cancel_round. 
        #     self.bcdb.remove_blocks(round_begin=round)
        # elif cancel_round > round + 1:    # Cancel block is in much later round
        #     self.downloader.download_db()
        self.create_cancel_block(accuser=accuser_id)
        self.bcdb.insert_block(self.bcdb.get_round_number()+1, self.latest_block)
        self.publish_block()

    def create_cancel_block(self, accuser: int):
        """ Generates a cancel block """
        # assert isinstance(message, Message)
        canceller = accuser
        round = self.bcdb.get_round_number()+1
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
            payload=json.dumps({"type": "cancel", "payload": json.dumps((self.mem_data.round_disconnect_list, self.cancel_number))}))
        self.latest_block = cancel_block
        return cancel_block

    def publish_block(self):
        """Winning writer fetches latest block in chain and publishes it to queue"""
        if not self.mem_data.conf["is_local"]:
            # latest_block = self.bcdb.get_block_by_round_number(round)
            self.broker.publish_block(json.dumps(self.latest_block.as_tuple()))
            
    def get_cancel_block_payload(self, round):
        return json.dumps({"type": "cancel", "faulty_node": self.mem_data.round_disconnect_list, "cancel_number": self.cancel_number, "prev_hash": self.get_prev_hash(round=round), "round": round})
        
    def check_for_old_cancel_message(self, round):
        """Checks for cancel blocks of previous rounds and overwrites block with cancel block"""
        message = self._recv_msg(type="cancel")
        if message is not None:
            cancel_block = self.create_cancel_block(message)
            if int(message.round) != round:
                self.bcdb.insert_block(int(message.round), cancel_block, overwrite=True)
                
    def get_latest_block_as_tuple(self):
        latest_block_dict = self.bcdb.get_latest_block(dict_form=True)
        block_obj = Block.from_dict(latest_block_dict)
        return block_obj.as_tuple()
    
    def get_latest_block_as_block_obj(self):
        latest_block_dict = self.bcdb.get_latest_block(dict_form=True)
        try:
            return Block.from_dict(latest_block_dict)
        except:
            return None
            
    def check_append_block(self, block: Block):
        latest_block = self.get_latest_block_as_block_obj()
        if latest_block:
            if block.is_next(latest_block):
                self.bcdb.insert_block(block.round, block)
                return True
        
    def check_view_change(self, view: int) -> tuple:
        """Checks for view-change messages and returns (bool, min_view_change_value)
        Node broadcasts a view-change if:
            1. Its timer for view v expires.
            2. A node has received f+1 view-change messages for view > v, despite its timer not having expiring.
        Coordinator broadcasts a new-view if:
            1. It has received 2f+1 view-change messages for some view x > v.
        """
        # Check if received f+1 view-change messages from different nodes for view v+1
        # Adds the view-change messages back to message queue and permanently removes old view-change messages
        broadcast_view_change = False
        min_view_change_value = view
        broadcast_new_view = False
        count_view_change_num_node_is_coordinator = [0]*len(self.mem_data.round_writer_list)*3   # List of view-change messages for view where node is coordinator
        counter = 0
        node_is_coordinator = 0 # Number of times node is the selected coordinator for view-change message
        active_nodes_in_round = self.mem_data.round_reader_list + self.mem_data.round_writer_list   # .. This is subject to change with view-changes
        # Should be enough to search through once and fit to the round and view for a node in the round
        valid_view_change_messages = []
        invalid_view_change_messages = []
        while not self.view_change_message_queue.empty():
            msg = self.view_change_message_queue.get()
            if msg.cancel_number == self.cancel_number and msg.view > view and msg.from_id in active_nodes_in_round:
                if counter == 0:
                    min_view_change_value = msg.view
                elif msg.view < min_view_change_value:
                    min_view_change_value = msg.view
                if self.get_cancel_coordinatorID(msg.view) == self.id:
                    node_is_coordinator += 1
                count_view_change_num_node_is_coordinator[msg.view] += 1
                valid_view_change_messages.append(msg)
            else:
                invalid_view_change_messages.append(msg)
                if msg.view > min_view_change_value:
                    min_view_change_value = msg.view
        for msg in invalid_view_change_messages:
            self.view_change_message_queue.put(msg)
        for msg in valid_view_change_messages:
            self.view_change_message_queue.put(msg)
        # Check if new_view 
        if len(valid_view_change_messages) >= math.floor((len(self.mem_data.round_writer_list)-1)/3)+1:    # view-change messages >= f+1
            broadcast_view_change = True   # Broadcast view-change message
        if node_is_coordinator >= 2*math.floor((len(self.mem_data.round_writer_list)-1)/3)+1:   # Node has received 2f+1 view-change messages for view where it is the coordinator
            for counter, index in enumerate(count_view_change_num_node_is_coordinator):
                if counter >= 2*math.floor((len(self.mem_data.round_writer_list)-1)/3)+1:
                    broadcast_new_view = True
                    min_view_change_value = index
                    return broadcast_view_change, min_view_change_value, broadcast_new_view
        return broadcast_view_change, min_view_change_value, broadcast_new_view
    
    def verify_announce(self, announce_tuple):
        # announce_tuple = (hash, <reply>, ..., <reply>, signature)
        # reply has removed hash: reply = <round, (curr_version, proposed_version), signature>
        # announce = ()
        # hash, reply_list, signature = announce_tuple
        pass
    
    def send_new_view(self, view):
        """Node knows it is a cancel coordinator for the corresponding view. Should broadcast a new-view message"""
        # Need to know the view number for the new_view message, figure out the latest verified announce and block and broadcast both with new_view message
        # Start by getting all the messages in the queue for view_change
        received_view_changes = []
        while not self.view_change_message_queue.empty():
            msg = self.view_change_message_queue.get()
            if msg.view == view:
                received_view_changes.append(msg)
        # Check for the latest verified announce and block from the messages
        for msg in received_view_changes:
            # <view, round, from_id, cancel_round, cancel_msg, payload=(verified_announce, block), timestamp>
            # check for the latest verified announce and block
            json_msg = json.loads(msg.payload)
            # Check if need to append block
            self.check_append_block(Block.from_any(json_msg["block"]))
            faulty_node = json_msg["faulty_node"]
        # Start by node just sending its tuple of fault
        payload = json.dumps({"prev_hash": self.get_prev_hash(), "view": view, "cancel_number": self.cancel_number, "block": self.get_latest_block_as_tuple(), "faulty_node": faulty_node})    #TODO: payload should be cancel msg, all verified announce
        self.broadcast(msg_type="new_view", msg=payload, view=view, round=self.bcdb.get_latest_block(dict_form=False, col="round")[0][0])

    def send_view_change(self, view, faulty_node):
        payload = json.dumps({"prev_hash": self.get_prev_hash(), "view": view, "cancel_number": self.cancel_number, "block": self.get_latest_block_as_tuple(), "faulty_node": faulty_node})
        self.broadcast(msg_type="view_change", msg=payload, view=view, round=self.bcdb.get_latest_block(dict_form=False, col="round")[0][0])
    
    def send_propose_cancel(self, faulty_node: int):
        """Broadcasts a round cancellation proposal. Only happens if view=0"""
        # Need a unique identifier to differentiate between old and current cancel messages
        # Nodes do also not have a consensus on the prev_hash.
        payload = json.dumps({"type": "propose_cancel", "prev_hash": self.get_prev_hash(), "block": self.get_latest_block_as_tuple(), "cancel_number": self.cancel_number, "faulty_node": faulty_node})
        msg = self.broadcast("propose_cancel", payload,  self.bcdb.get_round_number(), view=self.view, send_to_readers=True)
        
    def get_propose_cancel(self) -> tuple():
        """Checks for propose_cancel message and returns round of propose_cancel, and the accuser and accused id"""
        propose_message = self._search_msg(type="propose_cancel", cancel_msg=True)
        # It should be the prev_hash, because a cancelled round has a prev_hash.
        # If a round was successfully cancelled, all honest nodes should have had the same prev_hash. No, not if a node was behind and threw a propose_cancel message.
        if propose_message:
            payload = json.loads(propose_message.payload)
            if payload["cancel_number"] >= self.cancel_number:    # Only check new cancel messages
                faulty_node = payload["faulty_node"]
                self.check_append_block(Block.from_any(payload["block"]))
                # TODO: Node receives verified announce message
                return propose_message.from_id, faulty_node
        return None, None
 
    def send_vote_cancel(self, faulty_node: int, view: int):
        """Broadcasts a round cancellation vote"""
        payload = json.dumps({"type": "vote_cancel", "faulty_node": faulty_node, "cancel_number": self.cancel_number, "view": view})
        msg = self.broadcast("vote_cancel", payload, self.bcdb.length, view=view, send_to_readers=True)
    
    def send_request_cancel(self, vote: tuple, view: int):
        """Broadcasts a round cancellation vote"""
        payload = json.dumps({"type": "request_cancel", "vote": vote, "block": self.get_latest_block_as_tuple(), "cancel_number": self.cancel_number, "view": view})
        msg = self.broadcast("request_cancel", payload, self.bcdb.length, view=view, send_to_readers=True)
    
    def get_request_cancel(self, accuser_id, accused_id, view=0):    # -> accuser_id, accused_id, broadcasted_view_change, broadcast_new_view, received_req_cancel
        """Blocks for request cancel message and returns accuser, accuser_id, and whether it broadcasted a view-change message.
        If timer expires or f+1 received view-change messages, returns None, None, True"""
        broadcasted_view_change = False
        broadcast_new_view = False
        request_cancel_message = None
        run_time = time.time()
        min_view_change = view
        received_request_cancel = False
        while time.time() < run_time + self.timeout*(view+1):   # May not be its own vote proposal
            request_cancel_message = self._recv_msg(type="request_cancel", cancel_msg=True, cancel_round=self.cancel_number, view=view)
            if request_cancel_message:
                self.check_append_block(Block.from_any(json.loads(request_cancel_message.payload)["block"]))
                received_request_cancel = True
                payload = json.loads(request_cancel_message.payload)
                accuser_id = payload["vote"][0]     # From coordinator, accuser is the one who proposed the cancellation
                accused_id = payload["vote"][1]     # From coordinator, accused is the one who is being accused
                return accuser_id, accused_id, broadcasted_view_change, broadcast_new_view, received_request_cancel, min_view_change
            broadcast_view_change, min_view_change, broadcast_new_view = self.check_view_change(view)
            if broadcast_new_view:  # Immediately move to new view
                return accuser_id, accused_id, broadcasted_view_change, broadcast_new_view, received_request_cancel, min_view_change
            elif broadcast_view_change and not broadcasted_view_change: # f+1 view-changes received
                self.send_view_change(view+1, accused_id)
                # Node should broadcast view-change message, but not commit to view-change unless it receives 2f+1 view-change messages for view v+1 or new-view message for view v+1
                broadcasted_view_change = True
            # TODO: Node receives new-view message.
        time.sleep(0.01)
        if not broadcasted_view_change:
            self.send_view_change(view+1, accused_id)
        return accuser_id, accused_id, broadcasted_view_change, broadcast_new_view, received_request_cancel, min_view_change


    def get_vote_ballot(self, accuser_id, accused_id,  vote_for_accused, view, broadcasted_view_change) -> tuple():
        # TODO: Should also check for view-change messages
        # TODO: Node should check for view-change messages in the view it is coordinator
        """Blocks for vote messages or times out. Either returns (accuser_id, accused_id, broadcasted_view_change) or (None, None, True)"""
        start_time = time.time()
        votes = []
        consensus = False
        vote_accuser = 0
        vote_accused = 0
        if vote_for_accused:
            vote_accused += 1
            votes.append(accused_id)
        else:
            vote_accuser += 1
            votes.append(accuser_id)
        while len(votes) < len(self.mem_data.round_writer_list) + len(self.mem_data.round_reader_list) and not consensus:
            # TODO: Should also check for 
            message = self._recv_msg(type="vote_cancel", cancel_round=self.cancel_number, cancel_msg=True, view=view)
            if message is not None:
                payload = json.loads(message.payload)
                if payload["faulty_node"] == accuser_id:
                    vote_accuser += 1
                elif payload["faulty_node"] == accused_id:
                    vote_accused += 1
                else:
                    pass
                votes.append(payload["faulty_node"])
                # Check if consensus reached
                # Should be that we expect deterministic votes so that f+1 votes for accuser or accused is enough
                if vote_accuser > len(self.mem_data.round_writer_list) / 3 or vote_accused > len(self.mem_data.round_writer_list) / 3:
                    consensus = True
            # Check for view-change messages
            # if self.check_view_change(round, view):
            #     # Node should broadcast view-change message, but not commit to view-change unless it receives 2f+1 view-change messages for view v+1 or new-view message for view v+1
            #     self.broadcast("view_change", json.dumps({"type": "view_change", "view": view+1}), round, send_to_readers=True)

            # elif time.time() - start_time > self.timeout * (view+1):    # Expired 
            #     if not broadcasted_view_change:
            #         self.send_view_change(view+1, accused_id)
            #     return None, None, True

            
            
            time.sleep(0.01)
        # Majority voted for accuser
        if vote_accuser > len(self.mem_data.round_writer_list) / 2:
            # Both nodes sanctioned from consensus
            self.mem_data.round_disconnect_list.append(accuser_id)
            self.mem_data.round_disconnect_list.append(accused_id)
        else:
            # accused sanctioned from consensus
            self.mem_data.round_disconnect_list.append(accused_id)
        self.cancel_number += 1

    def vote(self, accuser_id, accused_id, view=0, broadcasted_view_change=False):
        """Node votes for accusing or accused node"""
        self.comm.peers_disconnected()
        if accused_id in self.mem_data.disconnected_nodes:  # Agrees with accusing node
            self.send_vote_cancel(faulty_node=accused_id, view=view)
            self.get_vote_ballot(accuser_id, accused_id, vote_for_accused=True, view=view, broadcasted_view_change=broadcasted_view_change)    # Blocks on receiving all votes
        else:   # Disagrees with accusing node
            self.send_vote_cancel(faulty_node=accuser_id, view=view)
            self.get_vote_ballot(accuser_id, accused_id, vote_for_accused=False, view=view, broadcasted_view_change=broadcasted_view_change)    # Blocks on receiving all votes
        
    def node_check_round_cancelled(self, view: int=0, accuser_id=None, accused_id=None):
        """Helper function for checking if round is cancelled and selecting coordinator for cancellation round"""
        self.view = view
        if self.get_cancel_coordinatorID(view) == self.id:
            return self.coordinator_round_cancelled(view, accuser_id, accused_id)
        else:
            return self.writer_round_cancelled(view, accuser_id, accused_id)

    
    def writer_round_cancelled(self, view: int=0, accuser_id=None, accused_id=None):
        """Checks for round cancellation messages for the current round and proposes a cancellation if it has not been proposed yet. Goes through the cancellation protocol"""
        # If view > 0, round already cancelled. Do not send another propose_cancel message.
        if view is None:
            view = 0
        if view == 0:
            accuser_id, accused_id = self.get_propose_cancel()   # Check for received propose_cancel based on cancel_round
            peer_disconnected =  self.comm.peers_disconnected()
            if peer_disconnected and not accused_id:  # Check for own propose cancel if not received propose_cancel
                accused_id = self.mem_data.disconnected_nodes[0]
        if accused_id or view > 0:  # If there is a faulty node
            # Broadcast own cancel message proposal, calculate votes, and set cancel block
            if view == 0:
                self.send_propose_cancel(faulty_node=accused_id)   # Broadcasts own cancel block proposal
            # Waits for request_cancel from coordinator 
            accuser_id, accused_id, broadcasted_view_change, broadcast_new_view, received_request_cancel, min_view_change = self.get_request_cancel(accuser_id, accused_id, view)
            if broadcast_new_view:
                self.send_new_view(min_view_change)
                return self.node_check_round_cancelled(view+1, accuser_id, accused_id)   # Commit to moving to new view
            if not received_request_cancel and broadcasted_view_change:  # Timed out before receiving request_cancel message or received 2f+1 view-change messages for view where node is coordinator, coordinator is faulty. Move to next view
                return self.node_check_round_cancelled(view+1, accuser_id, accused_id)   # Commit to moving to new view
            self.vote(accuser_id, accused_id, view, broadcasted_view_change)
            # Given that coordinator is not faulty node, nodes are synced on vote
            # Create cancel block and moves on. Each node creates its own cancel block. Payload is the disconnect list
            self.bcdb.remove_blocks(round_begin=self.bcdb.get_round_number())
            # Now the last f+1 rounds may be cancelled due to the cancellation.
            # If the round cancellation is for a later round, the node should catch up. given, that there were no cancellations there.
            return True
        return False
     
    def coordinator_round_cancelled(self, view=0, accuser_id=None, accused_id=None) -> tuple:
        """Checks for round cancellation messages for the current round and proposes a cancellation if it has not been proposed yet"""
        # cancel_round = round
        # Check for received propose_cancel
        is_accuser = False
        if view == 0:
            # Node in view 0 
            accuser_id, accused_id = self.get_propose_cancel()
            if self.comm.peers_disconnected() and not accused_id:  # Check and returns true if any node has disconnected
                accused_id = self.mem_data.disconnected_nodes[0]
                is_accuser = True
        if accused_id or view > 0:
            if not accuser_id:
                accuser_id = self.id
            if view == 0:
                self.send_propose_cancel(faulty_node=accused_id)   # Broadcasts own cancel block proposal
                # Has delivered 1 or 2 out of 2f+1 propose cancels. Wait for 2f+1 before broadcasting a request_cancel
                broadcasted_view_change, broadcast_new_view, received_request_cancel, min_view_change = self.wait_for_supermajority_propose_cancel(is_accuser, accused_id, view)
                # 1. Broadcasted view_change f+1 but success
                # 2. Broadcasted view_change and failed
                # 3. Did not broadcast view change and success.
                # 4. Should broadcast new_view and failed.
                if broadcast_new_view:
                    self.send_new_view(min_view_change)
                    return self.node_check_round_cancelled(view+1, accuser_id, accused_id)   # Commit to moving to new view
                if not received_request_cancel and broadcasted_view_change:  # Timed out before receiving request_cancel message or received 2f+1 view-change messages for view where node is coordinator, coordinator is faulty. Move to next view
                    return self.node_check_round_cancelled(view+1, accuser_id, accused_id)   # Commit to moving to new view
            self.send_request_cancel((accuser_id, accused_id), view)
            self.vote(accuser_id, accused_id, view=view, broadcasted_view_change=False)
            # Create cancel block and moves on. Each node creates its own cancel block. Payload is the disconnect list
            # self.create_cancel_block(accuser=accuser_id)
            # Remove the latest block and go back a round
            self.bcdb.remove_blocks(round_begin=self.bcdb.get_round_number())
            return True
        return False
    
    def wait_for_supermajority_propose_cancel(self, is_accuser, accused_id, view):
        """Waits for supermajority of propose_cancel. Broadcasts view_change if fits. Returns what happened in algo"""
        run_time = time.time()
        broadcasted_view_change = False
        broadcast_new_view = False
        achieved_majority = False
        received_messages = 2 - is_accuser   # From itself and one other node if it is not accuser
        min_view_change = view
        while time.time() < run_time + self.timeout:
            # Check for new propose cancel for the view and the cancel number
            msg = self._search_msg(type="propose_cancel", cancel_msg=True)
            if msg:
                received_messages += 1
                dict_payload = json.loads(msg.payload)
                # Check if node has newer block
                self.check_append_block(Block.from_any(tuple(dict_payload["block"])))
                # Check for 2f+1 received_messages
                if received_messages >= 2*math.floor((len(self.mem_data.round_writer_list)-1)/3)+1:
                    return achieved_majority, broadcasted_view_change, achieved_majority, min_view_change
                if not broadcasted_view_change: # Broadcast view-change message if f+1 view-change messages received
                    broadcast_view_change, min_view_change, broadcast_new_view = self.check_view_change(view)
                if broadcast_new_view:  # Move to new view
                    return achieved_majority, broadcasted_view_change, achieved_majority, min_view_change
                elif broadcast_view_change:
                    self.send_view_change(min_view_change, accused_id)
                    # Node should broadcast view-change message, but not commit to view-change unless it receives 2f+1 view-change messages for view v+1 or new-view message for view v+1
                    broadcasted_view_change = True
            # Check for sending view_change and new_view
        if not broadcasted_view_change:
            self.send_view_change(1, accused_id)
        return achieved_majority, broadcasted_view_change, achieved_majority, min_view_change

            
                
            

    # Consensus protocol messages
    def get_request_msg(self, id: int, round: int) -> tuple:
        """Blocks for request message and sends back message object and boolean for round cancellation"""
        message = None
        while message is None:
            message = self._recv_msg(type="request", recv_from=id, round=round, cancel_round=self.cancel_number, view=self.view)
            time.sleep(0.01)
            round_cancelled = self.node_check_round_cancelled()
            if round_cancelled:
                return None
        return message
    
    def get_announce_msg(self, id, round) -> tuple:
        """Blocks for announce message and sends back message object and boolean for round cancellation"""
        message = None
        while message is None:
            message = self._recv_msg("announce", recv_from=id, round=round, cancel_round=self.cancel_number, view=self.view)
            time.sleep(0.01)            
            round_cancelled = self.node_check_round_cancelled()
            if round_cancelled:
                return None
        return message
    
    def get_otp_numbers(self, round) -> tuple:
        """Blocks OTP nubmers from all active nodes and returns list of numbers and boolean for round cancellation"""
        numbers = []
        no_recv_messages = 0
        while no_recv_messages < len(self.mem_data.round_writer_list) + len(self.mem_data.round_reader_list) - 1:
            message = self._recv_msg(type="reply", round=round, cancel_round=self.cancel_number, view=self.view)
            if message is not None:
                no_recv_messages += 1
                if message.from_id in self.mem_data.round_writer_list:
                    numbers.append([message.from_id, message.payload])    #(id, otp)
            round_cancelled = self.node_check_round_cancelled()
            if round_cancelled:
                return None
            time.sleep(0.01)
        return numbers
    
    def receive_block(self, winner_id: int, round: int) -> tuple:
        message = None
        while message is None:
            message = self._recv_msg(type="block", recv_from=winner_id, round=round, cancel_round=self.cancel_number, view=self.view)    # Gets back tuple block
            round_cancelled = self.node_check_round_cancelled()
            if round_cancelled:
                return None
            time.sleep(0.01)
        # if not json.loads(message.payload):   # Winner had nothing to write. Round skipped
        #     return None, None
        # Receives json payload
        block = Block.from_any(message.payload) # Converts tuple json block to block object
        if not self.verify_block(block):
            self.cancel_round(faulty_node=winner_id,round=round)   # Sets latest block as cancel block 
        else:
            # Check if other writer cancelled block
            message = self._recv_msg(type="cancel") #TODO: Should not be a part of it. Just checking for recent propose_cancel messages with cancel_round + 1 and valid latest_hash
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
        return block

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
        self._send_msg(round, "reply", pad, sent_to=coordinator_id, view=self.view)

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
        message  = self.get_request_msg(coordinator_id, round)
        if not message: # Round cancelled
            return False
        # Step 1.1 - Check for new membership version based on message
        is_valid_version = self.check_membership_version_update(message.version)
        # Throw cancel block if not valid membership version
        # if not is_valid_version:
        #     self.cancel_round(faulty_node=coordinator_id, round=round)   # Sets latest block as cancel block
        # Step 2 - Generate next number and transmit to Coordinator
        pad = self.generate_pad()
        self._send_msg(round, "reply", pad, sent_to=coordinator_id)
        # Step 3 - Waiting for announcement from the Coordinator
        message = self.get_announce_msg(coordinator_id, round)
        if not message: # Round cancelled
            return False
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
            self.broadcast("block", json.dumps(block.as_tuple()), round, view=self.view, send_to_readers=True)  
        elif winner_verified:   # Node receives block from winner
            received_block = self.receive_block(winner_id, round)
            if self.mem_data.round_disconnect_list:
                # Round was cancelled
                return False
            elif not received_block:
                return round
        else:   # Round failed verification
            #TODO: Should throw propose_cancel
            self.cancel_round(faulty_node=winner_id, round=round)
        vverbose_print(f"[LATEST BLOCK] the latest block is: {self.latest_block}")
        self.bcdb.insert_block(round, self.latest_block)
        self.publish_block()
        return round

    def coordinator_round(self, round: int):
        vverbose_print(f"Round: {round} and ID={self.id}")
        assert isinstance(round, int)
        self.check_for_old_cancel_message(round=round)  #TODO: Clear up cancel blocks
        # Step 0 - Fetch latest membership configuration file from MA
        self.mem_data.get_remote_conf()
        # Step 1 - Request OTP number from writers. Piggyback version number on message
        self.broadcast(msg_type="request", msg=round, round=round, view=self.view, send_to_readers=True)
        # Step 2 - Wait for numbers reply from all
        numbers = self.get_otp_numbers(round)
        if not numbers: # Round cancelled
            return False
        # Step 3 - Declare and announce winner.
        winner = self.calculate_sum(numbers)
        self.broadcast(msg_type="announce", msg=winner, round=round, view=self.view, send_to_readers=True)
        winner_id = winner[2]
        # Step 4 - Receive new block (from winner)
        received_block = self.receive_block(winner_id, round)
        if self.mem_data.round_disconnect_list: # Round cancelled
            return False
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
                self.view = 0   # Reset after round cancellation
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
                    self.coordinator_round(round)
                else:
                    self.writer_round(round, coordinator)
                vverbose_print(f"[ROUND COMPLETE] round {round} finished with writer with ID {coordinator} as  the coordinator")
                # if curr_round > round:
                #     # Round was cancelled and node needs to catch up
                #     # Should do that before it adds the cancel block
                #     ...
                # elif curr_round < round:
                #     # Round was cancelled in a prior round, node needs to delete later blocks
                #     ...
                # round = curr_round
                round = self.bcdb.length
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
    def _send_msg(self, round: int, type: str, message, sent_to=None, send_to_readers=False, view=0):
        assert isinstance(sent_to, (int, NoneType))
        assert isinstance(type, (str, NoneType))
        # implements a remote procedure call wrt protocolCommunication
        msg = Message.create_msg(round=round, from_id=self.id, message=message, type=type, version=self.mem_data.get_version(), cancel_round=self.cancel_number, view=view)
        self.comm.send_msg(message=msg, send_to=sent_to, send_to_readers=send_to_readers)
        return msg

    def get_new_messages(self):
        messages = self.comm.recv_msg()  # Checks for new messages from other writers and adds them to the queue
        """Takes messages and adds to message or cancel queue as a Message object."""
        normal_msg_types = ["request", "reply", "announce", "block", "cancel"]
        cancel_msg_types = ["propose_cancel", "vote_cancel", "request_cancel"]
        view_change_msg_types = ["view_change", "new_view"]
        for msg in messages:
            msg = Message.from_json(msg[1]) # Takes msg json and loads into object
            if msg:
                if msg.type in normal_msg_types:
                    self.message_queue.put(msg)
                elif msg.type in cancel_msg_types:
                    self.cancel_message_queue.put(msg)
                elif msg.type in view_change_msg_types:
                    self.view_change_message_queue.put(msg)

    def _search_msg(self, type=None, recv_from=None, round=None, cancel_msg=False, view_change_msg=False):
        """Searches for message in queue and returns it if found. Otherwise returns None"""
        self.get_new_messages()
        if view_change_msg:
            search_queue = self.view_change_message_queue
        elif cancel_msg:
            search_queue = self.cancel_message_queue
        else:
            search_queue = self.message_queue
        add_back_queue = []
        stop_searching = False
        found_msg = None
        while not search_queue.empty() and not stop_searching:
            msg = search_queue.get()
            if msg:
                type_check = True
                from_check = True
                round_check = True
                cancel_round_check = True
                if type:
                    type_check = msg.type == type
                if recv_from:
                    from_check = msg.from_id == recv_from
                if round:    # Only check for round if not cancel or view-change message. 
                    round_check = msg.round == round
                if cancel_msg or view_change_msg:
                    cancel_round_check = msg.cancel_number == self.cancel_number
                if type_check and from_check and round_check and cancel_round_check:
                    stop_searching = True
                    found_msg = msg
                else:
                    add_back_queue.append(msg)
        for msg in add_back_queue:
            search_queue.put(msg)
        return found_msg
    
    # MSG FORMAT <round nr>-<from id>-<to id>-<msg type>-<msg body>
    def _recv_msg(self, type=None, recv_from=None, round=None, cancel_msg=False, view_change=False, view=None, cancel_round=None):
        assert isinstance(type, (str, NoneType))
        assert isinstance(recv_from, (int, NoneType))
        assert isinstance(round, (int, NoneType))
        # implements a remote procedure call wrt protocolCommunication
        self.get_new_messages()        
        if self.message_queue.empty() and not cancel_msg:
            vverbose_print("message queue empty")
            return None
        elif self.cancel_message_queue.empty() and cancel_msg:
            vverbose_print("cancel message queue empty")
            return None
        elif self.view_change_message_queue.empty() and view_change:
            return None
        if cancel_msg:
            msg = self.cancel_message_queue.get() # Reader checks for cancel messages
        elif view_change:
            msg = self.view_change_message_queue.get()
        else:
            msg = self.message_queue.get() # Reader checks for cancel messages and takes request message
        if not msg:
            self.message_queue.put(msg)
            return None
        type_check = True
        from_check = True
        round_check = True
        cancel_round_check = True
        view_check = True
        if type:
            type_check = msg.type == type
        if recv_from:
            from_check = msg.from_id == recv_from
        if round:
            round_check = msg.round == round
        if cancel_round:
            cancel_round_check = msg.cancel_number == cancel_round
        if view_change:
            view_check = msg.view == view
        if type_check and from_check and round_check and cancel_round_check and view_check:
            return msg  # Returns msg object if all is true
        else:
            if cancel_msg:
                self.cancel_message_queue.put(msg)
            elif view_change:
                self.view_change_message_queue.put(msg)
            else:
                self.message_queue.put(msg)    # Message added back. Was not supposed to be taken off of the queue
        return None

