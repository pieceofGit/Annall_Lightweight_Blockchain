#!/bin/bash
gunicorn wsgiProd:app -w 10 --threads 10 -b 0.0.0.0:6000
