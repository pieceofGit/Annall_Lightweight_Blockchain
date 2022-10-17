""" 
A Client API for Annáll using Flask and Gunicorn.
The Client API has a TCP socket connection to the blockchain TCP server on writer 1.
The TCP server expects a json for all its request.
The type of request to the TCP server is handled by the request_type field.
"""
import sys
import ast
import json
from flask import Flask, request, jsonify, Response
from py import process
from ClientAPI.serverConnection import ServerConnection
from exceptionHandler import InvalidUsage
from clientfunctions import *
from InputModels.BlockInputModel import BlockInputModel
# import sys
print("Starting annallClientAPI Flask application server")
app = Flask(__name__)
# Connect to server
TCP_PORT = 5001 # Connects to port of writer 1
# Adjust if config-local or config-remote
with open(f'../src/config-remote.json') as config_file:   # If in top directory for debug
  config = json.load(config_file)
  #TODO: Should get config from WriterAPI and attempt to connect as a client to the first available active writer
  IP_ADDR = config["node_set"][0]["hostname"] 
  TCP_PORT = config["node_set"][0]["client_port"]
print(TCP_PORT)
server = ServerConnection(IP_ADDR, TCP_PORT)
# Get the blockchain on startup
with open("bcdb.json", "w") as bcdb_file:
    try:
        resp_obj = server.send_data_msg(json.dumps({"request_type": "read_chain"}))
        bcdb = ast.literal_eval(resp_obj)
        json.dump(bcdb, bcdb_file, indent=4)
    except Exception as e:
        print(f"Failed to fetch blocks from writer: {e}")

def add_blocks(missing_blocks):
    """Adds blocks to json and saves"""
    if missing_blocks == [] or bcdb == []:
        if missing_blocks == []:    # Blockchain deleted
            bcdb.clear()
        elif bcdb == []:   # Append all blocks
            for i in missing_blocks:
                bcdb.append(i)
        with open("bcdb.json", "w") as bcdb_file:
            json.dump(bcdb, bcdb_file, indent=4)
            return
    if len(missing_blocks) == 1:
        return
    with open("bcdb.json", "w") as bcdb_file:
        for i in missing_blocks[1::]:
            bcdb.append(i)
        json.dump(bcdb, bcdb_file, indent=4)
            
    
    
    

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
            print("Couldn't find a type")
    print("Return list for the given type ", lis)
    lis = jsonify(lis)
    return Response(lis, mimetype="application/json",)


@app.route("/walletTest", methods=["GET"])
def testWallet():
    # Asks for blockchain and gets it back
    requestObject = request.get_json(request)
    return Response({}, mimetype="application/json")

@app.route("/v1/blocks", methods=["GET"])
def get_blockchain():
    """ Returns blocks in a list of dicts per block """
    try:
        resp_obj = server.send_data_msg(json.dumps({"request_type": "read_chain"}))
        res_list = ast.literal_eval(resp_obj)
        return Response(json.dumps(res_list[::-1]), mimetype="application/json")
    except Exception:
        # print(sys.getsizeof(resp_obj))
        print(f"The response object on failure {resp_obj}")
        raise InvalidUsage("Failed to read from writer", status=500)

@app.route("/blocks", methods=["GET"])
def get_blocks():
    """ Returns blocks in a list of dicts per block.
    The client only fetches blocks it does not already have. """
    if len(bcdb):
        latest_block_hash = bcdb[-1]["hash"]
    else:
        latest_block_hash = ""
    try:
        resp_obj = server.send_data_msg(json.dumps({"request_type": "get_missing_blocks", "hash": latest_block_hash}))
        res_list = ast.literal_eval(resp_obj)
        add_blocks(res_list)
        return Response(json.dumps(bcdb[::-1]), mimetype="application/json")
    except Exception as e:
        # print(sys.getsizeof(resp_obj))
        raise InvalidUsage(f"Failed to read from writer {e}", status=500)

@app.errorhandler(400)
def handle_bad_request(e):
    return Response(json.dumps({"error": "Could not parse the request object"}), mimetype="application/json", status=400)

@app.route("/blocks", methods=["POST"])
def insert_block():
    """ Sends the transaction for insertion as block on the chain. """
    request_json = request.get_json(request)
    request_obj = BlockInputModel(request_json)
    if request_obj.error:
        return Response(json.dumps(request_obj.dict), mimetype="application/json", status=400)
    try:
        resp_obj = server.send_msg(json.dumps(request_obj.dict))
        return Response(resp_obj, mimetype="application/json", status=201)
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
    return Response(resp_obj, mimetype="application/json", status=200)
    

if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=6000, threaded=False, processes=1)
    # app.run(debug=False)