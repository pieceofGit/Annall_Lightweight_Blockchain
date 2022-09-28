#!/bin/bash
gunicorn -w 1 -b 127.0.0.1:5000 --chdir ./ClientAPI annallClientAPI:app