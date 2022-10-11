#!/bin/bash
nohup gunicorn -w 4 --chdir ./ClientAPI annallClientAPI:app > clientAPI.out 2>&1&
