# a_list = [1,2]
# b_list = [3,4]
# bb_list = [1,2,3,4,5]

# a_list.extend(list(set(bb_list)-set(b_list)-set(a_list)))
# print(a_list)

# def tested(input, the_type):
#     if type(input) == the_type:
#         print(input)
#     else:
#         print("FAKE")
def calculate_sum(numbers: list, modulus):
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
    pad %= modulus
    # calculate winner, finds the minimum difference for all submitted numbers from the calculated pad.
    winner, number = min(
        numbers,
        key=lambda x: [
            min((x[1] - pad) % modulus, (pad - x[1]) % modulus),
            x[0],
        ],
    )
    return [numbers, pad, winner]

def verify_round_winner(numbers: list, my_number: int):
    """Verifies if the round winner is the writer
    Verifies that all details are correct. 
    """
    assert isinstance(numbers, list)
    assert len(numbers) == 3
    assert isinstance(my_number, int)
    # Calculate the sum to check if we have the correct results
    verified_results = calculate_sum(numbers[0], 65537)
    # Checking if we are using the same OTP
    same_pad = verified_results[1] == numbers[1]
    # Checking if the use the same winner for the calculation
    same_winner = verified_results[2] == numbers[2]
    # Check if all the entries match up for each
    my_numb_exists = any([my_number == entry[1] for entry in numbers[0]])
    # correct case here would return True, True, True
    return same_pad and same_winner and my_numb_exists
pad = 45712
a_list = [[[3, 59550]], 59550, 3]
numbers = [[3,59950]]
winner = calculate_sum(numbers, 65537)
winner_verified = verify_round_winner(winner, pad)

print(winner, winner_verified)



some_list = [1,2,3,4,5]

import time
timeout = 10
run_time = time.time()
print("run_time", run_time)
while time.time() < run_time + timeout:
    print("BEFORE TIMEOUT", time.time(), run_time, timeout)
    time.sleep(0.5)

num = 1
num2 = num
num = 2 # Immutable, so num2's value is not changed
print(num2, "NUMBER 2")

# tested(True, any)
def get_cancel_coordinatorID(pen_box, view_change_num: int = None):
    """Decides the coordinator for a cancel round in the membership protocol.
    Should only change when there is a view-change in the cancellation."""
    print(type(pen_box))
    sorted_nodes = sorted(pen_box.values(), key=lambda x: (x["honest_counter"], -x["id"]), reverse=True)
    coordinator_id = sorted_nodes[view_change_num]["id"]
    return coordinator_id

pen_box = {"aaa": {"id": 4, "honest_counter": 2},"some_key": {"id": 1, "honest_counter": 2}, "other_key": {"id": 2, "honest_counter": 2}, "third_key": {"id": 3, "honest_counter": 1}}
print("FIRST OUTPUT", get_cancel_coordinatorID(pen_box, 0))
print("SECOND OUTPUT", get_cancel_coordinatorID(pen_box, 1))
print("THIRD OUTPUT", get_cancel_coordinatorID(pen_box, 2))
print("THIRD OUTPUT", get_cancel_coordinatorID(pen_box, 3))

# print(bb_list, bb_list[1:])
from queue import Queue
from weakref import ref
some_queue = Queue()
some_queue.put(1)
some_queue.put(2)
ref_copy = some_queue
print("REF: ", ref_copy)
print("some", some_queue)
ref_copy.get()
print("REF: ", ref_copy)
print("some", some_queue)
ref_copy.get()
print("REF: ", ref_copy)
print("some", some_queue)
ref_copy.put(1)
print("REF: ", ref_copy)
print("some", some_queue)
ref_copy.put(2)
print("REF: ", ref_copy)
print("some", some_queue)


a_list = [1,2,3]

data = 3 in a_list 
print(data)

num = '222'
print(int(num) * 2)
value = '6587849500818316161519508278916854824201302152793630979346725188602264462651268740217047928962253207403830618696453825975409521538077356628137373401104759'
print(len(value))

