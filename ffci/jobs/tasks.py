from __future__ import absolute_import, unicode_literals

import json
import logging
import re

import requests

from ffci.config import FFCONFIG
from ffci.github.client import GITHUB_STATUS_MAP, GithubClient
from ffci.github.models.check import CheckStatus
from ffci.github.models.event import GithubEvent
from ffci.gitlab.client import GitlabClient
from ffci.jobs.job_base import JobBase
from ffci.jobs.runner import app
from ffci.pipeline import Pipeline

logger = logging.getLogger(__name__)


def is_authorized(self, user, group=None, config=None):
    if config is None:
        config = FFCONFIG
    return (
        config.failfast["authorized_users"] == "*"
        or user in config.failfast["authorized_users"]
    ) or (
        group
        and (
            config.failfast["authorized_groups"] == "*"
            or group in config.failfast["authorized_groups"]
        )
    )


def istriggered_on_comments(gevent, config=None):
    if config is None:
        config = FFCONFIG
    return (
        gevent.event_type == "issue_comment"
        and is_authorized(gevent.user, gevent.author_association)
        and gevent.comment in FFCONFIG.failfast.get("build", {}).get("on-comments", [])
    )


def istriggered_on_labels(gevent, config=None):
    if config is None:
        config = FFCONFIG
    return (
        gevent.event_type == "pull_request"
        and gevent.action == "labeled"
        and gevent.label in config.failfast.get("build", {}).get("on-labels", [])
    )


def istriggered_on_branches(gevent, config=None):
    if config is None:
        config = FFCONFIG

    branches = config.failfast.get("build", {}).get("on-branches", [])
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
    pr_list = FFCONFIG.failfast.get("build", {}).get("on-pullrequests", [])
    return (
        gevent.event_type == "pull_request"
        and gevent.action in ["opened", "reopened", "synchronize"]
        and "*" in pr_list
    )


@app.task(base=JobBase, retry_kwargs={"max_retries": 5}, retry_backoff=True)
def update_github_check(event):
    gitlabclient = GitlabClient()
    checkstatus = CheckStatus(event)
    installation_id = gitlabclient.get_variable(
        checkstatus.project_id, "GITHUB_INSTALLATION_ID"
    )["value"]
    github_repo = gitlabclient.get_variable(checkstatus.project_id, "GITHUB_REPO")[
        "value"
    ]
    githubclient = GithubClient(installation_id=installation_id)

    # Skip queued builds as they could be 'manual'
    if checkstatus.status == "queued" and checkstatus.object_kind == "build":
        return None

    if checkstatus.object_kind == "pipeline":
        githubclient.post_status(
            checkstatus.render_pipeline_status(), github_repo, checkstatus.sha
        )
    return githubclient.create_check(github_repo, checkstatus.render_check())


@app.task(bind=True, base=JobBase)
def pipeline(self, event, headers):
    gevent = GithubEvent(event, headers)
    config = FFCONFIG
    build = Pipeline(gevent, config)
    return build.trigger_pipeline()


@app.task(bind=True, base=JobBase)
def update_github_statuses_failure(self, request, exc, traceback, event, headers):
    """The pipeline has failed. Notify GitHub."""
    gevent = GithubEvent(event, headers)
    githubclient = GithubClient(gevent.installation_id)
    body = dict(
        state=GITHUB_STATUS_MAP["canceled"],
        target_url=(gevent.commit_url),  # TODO: link the gitlab YAML
        description="An error occurred in pipeline execution. %s" % (str(exc)),
        context="%s/%s" % (FFCONFIG.github["context-status"], "pipeline"),
    )
    return githubclient.post_status(body, gevent.repo, gevent.head_sha)


def post_pipeline_status(project, pipeline_attr):
    """
    POST the pipeline status on GitHub
    """
    descriptions = {
        "pending": "Pipeline in-progress",
        "success": "Pipeline success",
        "error": "Pipeline in error or canceled",
        "failure": "Pipeline failed",
    }
    gitlabclient = GitlabClient()
    installation_id = gitlabclient.get_variable(
        project["id"], "GITHUB_INSTALLATION_ID"
    )["value"]
    github_repo = gitlabclient.get_variable(project["id"], "GITHUB_REPO")["value"]

    githubclient = GithubClient(installation_id=installation_id)
    sha = pipeline_attr["sha"]
    context = FFCONFIG.github["context"]
    state = GITHUB_STATUS_MAP[pipeline_attr["status"]]
    pipeline_body = {
        "state": state,
        "target_url": project["web_url"] + "/pipelines/%s" % pipeline_attr["id"],
        "description": descriptions[state],
        "context": "%s/pipeline" % context,
    }
    resync_body = {
        "state": "success",
        "target_url": FFCONFIG.failfast["failfast_url"]
        + "/api/v1/resync/%s/%s" % (project["id"], pipeline_attr["id"]),
        "description": "resync-gitlab status",
        "context": "%s/resync-gitlab" % context,
    }
    githubclient.post_status(resync_body, github_repo, sha)
    return githubclient.post_status(pipeline_body, github_repo, sha)


