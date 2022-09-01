""" 
A Client API for Annáll using Flask and Gunicorn.
The Client API has a TCP socket connection to the blockchain TCP server on writer 1.
The TCP server expects a json for all its request.
The type of request to the TCP server is handled by the request_type field.
"""
import json
from flask import Flask, request, jsonify, Response
from connectToServer import ServerConnection
from exceptionHandler import InvalidUsage
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
    requestObject = get_json(request)
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
    requestObject = get_json(request)
    
    return Response({}, mimetype="application/json")

@app.route("/blocks", methods=["GET"])
def get_blockchain():
    """ Returns blocks in a list of dicts per block """
    try:
        resp_obj = server.send_msg(json.dumps({"request_type": "read_chain"}))
        return Response(resp_obj, mimetype="application/json")
    except Exception:
        raise InvalidUsage("Failed to read from writer", status_code=500)

@app.route("/blocks", methods=["POST"])
def insert_block():
    """ Sends the transaction for insertion as block on the chain. """
    request_object = get_json(request)
    if "payload" in request_object:
        block = json.dumps({"request_type": "block", "name": "name", "payload": request_object['payload'], "payload_id": 1})
        try:
            resp_obj = server.send_msg(block)
            return Response(resp_obj, mimetype="application/json")
        except Exception:
            raise InvalidUsage("Unable to post to writer", status_code=500)
    else:
        raise InvalidUsage("The JSON object key has to be named payload", status_code=400)



if __name__ == "__main__":
    app.run(debug=False)