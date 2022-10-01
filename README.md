# Lightweight-Blockchain

Lightweight blockchain project

### Installing

Start by creating a virtual environment in the root directory of the project

```bash
python -m venv .venv
```

Activate the virtual environment

windows

```bash
. .venv/Scripts/activate
```

linux

```bash
. .venv/bin/activate
```

Install the project itself (optional)

Installed the required packages

```bash
pip install -r requirements.txt
```

## Running

There are scripts for 5 nodes to run on the blockchain in the project root folder named ./ss<id>-local.sh. The scripts are configured to run the program indefinitely. Alternatively, you can set your own configuration for running the program with the environmental variables.
There are three optional environmental variables:
-myID: Sets the id of the writer.
-r: Sets the number of rounds. If not set, the writers run indefinitely.
-conf: specifies the local configuration file to use for running the program.
command:
python src/main.py -myID <id> -r <number of rounds> -conf <config file>

# About the program

The program has writers and readers of the blockchain, both writing to their own database.
The program executes the rounds when all writers and readers are connected.
The program's required set of writers and readers to start the blockchain are either set by the WriterAPI or with a local config file.
Writer with ID=3 runs the WriterAPI and should be started first for using the WriterAPI.
The writers and readers required to start are kept in the config file under "writer_list" and "reader_list".
To send POST and GET requests, you run the ClientAPI/annallClientAPI.py or you can just run src/tests/testclient.py <port no.> without the ClientAPI which connects and sends transactions directly to the blockchain.

# Example run

1. Open three terminals with the venv activated
2. run "./ss3-local.sh" to start the first node which activates the Writer API
3. run "./ss2-local.sh" and "./ss1-local.sh" separately
4. run "gunicorn -b 127.0.0.1:5000 annallClientAPI:app" to connect to writer 1 and sends requests.
5. Send successive POST and GET requests and see whether your transaction has been posted to the blockchain.
