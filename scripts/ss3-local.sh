#!/bin/bash
# programming-language file id transactionRounds 
source ./venv/bin/activate
pip install -r requirements.txt
python3 -u ./src/main.py -myID 3 -r 0 -conf configs/config-local.json