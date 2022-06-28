""" 
An API for Annáll using Flask and Gunicorn.
"""
import json

from flask import Flask, request, jsonify
import sys
from connectToServer import ServerConnection
from exceptionHandler import InvalidUsage
# import sys
print("HELLO WORLD")
app = Flask(__name__)
# Connect to server
TCP_PORT = 5011
if len(sys.argv) > 1:
    TCP_PORT = int(sys.argv[1])
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
    try:
        request_object = json.loads(request.data) 
    except Exception:
        raise InvalidUsage("The JSON could not be decoded", status_code=400)
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
        raise InvalidUsage("The key has to be named body", status_code=400)

@app.route('/foo')
def get_foo():
    raise InvalidUsage('This view is gone', status_code=410)

# class Block(Resource):
#     # Add block to blockchain
#     def post(self, block):
#         return {"block": "block id"}

# class Blocks(Resource):
#     # Returns blockchain
#     def get(self):
#         return {"blocks": "the blockchain"}
        

# api.add_resource(Block, "/block")
# api.add_resource(Annall, "/block/<int:blockid>")  # Define type of parameter 
# api.add_resource(Annall, "/blocks")



if __name__ == "__main__":
    app.run(debug=True)


