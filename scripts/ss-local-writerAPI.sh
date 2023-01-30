#!/bin/bash
kill -9 $(lsof -t -i:8000)
gunicorn -w 4 -b 127.0.0.1:8000 --chdir ./src/WriterAPI wsgiDev:app