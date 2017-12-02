#!/bin/bash
PORT=${PORT:-5000}
GITHUB_CONTEXT=${GITHUB_CONTEXT:-gitlab-ci}
GITLAB_TRIGGER=${GITLAB_TRIGGER:-b2cdcaa47b8e5bee6d827b11e5ae4a}
GITLAB_TOKEN=${GITLAB_TOKEN:-mytoken}
GITLAB_USER=${GITLAB_USER:-myusername}
GITLAB_REPO=${GITLAB_REPO:-ant31/hub2lab}
GITLAB_REPO=$GITLAB_REPO \
           GITHUB_CONTEXT=$GITHUB_CONTEXT \
           GITLAB_TRIGGER=$GITLAB_TRIGGER \
           GITLAB_TOKEN=$GITLAB_TOKEN \
           gunicorn hub2labhook.api.wsgi:app -b :$PORT --timeout 120 -w 4 --reload -c conf/gunicorn.py
