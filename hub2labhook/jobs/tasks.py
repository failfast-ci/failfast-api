from __future__ import absolute_import, unicode_literals
import logging
import re
import json
from datetime import datetime

import requests
from hub2labhook.github.models.event import GithubEvent
from hub2labhook.github.client import GITHUB_STATUS_MAP, GITHUB_CHECK_MAP, GithubClient
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


def _task_actions():
    return ([{
                "label": "retry",
                "identifier": "retry",
                "description": "Retries the job"
            },
            {
            "label": "Ignore test",
            "identifier": "skip",
            "description": "Marks the job as neutral"
        }])


@app.task(base=JobBase, retry_kwargs={'max_retries': 5}, retry_backoff=True)
def update_github_check(event):
    gitlabclient = GitlabClient()
    logger.info(event)
    build = event

    installation_id = gitlabclient.get_variable(
        build['project_id'], 'GITHUB_INSTALLATION_ID')['value']
    github_repo = gitlabclient.get_variable(build['project_id'],
                                            'GITHUB_REPO')['value']
    githubclient = GithubClient(installation_id=installation_id)

    extra = {'conclusion': None, 'started_at': None, 'completed_at': None}

    if build['build_status'] == "created":
        # Ignore such builds as they are probably manuals builds
        return None

    if not build['build_started_at']:
        status = "queued"
    elif not build['build_finished_at']:
        status = "in_progress"
        extra['started_at'] = datetime.strptime(
            build['build_started_at'],
            "%Y-%m-%d %H:%M:%S %Z").isoformat() + "Z"
    else:
        status = "completed"
        extra['conclusion'] = GITHUB_CHECK_MAP[build['build_status']]
        extra['started_at'] = datetime.strptime(
            build['build_started_at'],
            "%Y-%m-%d %H:%M:%S %Z").isoformat() + "Z"
        extra['completed_at'] = datetime.strptime(
            build['build_finished_at'],
            "%Y-%m-%d %H:%M:%S %Z").isoformat() + "Z"

    check = {
        "name":
            "%s/%s" % (FFCONFIG.github['context'], build['build_name']),
        "head_sha":
            build['sha'],
        "status":
            status,
        "external_id":
            json.dumps({
                'project': build['project_id'],
                'build': build['build_id']
            }),
        "details_url":
            build['repository']['homepage'] + "/builds/%s" % build['build_id'],
        "output": {
            "title":
                "%s/%s" % (build['build_stage'], build['build_name']),
            "summary":
                "'%s/%s" % (build['build_name'], status),
            "text":
                "# %s/%s" % (build['build_stage'], build['build_name']) +
                "\n\n ## Trace available: %s" % build['repository']['homepage']
                + "/builds/%s" % build['build_id']
        },  # noqa
        "actions": _task_actions()
    }

    for k, v in extra.items():
        if v is not None:
            check[k] = v

    logger.info(check)
    return githubclient.create_check(github_repo, check)


@app.task(bind=True, base=JobBase)
def pipeline(self, event, headers):
    gevent = GithubEvent(event, headers)
    config = FFCONFIG
    build = Pipeline(gevent, config)
    return build.trigger_pipeline()


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
        context="%s/%s" % (FFCONFIG.github['context'], "pipeline"))
    return githubclient.post_status(body, gevent.repo, gevent.head_sha)


