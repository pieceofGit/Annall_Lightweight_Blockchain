#!/bin/bash
gunicorn routes:wsgiProd -w 2 --threads 2 -b 0.0.0.0:80
