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
    
# tested(True, any)

# print(bb_list, bb_list[1:])

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
print(calculate_sum(65537, [(1, generate_pad()),(2, generate_pad()), (3,generate_pad())]))
# 1000, 0000
print(1^0)