def verify_block(payload, signature, keys, pub_key, block):
    '''
    To verify a block both the signature and hash of the block must be correct
    '''
    if block is not None:
        payload = payload
        signature = int(signature, 16)
        # Set some pub key as either string or int
        writer_pubkey = int(pub_key)  #TODO: Should not completely rely on id since the node_set is dynamic
        D = bytes_to_long(payload.encode("utf-8")) % writer_pubkey  #TODO: Figure out if pub key can be string in current setup and if str==int repr.
        res = pow(signature, keys[2], writer_pubkey)   #self.keys[2] is private key
        res = res % writer_pubkey
                
        # Get the hash based on what is in the block
        # hash = hash_block(block)  - invariant, part of block construction
        signature_correct = res == D
        return signature_correct
    else:
        # Only reason new_block is None is that the hash does not match
        return False ## only reason block was not created
    
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
    import struct
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
    
def sign_payload(keys: tuple, payload: str):
    # keys of form [p, q, e]
    '''Creates a signature of the payload'''
    assert isinstance(payload, str)
    p, q, e = keys # private keys
    N = p * q
    d = mod_inverse(e, (p - 1) * (q - 1))
    D = bytes_to_long(payload.encode("utf-8"))
    signature = pow(D, d, N)
    return hex(signature % N)
# Private keys
node_1_keys = 104171608550381805610629631974370644810978389674970109968994986331963820498789,63240354953645098909053921301429392257631457933829211049166951995700317410731,65537
signed_payload = sign_payload(node_1_keys, "johnny")
# test if correct
# verify_block(payload, signature, keys, pub_key, block):
node_1_pub_key = '6587849500818316161519508278916854824201302152793630979346725188602264462651268740217047928962253207403830618696453825975409521538077356628137373401104759'
print(verify_block("johnny", signed_payload, node_1_keys, node_1_pub_key, True), "TRUEEE")


def calculate_sum(modulus, numbers: list):
    """Numbers is a list of <ID, number> pairs. This function calculates the pad for the round from the numbers using xor
    then it calculates which ID corresponds to the number 'closest' to the pad. Returns a list of length 3, containing
    [<id number pairs>, <pad>, <winner_id>]
    Tiebreaker decided by lower ID number
    """
    assert isinstance(numbers, list)

    pad = 0
    for number in numbers:
        print(pad, number)
        pad ^= number[1]
        print(pad, number)
    # Same as pad = pad%self.modulus
    pad %= modulus
    # calculate winner, finds the minimum difference for all submitted numbers from the calculated pad.
    winner, number = min(
        numbers,
        key=lambda x: [
            min((x[1] - pad) % modulus, (pad - x[1]) % modulus),
            x[0],
        ],
    )
    return [numbers, pad, winner]
def generate_pad():
    ''' Generates a number '''
    modulus = 65537
    # TODO: This needs to be changed to use an already generated pad
    assert modulus > 0
    import os
    x = os.urandom(8)
    import struct
    number = struct.unpack("Q", x)[0]
    return number % modulus
# print(calculate_sum(65537, [(1, generate_pad()),(2, generate_pad()), (3,generate_pad())]))
# # 1000, 0000
# print(1^0)

dict = {"person": "a", "dogs": "b" }

for i in dict:
    print(i, "YES")
    
    
this_list = [1,3,22,4,2,8]
print(this_list)
this_list.sort()
print(this_list)
import json
some_thing = json.dumps((1, json.dumps({"a_dict":"field"})))
print(some_thing)
print(json.loads(some_thing))
values = [1,3,22,4,2,8]

print(values.index(max(values)))


# a = 0

# a += True
# print("A: ", a)

# mem_data = {}
# if mem_data.get(1, None).get("penalty_box", None):
#     print("FALSE")
# else:
#     print("TRUE")

def get_coordinator(round_number, num_coordinators, rounds_per_coordinator):
    coordinator_index = (round_number - 1) // rounds_per_coordinator % num_coordinators
    return coordinator_index

num_rounds = 15  # Total number of rounds
num_coordinators = 3  # Total number of coordinators
rounds_per_coordinator = 5  # Number of rounds per coordinator

for round_number in range(1, num_rounds + 1):
    coordinator_index = get_coordinator(round_number, num_coordinators, rounds_per_coordinator)
    print(f"Round {round_number}: Coordinator {coordinator_index + 1}")

round_writer_list = [1,2,3,4]
import math
print(len(round_writer_list)/3)
f = math.floor(len(round_writer_list)/3)
print(f)
the_round = 20
for round_i in range(the_round-math.floor((len(round_writer_list)-1)/3)-1, the_round+1):
    print(round_i)
