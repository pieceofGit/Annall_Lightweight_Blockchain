#!/bin/bash
gunicorn -w 1 --chdir ./ClientAPI annallClientAPI:app