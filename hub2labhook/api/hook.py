from flask import jsonify, request, Blueprint, current_app
from hub2labhook.api.app import getvalues
from hub2labhook.exception import (Hub2LabException,
                                   InvalidUsage,
                                   InvalidParams,
                                   UnauthorizedAccess,
                                   Unsupported)


hook_app = Blueprint('registry', __name__,)


@hook_app.errorhandler(Unsupported)
@hook_app.errorhandler(UnauthorizedAccess)
@hook_app.errorhandler(Hub2LabException)
@hook_app.errorhandler(InvalidUsage)
@hook_app.errorhandler(InvalidParams)
def render_error(error):
    response = jsonify({"error": error.to_dict()})
    response.status_code = error.status_code
    return response


def repo_name(namespace, name):
    def _check(name, scope):
        if name is None:
            raise InvalidUsage("%s: %s is malformed" % (scope, name), {'name': name})
    _check(namespace, 'namespace')
    _check(name, 'package-name')
    return "%s/%s" % (namespace, name)


@hook_app.route("/test_error")
def test_error():
    raise InvalidUsage("error message", {"path": request.path})


@hook_app.route("/api/v1/github_event", methods=['POST'], strict_slashes=False)
def github_event():
    params = getvalues()
