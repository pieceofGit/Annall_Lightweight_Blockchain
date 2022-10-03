#!/bin/bash
gunicorn -w 1 --chdir ./src annallWriterAPI:app