import hmac
import hashlib
from flask import jsonify, request, Blueprint
from hub2labhook.api.app import getvalues
from hub2labhook.exception import (InvalidUsage, Forbidden, Unsupported)
import hub2labhook.jobs.tasks as tasks

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

    headers = dict(request.headers.to_list())
    task = tasks.start_pipeline(params, headers)
    if task is None:
        return jsonify({'ignored': True})
    job = task.delay()
    return jsonify({'job_id': job.id, 'params': params})


@ffapi_app.route("/api/v1/gitlab_event", methods=['POST', 'GET'],
                 strict_slashes=False)
def gitlab_event():
    params = getvalues()
    headers = dict(request.headers.to_list())
    event = headers.get("X-Gitlab-Event", None)

    if event == "Pipeline Hook":
        task = tasks.update_pipeline_hook
    elif event == "Job Hook":
        pass
    else:
        return jsonify({'ignored': True, 'event': event})
    job = task.delay(params)
    return jsonify({'job_id': job.id, 'params': params})


@ffapi_app.route("/api/v1/resync/<int:gitlab_project_id>/<int:pipeline_id>",
                 methods=['POST', 'GET'], strict_slashes=False)
def resync(gitlab_project_id, pipeline_id):
    task = tasks.update_pipeline_status.apply_async(
        (gitlab_project_id, pipeline_id), )
    resp = task.get()
    # redirect(resp., code=302)
    return jsonify(resp)


@ffapi_app.route("/api/v1/github_status", methods=['POST'],
                 strict_slashes=False)
def github_status():
    params = getvalues()
    # gitlab_project_id = params['gitlab_project_id']
    # gitlab_build_id = params['build_id']
    # github_repo = params['github_repo']
    # sha = params['sha']
    # installation_id = params['installation_id']
    delay = int(params.get('delay', 0))
    job = tasks.update_build_status.apply_async((params, ), countdown=delay)
    return jsonify({'job_id': job.id, 'params': params})


@ffapi_app.route("/api/v1/github_statuses", methods=['POST'],
                 strict_slashes=False)
def github_statuses():
    params = getvalues()
    # gitlab_project_id = params['gitlab_project_id']
    # gitlab_build_id = params['build_id']
    # github_repo = params['github_repo']
    # sha = params['sha']
    # installation_id = params['installation_id']
    delay = int(params.get('delay', 0))
    job = tasks.update_github_statuses.apply_async((params, ), countdown=delay)
    return jsonify({'job_id': job.id, 'params': params})
