#!/bin/bash
gunicorn -w 1 -b 127.0.0.1:6000 --chdir ./ClientAPI annallClientAPI:app