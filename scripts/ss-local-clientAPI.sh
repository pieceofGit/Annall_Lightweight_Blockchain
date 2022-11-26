#!/bin/bash
gunicorn --workers=4 --threads=4 -b 127.0.0.1:6000 --chdir ./ClientAPI wsgiDev:app