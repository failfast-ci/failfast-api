import hmac
import hashlib
from flask import jsonify, request, Blueprint
from hub2labhook.api.app import getvalues
from hub2labhook.exception import (InvalidUsage, Forbidden, Unsupported)
import hub2labhook.jobs.tasks as tasks
from hub2labhook.github.models.event import GithubEvent
from hub2labhook.config import FFCONFIG

ffapi_app = Blueprint(
    'ffapi',
    __name__,
)  # type: Blueprint


@ffapi_app.route("/test_error")
def test_error():
    raise InvalidUsage("error message", {"path": request.path})


def verify_signature(payload_body, signature):
    secret_token = FFCONFIG.github.get('secret_token', None)
    if secret_token is None:
        raise Unsupported(
            "GITHUB_SECRET_TOKEN isn't configured, failed to verify signature")
    digest = 'sha1=' + hmac.new(secret_token.encode(), payload_body,
                                hashlib.sha1).hexdigest()

    if not hmac.compare_digest(signature, digest):
        raise Forbidden("Signature mismatch expected %s but got %s" %
                        (signature, digest), {
                            "signature": signature
                        })
    return True


@ffapi_app.route("/api/v1/github_event", methods=['POST'],
                 strict_slashes=False)
def github_event():
    params = getvalues()
    hook_signature = request.headers.get("X-Hub-Signature", None)

    if hook_signature:
        verify_signature(request.data, hook_signature)

    headers = dict(request.headers)
    gevent = GithubEvent(params, headers)
    job = None
    if gevent.event_type == "check_run" and gevent.action == "rerequested":
        job = tasks.retry_build.delay(gevent.external_id, gevent.head_sha)
    elif gevent.event_type == "check_run" and gevent.action == "requested_action":
        job = tasks.request_action(
            gevent.event['requested_action']['identifier'], params)
        if job is not None:
            job.delay()
    elif gevent.event_type == "check_suite" and gevent.action == "rerequested":
        headers['X-GITHUB-EVENT'] = "pull_request"
        headers['X-GITHUB-PREV-EVENT'] = "check_suite"
        params['prev_action'] = params['action']
        params['action'] = 'synchronize'
        job = tasks.prep_retry_check_suite.s(params) | tasks.pipeline.s(headers)
        job.delay()
    # elif gevent.event_type == "issue_comment":
    #     gevent["body"] == "/retest"
    #     job = tasks.prep_retry_comment.s(params, link=tasks.pipeline.s(headers))
    #     job.link_error(tasks.update_github_statuses_failure.s(params, headers))
    #     job.delay()
    elif gevent.event_type in ["push", "pull_request"]:
        job = tasks.start_pipeline(params, headers)
        if job is not None:
            job.delay()
    if job is None:
        return jsonify({'ignored': True, 'event': params, 'headers': headers})
    return jsonify({'job_id': job.id, 'params': params})


@ffapi_app.route("/api/v1/gitlab_event", methods=['POST', 'GET'],
                 strict_slashes=False)
def gitlab_event():
    params = getvalues()
    headers = dict(request.headers)
    event = headers.get("X-Gitlab-Event", None)

    if event in "Pipeline Hook":
        task = tasks.update_github_check
    elif event == "Job Hook":
        task = tasks.update_github_check
    else:
        return jsonify({'ignored': True, 'event': event, 'headers': headers})
    job = task.delay(params)
    return jsonify({'job_id': job.id, 'params': params})


@ffapi_app.route("/api/v1/resync/<int:gitlab_project_id>/<int:pipeline_id>",
                 methods=['POST', 'GET'], strict_slashes=False)
def resync(gitlab_project_id, pipeline_id):
    '''
    Force a update of the github statuses.
    It queries gitlab to receive the pipeline status, and update github statuses
    '''
    task = tasks.update_pipeline_status.apply_async(
        (gitlab_project_id, pipeline_id), )
    resp = task.get()
    # redirect(resp., code=302)
    return jsonify(resp)
