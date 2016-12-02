import time
from threading import Thread
import json
import os
import datetime
import base64
import jwt
import requests
import hub2labhook
from hub2labhook.gitlabclient import GitlabClient
from hub2labhook.utils import getenv


INTEGRATION_PEM = base64.b64decode(os.environ['GITHUB_INTEGRATION_PEM'])
INTEGRATION_ID = int(os.getenv('GITHUB_INTEGRATION_ID', '743'))
INSTALLATION_ID = '3709'
STATUS_MAP = {"running": "pending",
              "failed": "failure",
              "success": "success",
              "skipped": "failure",
              "unknown": "error",
              "canceled": "error",
              "created": "pending",
              "running": "pending"}
CONTEXT = os.getenv("GITHUB_CONTEXT", "gitlab-ci")


class DelayedRequest(Thread):
    def __init__(self, delay, func):
        Thread.__init__(self)
        self.delay = delay
        self.func = func

    def run(self):
        time.sleep(self.delay)
        self.func()


def jwt_token():
    payload = {
        "iat": datetime.datetime.utcnow(),
        "exp": (datetime.datetime.utcnow() + datetime.timedelta(seconds=60)),
        "iss": INTEGRATION_ID
    }

    return jwt.encode(payload, INTEGRATION_PEM, algorithm='RS256')


def get_integration_pem():
    return INTEGRATION_PEM


class GithubClient(object):
    def __init__(self, installation_id=None):
        self.installation_id = getenv(installation_id, "GITHUB_INSTALLATION_ID", INSTALLATION_ID)
        self.integration_pem = get_integration_pem()
        self._headers = None
        self._token = None

    @property
    def headers(self):
        if not self._headers:
            self._headers = {'Content-Type': 'application/json',
                             "Accept": "application/vnd.github.machine-man-preview+json",
                             'User-Agent': "hub2lab: %s" % hub2labhook.__version__,
                             'Authorization': "token %s" % self.token}
        return self._headers

    @property
    def token(self):
        if not self._token:
            headers = {'Content-Type': 'application/json',
                       "Accept": 'application/vnd.github.machine-man-preview+json',
                       'User-Agent': "hub2lab: %s" % hub2labhook.__version__,
                       'Authorization': "Bearer %s" % jwt_token()}
            path = "https://api.github.com/installations/%s/access_tokens" % self.installation_id
            resp = requests.post(path, headers=headers)
            resp.raise_for_status()
            self._token = resp.json()['token']
        return self._token

    def update_github_status(self, gitlab_project_id, build_id, github_repo, delay=0):
        descriptions = {"pending": "Build in-progress",
                        "success": "Build success",
                        "error": "Build in error or canceled",
                        "failure": "Build failed"}

        gitlabclient = GitlabClient()
        project = gitlabclient.get_project(gitlab_project_id)
        project_url = project['web_url']

        def _request():
            build = gitlabclient.get_build_status(gitlab_project_id, build_id)
            sha = build['commit']['id']

            build_body = {"state": STATUS_MAP[build['status']],
                          "target_url": project_url + "/builds/%s" % build_id,
                          "description": descriptions[STATUS_MAP[build['status']]],
                          "context": "%s/%s/%s" % (CONTEXT, build['stage'], build['name'])}

            pipeline_body = {"state": STATUS_MAP[build['pipeline']['status']],
                             "target_url": project_url + "/pipelines/%s" % build['pipeline']['id'],
                             "description": descriptions[STATUS_MAP[build['pipeline']['status']]],
                             "context": "%s/pipeline" % CONTEXT}

            resp = []
            resp.append(self._post_status(pipeline_body, github_repo, sha))
            resp.append(self._post_status(build_body, github_repo, sha))
            return resp

        if delay:
            thread = DelayedRequest(delay=delay, func=_request)
            thread.start()
            return {"update queued": delay}
        else:
            return _request()

    def _post_status(self, body, github_repo, sha):
        path = "https://api.github.com/repos/%s/commits/%s/statuses" % (github_repo, sha)
        resp = requests.post(path, data=json.dumps(body), headers=self.headers, timeout=5)
        resp.raise_for_status()
        return resp.json()
