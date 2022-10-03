#!/bin/bash
nohup gunicorn -w 1 --chdir ./src annallWriterAPI:app > /dev/null 2>&1&
