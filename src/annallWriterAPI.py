""" 
A WriterAPI for Annáll using Flask and Gunicorn.
"""
import json
import os
from flask import Flask, request, jsonify, Response
from exceptionHandler import InvalidUsage
from blockchainDB import BlockchainDB
from membershipData import MembershipData


# Configurable variables
PREPEND_PATH = os.getcwd() + "/"
UPDATE_NUM = [0]
CONFIG_PATH = "config-remote.json"    # Change for remote vs local setup
MEM_DATA = ["Before object initialization"]
BCDB = ["Before db initialization"]
CWD = os.getcwd()
db_path = CWD + "/db/test_blockchain.db"
print(f"[DIRECTORY PATH] {db_path}")
BCDB[0] = BlockchainDB(db_path)
IS_LOCAL = [True]
# MEM_DATA = ["Before object initialization"]
print("Starting annallWriterAPI Flask application server")
# print("conf file in: ",PREPEND_PATH+CONFIG_PATH)
# API_PATH = "127.0.0.1:8000/"
API_PATH = "176.58.116.107:70"
with open(PREPEND_PATH+CONFIG_PATH, "r") as config_file:
  conf = json.load(config_file)
MEM_DATA[0] = MembershipData(1, PREPEND_PATH, CONFIG_PATH, API_PATH, BCDB[0])
with open(PREPEND_PATH+"config-writer-api-update.json", "w") as writer_api_conf:
    json.dump({"update_number": 0}, writer_api_conf, indent=4)    

app = Flask(__name__)

def add_new_writer(writer):
    # Create new writer object
    try:
        id = len(conf["node_set"]) + 1
        new_writer = {
            "name": writer["name"],
            "id": id,
            "hostname": writer["hostname"],
            "pub_key": writer["pub_key"]
        }
        if IS_LOCAL[0]:
            new_writer["client_port"] = 5000 + id
            new_writer["protocol_port"] = 15000 + id
        else:
            new_writer["client_port"] = 5000
            new_writer["protocol_port"] = 5000
        # Add writer to writer set and save    
        conf["node_set"].append(new_writer)
        try:
            with open(PREPEND_PATH + CONFIG_PATH, "w") as file:
                json.dump(conf, file, indent=4)
        except:
            raise InvalidUsage("Could not access the json file", status_code=500)
    except Exception as e:
        raise InvalidUsage(f"Could not decode JSON {e}", status_code=400)

def authenticate_writer():
    # Checks if public ip address of request is in writer list
    # ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    # print(f"IP ADDRESS OF NODE; {ip_address}")
    # for obj in conf["node_set"]:
    #     if ip_address in obj["hostname"]:
    #         return True
    # return False
    return True

def get_json():
    try:
        return json.loads(request.data) 
    except Exception:
        raise InvalidUsage("The JSON could not be decoded", status_code=400)

# def get_missing_blocks(writer_latest_block):
#     # Needs to handle case if gbs and that it eventually catches up.
#     # How should other writers be a part of this?
#     # The api should not send duplicates that it will get when it has them already.
#     api_latest_block = BCDB[0].get_latest_block()   # Get latest block in dict
#     # if api_latest_block[""]
#     try:
#         if api_latest_block["hash"] == writer_latest_block["hash"] and writer_latest_block["prevHash"] == api_latest_block["prevHash"]: # Add compare prev hash
#             return False   # Writer is up to date
#         else:
#             if api_latest_block["round"] == writer_latest_block["round"] or writer_latest_block["prevHash"] == api_latest_block["prevHash"]:
#                 # Different hash, same round or prevHash. Something not ok on their end, return the blockchain
#                 try:
#                     missing_blocks = BCDB[0].get_blockchain()
#                     return missing_blocks
#                 except:
#                     raise InvalidUsage("Could not fetch blocks", status_code=500)
#             else:
#                 try:
#                     # Different prev_hash, hash, and rounds
#                     missing_blocks = BCDB[0].get_range_of_blocks(writer_latest_block["round"] + 1)
#                     return missing_blocks
#                 except:
#                     raise InvalidUsage("Could not fetch blocks", status_code=500)
#     except Exception as e:
#         raise InvalidUsage(f"Could not read the block {e}",status_code=400)

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.route("/config", methods=["GET"])
def get_config():    
    # Returns the conf file if writer is authenticated
    if authenticate_writer():
        print(f"THE CONF {conf}")
        return Response(json.dumps(conf), mimetype="application/json", status=200)
    else:
        raise InvalidUsage("Writer not whitelisted", status_code=400)

# @app.route("/conf", methods=["POST"])
# def add_writer_to_set():
#     """ required: {
#         "name": string,
#         "hostname": string,
#         "pub_key": string
#         }
#     """
#     # Adds writer to node set and returns the conf
#     # Assumes one node per public ip address if remote
#     writer_to_add = get_json()
#     if not IS_LOCAL[0]:
#         try:
#             if authenticate_writer(writer_to_add["hostname"]):  
#                 raise InvalidUsage("Writer already whitelisted", status_code=400)
#         except:
#             raise InvalidUsage("The JSON could not be decoded", status_code=400)
#     # Append api to writer_set
#     add_new_writer(writer_to_add)
#     return Response(status=201)

# @app.route("/activate_writer", methods=["POST"])
# def activate_writer():
#     """ Should add writer to active writer set """
#     ...

# @app.route("/activate_reader", methods=["POST"])
# def activate_reader():
#     """ Should add reader to active reader set """
#     ...

# @app.route("/blocks", methods=["GET"])
# def get_blocks():
#     """ optional: {
#         "hash": string,
#         "round": int,
#         "prevHash": string
#         }
#     """
#     # Returns the API's version of the blockchain. Needs to ask a writer for the rest
#     # We have a node set, an active writer set, and an active reader set 
#     if authenticate_writer():
#         print("REQUEST DATA: ", request.data)
#         if not request.data:
#             return Response(json.dumps(BCDB[0].get_blockchain()), mimetype="application/json", status=200)
#         latest_writer_block = get_json()
#         missing_blocks = get_missing_blocks(latest_writer_block)
#         if not missing_blocks:
#             return Response(json.dumps({"sync": True}), mimetype="application/json", status=200)
        
#         # Send back missing blocks or entire blockchain
#         return Response(json.dumps(missing_blocks), mimetype="application/json")
#         # except:
#         #     return Response("Sending blocks in json failed", status=500)
#     else:
#         return Response("Writer not whitelisted", status=400)


@app.route("/blocks", methods=["DELETE"])
def delete_chain():
    # if authenticate_writer():
    UPDATE_NUM[0] += 1
    with open(PREPEND_PATH+"config-writer-api-update.json", "r") as writer_api_conf:
        conf = json.load(writer_api_conf)
        conf["update_number"] = UPDATE_NUM[0]
    with open(PREPEND_PATH+"config-writer-api-update.json", "w") as writer_api_conf:
        json.dump(conf, writer_api_conf, indent=4)    
    return Response(status=204)

@app.route("/update", methods=["GET"])
def get_update():
    # if authenticate_writer():
    # Send update number of time of request and data
    return Response(json.dumps({"update_number": UPDATE_NUM[0], "restart": True}))


class WriterAPI():
    def __init__(self, app, debug=False):
        self.app = app
        self.debug = debug
    
    def run(self):
        # Register classes and send init arguments
        # self.app.run(host="127.0.0.1", port="8000", debug=self.debug)
        self.app.run(debug=False)

if __name__ == "__main__":
    program = WriterAPI(app, True)
    program.run()
    