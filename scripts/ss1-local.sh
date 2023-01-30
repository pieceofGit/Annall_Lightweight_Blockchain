#!/bin/bash
# programming-language file id transactionRounds 
kill -9 $(lsof -t -i:5000)
source ./venv/bin/activate
pip install -r requirements.txt
python3 -u ./src/main.py -myID 1 -r 0 -conf configs/config-local.json