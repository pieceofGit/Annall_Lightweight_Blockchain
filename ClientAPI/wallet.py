from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import requests
import json
BASE = "http://127.0.0.1:5000/"
def signTransaction(privateKey, message = 'no message'):
    ''' Takes in a private key and signs a transaction'''
    key = RSA.import_key(privateKey)
    message = b'message'
    hash = SHA256.new(message)
    signature = pkcs1_15.new(key).sign(hash)
    return hash, signature

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


def verifySignature(pubKey, hash, signature):
    ''' Verifies a signed message with the public key'''
    pkcsObj = pkcs1_15.new(pubKey)
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
            theHash, signature = signTransaction(privKey )
            pubKey = RSA.import_key(key.public_key().export_key())
            
            print("The pub ", type(pubKey))
            print("The theHash ", type(theHash))
            print("The sign ", type(signature))
            try:
                verifySignature(pubKey, theHash, signature)
                print("The signature is valid.")
            except (ValueError, TypeError):
                print("The signature is not valid.")
            dict = {
                    "payload": {
                    "headers" : {
                        "type" : "document",
                        "pubKey" : str(pubKey),
                        "hash": str(theHash),
                        "signature" : str(signature)
                    }, 
                    "payload": {
                        "userId" : 13,
                        "documentId" : 8
                        }
                    }
            }
            # r = requests.post(url = 'http://185.3.94.49:80/blocks' , json = dict 
            r = requests.post(BASE + "blocks", json.dumps(dict))
            print("THe r ", r.status_code)
            if r.status_code == 200:
                print("It worked")
            # r.json() to get the data from the endpoint
            # print("The resp ", r.json())
        elif command == 'q' or command == 'quit':
            exit()
        else:
            print('Invalid Command.')