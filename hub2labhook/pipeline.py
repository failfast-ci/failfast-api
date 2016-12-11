import yaml
import tempfile
import os
import uuid
from hub2labhook.githubclient import GithubClient
from hub2labhook.gitlabclient import GitlabClient
from hub2labhook.exception import Unexpected
from hub2labhook.utils import getenv

from git import Repo


DEFAULT_MODE = "sync"


class Pipeline(object):

    def __init__(self, git_event):
        self.gitlab = GitlabClient()
        self.ghevent = git_event
        self.github = GithubClient(installation_id=self.ghevent.installation_id)

    def _parse_ci_file(self, content, filepath):
        if filepath == ".gitlab-ci.yml":
            return yaml.load(content)

    def trigger_pipeline(self):
        gevent = self.ghevent
        if gevent.pr_id == "N/A":
            source_repo = gevent.repo
        else:
            source_repo = gevent.pr_repo
        ci_file = self.github.get_ci_file(source_repo, gevent.ref)
        content = self._parse_ci_file(ci_file['content'], ci_file['file'])
        namespace = content['variables'].get('FAILFASTCI_NAMESPACE', None)
        ci_project = self.gitlab.initialize_project(gevent.repo.replace("/", "__"), namespace)

        clone_url = gevent.clone_url.replace("https://", "https://bot:%s@" % self.github.token)
        variables = {'EVENT': gevent.event_type,
                     'PR_ID': str(gevent.pr_id),
                     'SHA': gevent.head_sha,
                     'FAILFASTCI_STATUS_API': "https://jobs.failfast-ci.io/api/v1/github_status",
                     'SOURCE_REF': gevent.refname,
                     'REF_NAME': gevent.refname,
                     'GITHUB_INSTALLATION_ID': str(gevent.installation_id),
                     'GITHUB_REPO': gevent.repo,
                     'SOURCE_REPO': clone_url}

        content['variables'].update(variables)
        if ('FAILFASTCI_SYNC_REPO' in content['variables'] and
           content['variables']['FAILFAST_SYNC_REPO'] == "true") or DEFAULT_MODE == "sync":
            """ Full synchronize the repo """
            gitlab_user = getenv(None, "GITLAB_USER")
            target_url = ci_project['http_url_to_repo'].replace("https://", "https://%s:%s@" % (gitlab_user, self.gitlab.gitlab_token))
            dirpath = tempfile.mkdtemp()
            repo_path = os.path.join(dirpath, "repo")
            gitbin = Repo.clone_from(clone_url, repo_path).git
            if gevent.pr_id == "N/A":
                gitbin.checkout(gevent.refname)
            else:
                pr_branch = "pr-%s" % gevent.pr_id
                gitbin.fetch('origin', "pull/%s/head:%s" % (gevent.pr_id, pr_branch))
                gitbin.checkout(pr_branch)

            if not gitbin.rev_parse('HEAD') == gevent.head_sha:
                raise Unexpected("git sha don't match",
                                 {'expected_sha': gevent.head_sha, 'sha': gitbin.ref_parse('HEAD')})
            gitbin.remote('add', 'target', target_url)
            path = os.path.join(repo_path, ".gitlab-ci.yml")
            with open(path, 'w') as gitlabcifile:
                gitlabcifile.write(yaml.safe_dump(content))
            gitbin.config("--global", "user.name", "FailFast-ci Bot")
            gitbin.config("--global", "user.email", "failfastci-bot@failfast-ci.io")
            gitbin.commit("-a", "-m", "update .gitlab-ci.yml")
            gitbin.push("target", 'HEAD:%s' % gevent.target_refname, "-f")
            return {'pushed': gevent.target_refname}
        else:
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
