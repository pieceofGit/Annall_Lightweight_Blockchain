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
from clientfunctions import *
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
    if "payload" in request_object:
       
        if verifyRequest(request_object):
            print("All is good and verified")
            try:
                resp_obj = server.send_msg(request_object['payload'])
                return Response(resp_obj, mimetype="application/json")
            except Exception:
                print("Failed to send to blockchain")
                raise InvalidUsage("Unable to post to writer", status_code=500)
        else:
            raise InvalidUsage("Invalid signature responding to public key", status_code=401)
        
        
        
    else:
        raise InvalidUsage("The JSON object key has to be named payload", status_code=400)



if __name__ == "__main__":
    app.run(debug=False)