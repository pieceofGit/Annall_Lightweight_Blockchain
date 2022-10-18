#!/bin/bash
# programming-language file id transactionRounds 
python3 ./src/main.py -myID 2 -r 0 -conf config-remote.json -writerApiPath http://176.58.116.107:70/  > writer2.out 2>&1 &