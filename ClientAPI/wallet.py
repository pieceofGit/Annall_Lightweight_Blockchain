from base64 import encode
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import requests
import json
import codecs
import rsa


BASE = "http://127.0.0.1:5000/"
def signTransaction(privateKey, message = 'no message'):
    ''' Takes in a private key and signs a transaction'''
    key = RSA.import_key(privateKey)
    message = b'message'
    hash = SHA256.new(message)
    signature = pkcs1_15.new(key).sign(hash)
    return hash, signature, message

def getKeys():
    ''' Returns a dictionary of a public and private key'''
    keyDict = {}
    key = RSA.generate(2048)
    privateKey = key.export_key()
    file_out = open("private.pem", "wb")
    file_out.write(privateKey)
    file_out.close()
    keyDict['privateKey'] = privateKey
    publicKey = key.publickey().export_key()
    file_out = open("public.pem", "wb")
    file_out.write(publicKey)
    file_out.close()
    keyDict['publicKey'] = publicKey
    return key 


def verifySignature(pubKey, message, signature):
    ''' Verifies a signed message with the public key'''
    pkcsObj = pkcs1_15.new(pubKey)
    hash = SHA256.new(message)
    
    return pkcsObj.verify(hash, signature)

def trash():
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

# userKeys = getKeys()
def verifySignatureString(pubKey, message, signature):
    ''' Verifies a signed message with the public key'''
    message = message.encode("ISO-8859-1") 
    signature = signature.encode("ISO-8859-1") 
    pubKey = pubKey.encode("ISO-8859-1") 
    pubKey = RSA.importKey(pubKey)
    pkcsObj = pkcs1_15.new(pubKey)
    hash = SHA256.new(message)
    return pkcsObj.verify(hash, signature)

def moreTrash():
    signature = signature.strip('b"')
    signature = signature.strip(' "')
    signature = signature[1:-1]
    signature = codecs.decode(signature, "ISO-8859-1")
    print("The sign ", type(signature), signature)
    # signature = signature.encode("ISO-8859-1") 
    print("The sign ", type(signature), signature)
            

def printTerminal():
    print("1. to generate a new walelt")
    print("2. Get data from the blockchain")
    print("3. Create a new message")
    print("q to quit")

def printKeys(key):
    print("Here is your public key ", key.public_key().export_key())
    print("Here is your private key ", key.export_key())
    print("Your keys are also saved in private.pem and public.pem files ")
if __name__ == "__main__":

    guard = True
    #command = input("Do you have a wallet? (y/n)").strip()
    command = 'y'
    if command == "y":
        f = open('private.pem','r')
        key = RSA.import_key(f.read())
        printKeys(key)
    else:
        key = getKeys()
        printKeys(key)
    while guard:
        pubKey = key.public_key().export_key()
        privKey = key.export_key()
        printTerminal()
        command = input('command? ').strip()
        # command = '2'
        if command == '1':
            key = getKeys()
            printKeys(key)
        elif command == '2':
            print('Doing something else')
            # r = requests.post(url = 'http://185.3.94.49:80/block' , data = {"payload": {"insurance":2}})
            r = requests.get(url = 'http://185.3.94.49:80/blocks' , data = {"payload": {"insurance":2}})
            print("THe r ", r.status_code)
            if r.status_code == 200:
                print("It worked")
            # r.json() to get the data from the endpoint
            # print("The resp ", r.json())
        elif command == '3':
            print('Doing something else')
            # r = requests.post(url = 'http://185.3.94.49:80/block' , data = {"payload": {"insurance":2}})
            theHash, signature, message = signTransaction(privKey )
            public_key = RSA.import_key(key.public_key().export_key())
            public_key = key.public_key()
            pub_key_exp = public_key.export_key()
            print("Our exp key ", pub_key_exp)
            # (public_key, private_key) = rsa.newkeys(512)
            print("The pub key ",public_key)
            # print("The private key ",private_key, type(private_key))
            # raw_key = codecs.decode(public_key, 'unicode_escape')
            # from binary to string
            # print('The raw key ', raw_key)
            message = message.decode("ISO-8859-1") 
            # Back into binary
            # message = message.encode() 
            # signature = str(signature)
            signature = signature.decode("ISO-8859-1") 

            pub_key_exp = pub_key_exp.decode("ISO-8859-1")
            verified = verifySignatureString(pub_key_exp, message, signature)
            print("The veri ", verified)
            print("The pub ",  pub_key_exp)
            try:
                verifySignatureString(pub_key_exp, message, signature)
                print("The signature is valid.")
            except (ValueError, TypeError):
                print("The signature is not valid.")
            
            
            print("The message ", message )
            print("The sig ", signature )
            dict = {
                    "payload": {
                    "headers" : {
                        "type" : "document",
                        "pubKey" : pub_key_exp,
                        "message": message,
                        "signature" : signature
                    }, 
                    "payload": {
                        "userId" : 13,
                        "documentId" : 8
                        }
                    }
            }
            r = requests.post(url = 'http://185.3.94.49:80/blocks' , json = dict)
            r = requests.post(BASE + "blocks", json.dumps(dict))
            print("THe r ", r.status_code)
            if r.status_code == 200:
                print("It worked")
                r.json() # to get the data from the endpoint
                print("The resp ", r.json())
        elif command == 'q' or command == 'quit':
            exit()
        else:
            print('Invalid Command.')