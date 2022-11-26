#!/bin/bash
nohup gunicorn -w 1 --chdir ./src annallWriterAPI:app > writerAPI.out 2>&1

