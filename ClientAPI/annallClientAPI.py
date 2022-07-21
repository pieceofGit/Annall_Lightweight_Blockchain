""" 
A ClientAPI for Annáll using Flask and Gunicorn.
"""
import json
import argparse
from flask import Flask, request, jsonify, Response
import sys
from connectToServer import ServerConnection
from exceptionHandler import InvalidUsage
from Crypto.PublicKey import RSA 
from Crypto.Signature import PKCS1_v1_5 
from Crypto.Hash import SHA256 
from Crypto.Signature import pkcs1_15

# import sys
print("Starting annallClientAPI Flask application server")
app = Flask(__name__)
# Connect to server
TCP_PORT = 5001 # Connects to port of writer 1

with open(f'../src/config-local.json') as config_file:   # If in top directory for debug
  config = json.load(config_file)
  #TODO: Should get config from WriterAPI and attempt to connect as a client to the first available active writer
  IP_ADDR = config["node_set"][0]["hostname"] 
  TCP_PORT = config["node_set"][0]["client_port"]
print(TCP_PORT)
server = ServerConnection(IP_ADDR, TCP_PORT)

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.route("/publishandsubscribe", methods=["GET"])
def createSmartContracts():
    # Asks for blockchain and gets it back
    requestObject = getJson(request)
    typeToGet = requestObject['type']
    typeToGet = typeToGet.lower()
    resp_obj = server.send_msg(json.dumps({"request_type": "read_chain"}))
    obj = json.loads(resp_obj)
    lis = []
    for res in obj:
        try:
            if res['payload']['headers']['type'] == typeToGet:
                lis.append(res)
        except:
            print("Couldnt find a type")
    print("Return list for the given type ", lis)
    lis = jsonify(lis)
    return Response(lis, mimetype="application/json")


@app.route("/walletTest", methods=["GET"])
def testWallet():
    # Asks for blockchain and gets it back
    requestObject = getJson(request)
    
    return Response({}, mimetype="application/json")

@app.route("/blocks", methods=["GET"])
def get_blockchain():
    # Asks for blockchain and gets it back
    try:
        resp_obj = server.send_msg(json.dumps({"request_type": "read_chain"}))
        return Response(resp_obj, mimetype="application/json")
    except Exception:
        raise InvalidUsage("Failed to read from writer", status_code=500)
    

@app.route("/blocks", methods=["POST"])
def insert_block():
    # Decode the JSON
    request_object = getJson(request)
    
    # Get the object 
    
    if "payload" in request_object:
        # print("request data", request.data)
        # print(f"[REQUEST] {request_object}")
        
        pub_key = request_object['payload']['headers']['pubKey']
        message = request_object['payload']['headers']['message']
        signature = request_object['payload']['headers']['signature']
        print("The pub ",  pub_key)
        print("The message ", message )
        print("The sig ", signature )
        pub_key = pub_key.encode("ISO-8859-1")
        pub_key = pub_key.decode("ISO-8859-1")
        print("new pub  ",  pub_key)
        # Assumes the data is base64 encoded to begin with
        # digest.update(b64decode(data)) 
        try:
            verifySignature(pub_key, message, signature)
            try:
                resp_obj = server.send_msg(request_object['payload'])
                return Response(resp_obj, mimetype="application/json")
            except Exception:
                raise InvalidUsage("Unable to post to writer", status_code=500)
        except:
            print("Invalid signature ")
            raise InvalidUsage("Invalid signature responding to public key", status_code=401)
    else:
        raise InvalidUsage("The JSON object key has to be named payload", status_code=400)

# Get back block if on blockchain and verified
# TODO: Add get block by blockid
# TODO: Get all blocks for a wallet
# @app.route("/block/<blockid>", methods=["GET"])
# def get_block():
#     request_object = getJson(request)
    
#     # return json.dumps({"message":"verified"})

def getJson(request):
    try:
        return json.loads(request.data) 
    except Exception:
        raise InvalidUsage("The JSON could not be decoded", status_code=400)

def verifySignature(pubKey, message, signature):
    ''' Verifies a signed message with the public key'''
    message = message.encode("ISO-8859-1") 
    signature = signature.encode("ISO-8859-1") 
    # pubKey = pubKey.encode("ISO-8859-1") 
    pubKey = RSA.importKey(pubKey)
    pkcsObj = pkcs1_15.new(pubKey)
    hash = SHA256.new(message)
    return pkcsObj.verify(hash, signature)

if __name__ == "__main__":
    app.run(debug=False)