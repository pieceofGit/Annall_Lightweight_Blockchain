(trap 'kill 0' SIGINT EXIT; python3 ./src/main.py -myID 1 -r 0 -conf config-local.json & python3 ./src/main.py -myID 2 -r 0 -conf config-local.json & gunicorn -w 1 --chdir ./API annallAPI:app)
