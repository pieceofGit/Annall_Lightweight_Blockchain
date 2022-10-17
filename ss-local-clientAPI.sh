#!/bin/bash
gunicorn --workers=1 --threads=4 -b 127.0.0.1:6000 --chdir ./ClientAPI annallClientAPI:app