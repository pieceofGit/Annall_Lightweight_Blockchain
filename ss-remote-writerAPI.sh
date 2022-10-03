#!/bin/bash
gunicorn -w 1 ./src annallWriterAPI:app