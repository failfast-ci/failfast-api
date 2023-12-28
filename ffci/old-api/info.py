import time
import logging

from flask import (jsonify, Blueprint, current_app, url_for)
from ffci.exception import Forbidden
import ffci

info_app = Blueprint(
    'info',
    __name__,
)

logger = logging.getLogger(__name__)


@info_app.route("/")
def index():
    return version()


@info_app.route("/error")
def gen_error():
    raise Forbidden("test")


@info_app.route("/slow")
def slow_req():
    time.sleep(5)
    return jsonify({"ok": 200})


@info_app.route("/version")
def version():
    return jsonify({"ffci-api": ffci.__version__})


@info_app.route("/routes")
def routes():
    import urllib
    output = []
    for rule in current_app.url_map.iter_rules():
        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)
        methods = ','.join(rule.methods)
        url = url_for(rule.endpoint, **options)
        line = urllib.parse.unquote("{:50s} {:20s} {}".format(
            rule.endpoint, methods, url))
        output.append(line)
    lines = []
    for line in sorted(output):
        lines.append(line)
    return jsonify({"routes": lines})
