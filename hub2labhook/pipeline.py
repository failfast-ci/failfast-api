import time
from copy import deepcopy
import json
import yaml
import tempfile
import os
import uuid
from hub2labhook.githubclient import GithubClient
from hub2labhook.gitlabclient import GitlabClient
from hub2labhook.exception import Unexpected, ResourceNotFound
from hub2labhook.utils import getenv, clone_url_with_auth
from git import Repo

# from celery.contrib import rdb;rdb.set_trace()


DEFAULT_MODE = "sync"
FAILFAST_API = os.getenv("FAILFAST_CI_API", "https://jobs.failfast-ci.io")

GITLAB_CI_KEYS = set(["before_script", "image", "services", "after_script",
                      "variables", "stages", "types", "cache"])


class Pipeline(object):

    def __init__(self, git_event):
        self.ghevent = git_event
        self.github = GithubClient(installation_id=self.ghevent.installation_id)

    def _parse_ci_file(self, content, filepath):
        if filepath == ".gitlab-ci.yml":
            return yaml.safe_load(content)

    def _checkout_repo(self, gevent, repo_path):
        clone_url = clone_url_with_auth(gevent.clone_url, "bot:%s" % self.github.token)
        try_count = 0
        while try_count < 3:
            try:
                time.sleep(1)
                gitbin = Repo.clone_from(clone_url, repo_path).git
                break
            except:
                try_count = try_count + 1
                if try_count >= 3:
                    raise

        gitbin.config("http.postBuffer", "1524288000")
        gitbin.config("--local", "user.name", "FailFast-ci Bot")
        gitbin.config("--local", "user.email", "failfastci-bot@failfast-ci.io")
        if gevent.pr_id == "N/A":
            gitbin.checkout(gevent.refname)
        else:
            pr_branch = "pr-%s" % gevent.pr_id
            gitbin.fetch('origin', "pull/%s/head:%s" % (gevent.pr_id, pr_branch))
            gitbin.checkout(pr_branch)
        if not gitbin.rev_parse('HEAD') == gevent.head_sha:
            raise Unexpected("git sha don't match",
                             {'expected_sha': gevent.head_sha, 'sha': gitbin.rev_parse('HEAD')})
        return gitbin

    def _get_ci_file(self, repo_path):
        content = None
        for filepath in [".gitlab-ci.yml", ".failfast-ci.jsonnet"]:
            path = os.path.join(repo_path, filepath)
            if not os.path.exists(path):
                continue
            with open(path, 'r') as f:
                content = f.read()
                return {"content": content,
                        "file": filepath}
        if content is None:
            raise ResourceNotFound("n o .gitlab-ci.yml or .failfail-ci.jsonnet")

    def _append_update_stage(self, content):
        stage_name = "github-status-update"
        url = FAILFAST_API + "/api/v1/github_statuses"
        update_status = {"ci_project_id": "$CI_PROJECT_ID",
                         "ci_sha": "$CI_BUILD_REF",
                         "sha": "$SHA",
                         "github_repo": "$GITHUB_REPO",
                         "installation_id": "$GITHUB_INSTALLATION_ID",
                         "delay": 150}
        update_status_30 = deepcopy(update_status)
        update_status_30['delay'] = 30
        params_150 = json.dumps(update_status)
        params_30 = json.dumps(update_status_30)
        job = {
            "image": "python:2.7",
            "stage": stage_name,
            "before_script": [],
            "after_script": ["curl -XPOST %s -d \"%s\" || true" % (url, params_30.replace('"', '\\\"')),
                             "curl -XPOST %s -d \"%s\" || true" % (url, params_150.replace('"', '\\\"'))],
            "script": ["echo curl -XPOST %s -d \"%s\" || true" % (url, params_30.replace('"', '\\\"')),
                       "echo curl -XPOST %s -d \"%s\" || true" % (url, params_150.replace('"', '\\\"'))],
            "tags": ["failfast-ci"],
            "when": "always"
            }
        content['stages'].append(stage_name)
        content['report-status'] = job

    def _append_update_build(self, content):
        params = json.dumps({"ci_project_id": "$CI_PROJECT_ID",
                             "ci_sha": "$CI_BUILD_REF",
                             "sha": "$SHA",
                             "build_id": "$CI_BUILD_ID",
                             "github_repo": "$GITHUB_REPO",
                             "installation_id": "$GITHUB_INSTALLATION_ID",
                             "delay": 45})
        url = FAILFAST_API + "/api/v1/github_status"
        task = "curl -m 45 --connect-timeout 45 -XPOST %s -d \"%s\" || true" % (url, params.replace('"', '\\\"'))
        for key, job in content.items():
            if key in GITLAB_CI_KEYS or key[0] == ".":
                continue
            if "after_script" not in job:
                job['after_script'] = []
            if task not in job:
                if task not in job['after_script']:
                    job['after_script'].append(task)

    def trigger_pipeline(self):
        gevent = self.ghevent
        gitlab_user = getenv(None, "GITLAB_USER")
        dirpath = tempfile.mkdtemp()
        repo_path = os.path.join(dirpath, "repo")
        gitbin = self._checkout_repo(gevent, repo_path)
        ci_file = self._get_ci_file(repo_path)
        content = self._parse_ci_file(ci_file['content'], ci_file['file'])
        namespace = content['variables'].get('FAILFASTCI_NAMESPACE', None)
        gitlab_endpoint = content['variables'].get('GITLAB_URL', None)
        self.gitlab = GitlabClient(gitlab_endpoint)

        ci_project = self.gitlab.initialize_project(gevent.repo.replace("/", "__"), namespace)

        clone_url = clone_url_with_auth(gevent.clone_url, "bot:%s" % self.github.token)
        target_url = clone_url_with_auth(ci_project['http_url_to_repo'],
                                         "%s:%s" % (gitlab_user, self.gitlab.gitlab_token))
        gitbin.remote('add', 'target', target_url)
        variables = {'EVENT': gevent.event_type,
                     'PR_ID': str(gevent.pr_id),
                     'SHA': gevent.head_sha,
                     'SHA8': gevent.head_sha[0:8],
                     'FAILFASTCI_STATUS_API': "https://jobs.failfast-ci.io/api/v1/github_status",
                     'SOURCE_REF': gevent.refname,
                     'REF_NAME': gevent.refname,
                     'GITHUB_INSTALLATION_ID': str(gevent.installation_id),
                     'GITHUB_REPO': gevent.repo,
                     'SOURCE_REPO': clone_url}

        content['variables'].update(variables)
        self._append_update_build(content)
        self._append_update_stage(content)
        if ('FAILFASTCI_SYNC_REPO' in content['variables'] and
           content['variables']['FAILFAST_SYNC_REPO'] == "true") or DEFAULT_MODE == "sync":
            # Full synchronize the repo
            path = os.path.join(repo_path, ".gitlab-ci.yml")
            with open(path, 'w') as gitlabcifile:
                gitlabcifile.write(yaml.safe_dump(content, default_style='"', width=float("inf")))
            gitbin.commit("-a", "-m", "build %s \n\n @ %s" % (gevent.head_sha, gevent.commit_url))
            gitbin.push("target", 'HEAD:%s' % gevent.target_refname, "-f")
            ci_sha = str(gitbin.rev_parse('HEAD'))
            return {'sha': gevent.head_sha,
                    'ci_sha': ci_sha,
                    'ci_ref': gevent.target_refname,
                    'ci_project_id': ci_project['id'],
                    'installation_id': gevent.installation_id,
                    'github_repo': gevent.repo}
        else:
            self.sync_only_ci_file(gevent, content, ci_project, ci_file)

    # @TODO this is a partial implem
    def sync_only_ci_file(self, gevent, content, ci_project, ci_file):
        """ Push only the .failfast-ci.yaml and set token to clone """
        tokenkey = "GH_TOKEN_%s" % str.upper(uuid.uuid4().hex)
        clone_url = gevent.clone_url.replace("https://", "https://bot:$%s:" % tokenkey)
        ci_branch = gevent.refname
        content['variables'].update({'SOURCE_REPO': clone_url})
        self.gitlab.set_variables(ci_project['id'], {tokenkey: self.github.token})
        return self.gitlab.push_file(project_id=ci_project['id'],
                                     file_path=ci_file['file'],
                                     file_content=yaml.safe_dump(content),
                                     branch=ci_branch,
                                     message=gevent.commit_message)
