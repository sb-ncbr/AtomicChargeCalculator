#!/bin/bash

# This script runs migrations before running the gunicorn server.
# It is used in the Dockerfile.

cd /acc/app

# run database migrations
alembic upgrade head

# Prepare shared examples once, before workers import the application.
python main.py || exit $?

# use gunicorn with 4 workers
# uvicorn_worker.UvicornWorker is used for async processing
# setting timeout to 1 hour for long lasting computations
# running on port 8000
exec gunicorn --workers 4 --worker-class uvicorn_worker.UvicornWorker --timeout 6000 --bind 0.0.0.0:8000 main:web_app
