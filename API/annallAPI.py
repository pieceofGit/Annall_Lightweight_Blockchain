""" 
An API for Annáll using Flask and Gunicorn.
"""
import json

from flask import Flask, request, jsonify
import sys
from connectToServer import ServerConnection
from exceptionHandler import InvalidUsage
# import sys
print("Starting annallAPI Flask application server")
app = Flask(__name__)
# Connect to server
TCP_PORT = 5001 # Connects to port of writer 1
# if len(sys.argv) > 1:
#     TCP_PORT = int(sys.argv[1])

with open('../src/config.json') as config_file:
  config = json.load(config_file)
  TCP_PORT = config["active_writer_set"][0]["hostname"]
server = ServerConnection(TCP_PORT)


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route("/blocks", methods=["GET"])
def get_blockchain():
    # Asks for blockchain and gets it back
    try:
        return server.send_msg(json.dumps({"request_type": "read_chain"}))
    except Exception:
        raise InvalidUsage("Failed to read from writer", status_code=500)
    

@app.route("/block", methods=["POST"])
def insert_block():
    # Decode the JSON
    
    request_object = get_json(request)
    
    # Get the object 
    if "body" in request_object:
        print("request data", request.data)
        print(f"[REQUEST] {request_object}")
        block = json.dumps({"request_type": "block", "name": "name", "body": request_object["body"], "payload_id": 1})
        try:
            return server.send_msg(block)
        except Exception:
            raise InvalidUsage("Unable to post to writer", status_code=500)
    else:
        raise InvalidUsage("The JSON object key has to be named 'body'", status_code=400)

# Get back block if on blockchain and verified
# TODO: Add get block by blockid
# TODO: Get all blocks for a wallet
# @app.route("/block/<blockid>", methods=["GET"])
# def get_block():
#     request_object = get_json(request)
    
#     # return json.dumps({"message":"verified"})

def get_json(request):
    try:
        return json.loads(request.data) 
    except Exception:
        raise InvalidUsage("The JSON could not be decoded", status_code=400)




if __name__ == "__main__":
    app.run(debug=False)


