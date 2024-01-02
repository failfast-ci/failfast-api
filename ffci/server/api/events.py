#!/usr/bin/env python3
# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods
import logging
import uuid

from aiohttp.client_exceptions import ClientConnectorError, ClientResponseError
from fastapi import APIRouter, Request

from ffci.config import GConfig
from ffci.models import AnyJSON, AsyncResponse, Job
from ffci.server.exception import Unexpected
from ffci.temporal.workflows import CaseWorkflowInput, EngineCaseWorkflow

from . import tclient

# from ffci.temporal.workflows import GiroCaseWorkflow, GiroCaseWorkflowInput

router = APIRouter(
    prefix="/api/v1",
    tags=["ffci", "v1", "events"],
)
logger = logging.getLogger(__name__)


def verify_signature(payload_body, signature):
    secret_token = FFCONFIG.github.get("secret_token", None)
    if secret_token is None:
        raise Unsupported(
            "GITHUB_SECRET_TOKEN isn't configured, failed to verify signature"
        )
    digest = (
        "sha1="
        + hmac.new(secret_token.encode(), payload_body, hashlib.sha1).hexdigest()
    )

    if not hmac.compare_digest(signature, digest):
        raise Forbidden(
            "Signature mismatch expected %s but got %s" % (signature, digest),
            {"signature": signature},
        )
    return True


@router.post("/github_event", response_model=AsyncResponse)
def github_event(
    request: Request,
    x_hub_signature: Annotated[str | None, Header()] = None,
    x_github_event: Annotated[str | None, Header()] = None,
) -> AsyncResponse:
    params: AnyJSON = request.json()

    if x_hub_signature:
        verify_signature(request.body(), h_hub_signature)

    headers = dict(request.headers.to_list())
    gevent = GithubEvent(params, x_github_event)
    if gevent.event_type == "check_run" and gevent.action == "rerequested":
        job = tasks.retry_build.delay(gevent.external_id, gevent.head_sha)
    elif gevent.event_type == "check_run" and gevent.action == "requested_action":
        job = tasks.request_action(
            gevent.event["requested_action"]["identifier"], params
        ).delay()
    elif gevent.event_type == "check_suite" and gevent.action == "rerequested":
        job = tasks.retry_pipeline.delay()
    elif gevent.event_type in ["push", "pull_request"]:
        job = tasks.start_pipeline(params, headers).delay()
    else:
        return jsonify({"ignored": True, "event": params, "headers": headers})

    return jsonify({"job_id": job.id, "params": params})


@ffapi_app.route("/api/v1/gitlab_event", methods=["POST", "GET"], strict_slashes=False)
def gitlab_event():
    params = getvalues()
    headers = dict(request.headers.to_list())
    event = headers.get("X-Gitlab-Event", None)

    if event in "Pipeline Hook":
        task = tasks.update_github_check
    elif event == "Job Hook":
        task = tasks.update_github_check
    else:
        return jsonify({"ignored": True, "event": event, "headers": headers})
    job = task.delay(params)
    return jsonify({"job_id": job.id, "params": params})


@ffapi_app.route(
    "/api/v1/resync/<int:gitlab_project_id>/<int:pipeline_id>",
    methods=["POST", "GET"],
    strict_slashes=False,
)
def resync(gitlab_project_id, pipeline_id):
    """
    Force a update of the github statuses.
    It queries gitlab to receive the pipeline status, and update github statuses
    """
    task = tasks.update_pipeline_status.apply_async(
        (gitlab_project_id, pipeline_id),
    )
    resp = task.get()
    # redirect(resp., code=302)
    return jsonify(resp)
