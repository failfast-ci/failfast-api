import yaml
import base64
import time
import json
import requests

import hub2labhook

from hub2labhook.utils import getenv


class GitlabClient(object):

    def __init__(self, endpoint=None, token=None):
        self.gitlab_token = getenv(token, "GITLAB_TOKEN")
        self.endpoint = getenv(endpoint, "GITLAB_API", "https://gitlab.com")
        self._headers = None

    @property
    def headers(self):
        if not self._headers:
            self._headers = {'Content-Type': 'application/json',
                             'User-Agent': "hub2lab: %s" % hub2labhook.__version__,
                             'PRIVATE-TOKEN': self.gitlab_token}
        return self._headers

    def get_project(self, project_id):
        path = self.endpoint + "/api/v3/projects/%s" % (project_id)
        resp = requests.get(path, headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_project_id(self, project_name=None):
        build_project = getenv(project_name, "GITLAB_REPO")
        namespace, name = build_project.split("/")
        project_path = "%s%%2f%s" % (namespace, name)
        project = self.get_project(project_path)
        return project['id']

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
        project_branch = getenv(branch, "GITLAB_BRANCH")
        trigger_token = getenv(trigger_token, 'GITLAB_TRIGGER')

        body = {"token": trigger_token,
                "ref": project_branch,
                "variables": variables}
        path = self.endpoint + "/api/v3/projects/%s/trigger/builds" % project_id
        resp = requests.post(path,
                             data=json.dumps(body),
                             headers=self.headers,
                             timeout=10)
        resp.raise_for_status()

        return resp.json()

    def set_variables(self, project_id, variables):
        path = self.endpoint + "/api/v3/projects/%s/variables" % project_id
        for key, value in variables.iteritems():
            key_path = path + "/%s" % key
            resp = requests.get(path)
            action = "post"
            if resp.status_code == 200:
                action = "put"
            body = {"key": key, "value": value}
            resp = getattr(requests, action)(path, data=json.dumps(body), headers=self.headers)
            resp.raise_for_status()


    def get_build_status(self, project_id, build_id):
        path = self.endpoint + "/api/v3/projects/%s/builds/%s" % (project_id, build_id)
        resp = requests.get(path, headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_pipeline_status(self, project_id, pipeline_id):
        path = self.endpoint + "/api/v3/projects/%s/pipelines/%s" % (project_id, pipeline_id)
        resp = requests.get(path, headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_namespace_id(self, namespace):
        path = self.endpoint + "/api/v3/namespaces"
        params = {'search': namespace}
        resp = requests.get(path, headers=self.headers, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()[0]['id']

    def get_or_create_project(self, project_name, namespace=None):
        group_name = getenv(namespace, "FAILFASTCI_NAMESPACE", "failfast-ci")
        project_path = "%s%%2f%s" % (group_name, project_name)
        path = self.endpoint + "/api/v3/projects/%s" % (project_path)
        resp = requests.get(path, headers=self.headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        group_id = self.get_namespace_id(group_name)
        path = self.endpoint + "/api/v3/projects"
        body = {
            "name":  project_name,
            "namespace_id": group_id,
            "issues_enabled": False,
            "merge_requests_enabled": False,
            "builds_enabled": True,
            "wiki_enabled": False,
            "snippets_enabled": False,
            "container_registry_enabled": False,
            "shared_runners_enabled": False,
            "public": True,
            "visibility_level": 20,
            "public_builds": True,
            }
        resp = requests.post(path, data=json.dumps(body),
                             headers=self.headers, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def push_file(self, project_id, file_path,
                  file_content, branch, message,
                  force=True):
        branch_path = self.endpoint + "/api/v3/projects/%s/repository/branches" % project_id
        branch_body = {'branch_name': branch, 'ref': "_failfastci"}
        resp = requests.post(branch_path,
                             params=branch_body,
                             headers=self.headers, timeout=30)

        path = self.endpoint + "/api/v3/projects/%s/repository/files" % (project_id)
        body = {"file_path": file_path,
                "branch_name": branch,
                "encoding": "base64",
                "content": base64.b64encode(file_content),
                "commit_message": message}
        resp = requests.post(path, data=json.dumps(body), headers=self.headers, timeout=30)
        if resp.status_code == 400:
            resp = requests.put(path, data=json.dumps(body), headers=self.headers, timeout=30)

        resp.raise_for_status()
        return resp.json()

    def initialize_project(self, project_name, namespace=None):
        project = self.get_or_create_project(project_name, namespace)
        branch = "master"
        branch_path = self.endpoint + "/api/v3/projects/%s/repository/branches/%s" % (project['id'], branch)
        resp = requests.get(branch_path, headers=self.headers, timeout=30)
        if resp.status_code == 404:
            self.push_file(project['id'],
                           file_path="README.md",
                           file_content="# %s" % project_name,
                           branch="master",
                           message="init readme")
            time.sleep(1)
            resp = requests.put(branch_path + "/unprotect", headers=self.headers, timeout=30)
            resp.raise_for_status()
            branch_path = self.endpoint + "/api/v3/projects/%s/repository/branches" % project['id']
            branch_body = {'branch_name': "_failfastci", 'ref': "master"}
            resp = requests.post(branch_path,
                                 params=branch_body,
                                 headers=self.headers, timeout=30)

        return project

    def trigger_build(self, gitlab_project, variables={}, trigger_token=None, branch=None):
        project_id = self.get_project_id(gitlab_project)
        project_branch = getenv(branch, "GITLAB_BRANCH")
        trigger_token = getenv(trigger_token, 'GITLAB_TRIGGER')

        body = {"token": trigger_token,
                "ref": project_branch,
                "variables": variables}

        path = self.endpoint + "/api/v3/projects/%s/trigger/builds" % project_id
        resp = requests.post(path,
                             data=json.dumps(body),
                             headers=self.headers,
                             timeout=10)
        resp.raise_for_status()
