""" 
A ClientAPI for Annáll using Flask and Gunicorn.
"""
import json
import os
import argparse
from flask import Flask, request, jsonify, Response
import sys
from exceptionHandler import InvalidUsage
# import sys
print("Starting annallClientAPI Flask application server")
app = Flask(__name__)
# Connect to server
print("WORKING DIRECTORY", os.getcwd())
LOCAL = True
if LOCAL:
    config_path = "config-local.json"
else:
    config_path = "config-remote.json"

with open(config_path) as config_file:
  config = json.load(config_file)


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route("/config", methods=["GET"])
def get_config():    
    # Returns the config file 
    # TODO: Authentication of writer. Probably check if IP address is in the json
    print(request.environ.get('HTTP_X_REAL_IP', request.remote_addr))
    print(config)
    if authenticate_writer():
        return json.dumps(config)
    else:
        raise InvalidUsage("Writer not whitelisted", status_code=400)

@app.route("/config", methods=["POST"])
def add_writer_to_set():
    # Sends in its name, ip address, and public key
    #TODO: Initial authentication
    
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
        return json.dumps(config)
    except:
        raise(InvalidUsage("Failed to add writer to config", status_code=500))



@app.route("/blockchain", methods=["GET"])
def get_blockchain():
    # Returns the API's version of the blockchain. Needs to ask a writer for the rest
    # Should the API be a constant blockchain reader? We can define separate sets for sending information
    # Reader set, active writer set, writer set, 
    ...

def add_new_writer(writer):
    # Create new writer object
    try:
        id = len(config["writer_set"]) + 1
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
        config["writer_set"].append(new_writer)
    except Exception as e:
        raise InvalidUsage(f"Could not decode JSON {e}", status_code=400)

def authenticate_writer():
    ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    for obj in config["writer_set"]:
        if ip_address in obj["hostname"]:
            return True
    return False

def get_json():
    try:
        return json.loads(request.data) 
    except Exception:
        raise InvalidUsage("The JSON could not be decoded", status_code=400)




if __name__ == "__main__":
    app.run(debug=True)


