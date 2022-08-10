nodeAPI is a Python Flask gateway API intermediary for whitelisting, analysis, and fetching the Annáll blockchain. On start, the API sets up two way communication to a writer on the Annáll blockchain using a TCP socket.
The API gets incoming requests of type:
a. GET /config
b. POST /config, {new_writer}
new_writer = {
"hostname": <public ip address>,
"name": <writer custom name>,
"pub_key": <public key>,
}
For a POST /config, the API expects the keys: hostname, name, and pub_key.
The endpoint sends back a 200 message if the request was successful.
For GET / config, the request needs to be from a writer in the writer set as it checks if the public ip address of the incoming request is in the writer set.

To run the API:

    1. virtualenv venv
    2. source ./venv/bin/activate
    3. pip install -r requirements.txt
    4. python nodeAPI.py

The API can run using gunicorn. Gunicorn is a WSGI server that can run in a production environment and supports multiple workers.

- gunicorn -w <no. of workers> nodeAPI:app
- gunicorn nodeAPI:app

  The API has a class for the writer connection and a class for exception handling.
