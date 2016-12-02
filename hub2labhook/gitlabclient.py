import yaml
import base64
import time
import json
import requests

import hub2labhook

from hub2labhook.exception import ResourceNotFound
from hub2labhook.utils import getenv


class GitlabClient(object):
    from hub2labhook.githubclient import GithubClient

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

    def _parse_ci_file(content, filepath):
        if filepath == ".gitlab-ci.yml":
            return yaml.loads(filepath)

    def get_ci_file(self, gevent):
        gc = GithubClient(installation_id=gevent.installation_id)
        if gevent.pr_id == "N/A":
            source_repo = ge.pr_repo
        else:
            source_repo = ge.repo

        content = None
        for filepath in [".gitlab-ci.yml", ".failfast-ci.jsonnet"]:
            try:
                content = gc.fetch_file(source_repo, filepath, ref=ge.ref)
                return {"_raw_content": content,
                        "content": self._parse_ci_file(content),
                        "file": filepath}
            except requests.exceptions.HTTPError as e:
                if e.response.status_code != 404:
                    raise e
        if content is None:
            raise ResourceNotFound("no .gitlab-ci.yml or .failfail-ci.jsonnet")

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

    def trigger_pipeline(self, gevent, gitlab_project=None,
                          trigger_token=None, branch="master"):


        # sync-source-target:
        #   stage: sync
        #   script:
        #     - git clone $SOURCE_REPO repo
        #     - cd repo
        #     - >-
        #       if [ $PR_ID == "N/A" ]; then
        #         git checkout ${SOURCE_REF}
        #       else
        #         git fetch origin pull/${PR_ID}/head:pr-${PR_ID}
        #         git checkout pr-${PR_ID}
        #       fi
        #     - eval "[ `git rev-parse HEAD` = $SHA ]"
        #     - git remote add target ${TARGET_REPO}
        #     - git push target HEAD:${TARGET_REF} -f
        #   tags:
        #     - kubespray
        #     - docker
        gc = GithubClient(installation_id=gevent.installation_id)
        ci_project = self.initialize_project(gevent.repo.replace("/","__"))
        ci_file = self.get_ci_file(gevent)
        ci_branch = gevent.target_refname
        self.set_variables(ci_project['id'], {'GH_TOKEN_%s' % gevent.target_refname: gc.token})
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
        group_name = getenv(namespace, "HUB2LAB_NAMESPACE", "failfast-ci")
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
                  file_content, branch, message):
        path = self.endpoint + "/api/v3/projects/%s/repository/files" % (project_id)
        body = {"file_path": file_path,
                "branch_name": branch,
                "encoding": "base64",
                "content": base64.b64encode(file_content),
                "commit_message": message}

        resp = requests.post(path, data=json.dumps(body), headers=self.headers, timeout=30)
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
        return project
