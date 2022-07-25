

import json
from exceptionHandler import InvalidUsage
from Crypto.PublicKey import RSA 
from Crypto.Signature import PKCS1_v1_5 
from Crypto.Hash import SHA256 
from Crypto.Signature import pkcs1_15

def getJson(request):
    try:
        return json.loads(request.data) 
    except Exception:
        raise InvalidUsage("The JSON could not be decoded", status_code=400)

def verifyRequest(request_object):
    pub_key_exp = request_object['payload']['headers']['pubKey']
    message = request_object['payload']['headers']['message']
    signature = request_object['payload']['headers']['signature']
    try:
        verifySignature(pub_key_exp, message, signature)
        return True
    except:
        return False
        

def verifySignature(pubKey, message, signature):
    ''' Verifies a signed message with the public key'''
    message = message.encode("ISO-8859-1") 
    signature = signature.encode("ISO-8859-1") 
    pubKey = pubKey.encode("ISO-8859-1") 
    pubKey = RSA.importKey(pubKey)
    pkcsObj = pkcs1_15.new(pubKey)
    hash = SHA256.new(message)
    return pkcsObj.verify(hash, signature)