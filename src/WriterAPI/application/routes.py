""" 
An API for Annáll nodes using Flask and Gunicorn.
The API handles membership changes for Annall nódes 
"""
import json
import os
from flask import Flask, request, jsonify, Response, current_app as app
from sympy import im
from application.exceptionHandler import InvalidUsage
from application.models.activateNodeInputModel import ActivateNodeInputModel

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
        save_conf_file()
    except Exception as e:
        raise InvalidUsage(f"Could not decode JSON {e}", status_code=400)
def save_conf_file():
    try:
        with open(app.config["CONFIG_NAME"], "w") as file:
            json.dump(app.config["CONF"], file, indent=4)
    except:
        raise InvalidUsage("Could not access the json file", status_code=500)

def authenticate_writer():
    # Checks if public ip address of request is in writer list
    ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    for obj in app.config["CONF"]["node_set"]:
        if ip_address in obj["hostname"] or app.config["IS_LOCAL"]:
            return True
    return False

def get_dict():
    try:
        return json.loads(request.data) 
    except Exception:
        raise InvalidUsage("The JSON could not be decoded", status_code=400)

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.route("/activate_node", methods=["POST"])
def activate_node():
    """
        Adds node to active reader or writer set and returns new config. Removes it from other active list.
        required: {
            "id": int,
            "is_writer": bool
        }
    """
    # TODO: Should be a signature, not an id to make changes for a node
    node_to_activate = get_dict()
    update = False
    request_obj = ActivateNodeInputModel(node_to_activate)
    if request_obj.error:
        return Response(json.dumps(request_obj.dict), mimetype="application/json", status=400)
    try:
        if node_to_activate["is_writer"]:
            # Node is writer
            if node_to_activate["id"] not in app.config["CONF"]["writer_list"]:
                app.config["CONF"]["writer_list"].append(node_to_activate["id"])
                update = True
                if node_to_activate["id"] in app.config["CONF"]["reader_list"]:
                    app.config["CONF"]["reader_list"].remove(node_to_activate["id"])
        else:
            # Node is reader
            if node_to_activate["id"] not in app.config["CONF"]["reader_list"]:
                app.config["CONF"]["reader_list"].append(node_to_activate["id"])
                update = True
                if node_to_activate["id"] in app.config["CONF"]["writer_list"]:
                    app.config["CONF"]["writer_list"].remove(node_to_activate["id"])
        if update:
            app.config["CONF"]["membership_version"] += 1   # Update version number of membership
        save_conf_file()
        return Response(json.dumps(app.config["CONF"]), mimetype="application/json", status=201)
    except Exception as e:
        raise InvalidUsage(json.dumps(f"The JSON could not be decoded. Error: {e}"), status_code=400)

@app.route("/deactivate_node", methods=["POST"])
def deactivate_node():
    """
        Adds node to active reader or writer set and returns new config
        required: {
            "id": int,
            "is_writer": bool
        }
    """
    # TODO: Should be a signature, not an id to make changes for a node
    node_to_deactivate = get_dict()
    update = False
    request_obj = ActivateNodeInputModel(node_to_deactivate)
    if request_obj.error:
        return Response(json.dumps(request_obj.dict), mimetype="application/json", status=400)
    try:
        if node_to_deactivate["is_writer"]:
            # Node is writer
            if node_to_deactivate["id"] in app.config["CONF"]["writer_list"]:
                app.config["CONF"]["writer_list"].remove(node_to_deactivate["id"])
                update = True
        else:
            # Node is reader
            if node_to_deactivate["id"] in app.config["CONF"]["reader_list"]:
                app.config["CONF"]["reader_list"].remove(node_to_deactivate["id"])
                update = True
        if update:
            app.config["CONF"]["membership_version"] += 1   # Update version number of membership
        save_conf_file()
        return Response(status=204)
    except Exception as e:
        raise InvalidUsage(json.dumps(f"The JSON could not be decoded. Error: {e}"), status_code=400)

@app.route("/config", methods=["GET"])
def get_config():    
    # Returns the conf file if writer is authenticated
    return Response(json.dumps(app.config["CONF"]), mimetype="application/json", status=200)
    # else:
    #     raise InvalidUsage("Writer not whitelisted", status_code=400)

@app.route("/config", methods=["POST"])
def add_node():
    """ required: {
        "name": string,
        "hostname": string,
        "pub_key": string
        }
    """
    # Adds writer to node set and returns the conf
    # Assumes one node per public ip address if remote
    writer_to_add = get_dict()
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
    with open(app.config["CONF_RESET_FILE"], "r") as writer_api_conf:
        update_num = json.load(writer_api_conf)
        return update_num["update_number"]

@app.route("/blocks", methods=["DELETE"])
def delete_chain():
    # if authenticate_writer():
    with open(app.config["CONF_RESET_FILE"], "r") as writer_api_conf:
        update_num = json.load(writer_api_conf)
    with open(app.config["CONF_RESET_FILE"], "w") as writer_api_conf:
        json.dump({"update_number":update_num["update_number"]+1}, writer_api_conf, indent=4)    
    return Response(status=204)

@app.route("/update", methods=["GET"])
def get_update():
    """Returns number of latest update"""
    return Response(json.dumps({"update_number": get_update_num(), "restart": True}), mimetype="application/json")