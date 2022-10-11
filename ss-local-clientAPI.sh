#!/bin/bash
gunicorn -w 4 -b 127.0.0.1:6000 --chdir ./ClientAPI annallClientAPI:app