import time
from datetime import datetime
import uuid
import tempfile
import json
import os
import logging
import yaml
from io import StringIO

from yaml.composer import ComposerError as YAMLComposeError

from hub2labhook.github.client import GithubClient
from hub2labhook.gitlab.client import GitlabClient
from hub2labhook.exception import Unexpected, ResourceNotFound
from hub2labhook.utils import clone_url_with_auth
from hub2labhook.config import FFCONFIG

from git import Repo

# from celery.contrib import rdb;rdb.set_trace()
logger = logging.getLogger(__name__)

DEFAULT_MODE = "sync"

GITLAB_CI_KEYS = set([
    "before_script", "image", "services", "after_script", "variables",
    "stages", "types", "cache"
])

class LogCapture:
    def __init__(self):
        self.log_capture_string = StringIO()
        self.log_capture_handler = logging.StreamHandler(self.log_capture_string)
        self.log_capture_handler.setLevel(logging.DEBUG)
        self.log_capture_formatter = logging.Formatter('[%(levelname)s]  %(message)s')
        self.log_capture_handler.setFormatter(self.log_capture_formatter)
        self.root_logger = logging.getLogger()
        self.root_logger.addHandler(self.log_capture_handler)

    def getvalue(self):
        return self.log_capture_string.getvalue()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.root_logger.removeHandler(self.log_capture_handler)

