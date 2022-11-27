#!/bin/bash
gunicorn -w 1 --chdir ./src/WriterAPI wsgiProd:app