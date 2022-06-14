import interfaces
from queue import Queue
import hashlib


from queue import Queue
from threading import Thread
import struct
import time
import ast

import sqlite3
import sys
import argparse
import random
import os
import json
from protocom import ProtoCom
from tcpserver import TCP_Server, ClientHandler

from interfaces import (
    ProtocolCommunication,
    BlockChainEngine,
    ClientServer,
    ProtocolEngine,
)

NoneType = type(None)


transactions = [
    ["none", "WALLET1", "500", "init"],
    ["none", "WALLET1", "500", "commit"],
    ["none", "WALLET2", "500", "init"],
    ["none", "WALLET2", "500", "commit"],
    ["none", "WALLET3", "500", "init"],
    ["none", "WALLET3", "500", "commit"],
    ["none", "WALLET4", "500", "init"],
    ["none", "WALLET4", "500", "commit"],
    ["WALLET2", "WALLET4", "100", "init"],
    ["WALLET2", "WALLET4", "100", "commit"],
    ["WALLET2", "WALLET1", "50", "init"],
    ["WALLET2", "WALLET1", "50", "commit"],
    ["WALLET3", "WALLET1", "150", "init"],
    ["WALLET3", "WALLET1", "150", "commit"],
]


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
    
    Block is a 7 item tuple containing the following attributes:
        prev_hash,
        writerID,
        coordinatorID,
        payload,
        winning_number,
        writer_signature,
        _ (current hash?)
    '''
    assert isinstance(block, tuple)
    assert len(block) == 7
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
    # 0x + the key hex string
    return "0x" + key.hexdigest()


class ProtoEngine(interfaces.ProtocolEngine):
    # Executes the consensus protocol
    # Communincates with protocolCommunication, via RPC to send and receive messages
    # Need to determine who blocks and where

    def __init__(
        self,
        keys: tuple,
        comm: interfaces.ProtocolCommunication,
        blockchain: interfaces.BlockChainEngine,
        clients: interfaces.ClientServer,
    ):  # what are the natural arguments
        assert isinstance(keys, tuple)
        assert len(keys) == 3
        # The interface initiates the following attributes
        interfaces.ProtocolEngine.__init__(self, comm, blockchain, clients)

        self.keys = keys

        self.clients = clients

        self.writer_list = []  # list of writer ID's
        self.max_writers = 4
        # Defining e
        self.modulus = 65537
        # The id of us the writer
        self.ID = None
        # The first block
        genesis_block = ("0", 0, 0, "genesis block", 0, "0", "0")
        # The latest block to be minted
        self.latest_block = genesis_block
        # Messages in our writer's queue
        self.message_queue = Queue()
        # Blockhain database: the blockchain engine
        self.bcdb.insert_block(0, genesis_block)
        ## TESTING WRITING TO DATABASE
        the_block = ["prevHash", 1, 2, "the payload", 1, "writer signature", "the hash"]
        msg = self.bcdb.read_blocks(0, 4)
        print(f"[MESSAGE READ GENESIS BLOCK] The message: {msg}")
        # For how many rounds the blockchain should run for
        self.rounds = None
        # Comes from the original config file (config.json) 
        self.conf = None
        # maintain a payload
        self.stashed_payload = None


    def set_rounds(self, round: int):
        ''' A round is a minting of a block, this defines for how many rounds the blockchain runs for'''
        assert isinstance(round, int)
        self.rounds = round

    def set_conf(self, data):
        ''' Assign config  '''
        assert isinstance(data, object)
        self.conf = data


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

    def set_ID(self, id: int):
        assert isinstance(id, int)
        self.ID = id

    def set_writers(self, writers: list):
        for w in writers:
            assert isinstance(w, int)
        self.writer_list = writers

    def verify_block(self, block: tuple):
        '''
        To verify a block both the signature and hash of the block must be correct
        '''
        assert isinstance(block, tuple)
        writer = block[1]
        payload = block[3]
        signature = int(block[5], 16)
        writer_pubkey = self.conf["active_writer_set"][int(writer) - 1]["pub_key"]

        D = bytes_to_long(payload.encode("utf-8")) % writer_pubkey
        res = pow(signature, self.keys[2], writer_pubkey)
        res = res % writer_pubkey
        # Get the hash based on what is in the block
        hash = hash_block(block)

        signature_correct = res == D

        # Verify the hash
        hash_correct = hash == block[6]

        # both signature and hash are correct => True else False
        return signature_correct and hash_correct

    def broadcast(self, msg_type: str, msg, round: int):
        assert isinstance(msg_type, str)
        assert isinstance(msg, (int, str, list))
        assert isinstance(round, int)
        self._send_msg(round=round, type=msg_type, message=msg, sent_to=None)

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

    def get_payload(self):
        """Retrieves payload from the client server part
        """
        # Get the queue we have from the clients
        # These are the transactions the client 
        # Has sent to our writer
        queue = self.clients.payload_queue
        if queue.empty():
            print("queue empty...")
            # If empty we just return anything
            return "arbitrarypayload"
        else:
            payload = queue.get()
            print(f"INSERTING PAYLOAD TO CHAIN")
            print(payload)
            self.stashed_payload = payload
            return payload[1]
        # else:
        #     if self.ID == 5:
        #         if transactions != []:
        #             l = transactions.pop(0)
        #             return f"walletserv,{l[0]},{l[1]},{l[2]},{l[3]}"
        #         else:
        #             return "arbitrarypayload"
        #     else:
        #         return "arbitrarypayload"

    def get_coordinatorID(self, round: int):
        """Decides the coordinator for the round
        """
        assert isinstance(round, int)
        # 8 - 1 % (3+1) 
        # 7 % 4 = 3
        # 8 
        coordinator = (round - 1) % (len(self.writer_list) + 1)
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
        # TODO: Where is the self.writer_list instantiated?
        while len(self.comm.list_connected_peers()) != len(self.writer_list):
            time.sleep(1)
        print(f"ID={self.ID} -> connected and ready to build")
        return None

    def cancel_round(self, cancel_log: str, round: int):
        """
        Cancel the round, send cancel message to errbody and write cancel block
        """
        self.broadcast("cancel", cancel_log, round)
        fake_message = f"{round}-{self.ID}-0-cancel-hehe"
        self.create_cancel_block(fake_message)

    def create_block(self, pad: int, coordinatorID: int, round):
        assert isinstance(pad, int)
        assert isinstance(coordinatorID, int)

        prev_hash = self.bcdb.read_blocks(round - 1, col="hash")[0][0]
        prev_hash = str(prev_hash)
        # Returns payload of writer or arbitrary string if there is no payload
        payload = self.get_payload()
        print(f"[PAYLOAD] the payload is: {payload} from the TCP server payload_queue")
        signature = self.sign_payload(payload)
        winning_number = pad
        coordinatorID = coordinatorID
        writerID = self.ID

        block = (
            prev_hash,
            writerID,
            coordinatorID,
            payload,
            winning_number,
            signature,
            -1,
        )

        hash = hash_block(block)

        block = (
            prev_hash,
            writerID,
            coordinatorID,
            payload,
            winning_number,
            signature,
            hash,
        )

        """if self.ID == 2:
            block = (
                prev_hash,
                writerID,
                coordinatorID,
                "wrongpayload",
                winning_number,
                signature,
                hash,
            )"""

        if self.stashed_payload is not None:
            confirm_payload = (self.stashed_payload[0], self.stashed_payload[1], hash)
            self.clients.confirm_queue.put(confirm_payload)
            print("PAYLOAD CONFIRMATION SENT")
            self.stashed_payload = None
        return block

    def create_cancel_block(self, message: str):
        ''' Generates a cancel block '''
        assert isinstance(message, str)
        parsed_message = message.split("-")
        canceller = parsed_message[1]
        round = int(parsed_message[0])
        coor_id = self.get_coordinatorID(round)
        prev_hash = self.bcdb.read_blocks(round - 1, col="hash")[0][0]
        prev_hash = str(prev_hash)
        cancel_block = (
            prev_hash,
            0,
            coor_id,
            f"round {round} cancelled by {canceller}",
            0,
            "0",
            "0",
        )
        cancel_block = (
            prev_hash,
            0,
            coor_id,
            f"round {round} cancelled by {canceller}",
            0,
            "0",
            hash_block(cancel_block),
        )
        self.latest_block = cancel_block
        return cancel_block

    def check_for_old_cancel_message(self, round):
        message = self._recv_msg(type="cancel")
        if message is not None:
            parsed_message = message.split("-")
            cancel_block = self.create_cancel_block(message)
            if int(parsed_message[0]) != round:
                self.bcdb.insert_block(
                    int(parsed_message[0]), cancel_block, overwrite=True
                )

    # The round for the writer when you are not coordinator
    def writer_round(self, round: int, coordinatorID: int):
        assert isinstance(round, int)
        assert isinstance(coordinatorID, int)

        # Step 1 - Receive request from Coordinator
        message = None
        while message is None:
            message = self._recv_msg("request", recv_from=coordinatorID)
            time.sleep(0.01)
        print("[REQUEST MESSAGE] Received message of request for OTP from coordinator")
        # Step 2 - Generate next number and transmit to Coordinator

        pad = self.generate_pad()
        self._send_msg(round, "reply", pad, sent_to=coordinatorID)

        # Step 3 -
        message = None
        while message is None:
            message = self._recv_msg("announce", recv_from=coordinatorID)
            time.sleep(0.01)
        print("[WINNER MESSAGE] received message of winner writer from coordinator")
        # Step 4 - Verify and receive new block from winner
        parsed_message = message.split("-")
        winner = ast.literal_eval(parsed_message[4])
        # 
        verified_round = self.verify_round_winner(winner, pad)
        print(f"[WINNER WRITER] writer with ID {winner[2]} won the round")
        if verified_round and self.ID == winner[2]:
            # I WON

            # First check if the previous round was cancelled and I had not seen the message yet
            self.check_for_old_cancel_message(round)
            block = self.create_block(pad, coordinatorID, round)
            self.latest_block = block
            # Broadcast our newest block before writing into chain
            self.broadcast("block", str(block), round)  

        elif verified_round:
            # Wait for a block to verify
            message = None
            while message is None:
                message = self._recv_msg(type="block", recv_from=winner[2], round=round)
                time.sleep(0.01)
            # TODO: Fails here 
            print(f"[NEW BLOCK VERIFICATION] {message}")
            parsed_message = message.split("-")
            print(f"[PARSED MESSAGE] {parsed_message}")
            # 2-1-100-block-('0xfc0ec25ad60aa9f0e254a7b9ad982b6852166e5b61098773252d27a620f46097', 1, 2, 'TESTclient,C-REQUEST,fjolnir', 20265, '0xa3ede6fd176eed10ffa58f48874d42b8556f8099113f86443e7d2012612cc8f62a2ab74f4b16b2f732a1dfd08a528ca6ca52cdeba233635e433d581f1a8a409', '0xf536298287fe32e5dfc265c77dc284113bdad46fd3d0e7d4c859f946e818e6db')
            block = ast.literal_eval(parsed_message[4]) # The block 

            if not self.verify_block(block):
                self.cancel_round("Block not correct", round)
                print(block)
                print("ERROR, BLOCK NOT CORRECT")
            else:

                # Check if cancelled round
                message = self._recv_msg(type="cancel")
                if message is not None:
                    print("[ROUND CANCEL] the round was cancelled because of cancel message")
                    parsed_message = message.split("-")
                    cancel_block = self.create_cancel_block(message)
                    # If the block belongs to this round we continue
                    if int(parsed_message[0]) != round:
                        self.bcdb.insert_block(
                            int(parsed_message[0]), cancel_block, overwrite=True
                        )
                        self.latest_block = block
                    else:
                        # The block does not belong to this round
                        # We assign the latest round as a cancel block
                        self.latest_block = cancel_block
                else:
                    self.latest_block = block
        else:
            # Round is not verified
            # Cancel the round
            print("[ROUND CANCEL] round was cancelled because it was not verified")
            self.cancel_round("Round not verified", round)
        print(f"[LATEST BLOCK] the latest block is: {self.latest_block}")
        self.bcdb.insert_block(round, self.latest_block)

    def coordinator_round(self, round: int):
        print(f"Round: {round} and ID={self.ID}")

        assert isinstance(round, int)

        # Step 1 -
        self.check_for_old_cancel_message(round=round)
        print("done with check_for_old_cancel_message")

        self.broadcast(msg_type="request", msg=round, round=round)
        print("done broadcast")

        # Step 2 - Wait for numbers reply from all
        numbers = []
        # Currently waiting for number from all writers in list
        # MSG FORMAT <round nr>-<from id>-<to id>-<msg type>-<msg body>
        print("Len numbers:",len(numbers))
        print("Len writer_list:",len(self.writer_list))
        count = 1
        while len(numbers) < len(self.writer_list):
            print(f"while: {count}")
            count += 1
            print("before recv_msg")
            message = self._recv_msg(type="reply")
            print("after recv_msg")
            print(message)
            if message is not None:
                print("message is NOT none")
                parsed_message = message.split("-")
                numbers.append([int(parsed_message[1]), int(parsed_message[4])])
            print("message is none")
            # if count == 2:
            #     break
            time.sleep(0.01)

        # Step 3 - Declare and announce winner

        winner = self.calculate_sum(numbers)
        self.broadcast("announce", winner, round)

        # Step 4 - Receive new block (from winner)
        message = None
        winner_id = winner[2]
        while message is None:
            message = self._recv_msg(type="block", recv_from=winner_id, round=round)
            time.sleep(0.01)
        parsed_message = message.split("-")
        block = ast.literal_eval(parsed_message[4])
        if not self.verify_block(block):
            self.cancel_round("Round not verified", round)
            print("ERROR, NOT CORRECT BLOCK")
        else:

            # Finally - write new block to the chain (DB)

            # Check if cancelled round
            # time.sleep(0.5)
            message = self._recv_msg(type="cancel")

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

    def run_forever(self):
        """
        """
        # Expect all writers to join. Program does not start until writers with ID 1-5 are all connected
        self.join_writer_set()
        print("[ALL JOINED] all writers have joined the writer set")
        count = 1
        while True:
            coordinator = self.get_coordinatorID(count)
            print(f"CordinatorId: {coordinator}")
            if coordinator == self.ID:
                self.coordinator_round(count)
                print("after coordinator")
            else:
                print("before writer_round")
                self.writer_round(count, coordinator)
                print("after writer_round")
            print(f"[ROUND COMPLETE] round {count} finished with writer with ID {coordinator} as  the coordinator")
            count += 1
            if count > self.rounds and self.rounds:
                # self.bcdb.__del__()     # Close database connection
                break

    # MSG FORMAT <round nr>-<from id>-<to id>-<msg type>-<msg body>
    def _send_msg(self, round: int, type: str, message, sent_to=None):
        assert isinstance(sent_to, (int, NoneType))
        assert isinstance(type, (str, NoneType))
        # implements a remote procedure call wrt protocolCommunication
        self.comm.send_msg(f"{round}-{self.ID}-{100}-{type}-{message}", send_to=sent_to)

    # MSG FORMAT <round nr>-<from id>-<to id>-<msg type>-<msg body>
    def _recv_msg(self, type=None, recv_from=None, round=None):
        assert isinstance(recv_from, (int, NoneType))
        assert isinstance(type, (str, NoneType))
        assert isinstance(round, (int, NoneType))
        # implements a remote procedure call wrt protocolCommunication
        rec = self.comm.recv_msg()
        # rec = [(1, '1-1-100-request-1')]
        for message in rec:
            self.message_queue.put(message[1])
        
        if self.message_queue.empty():
            print("message queue empty")
            return None
        # TODO: Why do we take the first message off of the queue when we have a list?
        mess = self.message_queue.get()
        print(mess)
        parsed_message = mess.split("-")
        type_check = True
        from_check = True
        round_check = True

        if type:
            # rec = [(1, '1-1-100-request-1')]
            # parsed_message = "request"
            type_check = parsed_message[3] == type
        if recv_from:
            from_check = int(parsed_message[1]) == recv_from
        if round:
            round_check = int(parsed_message[0]) == round

        if type_check and from_check and round_check:
            return mess
        else:
            self.message_queue.put(mess)
        
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
    with open("./src/config.json", "r") as f:
        data = json.load(f)

    # sqlite db connection
    dbpath = f"/src/db/blockchain{id}.db"
    connection = sqlite3.connect(os.getcwd() + dbpath, check_same_thread=False)

    # p2p network
    pcomm = ProtoCom(id, data)
    pcomm.daemon = True
    pcomm.start()

    # bce, blockchain writer to db
    bce = BlockChainEngine(connection)

    # client server thread
    if id == 1:
        TCP_IP = data["active_writer_set"][id - 1]["hostname"]
        TCP_PORT = 15005
        print("::> Starting up ClientServer thread")
        clients = TCP_Server("the server", TCP_IP, TCP_PORT, ClientHandler, bce)
        cthread = Thread(target=clients.run, name="ClientServerThread")
        cthread.daemon = True
        cthread.start()
        print("ClientServer up and running as:", cthread.name)
    else:
        clients = ClientServer()

    keys = data["active_writer_set"][id - 1]["priv_key"]

    # run the protocol engine, with all the stuff
    w = ProtoEngine(tuple(keys), pcomm, bce, clients,)
    w.set_ID(id)
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
