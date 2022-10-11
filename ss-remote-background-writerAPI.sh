#!/bin/bash
nohup gunicorn -w 4 --chdir ./src annallWriterAPI:app > writerAPI.out 2>&1

