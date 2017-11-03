import json
import os
import datetime
import base64
import jwt
import requests
import hub2labhook
from hub2labhook.exception import ResourceNotFound

from hub2labhook.config import (GITHUB_INTEGRATION_ID, GITHUB_INSTALLATION_ID)

INTEGRATION_PEM = base64.b64decode(os.environ['GITHUB_INTEGRATION_PEM'])

INTEGRATION_ID = int(GITHUB_INTEGRATION_ID)
INSTALLATION_ID = int(GITHUB_INSTALLATION_ID)
GITHUB_STATUS_MAP = {
    "failed": "failure",
    "success": "success",
    "skipped": "success",
    "unknown": "error",
    'manual': 'success',
    "canceled": "error",
    "pending": "pending",
    "created": "pending",
    "running": "pending"
}


def jwt_token():
    payload = {
        "iat": datetime.datetime.utcnow(),
        "exp": (datetime.datetime.utcnow() + datetime.timedelta(seconds=60)),
        "iss": INTEGRATION_ID
    }

    return jwt.encode(payload, INTEGRATION_PEM, algorithm='RS256').decode("utf-8")


def get_integration_pem():
    return INTEGRATION_PEM


class GithubClient(object):
    def __init__(self, installation_id=None):
        self.installation_id = installation_id or GITHUB_INSTALLATION_ID
        self.integration_pem = get_integration_pem()
        self._headers = None
        self._token = None

    @property
    def headers(self):
        if not self._headers:
            self._headers = {
                'Content-Type': 'application/json',
                "Accept": "application/vnd.github.machine-man-preview+json",
                'User-Agent': "hub2lab: %s" % hub2labhook.__version__,
                'Authorization': "token %s" % self.token
            }
        return self._headers

    @property
    def token(self):
        if not self._token:
            headers = {
                'Content-Type': 'application/json',
                "Accept": 'application/vnd.github.machine-man-preview+json',
                'User-Agent': "hub2lab: %s" % hub2labhook.__version__,
                'Authorization': "Bearer %s" % jwt_token()
            }
            path = "https://api.github.com/installations/%s/access_tokens" % self.installation_id
            resp = requests.post(path, headers=headers)
            resp.raise_for_status()
            self._token = resp.json()['token']
        return self._token

    def post_status(self, body, github_repo, sha):
        path = "https://api.github.com/repos/%s/commits/%s/statuses" % (github_repo, sha)
        resp = requests.post(path, data=json.dumps(body), headers=self.headers, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def fetch_file(self, repo, file_path, ref="master"):
        path = "https://api.github.com/repos/%s/contents/%s" % (repo, file_path)
        resp = requests.get(path, headers=self.headers, params={'ref': ref}, timeout=30)
        resp.raise_for_status()
        content = resp.json()
        filecontent = content['content']
        if content['encoding'] == "base64":
            filecontent = base64.b64decode(filecontent)
        return filecontent

    def get_ci_file(self, source_repo, ref):
        content = None
        for filepath in [".gitlab-ci.yml", ".failfast-ci.jsonnet"]:
            try:
                content = self.fetch_file(source_repo, filepath, ref=ref)
                return {"content": content, "file": filepath}
            except requests.exceptions.HTTPError as e:
                if e.response.status_code != 404:
                    raise e
        if content is None:
            raise ResourceNotFound("no .gitlab-ci.yml or .failfail-ci.jsonnet")
