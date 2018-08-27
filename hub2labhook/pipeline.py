import time
import json
import tempfile
import os
import uuid

import yaml

from yaml.composer import ComposerError as YAMLComposeError

from hub2labhook.github.client import GithubClient
from hub2labhook.gitlab.client import GitlabClient
from hub2labhook.exception import Unexpected, ResourceNotFound
from hub2labhook.utils import clone_url_with_auth
from hub2labhook.config import FFCONFIG

from git import Repo

# from celery.contrib import rdb;rdb.set_trace()

DEFAULT_MODE = "sync"

GITLAB_CI_KEYS = set([
    "before_script", "image", "services", "after_script", "variables",
    "stages", "types", "cache"
])


class Pipeline(object):
    def __init__(self, git_event, config=None):
        if config is None:
            config = FFCONFIG
        self.ghevent = git_event
        self.config = config
        self.github = GithubClient(
            installation_id=self.ghevent.installation_id)

    def _parse_ci_file(self, content, filepath):
        if filepath == ".gitlab-ci.yml":
            return yaml.safe_load(content)

    def _checkout_repo(self, gevent, repo_path):
        clone_url = clone_url_with_auth(gevent.clone_url,
                                        "bot:%s" % self.github.token)
        try_count = 0
        while try_count < 3:
            try:
                time.sleep(1)
                gitbin = Repo.clone_from(clone_url, repo_path).git
                break
            except Exception:
                try_count = try_count + 1
                if try_count >= 3:
                    raise

        gitbin.config("http.postBuffer", "1524288000")
        gitbin.config("--local", "user.name", "FailFast-ci Bot")
        gitbin.config("--local", "user.email", "failfastci-bot@failfast-ci.io")
        if gevent.pr_id == "":
            gitbin.checkout(gevent.refname)
        else:
            pr_branch = "pr-%s" % gevent.pr_id
            gitbin.fetch('origin', "pull/%s/head:%s" % (gevent.pr_id,
                                                        pr_branch))
            gitbin.checkout(pr_branch)
        if not gitbin.rev_parse('HEAD') == gevent.head_sha:
            raise Unexpected("git sha don't match", {
                'expected_sha': gevent.head_sha,
                'sha': gitbin.rev_parse('HEAD')
            })
        return gitbin

    def _get_ci_file(self, repo_path):
        content = None
        for filepath in [".gitlab-ci.yml", ".failfast-ci.jsonnet"]:
            path = os.path.join(repo_path, filepath)
            if not os.path.exists(path):
                continue
            with open(path, 'r') as f:
                content = f.read()
                return {"content": content, "file": filepath}
        if content is None:
            raise ResourceNotFound("no .gitlab-ci.yml or .failfast-ci.jsonnet")

    def _append_update_stage(self, content):
        stage_name = "github-status-update"
        url = self.config.failfast['failfast_url'] + "/api/v1/github_statuses"
        update_status = {
            "ci_project_id": "$CI_PROJECT_ID",
            "ci_sha": "$CI_BUILD_REF",
            "sha": "$SHA",
            "ci_ref": "$CI_COMMIT_REF_NAME",
            "github_repo": "$GITHUB_REPO",
            "installation_id": "$GITHUB_INSTALLATION_ID",
            "delay": 150
        }
        params_150 = json.dumps(update_status)

        job = {
            "image":
                "python:2.7",
            "stage":
                stage_name,
            "before_script": [],
            "after_script": [
                "curl -XPOST %s -d \"%s\" || true" %
                (url, params_150.replace('"', '\\\"'))
            ],
            "script": [
                "echo curl -XPOST %s -d \"%s\" || true" %
                (url, params_150.replace('"', '\\\"'))
            ],
            "when":
                "always"
        }

        if self.config.gitlab.get('runner_tags', None) is not None:
            job['tags'] = self.config.gitlab['runner_tags']

        # adopt GitLab's default if absent
        # https://docs.gitlab.com/ce/ci/yaml/README.html#stages
        stages = content.get('stages', ['build', 'test', 'deploy'])
        stages.append(stage_name)
        content['stages'] = stages

        content['report-status'] = job

    def trigger_pipeline(self):
        gevent = self.ghevent
        gitlab_user = self.config.gitlab['robot-user']
        dirpath = tempfile.mkdtemp()
        repo_path = os.path.join(dirpath, "repo")
        gitbin = self._checkout_repo(gevent, repo_path)

        try:
            ci_file = self._get_ci_file(repo_path)
        except ResourceNotFound:
            raise Unexpected("Could not find a CI config file in: %s" %
                             (repo_path))

        try:
            content = self._parse_ci_file(ci_file['content'], ci_file['file'])
        except YAMLComposeError:
            raise Unexpected("Could not parse CI file: %s" %
                             (ci_file['file'], ))
        lint_resp = GitlabClient().gitlabci_lint(content)
        if 'status' not in lint_resp or lint_resp['status'] != 'valid':
            raise Unexpected(".gitlab-ci.yml lint errors")

        variables = content.get('variables', dict())

        namespace = variables.get('FAILFASTCI_NAMESPACE',
                                  self.config.gitlab.get('namespace', None))
        repo = variables.get('GITLAB_REPOSITORY', None)
        reponame = gevent.repo.replace("/", "_")
        if repo:
            namespace, reponame = repo.split('/')
        gitlab_endpoint = variables.get('GITLAB_URL',
                                        self.config.gitlab.get(
                                            'gitlab_url', None))
        self.gitlab = GitlabClient(gitlab_endpoint, config=self.config)

        ci_project = self.gitlab.initialize_project(reponame, namespace)

        # @Todo(ant31) check if clone_url is required
        # clone_url = clone_url_with_auth(gevent.clone_url, "bot:%s" % self.github.token)
        target_url = clone_url_with_auth(ci_project['http_url_to_repo'],
                                         "%s:%s" % (gitlab_user,
                                                    self.gitlab.gitlab_token))
        gitbin.remote('add', 'target', target_url)

        variables.update({
            'EVENT':
                gevent.event_type,
            'PR_ID':
                str(gevent.pr_id),
            'SHA':
                gevent.head_sha,
            'SHA8':
                gevent.head_sha[0:8],
            'FAILFASTCI_STATUS_API': (
                '%s/api/v1/github_status' %
                (self.config.failfast['failfast_url'], )),
            'SOURCE_REF':
                gevent.refname,
            'REF_NAME':
                gevent.refname,
            'CI_REF':
                gevent.target_refname,
            'GITHUB_INSTALLATION_ID':
                str(gevent.installation_id),
            'GITHUB_REPO':
                gevent.repo
        })

        content['variables'] = variables

        self.gitlab.set_variables(
            ci_project['id'], {
                'GITHUB_INSTALLATION_ID': str(gevent.installation_id),
                'GITHUB_REPO': gevent.repo
            })
        perform_sync = variables.get("FAILFAST_SYNC_REPO", "false")

        if ((perform_sync == "true") or (DEFAULT_MODE == "sync")):
            # Full synchronize the repo)
            gitbin.push("target", 'HEAD:%s' % gevent.target_refname, "-f")
            ci_sha = str(gitbin.rev_parse('HEAD'))
            return {  # NOTE: the GitHub reference details for subsequent tasks.
                'sha': gevent.head_sha,
                'ci_sha': ci_sha,
                'ref': gevent.refname,
                'ci_ref': gevent.target_refname,
                'ci_project_id': ci_project['id'],
                'installation_id': gevent.installation_id,
                'github_repo': gevent.repo,
                'context': self.config.github['context']
            }
        else:
            self.sync_only_ci_file(gevent, content, ci_project, ci_file)

    # @TODO this is a partial implem
    def sync_only_ci_file(self, gevent, content, ci_project, ci_file):
        """ Push only the .failfast-ci.yaml and set token to clone """
        tokenkey = "GH_TOKEN_%s" % str.upper(uuid.uuid4().hex)
        clone_url = gevent.clone_url.replace("https://",
                                             "https://bot:$%s:" % tokenkey)
        ci_branch = gevent.refname
        content['variables'].update({'SOURCE_REPO': clone_url})
        self.gitlab.set_variables(ci_project['id'], {
            tokenkey: self.github.token
        })
        return self.gitlab.push_file(
            project_id=ci_project['id'], file_path=ci_file['file'],
            file_content=yaml.safe_dump(content), branch=ci_branch,
            message=gevent.commit_message)
