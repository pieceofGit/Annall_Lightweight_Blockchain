# import json
# import os
# from Cryptodome.Util.number import getPrime

# WRITERS = int(input())

# # one time usage when machine is created
# def generate_public_private_key() -> tuple:
#     # RSA PUBPRIV generation
#     p = getPrime(256, randfunc=os.urandom)
#     q = getPrime(256, randfunc=os.urandom)
#     e = 65537
#     return (
#         p,
#         q,
#         e,
#     )

# print(generate_public_private_key())
# data = {}
# data["no_permitted_writers"] = WRITERS

# writers = []
# for w in range(WRITERS):
#     keys = generate_public_private_key()
#     p, q, _ = keys

#     w_inf = {}
#     w_inf["id"] = w + 1
#     w_inf["hostname"] = "127.0.0.1"
#     w_inf["protocol_port"] = 15000 + w
#     w_inf["pub_key"] = p * q
#     w_inf["priv_key"] = keys

#     writers.append(w_inf)
# data["node_set"] = writers
# data["NO_coord"] = 1
# data["modulus"] = 65537
# data["version"] = "1.0"

# with open("./src/config.json", "w") as f:
#     json.dump(data, f)

import random
import sympy

def is_prime(n):
    """Check if a number is prime"""
    return sympy.isprime(n)

def generate_random_candidate(bits):
    """Generate a random integer of the specified number of bits"""
    return random.getrandbits(bits)

def getPrime(bits, randfunc=None):
    """Generate a random prime number of the specified number of bits"""
    while True:
        candidate = generate_random_candidate(bits)
        if randfunc:
            candidate = randfunc(bits)
        if candidate % 2 == 0:
            candidate += 1
        while not is_prime(candidate):
            candidate += 2
        if sympy.ntheory.isprime(candidate):
            return candidate

def generate_public_private_key() -> tuple:
    # RSA PUBPRIV generation
    p = getPrime(256)
    q = getPrime(256)
    e = 65537

    n = p * q
    phi_n = (p - 1) * (q - 1)

    # Find the modular multiplicative inverse of e modulo phi(n) to get d
    d = pow(e, -1, phi_n)

    # Return the public and private keys as a tuple
    # The public key is (n, e) and the private key is (n, d)
    return (n, e), (n, d)

# Example usage:
public_key, private_key = generate_public_private_key()
print("Public key (n, e):", public_key)
print("Private key (n, d):", private_key)
