import json
import time

import requests
from functools import lru_cache
from ffci.gitlab.models import (
    CreateGitlabWebhook,
    GitlabProject,
    GitlabCILint,
    GitlabWebhook,
    GitlabCILintContent,
    GitlabCILintSha,
    GitlabProjectVariable,
    CreateGitlabProjectVariable,
    UpdateGitlabProjectVariable,
    url_encode_id)

from ffci.client_base import BaseClient
from ffci.config import GitlabConfigSchema

GITLAB_API_VERSION = "/api/v4"


class GitlabClient(BaseClient):
    def __init__(self, config: GitlabConfigSchema) -> None:
        self.projects_cache = {}
        self.config = config
        self.gitlab_token = config.access_token
        super().__init__(
            endpoint=config.gitlab_url + GITLAB_API_VERSION, client_name="gitlab"
        )

    def headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "PRIVATE-TOKEN": self.gitlab_token,
        }
        if extra is not None:
            headers.update(extra)
        return super().headers("json", extra=headers)


    async def create_webhook(self, body: CreateGitlabWebhook) -> GitlabWebhook:
        path = self._url(f"/projects/{body.id}/hooks")
        headers = self.headers()
        body_dict = body.model_dump(exclude_defaults=True)
        resp = await self.session.post(
            path,
            json=body_dict,
            headers=headers,
            ssl=self.ssl_mode,
            timeout=30,
        )
        await self.log_request(
            path=path,
            params={},
            body=body_dict,
            method="POST",
            headers=headers,
            resp=resp,
        )
        resp.raise_for_status()
        return GitlabWebhook.model_validate(await resp.json())

    async def gitlabci_lint(
        self, project_id: int | str, body: GitlabCILintSha | GitlabCILintContent
    ) -> GitlabCILint:
        id = url_encode_id(project_id)
        headers = self.headers()
        path = self._url(f"/projects/{id}/ci/lint")
        body_dict = body.model_dump(exclude_defaults=True)
        if isinstance(body, GitlabCILintSha):
            resp = await self.session.get(
                path,
                params=body_dict,
                headers=headers,
                ssl=self.ssl_mode,
                timeout=30,
            )
            await self.log_request(
            path=path,
            params=body_dict,
            body={},
            method="GET",
            headers=headers,
            resp=resp,
            )
        elif isinstance(body, GitlabCILintContent):
            resp = await self.session.post(
                path,
                json=body_dict,
                headers=headers,
                ssl=self.ssl_mode,
                timeout=30,
            )
            await self.log_request(
            path=path,
            params={},
            body=body_dict,
            method="POST",
            headers=headers,
            resp=resp,
            )
        else:
            raise ValueError("body must be GitlabCILintSha or GitlabCILintContent")
        resp.raise_for_status()
        return GitlabCILint.model_validate(await resp.json())

    async def get_project(self, project_id: int | str) -> GitlabProject:
        """Returns the gitlab project dict
        link: https://docs.gitlab.com/ce/api/projects.html#get-single-project
        """
        pid = url_encode_id(project_id)
        path = self._url(f"/projects/{pid}")
        headers = self.headers()
        resp = await self.session.get(
            path,
            params={},
            headers=headers,
            ssl=self.ssl_mode,
            timeout=30,
        )
        await self.log_request(
            path=path,
            params={},
            body={},
            method="GET",
            headers=headers,
            resp=resp,
        )
        resp.raise_for_status()
        return GitlabProject.model_validate(await resp.json())

    # Cache the answers, ID is always the same for a project
    @lru_cache(maxsize=128, typed=True)
    def get_project_id(self, project_name: int | str) -> int:
        """Requests the project-id (int) from a project_name (str)"""
        if isinstance(project_name, int):
            return project_name
        project = self.get_project(project_name)
        return project.id

    async def get_variables(self, project_id: int | str) -> list[GitlabProjectVariable]:
        path = self._url(f"/projects/{self.get_project_id(project_id)}/variables")
        headers = self.headers()
        resp = await self.session.get(
            path,
            params={},
            headers=headers,
            ssl=self.ssl_mode,
            timeout=30,
        )
        await self.log_request(
            path=path,
            params={},
            body={},
            method="GET",
            headers=headers,
            resp=resp,
        )
        resp.raise_for_status()
        resp_json = await resp.json()
        return [GitlabProjectVariable.model_validate(var) for var in resp_json]

    ###########
    ###########

    async def get_variable(self, project_id: str | int, key: str) -> GitlabProjectVariable:
        path = self._url(f"/projects/{self.get_project_id(project_id)}/variables/{key}")
        resp = requests.get(
            path, headers=self.headers, timeout=self.config.gitlab["timeout"]
        )
        headers = self.headers()
        resp = await self.session.get(
            path,
            params={},
            headers=headers,
            ssl=self.ssl_mode,
            timeout=30,
        )
        await self.log_request(
            path=path,
            params={},
            body={},
            method="GET",
            headers=headers,
            resp=resp,
        )
        resp.raise_for_status()
        return GitlabProjectVariable.model_validate(await resp.json())

   async def create_variable(self, project_id: str | int, body: CreateGitlabProjectVariable) -> GitlabProjectVariable:
        path = self._url(f"/projects/{self.get_project_id(project_id)}/variables")
        headers = self.headers()
        body_dict = body.model_dump(exclude_defaults=True)
        resp = await self.session.post(
            path,
            json=body_dict,
            headers=headers,
            ssl=self.ssl_mode,
            timeout=30,
        )
        await self.log_request(
            path=path,
            params={},
            body=body_dict,
            method="POST",
            headers=headers,
            resp=resp,
        )
        resp.raise_for_status()
        return GitlabProjectVariable.model_validate(await resp.json())

    async def update_variable(self, project_id: str | int, key: str, body: UpdateGitlabProjectVariable | CreateGitlabProjectVariable) -> GitlabProjectVariable:
        path = self._url(f"/projects/{self.get_project_id(project_id)}/variables/{key}")
        headers = self.headers()
        body_dict = body.model_dump(exclude_defaults=True)
        resp = await self.session.put(
            path,
            json=body_dict,
            headers=headers,
            ssl=self.ssl_mode,
            timeout=30,
        )
        await self.log_request(
            path=path,
            params={},
            body=body_dict,
            method="PUT",
            headers=headers,
            resp=resp,
        )
        resp.raise_for_status()
        return GitlabProjectVariable.model_validate(await resp.json())

    def variables_to_dict(self, variables: list[GitlabProjectVariable]) -> dict[str, GitlabProjectVariable]:
        return {var.key: var for var in variables}

    async def set_variables(self, project_id: str | int, variables: dict[str, str]) -> list[GitlabProjectVariable]:
        """Create or update(if exists) pipeline variables"""
        project_variables = await self.get_variables(project_id)
        project_variables_dict = self.variables_to_dict(project_variables)
        res = []
        # Do all the call in multiple async loop
        for key, value in variables.items():
            if key in project_variables_dict and project_variables_dict[key].value != value:
                # Update value: key exists and value is different
                var = project_variables_dict[key]
                var.value = value
                res.append(await self.update_variable(project_id, key, var))
            elif key not in project_variables_dict:
                # Create variable: key does not exist
                res.append(await self.create_variable(project_id, CreateGitlabProjectVariable(value=value, key=key)))
        return res

    def get_job(self, project_id, job_id):
        path = self._url(
            "/projects/%s/jobs/%s" % (self.get_project_id(project_id), job_id)
        )
        resp = requests.get(
            path, headers=self.headers, timeout=self.config.gitlab["timeout"]
        )
        resp.raise_for_status()
        return resp.json()

    def get_statuses(self, project_id, sha):
        path = self._url(
            "/projects/%s/repository/commits/%s/statuses"
            % (self.get_project_id(project_id), sha)
        )
        resp = requests.get(
            path, headers=self.headers, timeout=self.config.gitlab["timeout"]
        )
        resp.raise_for_status()
        return resp.json()

    def get_jobs(self, project_id, pipeline_id):
        path = self._url(
            "/projects/%s/pipelines/%s/jobs"
            % (self.get_project_id(project_id), pipeline_id)
        )
        resp = requests.get(
            path, headers=self.headers, timeout=self.config.gitlab["timeout"]
        )
        resp.raise_for_status()
        return resp.json()

    def get_pipelines(self, project_id, ref=None):
        path = self._url("/projects/%s/pipelines" % (self.get_project_id(project_id)))
        params = {}
        if ref:
            params["ref"] = ref
        resp = requests.get(
            path,
            headers=self.headers,
            params=params,
            timeout=self.config.gitlab["timeout"],
        )
        return resp.json()

    def get_pipeline_status(self, project_id, pipeline_id):
        path = self._url(
            "/projects/%s/pipelines/%s" % (self.get_project_id(project_id), pipeline_id)
        )
        resp = requests.get(
            path, headers=self.headers, timeout=self.config.gitlab["timeout"]
        )
        resp.raise_for_status()
        return resp.json()

    def get_namespace_id(self, namespace):
        path = self._url("/namespaces")
        params = {"search": namespace}
        resp = requests.get(
            path,
            headers=self.headers,
            params=params,
            timeout=self.config.gitlab["timeout"],
        )
        resp.raise_for_status()
        return resp.json()[0]["id"]

    def get_or_create_project(
        self, project_name, namespace=None, repo_public: bool = False
    ):
        group_name = namespace or self.config.gitlab["namespsace"]
        project_path = "%s%%2f%s" % (group_name, project_name)
        path = self._url("/projects/%s" % (project_path))
        resp = requests.get(
            path, headers=self.headers, timeout=self.config.gitlab["timeout"]
        )
        if resp.status_code == 200:
            return resp.json()
        group_id = self.get_namespace_id(group_name)
        path = self._url("/projects")
        body = {
            "name": project_name,
            "namespace_id": group_id,
            "builds_access_level": "enabled",
            "operations_access_level": "enabled",
            "merge_requests_access_level": "enabled",
            "public_builds": False,
            "repository_access_level": "enabled",
            "shared_runners_enabled": False,
            "visibility": "private",
        }

        resp = requests.post(
            path,
            data=json.dumps(body).encode(),
            headers=self.headers,
            timeout=self.config.gitlab["timeout"],
        )
        resp.raise_for_status()
        _ = self.create_webhooks(resp.json()["id"])
        return resp.json()

    def initialize_project(self, project_name: str, namespace: str = None):
        project = self.get_or_create_project(project_name, namespace)
        branch = "master"

        branch_path = self._url(
            "/projects/%s/repository/branches/%s" % (project["id"], branch)
        )
        resp = requests.get(
            branch_path, headers=self.headers, timeout=self.config.gitlab["timeout"]
        )
        if resp.status_code == 404:
            time.sleep(2)
            self.push_file(
                project["id"],
                file_path="README.md",
                file_content=bytes(("# %s" % project_name).encode()),
                branch="master",
                message="init readme",
            )
            time.sleep(2)
            resp = requests.put(
                branch_path + "/unprotect",
                headers=self.headers,
                timeout=self.config.gitlab["timeout"],
            )
            resp.raise_for_status()
            branch_path = self._url("/projects/%s/repository/branches" % project["id"])
            branch_body = {"branch": "_failfastci", "ref": "master"}
            resp = requests.post(
                branch_path,
                params=branch_body,
                headers=self.headers,
                timeout=self.config.gitlab["timeout"],
            )

        return project

    def retry_build(self, gitlab_project_id, build_id):
        path = self._url("/projects/%s/jobs/%s/retry" % (gitlab_project_id, build_id))
        resp = requests.post(
            path, headers=self.headers, timeout=self.config.gitlab["timeout"]
        )
        resp.raise_for_status()
        return resp.json()

    def retry_pipeline(self, gitlab_project_id, sha):
        path = self._url("/projects/%s/pipeline" % gitlab_project_id)
        resp = requests.post(
            path,
            params={"ref": sha},
            headers=self.headers,
            timeout=self.config.gitlab["timeout"],
        )
        resp.raise_for_status()
        return resp.json()

    # def get_branches(self, project_id, search=None):
    #     branches = []
    #     page = 1
    #     page_count = 100
    #     while page <= page_count:
    #         params = {"page": page, "per_page": 50}
    #         if search:
    #             params["search"] = search
    #         path = self._url(
    #             "/projects/%s/repository/branches" % (self.get_project_id(project_id))
    #         )
    #         resp = requests.get(path, headers=self.headers, params=params)
    #         resp.raise_for_status()
    #         branches += resp.json()
    #         page_count = resp.headers["X-Total-Pages"]
    #         if not resp.headers["X-Next-Page"]:
    #             break
    #         page = resp.headers["X-Next-Page"]
    #     return branches

    # def delete_old_branches(self, project_id, branches, days_old):
    #     from datetime import datetime, timedelta

    #     delta = timedelta(days_old)
    #     max_date = datetime.utcnow() - delta
    #     project_id = self.get_project_id(project_id)
    #     delete_branches = 0
    #     for branch in branches:
    #         date = datetime.fromisoformat(branch["commit"]["committed_date"]).replace(
    #             tzinfo=None
    #         )
    #         if date < max_date and branch["name"] != "master":
    #             self.delete_branch(project_id, branch["name"])
    #             delete_branches += 1
    #     return delete_branches

    # def delete_branch(self, project_id, branch):
    #     path = self._url(
    #         "/projects/%s/repository/branches/%s"
    #         % (self.get_project_id(project_id), urllib.parse.quote_plus(branch))
    #     )
    #     resp = requests.delete(
    #         path, headers=self.headers, timeout=self.config.gitlab["timeout"]
    #     )
    #     resp.raise_for_status()
    #     return True

    # def delete_project(self, project_id):
    #     path = self._url("/projects/%s" % (self.get_project_id(project_id)))
    #     resp = requests.delete(path)
    #     resp.raise_for_status()
    #     return resp.json()

    #     def push_file(
    #     self, project_id, file_path, file_content, branch, message, force=True
    # ):
    #     branch_path = self._url(
    #         "/projects/%s/repository/branches" % self.get_project_id(project_id)
    #     )
    #     branch_body = {"branch": branch, "ref": "_failfastci"}
    #     resp = requests.post(
    #         branch_path,
    #         params=branch_body,
    #         headers=self.headers,
    #         timeout=self.config.gitlab["timeout"],
    #     )

    #     path = self._url(
    #         "/projects/%s/repository/files/%s"
    #         % (self.get_project_id(project_id), urllib.parse.quote_plus(file_path))
    #     )
    #     body = {
    #         "file_path": file_path,
    #         "branch": branch,
    #         "encoding": "base64",
    #         "content": base64.b64encode(file_content).decode(),
    #         "commit_message": message,
    #     }
    #     resp = requests.post(
    #         path,
    #         data=json.dumps(body),
    #         headers=self.headers,
    #         timeout=self.config.gitlab["timeout"],
    #     )
    #     if resp.status_code == 400 or resp.status_code == 409:
    #         resp = requests.put(
    #             path,
    #             data=json.dumps(body),
    #             headers=self.headers,
    #             timeout=self.config.gitlab["timeout"],
    #         )

    #     resp.raise_for_status()
    #     return resp.json()
