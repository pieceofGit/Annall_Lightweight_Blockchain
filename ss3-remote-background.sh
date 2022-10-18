#!/bin/bash
# programming-language file id transactionRounds 
python3 ./src/main.py -myID 3 -r 20 -conf config-remote.json -writerApiPath http://176.58.116.107:70/  > writer3.out 2>&1&