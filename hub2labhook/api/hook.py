from flask import jsonify, request, Blueprint, current_app
import os
from hub2labhook.githubevent import GithubEvent
from hub2labhook.pipeline import Pipeline
from hub2labhook.githubclient import GithubClient
from hub2labhook.api.app import getvalues
from hub2labhook.exception import (Hub2LabException,
                                   InvalidUsage,
                                   InvalidParams,
                                   UnauthorizedAccess,
                                   Unsupported)


import hub2labhook.jobs.tasks as tasks


hook_app = Blueprint('registry', __name__,)


@hook_app.before_request
def pre_request_logging():
    jsonbody = request.get_json(force=True, silent=True)
    values = request.values.to_dict()
    if jsonbody:
        values.update(jsonbody)

    current_app.logger.info("request", extra={
        "remote_addr": request.remote_addr,
        "http_method": request.method,
        "original_url": request.url,
        "path": request.path,
        "data":  values,
        "headers": dict(request.headers.to_list())})


@hook_app.errorhandler(Unsupported)
@hook_app.errorhandler(UnauthorizedAccess)
@hook_app.errorhandler(Hub2LabException)
@hook_app.errorhandler(InvalidUsage)
@hook_app.errorhandler(InvalidParams)
def render_error(error):
    response = jsonify({"error": error.to_dict()})
    response.status_code = error.status_code
    return response


@hook_app.route("/test_error")
def test_error():
    raise InvalidUsage("error message", {"path": request.path})


@hook_app.route("/api/v1/github_event", methods=['POST'], strict_slashes=False)
def github_event():
    print("here")
    params = getvalues()
    event = request.headers.get("X-GITHUB-EVENT", "push")
    allowed_events = []
    print(params)
    if os.getenv("BUILD_PULL_REQUEST", "true") == "true":
        allowed_events.append("pull_request")

    if ((os.getenv("BUILD_PUSH", "false") == "true") or
        (event == "push" and
         (params['ref'] == "refs/heads/master" or str.startswith(params['ref'], "refs/tags/")))):
        allowed_events.append("push")

    if ((event not in allowed_events) or
       (event == "pull_request" and params['action'] not in ['opened', 'reopened', 'synchronize'])):
        return jsonify({'ignored': True})

    task = tasks.pipeline.s(params, dict(request.headers.to_list()))
    task.link(tasks.update_github_statuses.s())
    job = task.delay()
    return jsonify({'job_id': job.id, 'params': params})


@hook_app.route("/api/v1/github_status", methods=['POST'], strict_slashes=False)
def github_status():
    params = getvalues()
    # gitlab_project_id = params['gitlab_project_id']
    # gitlab_build_id = params['build_id']
    # github_repo = params['github_repo']
    # sha = params['sha']
    # installation_id = params['installation_id']
    delay = int(params.get('delay', 0))
    job = tasks.update_build_status.apply_async((params,), countdown=delay)
    return jsonify({'job_id': job.id, 'params': params})


@hook_app.route("/api/v1/github_statuses", methods=['POST'], strict_slashes=False)
def github_statuses():
    params = getvalues()
    # gitlab_project_id = params['gitlab_project_id']
    # gitlab_build_id = params['build_id']
    # github_repo = params['github_repo']
    # sha = params['sha']
    # installation_id = params['installation_id']
    delay = int(params.get('delay', 0))
    job = tasks.update_github_statuses.apply_async((params,), countdown=delay)
    return jsonify({'job_id': job.id, 'params': params})
