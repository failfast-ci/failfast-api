from __future__ import absolute_import, unicode_literals

from hub2labhook.githubevent import GithubEvent
from hub2labhook.pipeline import Pipeline

from .runner import app
from .job_base import JobBase


@app.task(bind=True, base=JobBase, retry=3)
def pipeline(self, event, headers):
    gevent = GithubEvent(event, headers)
    build = Pipeline(gevent)
    return build.trigger_pipeline()


@app.task(bind=True, base=JobBase, retry=3)
def update_github_statuses(self, sha):

    githubclient = GithubClient(installation_id=params['installation_id'])
    delay = params.get('delay', 0)
    return jsonify(githubclient.update_github_status(params['gitlab_project_id'],
                                                     params['gitlab_build_id'],
                                                     params['github_repo'],
                                                     delay))
