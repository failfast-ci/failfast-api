from __future__ import absolute_import, unicode_literals
import requests

from hub2labhook.github.models.event import GithubEvent
from hub2labhook.github.client import GITHUB_STATUS_MAP, GithubClient
from hub2labhook.gitlab.client import GitlabClient
from hub2labhook.pipeline import Pipeline
from hub2labhook.config import GITHUB_CONTEXT

from hub2labhook.jobs.runner import app
from hub2labhook.jobs.job_base import JobBase


@app.task(bind=True, base=JobBase)
def pipeline(self, event, headers):
    gevent = GithubEvent(event, headers)
    build = Pipeline(gevent)
    return build.trigger_pipeline()


def update_github_status(project, build, github_repo, sha, installation_id):
    descriptions = {
        "pending": "Build in-progress",
        "success": "Build success",
        "error": "Build in error or canceled",
        "failure": "Build failed"
    }
    githubclient = GithubClient(installation_id)
    project_url = project['web_url']
    # sha = build['commit']['id']
    state = GITHUB_STATUS_MAP[build['status']]
    build_body = {
        "state": state,
        "target_url": (project_url + "/builds/%s") % build['id'],
        "description": descriptions[GITHUB_STATUS_MAP[build['status']]],
        "context": "%s/%s/%s" % (GITHUB_CONTEXT, build['stage'], build['name'])
    }
    return githubclient.post_status(build_body, github_repo, sha)


@app.task(bind=True, base=JobBase)
def update_build_status(self, params):
    try:
        gitlab_project_id = params['ci_project_id']
        github_repo = params['github_repo']
        sha = params['sha']
        installation_id = params['installation_id']
        build_id = params['build_id']
        gitlabclient = GitlabClient()
        project = gitlabclient.get_project(gitlab_project_id)
        build = gitlabclient.get_build(project['id'], build_id)
        return update_github_status(project, build, github_repo, sha, installation_id)
    except Exception as exc:
        self.retry(countdown=60, exc=exc)


@app.task(bind=True, base=JobBase)
def update_github_statuses(self, trigger):
    descriptions = {
        "pending": "Pipeline in-progress",
        "success": "Pipeline success",
        "error": "Pipeline in error or canceled",
        "failure": "Pipeline failed"
    }

    gitlab_project_id = trigger['ci_project_id']
    github_repo = trigger['github_repo']
    sha = trigger['sha']
    installation_id = trigger['installation_id']
    ref = trigger['ci_ref']
    pending = False
    gitlabclient = GitlabClient()
    githubclient = GithubClient(installation_id=installation_id)
    try:
        pipelines = {}
        project = gitlabclient.get_project(gitlab_project_id)
        project_url = project['web_url']
        pipelines = gitlabclient.get_pipelines(int(gitlab_project_id), ref=ref)
        if not pipelines:
            raise self.retry(countdown=60)
        pipe = pipelines[0]
        state = GITHUB_STATUS_MAP[pipe['status']]
        pending = state == "pending"
        pipeline_body = {
            "state": state,
            "target_url": project_url + "/pipelines/%s" % pipe['id'],
            "description": descriptions[state],
            "context": "%s/pipeline" % GITHUB_CONTEXT
        }
        resp = []
        resp.append(githubclient.post_status(pipeline_body, github_repo, sha))
        builds = gitlabclient.get_jobs(project['id'], pipe['id'])
        if not builds:
            raise self.retry(countdown=60)
        pdict = {'builds': {}}
        for build in builds:
            if build['name'] not in pdict['builds']:
                pdict[build['name']] = []
            pdict[build['name']].append(build)

        for _, builds in pdict['builds'].items():
            build = sorted(builds, key=lambda x: x['id'], reverse=True)[0]
            if build['status'] not in ['skipped', 'created']:
                resp.append(
                    update_github_status(project, build, github_repo, sha, installation_id))
        if pending:
            raise self.retry(countdown=60)
        return resp
    except requests.exceptions.RequestException as exc:
        raise self.retry(countdown=60, exc=exc)
    except Exception as exc:
        raise self.retry(countdown=60, exc=exc)
