import json
import os
import requests

import hub2labhook


class GitlabClient(object):
    def __init__(self, endpoint=None, token=None):
        self.gitlab_token = self._getenv(token, "GITLAB_TOKEN")
        self.endpoint = self._getenv(endpoint, "GITLAB_API", "https://gitlab.com")
        self._headers = None

    def _getenv(self, value, envname, default=None):
        if not value:
            if default:
                value = os.getenv(envname, default)
            else:
                value = os.environ[envname]
        return value

    @property
    def headers(self):
        if not self._headers:
            self._headers = {'Content-Type': 'application/json',
                             'User-Agent': "hub2lab: %s" % hub2labhook.__version__,
                             'PRIVATE-TOKEN': self.gitlab_token}
        return self._headers

    def get_project_id(self, project_name=None):
        build_project = self._getenv(project_name, "GITLAB_REPO")
        namespace, name = build_project.split("/")
        path = self.endpoint + "/api/v3/projects/%s%%2f%s" % (namespace, name)
        resp = requests.get(path, headers=self.headers, timeout=5)
        resp.raise_for_status()
        return resp.json()['id']

    def trigger_pipeline(self, gevent, gitlab_project=None,
                         trigger_token=None, branch="master"):

        variables = {
            'EVENT': gevent.event_type,
            'PR_ID': str(gevent.pr_id),
            'SHA': gevent.head_sha,
            'SOURCE_REF': gevent.refname,
            'TARGET_REF': gevent.target_refname,
            'REF_NAME': gevent.refname,
            'SOURCE_REPO_NAME': gevent.repo,
            'TARGET_REPO_NAME': gevent.repo}

        project_id = self.get_project_id(gitlab_project)
        project_branch = self._getenv(branch, "GITLAB_BRANCH")
        trigger_token = self._getenv(trigger_token, 'GITLAB_TRIGGER')

        body = {"token": trigger_token,
                "ref": project_branch,
                "variables": variables}
        path = self.endpoint + "/api/v3/projects/%s/trigger/builds" % project_id
        resp = requests.post(path,
                             data=json.dumps(body),
                             headers=self.headers,
                             timeout=5)
        print resp.content
        print variables
        resp.raise_for_status()

        return resp.json()
