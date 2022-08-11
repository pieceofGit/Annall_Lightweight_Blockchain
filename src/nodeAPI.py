""" 
A NodeAPI for Annáll using Flask and Gunicorn.
"""
print("importing annall node API")
import json
import os
from flask import Flask, request, Response
print("WORKING DIRECTORY",os.getcwd())
PREPEND_PATH = os.getcwd() + "/src/"
from exceptionHandler import InvalidUsage
from_main = True
# import sys 
BCDB = ["Before db initialization"]
MEM_DATA = ["Before mem_data initialization"]
print("Starting annallClientAPI Flask application server")
app = Flask(__name__)
# Connect to server
LOCAL = True
if LOCAL:
    CONFIG_PATH = "config-local.json"
else:
    CONFIG_PATH = "config-remote.json"
print("config file in: ",PREPEND_PATH+CONFIG_PATH)

def add_to_config_by_key(key, value):
    try:
        MEM_DATA[0].add_to_config_by_key(key, value)
    except Exception as e:
        raise InvalidUsage("Could not access the json file", status_code=500)

def add_new_node(node):
    # Create new node object
    try:
        id = len(MEM_DATA[0].conf["node_set"]) + 1
        new_node = {
            "name": node["name"],
            "id": id,
            "hostname": node["hostname"],
            "pub_key": node["pub_key"]
        }
        if LOCAL:
            new_node["client_port"] = 5000 + id
            new_node["protocol_port"] = 15000 + id
        else:
            new_node["client_port"] = 5000
            new_node["protocol_port"] = 5000
        # Add node to node set and save    
        MEM_DATA[0].add_to_config_by_key("node_set", new_node)
    except Exception as e:
        raise InvalidUsage(f"Could not decode JSON {e}", status_code=400)

def node_authenticated(ip_address=None):
    # Checks if the request ip address or ip_address is in the node_set
    if not ip_address:
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    for obj in MEM_DATA[0].conf["node_set"]:
        if ip_address in obj["hostname"]:
            return True
    return False

def get_dict():
    try:
        return json.loads(request.data) 
    except Exception:
        raise InvalidUsage("The JSON could not be decoded", status_code=400)

def add_to_waiting_room(key):
    """ Adds node to the waiting list if it has the latest block
    """
    if node_authenticated():
        # compare latest blocks
        request_obj = get_dict()
        try:
            block = request_obj["block"]
            node_id = request_obj["node"]["id"]
            is_writer = request_obj["node"]["is_writer"]
            if node_id in MEM_DATA[0].conf[key]:
                return Response("Node already in set", status=200)
            api_latest_block = BCDB[0].get_latest_block()
            if not api_latest_block:
                return Response(json.dumps({"message": "Cannot verify node. Blockchain not started"}),
                    mimetype="application/json", status=500)
            if api_latest_block["hash"] == block["hash"]:
                # Add node to waiting list if not in any active set
                if not MEM_DATA[0].node_in_active_set(node_id):
                    MEM_DATA[0].add_to_config_by_key(key, value=(node_id, is_writer))
                    return Response(json.dumps(MEM_DATA[0].conf), mimetype="application/json", status=201)
                else:
                    return Response(json.dumps({"message": "node already in conf"}), mimetype="application/json", status=200)
            else:
                return Response(json.dumps({"message": "Node not up to date"}), mimetype="application/json", status=400)
        except Exception as e:
            raise InvalidUsage(f"Could not read the data {e}", status_code=400)
    else:
        return Response("Node not whitelisted", status=400)

def get_missing_blocks(writer_latest_block):
    # Needs to handle case if gbs and that it eventually catches up.
    # How should other writers be a part of this?
    # The api should not send duplicates that it will get when it has them already.
    api_latest_block = BCDB[0].get_latest_block()   # Get latest block in dict
    if not api_latest_block:    # Database empty
        return False
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

# Flask endpoints

@app.route("/config", methods=["GET"])
def get_config():    
    # Returns the config file if the writer is in the node_set
    if node_authenticated():
        return Response(json.dumps(MEM_DATA[0].conf), mimetype="application/json", status=200)
    else:
        raise InvalidUsage("Writer not whitelisted", status_code=400)

@app.route("/config", methods=["POST"])
def add_node_to_set():
    """ required: {
        "name": string,
        "hostname": string,
        "pub_key": string
        }
    """
    # Adds writer to node_set and returns the config. Can have duplicate ip addresseses if local
    node_to_add = get_dict()
    if not LOCAL:
        try:
            if node_authenticated(node_to_add["hostname"]):  
                raise InvalidUsage("Writer already whitelisted", status_code=400)
        except:
            raise InvalidUsage("The JSON could not be decoded", status_code=400)
    # Append node to the node_set
    add_new_node(node_to_add)
    return Response(status=201)

@app.route("/activate_node", methods=["POST"])
def activate_node():
    """ 
    {   "block": { "hash": string, "round": int, prev_hash: string},
        "node": {"id": int, "is_writer": bool}  }
    """
    # Returns the config, if node is added
    return add_to_waiting_room("waiting_list")

@app.route("/blocks", methods=["GET"])
def get_blocks():
    """ { "hash": string, "round": int, "prev_hash": string }
    """
    # Returns the API's version of the blockchain. Needs to ask a writer for the rest
    # We have a node set, an active writer set, and an active reader set 
    if node_authenticated():
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

class NodeAPI():
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
    program = NodeAPI(app)
    program.run()
    