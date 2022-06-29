# Lightweight-Blockchain

Lightweight blockchain project

### Running

There are two optional environmental variables
-myID: Sets the id of the writer. if myID == 1, the program starts the TCPServer.
-r: Sets the number of rounds. If not set, the writers run indefinitely.
command:
python src/main.py -myID <id> -r <number of rounds>
The program executes the rounds when all the set writers are connected. The no. of writers can be changed in main.py with the NUM_WRITERS variable. To send POST and GET requests, you run the API/annallAPI.py or you can just run src/tests/testclient.py <port no.> without the API which connects and sends transactions directly to the blockchain.

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
