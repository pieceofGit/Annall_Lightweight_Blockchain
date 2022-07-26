""" 
A WriterAPI for Annáll using Flask and Gunicorn.
"""
print("importing annall writer api")
import json
import os
import argparse
from flask import Flask, request, jsonify, Response
import sys
print("WORKING DIRECTORY",os.getcwd())
PREPEND_PATH = os.getcwd() + "/src/"
from exceptionHandler import InvalidUsage
from_main = True
# import sys 
BCDB = ["Before db initialization"]
print("Starting annallClientAPI Flask application server")
app = Flask(__name__)
# Connect to server
LOCAL = True
if LOCAL:
    if from_main:   # Running from command line in top directory
        CONFIG_PATH = "config-local.json"
    else:
        CONFIG_PATH ="config-local.json"
else:
    CONFIG_PATH = "config-remote.json"
print("config file in: ",PREPEND_PATH+CONFIG_PATH)

with open(PREPEND_PATH+CONFIG_PATH, "r") as config_file:
  config = json.load(config_file)

def add_to_config_by_key(key, value):
    try:
        config[key].append(value)
        with open(CONFIG_PATH, "w") as file:
            json.dump(config, file, indent=4)
    except:
        raise InvalidUsage("Could not access the json file", status_code=500)


def add_new_writer(writer):
    # Create new writer object
    try:
        id = len(config["node_set"]) + 1
        new_writer = {
            "name": writer["name"],
            "id": id,
            "hostname": writer["hostname"],
            "pub_key": writer["pub_key"]
        }
        if LOCAL:
            new_writer["client_port"] = 5000 + id
            new_writer["protocol_port"] = 15000 + id
        else:
            new_writer["client_port"] = 5000
            new_writer["protocol_port"] = 5000
        # Add writer to writer set and save    
        add_to_config_by_key("node_set", new_writer)
        # config["node_set"].append(new_writer)
    except Exception as e:
        raise InvalidUsage(f"Could not decode JSON {e}", status_code=400)

def authenticate_writer(ip_address=None):
    # Checks if public ip address of request is in writer list
    if not ip_address:
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    for obj in config["node_set"]:
        if ip_address in obj["hostname"]:
            return True
    return False

def get_dict():
    try:
        return json.loads(request.data) 
    except Exception:
        raise InvalidUsage("The JSON could not be decoded", status_code=400)

def add_to_active_set(key):
    """ Adds writer or reader to their respective active set if the incoming node's blockchain is up to date 
    Writer sends in object with keys block and node
    """
    if authenticate_writer():
        # compare latest blocks
        request_obj = get_dict()
        try:
            block = request_obj["block"]
            node = request_obj["node"]
            if node["id"] in config[key]:
                return Response("Node already in set", status=200)
            api_latest_block = BCDB[0].get_latest_block()
            if api_latest_block["hash"] == block["hash"]:
                # Add writer to active writer set
                add_to_config_by_key(key, node["id"])
                return Response(json.dumps(config), mimetype="application/json", status=201)
            else:
                return Response(json.dumps({"message": "Node not up to date"}), status=400) #TODO: wrong pattern
        except Exception as e:
            raise InvalidUsage(f"Could not read the data {e}", status_code=400)
    else:
        return Response("Node not whitelisted", status=400)

def get_missing_blocks(writer_latest_block):
    # Needs to handle case if gbs and that it eventually catches up.
    # How should other writers be a part of this?
    # The api should not send duplicates that it will get when it has them already.
    api_latest_block = BCDB[0].get_latest_block()   # Get latest block in dict
    # if api_latest_block[""]
    try:
        if api_latest_block["hash"] == writer_latest_block["hash"] and writer_latest_block["prev_hash"] == api_latest_block["prev_hash"]: # Add compare prev hash
            return False   # Writer is up to date
        else:
            if api_latest_block["round"] == writer_latest_block["round"] or writer_latest_block["prev_hash"] == api_latest_block["prev_hash"]:
                # Different hash, same round or prev_hash. Something not ok on their end, return the blockchain
                try:
                    missing_blocks = BCDB[0].get_blockchain()
                    return missing_blocks
                except:
                    raise InvalidUsage("Could not fetch blocks", status_code=500)
            else:
                try:
                    # Different prev_hash, hash, and rounds
                    missing_blocks = BCDB[0].get_range_of_blocks(writer_latest_block["round"] + 1)
                    return missing_blocks
                except:
                    raise InvalidUsage("Could not fetch blocks", status_code=500)
    except Exception:
        raise InvalidUsage("Could not read the block",status_code=400)

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.route("/config", methods=["GET"])
def get_config():    
    # Returns the config file if writer is authenticated
    if authenticate_writer():
        return Response(json.dumps(config), mimetype="application/json", status=200)
    else:
        raise InvalidUsage("Writer not whitelisted", status_code=400)

@app.route("/config", methods=["POST"])
def add_writer_to_set():
    """ required: {
        "name": string,
        "hostname": string,
        "pub_key": string
        }
    """
    # Adds writer to node set and returns the config
    # Assumes one node per public ip address if remote
    writer_to_add = get_dict()
    if not LOCAL:
        try:
            if authenticate_writer(writer_to_add["hostname"]):  
                raise InvalidUsage("Writer already whitelisted", status_code=400)
        except:
            raise InvalidUsage("The JSON could not be decoded", status_code=400)
    # Append api to writer_set
    add_new_writer(writer_to_add)
    return Response(status=201)

@app.route("/activate_writer", methods=["POST"])
def activate_writer():
    """ Adds writer to active writer set if his blockchain is up to date 
    Writer sends in object with keys block and node
    """
    return add_to_active_set("active_writer_set_id_list")

@app.route("/activate_reader", methods=["POST"])
def activate_reader():
    """ Adds reader to active reader set if his blockchain is up to date """
    ...

@app.route("/blocks", methods=["GET"])
def get_blocks():
    """ optional: {
        "hash": string,
        "round": int,
        "prev_hash": string
        }
    """
    # Returns the API's version of the blockchain. Needs to ask a writer for the rest
    # We have a node set, an active writer set, and an active reader set 
    if authenticate_writer():
        print(request)
        print("REQUEST DATA: ", request.data)
        if not request.data:
            return Response(json.dumps(BCDB[0].get_blockchain()), mimetype="application/json", status=200)
        latest_writer_block = get_dict()
        missing_blocks = get_missing_blocks(latest_writer_block)
        if not missing_blocks:
            # return Response(json.dumps({"sync": True}), mimetype="application/json", status=200)
            return Response(json.dumps(False), status=200)
        
        # Send back missing blocks or entire blockchain
        return Response(json.dumps(missing_blocks), mimetype="application/json")
        # except:
        #     return Response("Sending blocks in json failed", status=500)
    else:
        return Response("Writer not whitelisted", status=400)

class WriterAPI():
    def __init__(self, app):
        self.app = app
    
    def run(self):
        # Register classes and send init arguments
        self.app.run(host="127.0.0.1", port="8000", debug=False)

if not from_main:
    from src.blockchainDB import BlockchainDB
    CWD = os.getcwd()
    db_path = CWD + "../src/db/test_blockchain.db"
    print(f"[DIRECTORY PATH] {db_path}")
    blocks_db = BlockchainDB(db_path)
    program = WriterAPI(app)
    program.run()
    