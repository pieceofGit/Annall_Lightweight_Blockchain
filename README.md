# Lightweight-Blockchain

Lightweight blockchain project

### Run without Docker

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

There are scripts for 5 nodes to run on the blockchain in the project root folder named ./ss(id)-local.sh. The scripts are configured to run the program indefinitely. Alternatively, you can set your own configuration for running the program with the environmental variables.
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

## Example run without Docker
Make sure the config-local file is setup with the number of writers and readers you want to start.
1. Setup venv and install requirements for writer API
2. Start writer API with command:
```bash
./ss-local-writerAPI.sh
```
3. For each writer start up with the id:
```bash
./ss<id>-local-writerAPI.sh
```
4. Start client API with command:
```bash
./ss-local-clientAPI.sh
```
5. Send successive POST and GET requests and see whether your transaction has been posted to the blockchain.

## Example run with Docker
Make sure docker is installed
1. Under directory / run:
```bash
docker compose up -d
```
2. Send successive POST and GET requests and see whether your transaction has been posted to the blockchain.



