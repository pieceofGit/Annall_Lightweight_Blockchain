#!/bin/bash
nohup gunicorn -w 1 --chdir ./ClientAPI annallClientAPI:app > /dev/null 2>&1&
