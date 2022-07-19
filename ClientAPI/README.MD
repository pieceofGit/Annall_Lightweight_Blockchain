annallClientAPI is a Python Flask gateway API intermediary between a client and the Annáll blockchain. On start, the API sets up two way communication to a writer on the Annáll blockchain using a TCP socket.
The API gets incoming requests of type:
a. GET /blocks
b. POST /block {"body": payload}
For a POST /block, the API expects a key "body" and payload in a JSON object.

To run the API:

    1. virtualenv api_venv
    2. source ./api_venv/bin/activate
    3. pip install -r requirements.txt
    4. python annallClientAPI.py <local writer port>

    For auto flask run this command: FLASK_APP=annallClientAPI.py FLASK_ENV=development flask run

NOTE: A writer has to be running for the API to service requests.

The API tries ten times over ten seconds to connect to the TCP socket of the writer on the selected port. If it fails ten times, the API remains running but none of the requests are handled.

The API can run using gunicorn. Gunicorn is a WSGI server that can run in a production environment and supports multiple workers.

- gunicorn -w <no. of workers> -b <ip_address:port> annallClientAPI:app
- gunicorn annallClientAPI:app

  The API has a class for the writer connection and a class for exception handling.
