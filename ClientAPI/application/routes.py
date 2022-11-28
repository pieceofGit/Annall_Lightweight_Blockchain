""" 
A Client API for Annáll using Flask and Gunicorn.
The Client API has a TCP socket connection to the blockchain TCP server on writer 1.
The TCP server expects a json for all its request.
The type of request to the TCP server is handled by the request_type field.
"""
import json
from flask import request, jsonify, Response, Blueprint
from application.exceptionHandler import InvalidUsage
from application.clientFunctions import *
from application.models.blockInputModel import BlockInputModel
from flask import current_app as app
# from configs.flaskConfig import FlaskConfig
# Blueprint Configuration

annall = Blueprint('annall', __name__)

print("Starting annallClientAPI Flask application server")

def add_blocks(missing_blocks):
    """Adds blocks to json and saves"""
    if missing_blocks == [] or app.config["BCDB"] == []:
        if missing_blocks == []:    # Blockchain deleted
            app.config["BCDB"].clear()
        elif app.config["BCDB"] == []:   # Append all blocks
            for i in missing_blocks:
                app.config["BCDB"].append(i)
        with open("application/data/bcdb.json", "w") as bcdb_file:
            json.dump(app.config["BCDB"], bcdb_file, indent=4)
            return
    if len(missing_blocks) == 1:
        return
    with open("bcdb.json", "w") as bcdb_file:
        for i in missing_blocks[1::]:
            app.config["BCDB"].append(i)
        json.dump(app.config["BCDB"], bcdb_file, indent=4)

@annall.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status = error.status
    return response

@annall.route("/publishandsubscribe", methods=["GET"])
def createSmartContracts():
    # Asks for blockchain and gets it back
    requestObject = request.get_json(request)
    typeToGet = requestObject['type']
    typeToGet = typeToGet.lower()
    resp_obj = app.config["SERVER"].send_data_msg(json.dumps({"request_type": "read_chain"}))
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

@annall.route("/walletTest", methods=["GET"])
def testWallet():
    # Asks for blockchain and gets it back
    requestObject = request.get_json(request)
    return Response({}, mimetype="application/json")

@annall.route("/blocks", methods=["GET"])
def get_blocks():
    """ Returns blocks in a list of dicts per block.
    The client only fetches blocks it does not already have. """
    if len(app.config["BCDB"]):
        latest_block_hash = app.config["BCDB"][-1]["hash"]
    else:
        latest_block_hash = ""
    try:
        resp_obj = app.config["SERVER"].send_data_msg(json.dumps({"request_type": "get_missing_blocks", "hash": latest_block_hash}))
        res_list = json.loads(resp_obj)
        add_blocks(res_list)
        return Response(json.dumps(app.config["BCDB"][::-1]), mimetype="application/json")
    except Exception as e:
        raise InvalidUsage(f"Failed to read from writer {e}", status=500)

@annall.errorhandler(400)
def handle_bad_request(e):
    return Response(json.dumps({"error": "Could not parse the request object"}), mimetype="application/json", status=400)

@annall.route("/blocks", methods=["POST"])
def insert_block():
    """ Sends the transaction for insertion as block on the chain. """
    request_json = request.get_json(request)
    request_obj = BlockInputModel(request_json)
    if request_obj.error:
        return Response(json.dumps(request_obj.dict), mimetype="application/json", status=400)
    try:
        resp_obj = app.config["SERVER"].send_msg(json.dumps(request_obj.dict))
        return Response(resp_obj, mimetype="application/json", status=201)
    except Exception:
        raise InvalidUsage("Unable to post to writer", status=500)

@annall.route("/blocks/<hash>/verified")
def block_hash_exists(hash):
    # Returns true or false if block is verified based on its hash
    ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    # Ask for verification of hash
    to_send = json.dumps({"request_type": "verify", "hash": hash})
    resp_obj = app.config["SERVER"].send_msg(to_send)
    return Response(resp_obj, mimetype="application/json", status=200)