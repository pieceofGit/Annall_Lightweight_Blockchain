""" 
A WriterAPI for Annáll using Flask and Gunicorn.
"""
import json
import os
from flask import Flask, request, jsonify, Response, current_app as app
from application.exceptionHandler import InvalidUsage


# Configurable variables
print("Starting annallWriterAPI Flask application server")

def add_new_writer(writer):
    # Create new writer object
    try:
        id = len(app.config["CONF"]["node_set"]) + 1
        new_writer = {
            "name": writer["name"],
            "id": id,
            "hostname": writer["hostname"],
            "pub_key": writer["pub_key"]
        }
        if app.config["IS_LOCAL"]:
            new_writer["client_port"] = 5000 + id
            new_writer["protocol_port"] = 15000 + id - 1
        else:
            new_writer["client_port"] = 5000
            new_writer["protocol_port"] = 5000
        # Add writer to writer set and save    
        app.config["CONF"]["node_set"].append(new_writer)
        try:
            with open(app.config["CONFIG_NAME"], "w") as file:
                json.dump(app.config["CONF"], file, indent=4)
        except:
            raise InvalidUsage("Could not access the json file", status_code=500)
    except Exception as e:
        raise InvalidUsage(f"Could not decode JSON {e}", status_code=400)

def authenticate_writer():
    # Checks if public ip address of request is in writer list
    ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    for obj in app.config["CONF"]["node_set"]:
        if ip_address in obj["hostname"] or ip_address == "172.17.0.1":
            return True
    return False

def get_json():
    try:
        return json.loads(request.data) 
    except Exception:
        raise InvalidUsage("The JSON could not be decoded", status_code=400)

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.route("/config", methods=["GET"])
def get_config():    
    # Returns the conf file if writer is authenticated
    return Response(json.dumps(app.config["CONF"]), mimetype="application/json", status=200)
    # else:
    #     raise InvalidUsage("Writer not whitelisted", status_code=400)

@app.route("/config", methods=["POST"])
def add_writer_to_set():
    """ required: {
        "name": string,
        "hostname": string,
        "pub_key": string
        }
    """
    # Adds writer to node set and returns the conf
    # Assumes one node per public ip address if remote
    writer_to_add = get_json()
    if not app.config["IS_LOCAL"]:
        try:
            if authenticate_writer(writer_to_add["hostname"]):
                raise InvalidUsage("Writer already whitelisted", status_code=400)
        except:
            raise InvalidUsage("The JSON could not be decoded", status_code=400)
    # Append api to writer_set
    add_new_writer(writer_to_add)
    return Response(status=201)
def get_update_num():
    with open(app.config["CONF_WRITER_FILE"], "r") as writer_api_conf:
        update_num = json.load(writer_api_conf)
        return update_num["update_number"]

@app.route("/blocks", methods=["DELETE"])
def delete_chain():
    # if authenticate_writer():
    with open(app.config["CONF_WRITER_FILE"], "r") as writer_api_conf:
        update_num = json.load(writer_api_conf)
    with open(app.config["CONF_WRITER_FILE"], "w") as writer_api_conf:
        json.dump({"update_number":update_num["update_number"]+1}, writer_api_conf, indent=4)    
    return Response(status=204)

@app.route("/update", methods=["GET"])
def get_update():
    """Returns number of latest update"""
    return Response(json.dumps({"update_number": get_update_num(), "restart": True}), mimetype="application/json")