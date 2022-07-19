# Lightweight-Blockchain

Lightweight blockchain project

### Running

There are two optional environmental variables
-myID: Sets the id of the writer.
-r: Sets the number of rounds. If not set, the writers run indefinitely.
command:
python src/main.py -myID <id> -r <number of rounds>

The program has writers and readers of the blockchain, both writing to their own database.
The program executes the rounds when all writers and readers are connected.
The program's writers and readers are either set by starting the WriterAPI or with a local config file.
The writers and readers required to start are kept in the config under "active_writer_set_id_list" and "active_reader_set_id_list".
To send POST and GET requests, you run the ClientAPI/annallClientAPI.py or you can just run src/tests/testclient.py <port no.> without the ClientAPI which connects and sends transactions directly to the blockchain.

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

Now you should be able to run any script in the project from the root directory

```
python <PATH_TO_SCRIPT>
```
