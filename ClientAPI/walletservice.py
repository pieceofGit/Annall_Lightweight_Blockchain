from base64 import encode
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import requests
import json
import codecs
import rsa
from messagetype import get_message_type_dict
from wallet import Wallet

GLOBAL = "http://185.3.94.49:80"
LOCAL = "http://127.0.0.1:5000/"
def signTransaction(privateKey, message = 'no message'):
    ''' Takes in a private key and signs a transaction'''
    key = RSA.import_key(privateKey)
    message = message.encode()
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
def test_sig(dict):
    pub_key_exp = dict['payload']['headers']['pubKey']
    message = dict['payload']['headers']['message']
    signature = dict['payload']['headers']['signature']
    try:
        verifySignatureString(pub_key_exp, message, signature)
        print("The signature is valid.")
    except (ValueError, TypeError):
        print("This should really never be invalid")
        print("The signature is not valid.")
    

def verifySignature(pubKey, message, signature):
    ''' Verifies a signed message with the public key'''
    pkcsObj = pkcs1_15.new(pubKey)
    hash = SHA256.new(message)
    
    return pkcsObj.verify(hash, signature)



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
    print("1. Generate a new wallet")
    print("2. Get data from the blockchain")
    print("3. Create message")
    print("q to quit")

def printKeys(key):
    print("Here is your public key ", key.public_key().export_key())
    print("Here is your private key ", key.export_key())
    print("Your keys are also saved in private.pem and public.pem files locally ")
if __name__ == "__main__":
    remoteClientBool = False
    if remoteClientBool:
        clienturl = GLOBAL
    else:
        clienturl = LOCAL
    
    guard = True
    #command = input("Do you have a wallet? (y/n)").strip()
    command = 'y'
    wallet = Wallet()
    if command == "y":
        f = open('private.pem','r')
        key = RSA.import_key(f.read())
        
        printKeys(key)
    else:
        key = getKeys()
        printKeys(key)
    # Saving the public key
    wallet.pub_key = key.public_key().export_key()
    # Saving the private key
    wallet.priv_key = key.export_key()
    while guard:
        printTerminal()
        command = input('command? ').strip()
        if command == '1':
            key = getKeys()
            printKeys(key)
        elif command == '2':
            # Get all the blockchain data
            r = requests.get(url =  GLOBAL + '/blocks' )
            
            if r.status_code == 200:
                blockchain_data = r.json()
                # data = blockchain_data[-3:]
                data = blockchain_data
                for transaction in data:
                    print("Last 3 transactions ")
                    print("Round ", transaction['round'] , "payload",  transaction['payload'])
            else:
                print("Could not retreive blockchain data")
                
                
        elif command == '3':
            # Message should be written in
            message = 'no_message'
            
            theHash, signature, message = signTransaction(wallet.priv_key, message)
            message = message.decode("ISO-8859-1") 
            signature = signature.decode("ISO-8859-1") 
            pub_key_exp = wallet.pub_key.decode("ISO-8859-1")
            # Here you get the dictionary that fits the expected type
            dict = get_message_type_dict(pub_key_exp, message, signature, 'document')
            test_sig(dict)
            r = requests.post(url = 'http://185.3.94.49:80/blocks' , json = dict)
            # r = requests.post(BASE + "blocks", json.dumps(dict))
            print("THe r ", r.status_code)
            if r.status_code == 200:
                print("It worked")
                r.json() # to get the data from the endpoint
                print("The resp ", r.json())
                
        elif command == 'q' or command == 'quit':
            exit()
        else:
            print('Invalid Command.')
            
