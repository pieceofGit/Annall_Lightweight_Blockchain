#!/bin/bash
gunicorn wsgiProd:app -w 50 --threads 100 -b 0.0.0.0:6000
