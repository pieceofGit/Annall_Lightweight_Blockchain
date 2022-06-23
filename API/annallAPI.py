""" An API for Annáll using Flask and Gunicorn.
"""
# Response is a JSON object
# create a block on blockchain
# POST /API/ block
# send back block and acknowledge if verified
# GET /API/ block / <block id>
# send back all blocks on blockchain
# GET /API/ blocks
import json
from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from connectToServer import ServerConnection
import sys
print("HELLO WORLD")
app = Flask(__name__)
api = Api(app)
# Connect to server
TCP_PORT = 5030
# if len(sys.argv) > 1:
#     TCP_PORT = int(sys.argv[1])
server = ServerConnection(TCP_PORT)

@app.route("/blocks", methods=["GET"])
def get_blockchain():
    # Asks for blockchain and gets it back
    return server.send_msg(json.dumps({"request_type": "read_chain"}))

@app.route("/block", methods=["POST"])
def insert_block():
    # body the only thing that matters
    body = json.loads(request.data)
    print(f"[BODY] {body}")
    block = json.dumps({"request_type": "block", "name": "name", "body": body["body"], "payload_id": 1})
    return server.send_msg(block)

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


