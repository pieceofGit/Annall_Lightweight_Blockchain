#!/bin/bash
gunicorn wsgiProd:app -w 2 --threads 2 -b 0.0.0.0:6000