class Pipeline(object):
    def __init__(self, git_event, config=None):
        if config is None:
            config = FFCONFIG
        self.ghevent = git_event
        self.config = config
        self.github = GithubClient(
            installation_id=self.ghevent.installation_id)
        self.check_run = None

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
            logger.error("git sha don't match: expected_sha: %s  != %s", gevent.head_sha, gitbin.rev_parse('HEAD'))
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
            log = "no .gitlab-ci.yml or .failfast-ci.jsonnet"
            logger.error(log)
            raise ResourceNotFound(log)

    def create_sync_check_run(self, gevent):
        eid = {
            'object_kind': "",
            'object_id': "",
            'project_id': "",
            'gh_prid': gevent.pr_id,
            'gh_ref': gevent.ref,
            'ref': gevent.ref,
            'sha': gevent.head_sha,
            'installation_id': gevent.installation_id,
        }

        body = {
            "name": 'Gitlab SYNC',
            "head_sha": gevent.head_sha,
            "external_id": json.dumps(eid),
            "status": "in_progress",
            "started_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "output": {
                "title": "Syncing CI pipeline to Gitlab",
                "summary": "Push commits to Gitlab and trigger CI pipeline",
                "text":  "# Sync \n\n"
            },
            "actions": [{
                "label": "retry",
                "identifier": "retry-gitlab-sync",
                "description": "Retries the gitlab sync"
            }],
            }

        return body

    def update_sync_check_run(self, check_run, status, conclusion, text_list):
        body = {
            "name": check_run['name'],
            "head_sha": check_run['head_sha'],
            "external_id": check_run['external_id'],
            "status": status,
            "started_at": check_run['started_at'],
            "output": {
                "title": check_run['output']['title'],
                "summary": check_run['output']['summary'],
                "text": "# Sync \n\n" + text_list,
            },
            "actions":              [{
                "label": "retry",
                "identifier": "retry-gitlab-sync",
                "description": "Retries the gitlab sync"
            }]
        }

        if status == "completed":
            body['completed_at'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            body['conclusion'] = conclusion
        return body

    def trigger_pipeline(self):
        with LogCapture() as logs:
            try:
                return self._trigger_pipeline(logs)
            except Exception as e:
                logger.error("Error: %s", e)
                if self.check_run is not None:
                    log = ""
                    if logs is not None:
                        log = logs.getvalue()
                    self.github.update_check_run(self.ghevent.repo,
                                                 self.update_sync_check_run(self.check_run, "completed", "failure", log), self.check_run['id'])
                raise

    def _trigger_pipeline(self, logs):
        gevent = self.ghevent
        gitlab_user = self.config.gitlab['robot-user']
        dirpath = tempfile.mkdtemp()
        repo_path = os.path.join(str(dirpath), "repo")

        check_run = self.github.create_check(gevent.repo, self.create_sync_check_run(gevent))
        self.check_run = check_run
        gitbin = self._checkout_repo(gevent, repo_path)
        logger.info("[ok] Cloning repo %s", repo_path)
        self.github.update_check_run(gevent.repo,
                                     self.update_sync_check_run(check_run, "in_progress", "in_progress", logs.getvalue()),  check_run['id'])

        # 1 Create new TestSuit

        try:
            ci_file = self._get_ci_file(repo_path)
        except ResourceNotFound:
            self.github.update_check_run(gevent.repo,
                                         self.update_sync_check_run(check_run, "completed", "failure", logs.getvalue()), self.check_run['id'])
            raise Unexpected(
                "Could not find a CI config file in: %s" % (repo_path))

        try:
            content = self._parse_ci_file(ci_file['content'], ci_file['file'])
        except YAMLComposeError:
            logger.error("Could not parse CI file: %s", ci_file['file'])
            self.github.update_check_run(gevent.repo,
                                         self.update_sync_check_run(check_run, "completed", "failure", logs.getvalue()),  check_run['id'])
            raise Unexpected("Could not parse CI file: %s" % (ci_file['file']),
                             {})

        if self.config.failfast['enable_linter']:
            lint_resp = GitlabClient().gitlabci_lint(ci_file['content'])
            if 'status' not in lint_resp or lint_resp['status'] != 'valid':
                logger.error("Invalid .gitlab-ci.yml syntax: %s", lint_resp)
                self.github.update_check_run(gevent.repo,
                                             self.update_sync_check_run(check_run, "completed", "failure", logs.getvalue()),  check_run['id'])

                raise Unexpected(".gitlab-ci.yml syntax error",
                                 {'r': lint_resp})

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
        logger.info("Initialized project: %s, %s/%s", ci_project['id'], namespace, reponame)
        self.github.update_check_run(gevent.repo,
                                     self.update_sync_check_run(check_run, "in_progress", "in_progress", logs.getvalue()), check_run['id'])

        # @Todo(ant31) check if clone_url is required
        # clone_url = clone_url_with_auth(gevent.clone_url, "bot:%s" % self.github.token)
        target_url = clone_url_with_auth(ci_project['http_url_to_repo'],
                                         "%s:%s" % (gitlab_user,
                                                    self.gitlab.gitlab_token))
        gitbin.remote('add', 'target', target_url)
        labels = ','.join(gevent.labels)
        variables = {
            'PR_LABELS': labels,
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
            'GITHUB_REPO':
                gevent.repo
        }

        content['variables'] = variables

        self.gitlab.set_variables(
            ci_project['id'], {
                'GITHUB_INSTALLATION_ID': str(gevent.installation_id),
                'GITHUB_REPO': gevent.repo
            })
        logger.info("Setting variables: %s", variables)
        self.github.update_check_run(gevent.repo,
                                     self.update_sync_check_run(check_run, "in_progress", "in_progress", logs.getvalue()), check_run['id'])

        perform_sync = variables.get("FAILFAST_SYNC_REPO", "false")

        if ((perform_sync == "true") or (DEFAULT_MODE == "sync")):
            # Full synchronize the repo)
            options = ["-o", f"ci.skip"]
            gitbin.push("target", 'HEAD:%s' % gevent.target_refname, "-f", *options)
            logger.info("Pushed to gitlab: %s", gevent.target_refname)
            pipeline = self.gitlab.new_pipeline(ci_project['id'], ref = gevent.target_refname, variables = variables)
            logger.info("Pipeline triggered: %s", pipeline['id'])
            self.github.update_check_run(gevent.repo,
                                         self.update_sync_check_run(check_run, "completed", "success", logs.getvalue()), check_run['id'])

            ci_sha = str(gitbin.rev_parse('HEAD'))
            return {  # NOTE: the GitHub reference details for subsequent tasks.
                'sha': gevent.head_sha,
                'ci_sha': ci_sha,
                'ref': gevent.refname,
                'ci_ref': gevent.target_refname,
                'ci_project_id': ci_project['id'],
                'pipeline_id': pipeline['id'],
                'installation_id': gevent.installation_id,
                'github_repo': gevent.repo,
                'labels': labels,
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
