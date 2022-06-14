# Lightweight-Blockchain

Lightweight blockchain project

### Running

There are two optional environmental variables
-myID: Sets the id of the writer. if myID == 1, the program starts the TCPServer.
If myID != 1, it starts the ClientServer which is empty.
-r: Sets the number of rounds.
command:
python src/main.py -myID <id> -r <number of rounds>

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

Create manually /src/db/blockchain.db

All scripts should be located in the directory

```
/src/<script>
```

Now you should be able to run any script in the project from the root directory

```
python <PATH_TO_SCRIPT>
```
