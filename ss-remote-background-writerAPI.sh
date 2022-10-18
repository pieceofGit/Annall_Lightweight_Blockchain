#!/bin/bash
nohup gunicorn --workers=1 --threads=4 --chdir ./src annallWriterAPI:app > writerAPI.out 2>&1

