# About

annallClientAPI is a Python Flask gateway API intermediary between a client and the Annáll blockchain. On start, the API sets up two way communication to a writer on the Annáll blockchain using a TCP socket.

The API gets incoming requests of type:
a. GET /blocks
b. POST /block {"payload": payload}
For a POST /block, the API expects a key "payload" in a JSON object with any value.

To run the API: 1. virtualenv api_venv 2. source ./api_venv/bin/activate 3. pip install -r requirements.txt 4. python annallClientAPI.py <local writer port>

    For auto flask run this command: FLASK_APP=annallClientAPI.py FLASK_ENV=development flask run

NOTE: the writer 1 has to be running for the API to forward requests to the blockchain. The blockchain has to be running for the GET method and for putting transactions into blocks on the blockchain.

The API tries ten times over ten seconds to connect to the TCP socket of the writer on the selected port. If it fails ten times, the API remains running but none of the requests are handled.

The API can run using gunicorn. Gunicorn is a WSGI server that can run in a production environment and supports multiple workers.

- gunicorn -w <no. of workers> -b <ip_address:port> annallClientAPI:app
- gunicorn annallClientAPI:app

  The API has a class for the writer connection and a class for exception handling.

# Example endpoint 

POST / blocks
´´
@app.route("/blocks", methods=["POST"])
def insert_block():
    """ Sends the transaction for insertion as block on the chain. """
    request_object = get_json(request)
    if "payload" in request_object:
        block = json.dumps({"request_type": "block", "name": "name", "payload": request_object['payload'], "payload_id": 1})
        try:
            resp_obj = server.send_msg(block)
            return Response(resp_obj, mimetype="application/json")
        except Exception:
            raise InvalidUsage("Unable to post to writer", status_code=500)
    else:
        raise InvalidUsage("The JSON object key has to be named payload", status_code=400)
´´

The example shows how a request for posting a block to the blockchain. 
The TCP server requires the field "request_type" and the field "payload" if "request_type": "block".
The client sends the message to the server in a json format. 
The server can alternatively handle the request types "read_chain" and "verify". 
If "read_chain", the server sends back the entire blockchain.
If "verify", the server sends a confirmation if block is verified or not using the hash.