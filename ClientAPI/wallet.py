from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
def signTransaction(privateKey, message = 'no message'):
    ''' Takes in a private key and signs a transaction'''

    # key = RSA.import_key(open('private.pem').read())
    key = RSA.import_key(privateKey)
    message = b'message'
    hash = SHA256.new(message)
    signature = pkcs1_15.new(key).sign(hash)
    return hash, signature

def getKeys():
    ''' Returns a dictionary of a public and private key'''
    keyDict = {}
    key = RSA.generate(4096)
    privateKey = key.export_key()
    file_out = open("private.pem", "wb")
    file_out.write(privateKey)
    file_out.close()
    keyDict['privateKey'] = privateKey
    publicKey = key.publickey().export_key()
    file_out = open("receiver.pem", "wb")
    file_out.write(publicKey)
    file_out.close()
    keyDict['publicKey'] = publicKey
    return keyDict 

def signTransaction(privateKey, message = 'no message'):
    ''' Takes in a private key and signs a transaction'''
    # key = RSA.import_key(open('private.pem').read())
    key = RSA.import_key(privateKey)
    message = b'message'

    hash = SHA256.new(message)
    signature = pkcs1_15.new(key).sign(hash)
    return hash, signature

def verifySignature(pubKey, hash, signature):
    ''' Verifies a signed message with the public key'''
    pkcsObj = pkcs1_15.new(pubKey)
    return pkcsObj.verify(hash, signature)

# A dictionary of public and private keys
userKeys = getKeys()
message = 'My message to you'
hash, signature = signTransaction(userKeys['privateKey'])
pubKey = RSA.import_key(userKeys['publicKey'])
# key = RSA.import_key(open('receiver.pem').read())
print("The hash ", hash.hexdigest())
try:
    verifySignature(pubKey, hash, signature)
    print("The signature is valid.")
except (ValueError, TypeError):
   print("The signature is not valid.")

userKeys = getKeys()
print("User key ", userKeys)

