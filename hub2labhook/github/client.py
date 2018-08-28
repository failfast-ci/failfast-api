import json
import os
import datetime
import base64
import jwt
import requests
import hub2labhook
from hub2labhook.exception import ResourceNotFound

from hub2labhook.config import FFCONFIG

INTEGRATION_PEM = base64.b64decode(os.environ['GITHUB_INTEGRATION_PEM'])

INTEGRATION_ID = int(FFCONFIG.github['integration_id'])

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

    return jwt.encode(payload, INTEGRATION_PEM,
                      algorithm='RS256').decode("utf-8")


def get_integration_pem():
    return INTEGRATION_PEM


class GithubClient(object):
    def __init__(self, installation_id):
        self.installation_id = installation_id
        self.integration_pem = get_integration_pem()
        self._token = None
        self.endpoint = "https://api.github.com"

    def headers(self, extra=None):
        headers = {
            'Content-Type': 'application/json',
            "Accept": "application/vnd.github.machine-man-preview+json",
            'User-Agent': "hub2lab: %s" % hub2labhook.__version__,
            'Authorization': "token %s" % self.token
        }
        if extra:
            headers.update(extra)
        return headers

    def _url(self, path):
        """ Construct the url from a relative path """
        return self.endpoint + path

    @property
    def token(self):
        if not self._token:
            headers = {
                'Content-Type': 'application/json',
                "Accept": 'application/vnd.github.machine-man-preview+json',
                'User-Agent': "hub2lab: %s" % hub2labhook.__version__,
                'Authorization': "Bearer %s" % jwt_token()
            }
            path = self._url(
                "/installations/%s/access_tokens" % self.installation_id)

            resp = requests.post(path, headers=headers)
            resp.raise_for_status()
            self._token = resp.json()['token']
        return self._token

    def post_status(self, body, github_repo, sha):
        path = self._url("/repos/%s/commits/%s/statuses" % (github_repo, sha))
        resp = requests.post(path, data=json.dumps(body),
                             headers=self.headers(), timeout=5)
        resp.raise_for_status()
        return resp.json()

    def fetch_file(self, repo, file_path, ref="master"):
        path = self._url("/repos/%s/contents/%s" % (repo, file_path))
        resp = requests.get(path, headers=self.headers(), params={'ref': ref},
                            timeout=30)
        resp.raise_for_status()
        content = resp.json()
        filecontent = content['content']
        if content['encoding'] == "base64":
            filecontent = base64.b64decode(filecontent)
        return filecontent

    def get_json(self, path, params={}):
        resp = requests.get(path, headers=self.headers(), params=params)
        resp.raise_for_status()
        return resp.json()

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

    def get_checks(self, github_repo, sha):
        path = self._url("/repos/%s/commits/%s/check-runs" % (github_repo,
                                                              sha))
        resp = requests.get(path, headers=self.headers({
            'Accept': 'application/vnd.github.antiope-preview+json'
        }), params={})
        resp.raise_for_status()
        return resp.json()

    def create_check(self, github_repo, sha):
        check = {
            "name": "mighty_readme",
            "head_sha": sha,
            "status": "in_progress",
            "external_id": "42",
            "started_at": "2018-05-04T01:14:52Z",
            "output": {
                "title": "Mighty Readme report",
                "summary": "foo",
                "text": "bright"
            }
        }
        check2 = {
            "conclusion":
                "neutral",
            "name":
                "Check2",
            "head_sha":
                sha,
            "status":
                "completed",
            "started_at":
                "2017-11-30T19:39:10Z",
            "completed_at":
                "2017-11-30T19:49:10Z",
            "output": {
                "title":
                    "Mighty Readme report",
                "summary":
                    "There are 0 failures, 2 warnings, and 1 notices.",
                "text":
                    "You may have some misspelled words on lines 2 and 4. You also may want to add a section in your README about how to install your app.",
                "annotations": [{
                    "path": "README.md",
                    "annotation_level": "warning",
                    "title": "Spell Checker",
                    "message": "Check your spelling for 'banaas'.",
                    "raw_details": "Do you mean 'bananas' or 'banana'?",
                    "start_line": 2,
                    "end_line": 2
                }, {
                    "path": "README.md",
                    "annotation_level": "warning",
                    "title": "Spell Checker",
                    "message": "Check your spelling for 'aples'",
                    "raw_details": "Do you mean 'apples' or 'Naples'",
                    "start_line": 2,
                    "end_line": 2
                }],
                "images": [{
                    "alt": "Super bananas",
                    "image_url": "http://example.com/images/42"
                }]
            },
            "actions": [{
                "label": "Fix",
                "identifier": "fix_errors",
                "description": "Allow us to fix these errors for you"
            }]
        }
        path = self._url("/repos/%s/check-runs" % github_repo)
        print(check)
        resp = requests.post(
            path, data=json.dumps(check2), headers=self.headers({
                'Accept': 'application/vnd.github.antiope-preview+json'
            }))

        return resp.json()

    def check_run(self, github_repo, sha):
        path = self._url("/repos/:%s/check-runs" % github_repo)
        return path