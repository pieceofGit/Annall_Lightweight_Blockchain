#!/bin/bash
# programming-language file id transactionRounds 
source ./venv/bin/activate
pip install -r requirements.txt
kill -9 $(lsof -t -i:5001)
python3 -u ./src/main.py -myID 2 -r 0 -conf configs/config-local.json