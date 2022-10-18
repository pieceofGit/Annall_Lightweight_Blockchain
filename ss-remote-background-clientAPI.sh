#!/bin/bash
nohup gunicorn --workers=1 --threads=4 --chdir ./ClientAPI annallClientAPI:app > clientAPI.out 2>&1&