""" 
A Client API for Annáll using Flask and Gunicorn.
The Client API has a TCP socket connection to the blockchain TCP server on writer 1.
The TCP server expects a json for all its request.
The type of request to the TCP server is handled by the request_type field.
"""
import json
from tkinter import E
from flask import request, jsonify, Response, Blueprint
from application.exceptionHandler import InvalidUsage
from application.models.blockInputModel import BlockInputModel
from application.models.latestBlockInputModel import LatestBlockInputModel
from flask import current_app as app
# from configs.flaskConfig import FlaskConfig
# Blueprint Configuration

annall = Blueprint('annall', __name__)

print("Starting annallClientAPI Flask application server")

@annall.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status = error.status
    return response

@annall.route("/blocks", methods=["GET"])
def get_blocks():
    """ Returns blocks in a list of dicts per block. """
    try:
        return Response(json.dumps(app.config["BCDB"].get_blockchain()[::-1]), mimetype="application/json")
    except Exception as e:
        raise InvalidUsage(f"Failed to read from writer {e}", status=500)
    
@annall.route("/missing_blocks", methods=["GET"])
def get_missing_blocks():
    """Returns blocks appended after round number."""
    print(request)
    request_json = request.get_json(request)
    request_obj = LatestBlockInputModel(request_json)
    if request_obj.error:
        return Response(json.dumps(request_obj.dict), mimetype="application/json", status=400)
    try:
        latest_block = app.config["BCDB"].get_latest_block()
        if request_obj.round > latest_block["round"] or request_obj.round < 0:
            return Response(json.dumps({"error": f"Blockchain length {latest_block['round']} but got round number {request_obj.round}"}), mimetype="application/json", status=404)
        if latest_block: # Blockchain is not empty. Return missing blocks
            missing_blocks = app.config["BCDB"].get_missing_blocks(request_obj.hash)
            if missing_blocks:
                return Response(json.dumps(missing_blocks), mimetype="application/json", status=200)
            else:
                return Response(json.dumps({"error": f"Hash {request_obj.hash} not in blockchain"}), mimetype="application/json", status=404)
        else:
            return Response(json.dumps([]), mimetype="application/json", status=200)
    except Exception as e:
        raise InvalidUsage(f"Failed to read database {e}", status=500)

# @annall.errorhandler(400)
# def handle_bad_request(e):
#     return Response(json.dumps({"error": f"Could not parse the request object {e}"}), mimetype="application/json", status=400)

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