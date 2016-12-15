from __future__ import absolute_import, unicode_literals
import requests

from hub2labhook.githubevent import GithubEvent
from hub2labhook.githubclient import STATUS_MAP, CONTEXT, GithubClient
from hub2labhook.gitlabclient import GitlabClient
from hub2labhook.pipeline import Pipeline

from .runner import app
from .job_base import JobBase


@app.task(bind=True, base=JobBase)
def pipeline(self, event, headers):
    gevent = GithubEvent(event, headers)
    build = Pipeline(gevent)
    return build.trigger_pipeline()


def update_github_status(project, build, github_repo, sha, installation_id):

    descriptions = {"pending": "Build in-progress",
                    "success": "Build success",
                    "error": "Build in error or canceled",
                    "failure": "Build failed"}
    githubclient = GithubClient(installation_id)
    project_url = project['web_url']
    # sha = build['commit']['id']
    state = STATUS_MAP[build['status']]
    build_body = {"state": state,
                  "target_url": (project_url + "/builds/%s") % build['id'],
                  "description": descriptions[STATUS_MAP[build['status']]],
                  "context": "%s/%s/%s" % (CONTEXT, build['stage'], build['name'])}
    return githubclient.post_status(build_body, github_repo, sha)


@app.task(bind=True, base=JobBase)
def update_github_statuses(self, trigger):
    descriptions = {"pending": "Pipeline in-progress",
                    "success": "Pipeline success",
                    "error": "Pipeline in error or canceled",
                    "failure": "Pipeline failed"}

    gitlab_project_id = trigger['ci_project_id']
    github_repo = trigger['github_repo']
    sha = trigger['sha']
    ci_sha = trigger['ci_sha']
    installation_id = trigger['installation_id']

    pending = False
    gitlabclient = GitlabClient()
    githubclient = GithubClient(installation_id=installation_id)
    try:
        pipelines = {}
        project = gitlabclient.get_project(gitlab_project_id)
        project_url = project['web_url']
        builds = gitlabclient.get_builds(project['id'], ci_sha)
        if not builds:
            raise self.retry(countdown=30, max_retries=30)
        for build in builds:
            pipeline_id = build['pipeline']['id']
            if pipeline_id not in pipelines:
                pdict = {'builds': []}
                pdict.update(build['pipeline'])
                pipelines[pipeline_id] = pdict
            pipelines[pipeline_id]['builds'].append(build)
        pipe = pipelines[sorted(pipelines.keys())[-1]]
        state = STATUS_MAP[pipe['status']]
        pending = state == "pending"
        pipeline_body = {"state": state,
                         "target_url": project_url + "/pipelines/%s" % pipe['id'],
                         "description": descriptions[state],
                         "context": "%s/pipeline" % CONTEXT}
        resp = []
        resp.append(githubclient.post_status(pipeline_body, github_repo, sha))
        for build in pipe['builds']:
            resp.append(update_github_status(project, build, github_repo, sha, installation_id))
        if pending:
            raise self.retry(countdown=30, max_retries=400)
        return resp
    except requests.exceptions.RequestException as exc:
        raise self.retry(countdown=30, max_retries=30, exc=exc)
    except Exception as exc:
        raise self.retry(countdown=30, max_retries=30, exc=exc)
