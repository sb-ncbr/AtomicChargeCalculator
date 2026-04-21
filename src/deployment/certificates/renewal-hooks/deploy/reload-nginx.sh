#!/bin/bash

set -e

NGINX_CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep nginx)

if [[ -z "$NGINX_CONTAINER_NAME" ]]; then
    echo "No nginx container found"
    exit 1
fi

if docker exec "$NGINX_CONTAINER_NAME" nginx -s reload 2> /dev/null; then
    echo "Successfully reloaded nginx"
else
    echo "Unable to reload nginx"
    exit 1
fi