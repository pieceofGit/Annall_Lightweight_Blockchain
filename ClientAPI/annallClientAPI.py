""" 
A Client API for Annáll using Flask and Gunicorn.
The Client API has a TCP socket connection to the blockchain TCP server on writer 1.
The TCP server expects a json for all its request.
The type of request to the TCP server is handled by the request_type field.
"""
import json
from flask import Flask, request, jsonify, Response
from serverConnection import ServerConnection
from exceptionHandler import InvalidUsage
from InputModels.BlockInputModel import BlockInputModel
from clientfunctions import *
# import sys
print("Starting annallClientAPI Flask application server")
app = Flask(__name__)
# Connect to server
TCP_PORT = 5001 # Connects to port of writer 1

with open(f'../src/config-remote.json') as config_file:   # If in top directory for debug
  config = json.load(config_file)
  #TODO: Should get config from WriterAPI and attempt to connect as a client to the first available active writer
  IP_ADDR = config["node_set"][0]["hostname"] 
  TCP_PORT = config["node_set"][0]["client_port"]
print(TCP_PORT)
server = ServerConnection(IP_ADDR, TCP_PORT)

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status = error.status
    return response

@app.route("/publishandsubscribe", methods=["GET"])
def createSmartContracts():
    # Asks for blockchain and gets it back
    requestObject = request.get_json(request)
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
    return Response(lis)


@app.route("/walletTest", methods=["GET"])
def testWallet():
    # Asks for blockchain and gets it back
    requestObject = request.get_json(request)
    return Response({}, mimetype="application/json")

@app.route("/blocks", methods=["GET"])
def get_blockchain():
    """ Returns blocks in a list of dicts per block """
    try:
        resp_obj = server.send_msg(json.dumps({"request_type": "read_chain"}))
        return Response(resp_obj, mimetype="application/json")
    except Exception:
        raise InvalidUsage("Failed to read from writer", status=500)

@app.errorhandler(400)
def handle_bad_request(e):
    return Response(json.dumps({"error": "Could not parse the request object"}), 400)

@app.route("/blocks", methods=["POST"])
def insert_block():
    """ Sends the transaction for insertion as block on the chain. """
    request_json = request.get_json(request)
    request_obj = BlockInputModel(request_json)
    if request_obj.error:
        return Response(json.dumps(request_obj.dict), status=400)
    try:
        resp_obj = server.send_msg(json.dumps(request_obj.dict))
        return Response(resp_obj, status=201)
    except Exception:
        raise InvalidUsage("Unable to post to writer", status=500)
    # else:
    #     raise InvalidUsage("The JSON object key has to be named payload", status=400)

@app.route("/blocks/<hash>/verified")
def block_hash_exists(hash):
    # Returns true or false if block is verified based on its hash
    ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    # Ask for verification of hash
    to_send = json.dumps({"request_type": "verify", "hash": hash})
    resp_obj = server.send_msg(to_send)
    return Response(resp_obj,status=200)
    

if __name__ == "__main__":
    app.run(debug=True)