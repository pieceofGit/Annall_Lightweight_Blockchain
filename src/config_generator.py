import json
import os
from Cryptodome.Util.number import getPrime

WRITERS = int(input())

# one time usage when machine is created
def generate_public_private_key() -> tuple:
    # RSA PUBPRIV generation
    p = getPrime(256, randfunc=os.urandom)
    q = getPrime(256, randfunc=os.urandom)
    e = 65537
    return (
        p,
        q,
        e,
    )


data = {}
data["NO_permitted_writers"] = WRITERS

writers = []
for w in range(WRITERS):
    keys = generate_public_private_key()
    p, q, _ = keys

    w_inf = {}
    w_inf["id"] = w + 1
    w_inf["hostname"] = "127.0.0.1"
    w_inf["port"] = 15000 + w
    w_inf["pub_key"] = p * q
    w_inf["priv_key"] = keys

    writers.append(w_inf)
data["active_writer_set"] = writers
data["NO_coord"] = 1
data["modulus"] = 65537
data["version"] = "1.0"

with open("./src/config.json", "w") as f:
    json.dump(data, f)

