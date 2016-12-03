import uuid
import yaml
from hub2labhook.githubclient import GithubClient
from hub2labhook.gitlabclient import GitlabClient


class Pipeline(object):

    def __init__(self, git_event):
        self.gitlab = GitlabClient()
        self.ghevent = git_event
        self.github = GithubClient(installation_id=self.ghevent.installation_id)

    def _parse_ci_file(self, content, filepath):
        if filepath == ".gitlab-ci.yml":
            return yaml.load(content)

    def trigger_pipeline(self):

        script = """
         git clone $SOURCE_REPO repo
         cd repo
         if [ $PR_ID == \"N/A\" ]; then
                git checkout ${SOURCE_REF}
         else
                git fetch origin pull/${PR_ID}/head:pr-${PR_ID}
                git checkout pr-${PR_ID}
         fi
         eval \"[ `git rev-parse HEAD` = $SHA ]\"
        """
        gevent = self.ghevent
        if gevent.pr_id == "N/A":
            source_repo = gevent.repo
        else:
            source_repo = gevent.pr_repo
        ci_file = self.github.get_ci_file(source_repo, gevent.ref)
        content = self._parse_ci_file(ci_file['content'], ci_file['file'])
        namespace = None
        if 'failfastci_group' in content['variables']:
            namespace = content['variables']['failfastci_group']
        ci_project = self.gitlab.initialize_project(gevent.repo.replace("/", "__"), namespace)
        ci_branch = gevent.refname
        tokenkey = "GH_TOKEN_%s" % str.upper(uuid.uuid4().hex)
        self.gitlab.set_variables(ci_project['id'], {tokenkey: self.github.token})
        clone_url = gevent.clone_url.replace("https://", "https://bot:$%s:" % tokenkey)

        variables = {'EVENT': gevent.event_type,
                     'PR_ID': str(gevent.pr_id),
                     'SHA': gevent.head_sha,
                     'SOURCE_REF': gevent.refname,
                     'REF_NAME': gevent.refname,
                     'GITHUB_INSTALLATION_ID': gevent.installation_id,
                     'GITHUB_REPO': gevent.repo,
                     'SOURCE_REPO': clone_url}

        content['variables'].update(variables)

        return self.gitlab.push_file(project_id=ci_project['id'],
                                     file_path=ci_file['file'],
                                     file_content=yaml.safe_dump(content),
                                     branch=ci_branch,
                                     message=gevent.commit_message)