def post_pipeline_status(project, pipeline_attr):
    '''
    POST the pipeline status on GitHub
    '''
    descriptions = {
        "pending": "Pipeline in-progress",
        "success": "Pipeline success",
        "error": "Pipeline in error or canceled",
        "failure": "Pipeline failed"
    }
    gitlabclient = GitlabClient()
    installation_id = gitlabclient.get_variable(
        project['id'], 'GITHUB_INSTALLATION_ID')['value']
    github_repo = gitlabclient.get_variable(project['id'],
                                            'GITHUB_REPO')['value']

    githubclient = GithubClient(installation_id=installation_id)
    sha = pipeline_attr['sha']
    context = FFCONFIG.github['context']
    state = GITHUB_STATUS_MAP[pipeline_attr['status']]
    pipeline_body = {
        "state":
            state,
        "target_url":
            project['web_url'] + "/pipelines/%s" % pipeline_attr['id'],
        "description":
            descriptions[state],
        "context":
            "%s/pipeline" % context
    }
    resync_body = {
        "state":
            "success",
        "target_url":
            FFCONFIG.failfast['failfast_url'] + "/api/v1/resync/%s/%s" %
            (project['id'], pipeline_attr['id']),
        "description":
            "resync-gitlab status",
        "context":
            "%s/resync-gitlab" % context
    }
    githubclient.post_status(resync_body, github_repo, sha)
    return githubclient.post_status(pipeline_body, github_repo, sha)


@app.task(base=JobBase, retry_kwargs={'max_retries': 5}, retry_backoff=True)
def update_pipeline_status(gitlab_project_id, pipeline_id):
    '''
    Queries GitLab to get the pipeline status and then update the GitHub statuses
    '''
    gitlabclient = GitlabClient()
    project = gitlabclient.get_project(gitlab_project_id)
    pipeline_attr = gitlabclient.get_pipeline_status(gitlab_project_id,
                                                     pipeline_id)

    return post_pipeline_status(project, pipeline_attr)


@app.task(bind=True, base=JobBase, retry_kwargs={'max_retries': 5},
          retry_backoff=True)
def update_pipeline_hook(self, event):
    '''
    The job triggered when GitLab POST a webhook
    `Pipeline Hook` and then update GitHub statuses
    '''
    logger.info(event)
    pipeline_attr = event['object_attributes']
    project = event['project']
    try:
        return post_pipeline_status(project, pipeline_attr)
    except requests.exceptions.RequestException as exc:
        logger.error('Error request')
        raise self.retry(countdown=60, exc=exc)


@app.task(bind=True, base=JobBase, retry_kwargs={'max_retries': 5},
          retry_backoff=True)
def retry_build(self, external_id):
    project_id = external_id['project']
    build_id = external_id['build']
    gitlabclient = GitlabClient()
    try:
        return gitlabclient.retry_build(project_id, build_id)
    except requests.exceptions.RequestException as exc:
        logger.error('Error request')
        raise self.retry(countdown=60, exc=exc)


@app.task(bind=True, base=JobBase, retry_kwargs={'max_retries': 5},
          retry_backoff=True)
def skip_check(self, event):
    try:
        check = {
            'status':
                'completed',
            'conclusion':
                'neutral',
            'completed_at':
                datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "actions": _task_actions()
        }

        githubclient = GithubClient(
            installation_id=event['installation']['id'])
        return githubclient.update_check_run(event['repository']['full_name'],
                                             check, event['check_run']['id'])
    except requests.exceptions.RequestException as exc:
        logger.error('Error request')
        raise self.retry(countdown=60, exc=exc)


def request_action(action, event):
    if action == "skip":
        return skip_check.s(event)
    if action == "retry":
        return retry_build.s(json.loads(event['check_run']['external_id']))


@app.task(bind=True, base=JobBase, retry_kwargs={'max_retries': 5},
          retry_backoff=True)
def retry_pipeline(self, external_id):
    pass


def start_pipeline(event, headers):
    '''
    start_pipeline is launching the job 'pipeline' if conditions are met.
    The pipeline job clone the github-repo and push it to gitlab
    '''
    gevent = GithubEvent(event, headers)
    config = FFCONFIG
    trigger_build = (
        istriggered_on_branches(gevent, config) or
        istriggered_on_pr(gevent, config) or
        istriggered_on_labels(gevent, config))
    if trigger_build:
        task = pipeline.s(event, headers)
        task.link_error(update_github_statuses_failure.s(event, headers))
        return task
    else:
        return None