@app.task(base=JobBase, retry_kwargs={"max_retries": 5}, retry_backoff=True)
def update_pipeline_status(gitlab_project_id, pipeline_id):
    """
    Queries GitLab to get the pipeline status and then update the GitHub statuses
    """
    gitlabclient = GitlabClient()
    project = gitlabclient.get_project(gitlab_project_id)
    pipeline_attr = gitlabclient.get_pipeline_status(gitlab_project_id, pipeline_id)

    return post_pipeline_status(project, pipeline_attr)


@app.task(bind=True, base=JobBase, retry_kwargs={"max_retries": 5}, retry_backoff=True)
def update_pipeline_hook(self, event):
    """
    The job triggered when GitLab POST a webhook
    `Pipeline Hook` and then update GitHub statuses
    """
    logger.info(event)
    pipeline_attr = event["object_attributes"]
    project = event["project"]
    try:
        return post_pipeline_status(project, pipeline_attr)
    except requests.exceptions.RequestException as exc:
        logger.error("Error request")
        raise self.retry(countdown=60, exc=exc)


@app.task(bind=True, base=JobBase, retry_kwargs={"max_retries": 5}, retry_backoff=True)
def retry_build(self, external_id, sha=None):
    project_id = external_id["project_id"]
    object_id = external_id["object_id"]
    kind = external_id["object_kind"]
    gitlabclient = GitlabClient()
    try:
        if kind == "build":
            return gitlabclient.retry_build(project_id, object_id)
        elif kind == "pipeline":
            return gitlabclient.retry_pipeline(project_id, sha)

    except requests.exceptions.RequestException as exc:
        logger.error("Error request")
        raise self.retry(countdown=60, exc=exc)


@app.task(bind=True, base=JobBase, retry_kwargs={"max_retries": 5}, retry_backoff=True)
def skip_check(self, event):
    try:
        check = {
            "status": "completed",
            "conclusion": "neutral",
            "completed_at": CheckStatus.ztime(),
            "actions": CheckStatus.list_task_actions(),
        }

        githubclient = GithubClient(installation_id=event["installation"]["id"])
        return githubclient.update_check_run(
            event["repository"]["full_name"], check, event["check_run"]["id"]
        )
    except requests.exceptions.RequestException as exc:
        logger.error("Error request")
        raise self.retry(countdown=60, exc=exc)


def request_action(action, event):
    if action == "skip":
        return skip_check.s(event)
    if action == "retry":
        return retry_build.s(json.loads(event["check_run"]["external_id"]))
    if action == "resync":
        return resync_action.s(event)


@app.task(bind=True, base=JobBase, retry_kwargs={"max_retries": 5}, retry_backoff=True)
def retry_pipeline(self, event):
    pass


@app.task(bind=True, base=JobBase, retry_kwargs={"max_retries": 5}, retry_backoff=True)
def resync_action(self, event):
    status_mappings = {
        "created": {"status": "requested", "conclusion": None},
        "waiting_for_resource": {
            "status": "requested",
            "conclusion": None,
        },
        "preparing": {
            "status": "requested",
            "conclusion": None,
        },
        "pending": {
            "status": "requested",
            "conclusion": None,
        },
        "running": {
            "status": "in_progress",
            "conclusion": None,
        },
        "success": {
            "status": "completed",
            "conclusion": "success",
        },
        "failed": {
            "status": "completed",
            "conclusion": "failure",
        },
        "canceled": {
            "status": "completed",
            "conclusion": "cancelled",
        },
        "skipped": {
            "status": "completed",
            "conclusion": "neutral",
        },
        "manual": {
            "status": "completed",
            "conclusion": "neutral",
        },
        "scheduled": {
            "status": "requested",
            "conclusion": None,
        },
    }
    try:
        external_id = json.loads(event["check_run"]["external_id"])
        gitlabclient = GitlabClient()
        if external_id["object_kind"] == "pipeline":
            pipeline_attr = gitlabclient.get_pipeline_status(
                external_id["project_id"], external_id["object_id"]
            )
            result = status_mappings[pipeline_attr["status"]]
            project = gitlabclient.get_project(external_id["project_id"])
            post_pipeline_status(project, pipeline_attr)

        elif external_id["object_kind"] == "build":
            job_attr = gitlabclient.get_job(
                external_id["project_id"], external_id["object_id"]
            )
            result = status_mappings[job_attr["status"]]
            if job_attr["status"] == "failed" and job_attr["allow_failure"]:
                result["conclusion"] = "neutral"

        check = {
            "completed_at": CheckStatus.ztime(),
            "actions": CheckStatus.list_task_actions(),
        }
        check.update(result)

        githubclient = GithubClient(installation_id=event["installation"]["id"])
        return githubclient.update_check_run(
            event["repository"]["full_name"], check, event["check_run"]["id"]
        )
    except requests.exceptions.RequestException as exc:
        logger.error("Error request")
        raise self.retry(countdown=60, exc=exc)


def start_pipeline(event, headers):
    """
    start_pipeline is launching the job 'pipeline' if conditions are met.
    The pipeline job clone the github-repo and push it to gitlab
    """
    gevent = GithubEvent(event, headers)
    config = FFCONFIG
    trigger_build = (
        istriggered_on_branches(gevent, config)
        or istriggered_on_pr(gevent, config)
        or istriggered_on_labels(gevent, config)
    )
    if trigger_build:
        task = pipeline.s(event, headers)
        task.link_error(update_github_statuses_failure.s(event, headers))
        return task
    else:
        return None
