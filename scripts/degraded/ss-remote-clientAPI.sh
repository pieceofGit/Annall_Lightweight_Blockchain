#!/bin/bash
gunicorn -w 1 --chdir ./ClientAPI wsgiProd:app -b 0.0.0.0:5000