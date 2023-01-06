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
from application.models.createNodeInputModel import CreateNodeInputModel

# Configurable variables
print("Starting annallWriterAPI Flask application server")

def add_new_node(node):
    # Create new node object
    try:
        id = app.config["DB"].get_new_node_id()
        new_node = {
            "name": node["name"],
            "id": id,
            "hostname": node["hostname"],
            "pub_key": node["pub_key"]
        }
        if app.config["IS_LOCAL"]:
            new_node["client_port"] = 5000 + id
            new_node["protocol_port"] = 15000 + id - 1
        else:
            new_node["client_port"] = 5000
            new_node["protocol_port"] = 5000
        # Add node to node set and save
        
        return app.config["DB"].add_to_node_set(new_node)
    except ValueError:
        raise InvalidUsage(f"Node with key pub_key already exists", status_code=409)
    except Exception as e:
        raise InvalidUsage(f"Could not decode JSON {e}", status_code=400)

def authenticate_writer():
    # Checks if public ip address of request is in writer list
    ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    for obj in app.config["CONF"]["node_set"]:
        if ip_address in obj["hostname"] or app.config["IS_LOCAL"]:
            return True
    return False

def load_json():
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
        Adds node to active reader or writer set and returns new config. 
        If node is in another active set it is removed from it.
        required: {
            "id": int,
            "is_writer": bool
        }
    """
    # TODO: Should be a signature, not an id to make changes for a node
    node_input_model = ActivateNodeInputModel(load_json())
    if node_input_model.error:
        return Response(json.dumps(node_input_model.dict), mimetype="application/json", status=400)
    try:
        latest_conf = app.config["DB"].activate_node(id=node_input_model.id, is_writer=node_input_model.is_writer)
        return Response(json.dumps(latest_conf), mimetype="application/json", status=201)
    except ValueError:
        return Response(json.dumps(f"Node already in active set"), mimetype="application/json", status=409)
    except KeyError:
        return Response(json.dumps(f"Node with id {node_input_model.id} not found"), mimetype="application/json", status=404)
    except Exception as e:
        raise InvalidUsage(json.dumps(f"Failed to complete request. Error: {e}"), status_code=500)

@app.route("/deactivate_node", methods=["POST"])    #TODO: Add PUT on editing node details and increment version number. 
def deactivate_node():
    """
        Removes node from active reader or writer set and returns NoContent
        required: {
            "id": int,
            "is_writer": bool
        }
    """
    # TODO: Should be a signature, not an id to make changes for a node
    node_input_model = ActivateNodeInputModel(load_json())
    if node_input_model.error:
        return Response(json.dumps(node_input_model.dict), mimetype="application/json", status=400)
    try:
        latest_conf = app.config["DB"].deactivate_node(id=node_input_model.id, is_writer=node_input_model.is_writer)
        return Response(json.dumps({"id": latest_conf}), mimetype="application/json", status=204)
    except ValueError:
        return Response(json.dumps(f"Node not in active set"), mimetype="application/json", status=409)
    except KeyError:
        return Response(json.dumps(f"Node with id {node_input_model.id} not found"), mimetype="application/json", status=404)
    except Exception as e:
        raise InvalidUsage(json.dumps(f"Failed to complete request. Error: {e}"), status_code=500)

@app.route("/config", methods=["GET"])
def get_config():    
    # Returns the conf file if writer is authenticated
    return Response(json.dumps(app.config["DB"].get_latest_config()), mimetype="application/json", status=200)
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
    node_input_model = CreateNodeInputModel(load_json())
    if node_input_model.error:
        return Response(json.dumps(node_input_model.dict), mimetype="application/json", status=400)
    if not app.config["IS_LOCAL"]:
        try:
            if authenticate_writer(node_input_model.hostname):
                raise InvalidUsage("Writer already whitelisted", status_code=400)
        except:
            raise InvalidUsage("The JSON could not be decoded", status_code=400)
    # Append api to writer_set
    add_new_node(node_input_model.dict)
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