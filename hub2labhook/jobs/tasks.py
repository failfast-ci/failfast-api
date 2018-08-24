from __future__ import absolute_import, unicode_literals
import logging
import re
import requests
import time
from celery import signature
from hub2labhook.github.models.event import GithubEvent
from hub2labhook.github.client import GITHUB_STATUS_MAP, GithubClient
from hub2labhook.gitlab.client import GitlabClient
from hub2labhook.pipeline import Pipeline
from hub2labhook.config import FFCONFIG

from hub2labhook.jobs.runner import app
from hub2labhook.jobs.job_base import JobBase

logger = logging.getLogger(__name__)


def is_authorized(self, user, group=None, config=None):
    if config is None:
        config = FFCONFIG
    return ((config.failfast['authorized_users'] == '*' or
             user in config.failfast['authorized_users']) or
            (group and (config.failfast['authorized_groups'] == '*' or
                        group in config.failfast['authorized_groups'])))


def istriggered_on_comments(gevent, config=None):
    if config is None:
        config = FFCONFIG
    return (gevent.event_type == "issue_comment" and
            is_authorized(gevent.user, gevent.author_association) and
            gevent.comment in FFCONFIG.failfast.get('build', {}).get(
                'on-comments', []))


def istriggered_on_labels(gevent, config=None):
    if config is None:
        config = FFCONFIG
    return (gevent.event_type == "pull_request" and
            gevent.action == "labeled" and gevent.label in config.failfast.get(
                'build', {}).get('on-labels', []))


def istriggered_on_branches(gevent, config=None):
    if config is None:
        config = FFCONFIG

    branches = config.failfast.get('build', {}).get('on-branches', [])
    if str.startswith(gevent.ref, "refs/tags/"):
        return "tags" in branches

    for branch in branches:
        r = re.compile(branch)
        if r.match(gevent.refname):
            return True

    return False


def istriggered_on_pr(gevent, config=None):
    if config is None:
        config = FFCONFIG
    pr_list = FFCONFIG.failfast.get('build', {}).get('on-pullrequests', [])
    return (gevent.event_type == "pull_request" and
            gevent.action in ['opened', 'reopened', 'synchronize'] and
            '*' in pr_list)


def update_github_status(project, build, github_repo, sha, installation_id,
                         context):
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
        "context": "%s/%s/%s" % (context, build['stage'], build['name'])
    }
    return githubclient.post_status(build_body, github_repo, sha)


@app.task(bind=True, base=JobBase)
def pipeline(self, event, headers):
    gevent = GithubEvent(event, headers)
    config = FFCONFIG
    build = Pipeline(gevent, config)
    return build.trigger_pipeline()


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
        build = gitlabclient.get_job(project['id'], build_id)
        return update_github_status(project, build, github_repo, sha,
                                    installation_id, params['context'])
    except Exception as exc:
        raise self.retry(countdown=60, exc=exc)


@app.task(bind=True, base=JobBase)
def update_github_statuses_failure(self, request, exc, traceback, event,
                                   headers):
    """ The pipeline has failed. Notify GitHub. """
    gevent = GithubEvent(event, headers)
    githubclient = GithubClient(gevent.installation_id)
    body = dict(
        state=GITHUB_STATUS_MAP["canceled"],
        target_url=(gevent.commit_url),  # TODO: link the gitlab YAML
        description="An error occurred in initial pipeline execution",
        context="%s/%s/%s" % (FFCONFIG.github['context'], "pipeline",
                              "initalize"))
    return githubclient.post_status(body, gevent.repo, gevent.head_sha)


@app.task(bind=True, base=JobBase, retry_kwargs={'max_retries': 5},
          retry_backoff=True)
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
    context = FFCONFIG.github['context']
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
            logger.info('no pipelines')
            raise self.retry(countdown=60)
        pipe = pipelines[0]
        state = GITHUB_STATUS_MAP[pipe['status']]
        pending = state == "pending"
        pipeline_body = {
            "state": state,
            "target_url": project_url + "/pipelines/%s" % pipe['id'],
            "description": descriptions[state],
            "context": "%s/pipeline" % context
        }
        resp = []
        resp.append(githubclient.post_status(pipeline_body, github_repo, sha))
        builds = gitlabclient.get_jobs(project['id'], pipe['id'])
        if not builds:
            logger.info('no builds')
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
                    update_github_status(project, build, github_repo, sha,
                                         installation_id, context))
        if pending:
            logger.info('still pending: retry')
            time.sleep(10)
            raise self.retry(exc=None, countdown=60)
        return resp
    except requests.exceptions.RequestException as exc:
        logger.error('Error request')
        raise self.retry(countdown=60, exc=exc)


def start_pipeline(event, headers):
    gevent = GithubEvent(event, headers)
    config = FFCONFIG
    trigger_build = (
        istriggered_on_branches(gevent, config) or
        istriggered_on_pr(gevent, config) or
        istriggered_on_labels(gevent, config))
    if trigger_build:
        task = pipeline.s(event, headers)
        status_sig = signature('hub2labhook.jobs.tasks.update_github_statuses',
                               args=(), countdown=10)
        task.link(status_sig)
        task.link_error(update_github_statuses_failure.s(event, headers))
        return task
    else:
        return None
