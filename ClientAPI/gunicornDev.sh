#!/bin/bash
gunicorn 'wsgiDevDocker:create_app(1)' -w 1 --threads 1 -b 0.0.0.0:6000
