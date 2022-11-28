#!/bin/bash
gunicorn -w 1 --chdir ./ClientAPI wsgiProd:app -b 127.0.0.1:80