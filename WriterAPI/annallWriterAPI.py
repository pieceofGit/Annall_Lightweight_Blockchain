""" 
A ClientAPI for Annáll using Flask and Gunicorn.
"""
print("importing annall writer api")
import json
import os
import argparse
from flask import Flask, request, jsonify, Response
import sys
try: 
    from .exceptionHandler import InvalidUsage
    from_main = True
except: 
    from exceptionHandler import InvalidUsage
    from_main = False
# import sys
print("Starting annallClientAPI Flask application server")
app = Flask(__name__)
# Connect to server
print("WORKING DIRECTORY: ", os.getcwd())
LOCAL = True
if LOCAL:
    if from_main:
        CONFIG_PATH = os.getcwd()+"/WriterAPI/config-local.json"
    else:
        CONFIG_PATH = "config-local.json"
else:
    CONFIG_PATH = "config-remote.json"

with open(CONFIG_PATH, "r") as config_file:
  config = json.load(config_file)


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.route("/config", methods=["GET"])
def get_config():    
    # Returns the config file if writer is authenticated
    if authenticate_writer():
        return json.dumps(config)
    else:
        raise InvalidUsage("Writer not whitelisted", status_code=400)

@app.route("/config", methods=["POST"])
def add_writer_to_set():
    # Sends in its name, ip address, and public key
    # Gets back entire config
    writer_to_add = get_json()
    if not LOCAL:
        try:
            if authenticate_writer(writer_to_add["hostname"]):
                raise InvalidUsage("Writer already whitelisted", status_code=400)
        except:
            raise InvalidUsage("The JSON could not be decoded", status_code=400)
    # Append api to writer_set
    #TODO: The API should share info about new writer to other writers
    try:
        add_new_writer(writer_to_add)
        return Response(status=200, mimetype="application/json")
    except:
        raise(InvalidUsage("Failed to add writer to config", status_code=500))

@app.route("/blockchain", methods=["GET"])
def get_blockchain():
    # Returns the API's version of the blockchain. Needs to ask a writer for the rest
    # Should the API be a constant blockchain reader? We can define separate sets for sending information
    # Reader set, active writer set, writer set, 
    ...

@app.route("/blocks", methods=["GET"])
def get_missing_blocks():
    # Gets the latest block of the writer's blockchain. Sends it missing blocks in the chain
    ...


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
        config["node_set"].append(new_writer)
        with open(CONFIG_PATH, "w") as file:
            json.dump(config, file, indent=4)
    except Exception as e:
        raise InvalidUsage(f"Could not decode JSON {e}", status_code=400)

def authenticate_writer():
    # Checks if public ip address of request is in writer list
    ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    for obj in config["node_set"]:
        if ip_address in obj["hostname"]:
            return True
    return False

def get_json():
    try:
        return json.loads(request.data) 
    except Exception:
        raise InvalidUsage("The JSON could not be decoded", status_code=400)

if not from_main:
    app.run(debug=True)

class WriterAPI:
    def __init__(self, bcdb, app):
        self.bcdb = bcdb
        self.app = app
    
    def run(self):
        self.app.run(host="127.0.0.1", port="8000")
