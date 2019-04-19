#!/bin/bash
PORT=${PORT:-5000}
GITHUB_CONTEXT=${GITHUB_CONTEXT:-gitlab-ci}
GITLAB_TOKEN=${GITLAB_TOKEN:-mytoken}
GITLAB_USER=${GITLAB_USER:-myusername}
           GITHUB_CONTEXT=$GITHUB_CONTEXT \
           GITLAB_TOKEN=$GITLAB_TOKEN \
           gunicorn hub2labhook.api.wsgi:app -b :$PORT --timeout 120 -w 4 --reload -c conf/gunicorn.py
