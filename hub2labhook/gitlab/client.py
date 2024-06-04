import base64
import time
import json
import urllib.parse

import requests

import hub2labhook

from hub2labhook.config import FailFastConfig, FFCONFIG

API_VERSION = "/api/v4"


class GitlabClient(object):
    def __init__(self, endpoint: str = None, token: str = None,
                 config: FailFastConfig = None) -> None:
        """ Creates a gitlab-client instance initialized with the private-token and endpoint urllib

        Args:
          endpoint(:obj:`str`) the gitlab instance url,
                               if `None` takes value from GITLAB_API env-var.
          token (:obj:`str`) the private gitlab token,
                              if `None` takes value from GITLAB_TOKEN env-var.
          config (:obj:`FailFastConfig`) configuration
        """
        if config is None:
            config = FFCONFIG
        self.config = config
        self.gitlab_token = token or self.config.gitlab['secret_token']
        self.endpoint = endpoint or self.config.gitlab['gitlab_url']
        self._headers = None
        self.host = self.endpoint

    def _url(self, path):
        """ Construct the url from a relative path """
        return self.endpoint + API_VERSION + path

    def create_webhooks(self, project_id):
        body = {
        'job_events': True,
        'pipeline_events': True,
        'deployment_events': True,
        'url': self.config.gitlab['webhook_url'],
        }
        path = self._url("/projects/%s/hooks" % project_id)
        resp = requests.post(path, data=json.dumps(body).encode(),
                             headers=self.headers,
                             timeout=self.config.gitlab['timeout'])
        resp.raise_for_status()
        return resp

    @property
    def headers(self):
        """ Configure requests headers with the private token """
        if not self._headers:
            self._headers = {
                'Content-Type': 'application/json',
                'User-Agent': "hub2lab: %s" % hub2labhook.__version__,
                'PRIVATE-TOKEN': self.gitlab_token
            }
        return self._headers

    def gitlabci_lint(self, data):
        path = self._url("/ci/lint")
        resp = requests.post(path, json={'content': data},
                             headers=self.headers,
                             timeout=self.config.gitlab['timeout'])
        return resp.json()

    def get_project(self, project_id):
        """ Returns the gitlab project dict
            link: https://docs.gitlab.com/ce/api/projects.html#get-single-project
        """
        path = self._url("/projects/%s" % project_id)
        resp = requests.get(path, headers=self.headers,
                            timeout=self.config.gitlab['timeout'])
        resp.raise_for_status()
        return resp.json()

    def get_project_id(self, project_name=None):
        """ Requests the project-id (int) from a project_name (str) """
        if isinstance(project_name, int):
            return project_name

        build_project = project_name or self.config.gitlab['repo']
        namespace, name = build_project.split("/")
        project_path = "%s%%2f%s" % (namespace, name)
        project = self.get_project(project_path)
        return project['id']

    def get_variables(self, project_id):
        path = self._url(
            "/projects/%s/variables" % self.get_project_id(project_id))
        resp = requests.get(path, headers=self.headers,
                            timeout=self.config.gitlab['timeout'])
        resp.raise_for_status()
        return resp.json()

    def get_variable(self, project_id, key):
        path = self._url("/projects/%s/variables/%s" %
                         (self.get_project_id(project_id), key))
        resp = requests.get(path, headers=self.headers,
                            timeout=self.config.gitlab['timeout'])
        resp.raise_for_status()
        return resp.json()

    def set_variables(self, project_id, variables):
        """ Create or update(if exists) pipeline variables """
        path = self._url(
            "/projects/%s/variables" % self.get_project_id(project_id))
        for key, value in variables.items():
            key_path = path + "/%s" % key
            resp = requests.get(key_path, headers=self.headers)
            action = "post"
            if resp.status_code == 200:
                if resp.json()['value'] == value:
                    continue
                action = "put"
                path = key_path

            body = {"key": key, "value": value}

            resp = getattr(requests, action)(path, data=json.dumps(body),
                                             headers=self.headers)
            resp.raise_for_status()

    def get_job(self, project_id, job_id):
        path = self._url("/projects/%s/jobs/%s" %
                         (self.get_project_id(project_id), job_id))
        resp = requests.get(path, headers=self.headers,
                            timeout=self.config.gitlab['timeout'])
        resp.raise_for_status()
        return resp.json()

    def get_statuses(self, project_id, sha):
        path = self._url("/projects/%s/repository/commits/%s/statuses" %
                         (self.get_project_id(project_id), sha))
        resp = requests.get(path, headers=self.headers,
                            timeout=self.config.gitlab['timeout'])
        resp.raise_for_status()
        return resp.json()

    def get_jobs(self, project_id, pipeline_id):
        path = self._url("/projects/%s/pipelines/%s/jobs" %
                         (self.get_project_id(project_id), pipeline_id))
        resp = requests.get(path, headers=self.headers,
                            timeout=self.config.gitlab['timeout'])
        resp.raise_for_status()
        return resp.json()

    def cancel_pipeline(self, project_id, pipeline_id):
        path = self._url("/projects/%s/pipelines/%s/cancel" %
                         (self.get_project_id(project_id), pipeline_id))
        resp = requests.post(path, headers=self.headers,
                             timeout=self.config.gitlab['timeout'])
        resp.raise_for_status()
        return resp.json()

    def new_pipeline(self, project_id, ref=None, sha=None, variables=None, cancel_prev=True):
        if ref is None and sha is None:
            raise ValueError("ref or sha must be provided")
        if cancel_prev:
            get_pipelines = self.get_pipelines(project_id, ref=ref, sha=sha)
            for pipeline in get_pipelines:
                if pipeline['ref'] == ref:
                    self.cancel_pipeline(project_id, pipeline['id'])
        fmt_vars = []
        if variables:
            fmt_vars = [{"key": k, "value": v} for k, v in variables.items()]
        path = self._url("/projects/%s/pipeline" % self.get_project_id(project_id))
        body = {
            "ref": ref,
            "variables": fmt_vars,
        }
        resp = requests.post(path, data=json.dumps(body).encode(),
                             headers=self.headers,
                             timeout=self.config.gitlab['timeout'])
        resp.raise_for_status()

        return resp.json()


    def get_pipelines(self, project_id, ref=None, sha=None):
        path = self._url("/projects/%s/pipelines" %
                         (self.get_project_id(project_id)))
        params = {}
        if ref:
            params["ref"] = ref

        if sha:
            params["sha"] = sha
        resp = requests.get(path, headers=self.headers, params=params,
                            timeout=self.config.gitlab['timeout'])
        return resp.json()

    def get_pipeline_status(self, project_id, pipeline_id):
        path = self._url("/projects/%s/pipelines/%s" %
                         (self.get_project_id(project_id), pipeline_id))
        resp = requests.get(path, headers=self.headers,
                            timeout=self.config.gitlab['timeout'])
        resp.raise_for_status()
        return resp.json()

    def get_namespace_id(self, namespace):
        path = self._url("/namespaces")
        params = {'search': namespace}
        resp = requests.get(path, headers=self.headers, params=params,
                            timeout=self.config.gitlab['timeout'])
        resp.raise_for_status()
        return resp.json()[0]['id']

    def get_or_create_project(self, project_name, namespace=None,
                              repo_public: bool = False):
        group_name = namespace or self.config.gitlab['namespsace']
        project_path = "%s%%2f%s" % (group_name, project_name)
        path = self._url("/projects/%s" % (project_path))
        resp = requests.get(path, headers=self.headers,
                            timeout=self.config.gitlab['timeout'])
        if resp.status_code == 200:
            return resp.json()
        group_id = self.get_namespace_id(group_name)
        path = self._url("/projects")
        body = {
            "name": project_name,
            "namespace_id": group_id,
            "builds_access_level": 'enabled',
            "operations_access_level": 'enabled',
            "merge_requests_access_level": 'enabled',
            "public_builds": False,
            'repository_access_level': 'enabled',
            'shared_runners_enabled': False,
            "visibility": "private"
        }

        resp = requests.post(path, data=json.dumps(body).encode(),
                             headers=self.headers,
                             timeout=self.config.gitlab['timeout'])
        resp.raise_for_status()
        _ = self.create_webhooks(resp.json()['id'])
        return resp.json()

    def push_file(self, project_id, file_path, file_content, branch, message,
                  force=True):
        branch_path = self._url("/projects/%s/repository/branches" %
                                self.get_project_id(project_id))
        branch_body = {'branch': branch, 'ref': "_failfastci"}
        resp = requests.post(branch_path, params=branch_body,
                             headers=self.headers,
                             timeout=self.config.gitlab['timeout'])

        path = self._url("/projects/%s/repository/files/%s" %
                         (self.get_project_id(project_id),
                          urllib.parse.quote_plus(file_path)))
        body = {
            "file_path": file_path,
            "branch": branch,
            "encoding": "base64",
            "content": base64.b64encode(file_content).decode(),
            "commit_message": message
        }
        resp = requests.post(path, data=json.dumps(body), headers=self.headers,
                             timeout=self.config.gitlab['timeout'])
        if resp.status_code == 400 or resp.status_code == 409:
            resp = requests.put(path, data=json.dumps(body),
                                headers=self.headers,
                                timeout=self.config.gitlab['timeout'])

        resp.raise_for_status()
        return resp.json()

    def delete_project(self, project_id):
        path = self._url("/projects/%s" % (self.get_project_id(project_id)))
        resp = requests.delete(path)
        resp.raise_for_status()
        return resp.json()

    def get_branches(self, project_id, search=None):
        branches = []
        page = 1
        page_count = 100
        while page <= page_count:
            params = {"page": page, "per_page": 50}
            if search:
                params['search'] = search
            path = self._url("/projects/%s/repository/branches" % (self.get_project_id(project_id)))
            resp = requests.get(path, headers=self.headers, params=params)
            resp.raise_for_status()
            branches += resp.json()
            page_count = resp.headers['X-Total-Pages']
            if not resp.headers['X-Next-Page']:
                break
            page = resp.headers['X-Next-Page']
        return branches

    def delete_old_branches(self, project_id, branches, days_old):
        from datetime import datetime, timedelta
        delta = timedelta(days_old)
        max_date = datetime.utcnow() - delta
        project_id = self.get_project_id(project_id)
        delete_branches = 0
        for branch in branches:
            date = datetime.fromisoformat(branch['commit']['committed_date']).replace(tzinfo=None)
            if date < max_date and branch['name'] != "master":
                self.delete_branch(project_id, branch['name'])
                delete_branches += 1
        return delete_branches

    def delete_branch(self, project_id, branch):
        path = self._url("/projects/%s/repository/branches/%s" %
                         (self.get_project_id(project_id), urllib.parse.quote_plus(branch)))
        resp = requests.delete(path, headers=self.headers, timeout=self.config.gitlab['timeout'])
        resp.raise_for_status()
        return True

    def initialize_project(self, project_name: str, namespace: str = None):
        project = self.get_or_create_project(project_name, namespace)
        branch = "master"

        branch_path = self._url("/projects/%s/repository/branches/%s" %
                                (project['id'], branch))
        resp = requests.get(branch_path, headers=self.headers,
                            timeout=self.config.gitlab['timeout'])
        if resp.status_code == 404:
            time.sleep(2)
            self.push_file(project['id'], file_path="README.md",
                           file_content=bytes(
                               ("# %s" % project_name).encode()),
                           branch="master", message="init readme")
            time.sleep(2)
            resp = requests.put(branch_path + "/unprotect",
                                headers=self.headers,
                                timeout=self.config.gitlab['timeout'])
            resp.raise_for_status()
            branch_path = self._url(
                "/projects/%s/repository/branches" % project['id'])
            branch_body = {'branch': "_failfastci", 'ref': "master"}
            resp = requests.post(branch_path, params=branch_body,
                                 headers=self.headers,
                                 timeout=self.config.gitlab['timeout'])

        return project

    def retry_build(self, gitlab_project_id, build_id):
        path = self._url("/projects/%s/jobs/%s/retry" % (gitlab_project_id,
                                                         build_id))
        resp = requests.post(path, headers=self.headers,
                             timeout=self.config.gitlab['timeout'])
        resp.raise_for_status()
        return resp.json()

    def retry_pipeline(self, project_id, pipeline_id):
        path = self._url(f"/projects/{project_id}/pipeline/{pipeline_id}/retry")
        resp = requests.post(path, params={}, headers=self.headers,
                             timeout=self.config.gitlab['timeout'])
        resp.raise_for_status()
        return resp.json()

    # TODO(ant31): dead-code
    def trigger_build(self, gitlab_project, variables=None, trigger_token=None,
                      branch="master"):
        if not variables:
            variables = {}
        project_id = self.get_project_id(gitlab_project)
        project_branch = branch
        trigger_token = trigger_token

        body = {
            "token": trigger_token,
            "ref": project_branch,
            "variables": variables
        }

        path = self._url("/projects/%s/trigger/builds" % project_id)
        resp = requests.post(path, data=json.dumps(body), headers=self.headers,
                             timeout=self.config.gitlab['timeout'])
        resp.raise_for_status()
        return resp.json()
