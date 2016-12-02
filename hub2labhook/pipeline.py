import yaml
from hub2labhook.githubclient import GithubClient
from hub2labhook.gitlabclient import GitlabClient


class Pipeline(object):

    def __init__(self, git_event):
        self.gitlab = GitlabClient()
        self.ghevent = git_event
        self.github = GithubClient(installation_id=self.gitevent.installation_id)

    def _parse_ci_file(content, filepath):
        if filepath == ".gitlab-ci.yml":
            return yaml.load(filepath)

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
        ci_file = self.github.get_ci_file(source_repo)
        content = self._parse_ci_file(ci_file['content'])
        namespace = None
        if 'failfastci_group' in content['variables']:
            namespace = content['variables']['failfastci_group']
        ci_project = self.gitlab.initialize_project(gevent.repo.replace("/","__"), namespace)
        ci_branch = gevent.target_refname
        tokenkey = "GH_TOKEN_%s" % gevent.target_refname
        self.gitlab.set_variables(ci_project['id'], {tokenkey: self.github.token})
        clone_url = gevent.clone_url.replace("https://", "https://bot:$%s:" % tokenkey)

        variables = {'EVENT': gevent.event_type,
                     'PR_ID': str(gevent.pr_id),
                     'SHA': gevent.head_sha,
                     'SOURCE_REF': gevent.refname,
                     'REF_NAME': gevent.refname,
                     'SOURCE_REPO': clone_url}

        content['variables'].update(variables)

        return self.gitlab.push_file(project_id=ci_project['id'],
                                     file_path=content['file'],
                                     file_content=yaml.dump(content),
                                     branch=ci_branch,
                                     message=gevent.commit_message)
