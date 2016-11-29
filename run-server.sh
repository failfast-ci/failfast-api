#!/bin/bash
PORT=${PORT:-5000}
GITLAB_TOKEN=${GITLAB_TOKEN:-mytoken}
GITLAB_TOKEN=$GITLAB_TOKEN gunicorn hub2labhook.api.wsgi:app -b :$PORT --timeout 120 -w 4 --reload
