import time
import logging
from flask import request
import hub2labhook


def default_filter(_):
    return '[FILTERED]'


FILTERED_VALUES = [{'key': ['password'], 'fn': default_filter}]
logger = logging.getLogger(__name__)


def filter_logs(values, filtered_fields):
    """
    Takes a dict and a list of keys to filter.
    eg:
     with filtered_fields:
        [{'key': ['k1', k2'], 'fn': lambda x: 'filtered'}]
     and values:
       {'k1': {'k2': 'some-secret'}, 'k3': 'some-value'}
    the returned dict is:
      {'k1': {k2: 'filtered'}, 'k3': 'some-value'}
  """
    for field in filtered_fields:
        cdict = values

        for key in field['key'][:-1]:
            if key in cdict:
                cdict = cdict[key]

        last_key = field['key'][-1]

        if last_key in cdict and cdict[last_key]:
            cdict[last_key] = field['fn'](cdict[last_key])


def after_request_log(resp):
    jsonbody = request.get_json(force=True, silent=True)
    values = request.values.to_dict()

    if jsonbody and not isinstance(jsonbody, dict):
        jsonbody = {'_parsererror': jsonbody}

    if isinstance(values, dict):
        filter_logs(values, FILTERED_VALUES)

    extra = {
        "endpoint": request.endpoint,
        "remote_addr": request.remote_addr,
        "http_method": request.method,
        "original_url": request.url,
        "headers": dict(request.headers.to_list()),
        "path": request.path,
        "parameters": values,
        "response_time": request.request_time(),
        "json_body": jsonbody,
        "version": "%s/%s" % (hub2labhook.__version__, hub2labhook.__gitsha__),
    }

    if request.user_agent is not None:
        extra["user-agent"] = request.user_agent.string

    logger.info("request-end", extra=extra)

    logger.debug('Ending request: %s', request.path)
    return resp


def before_request_log():
    request.request_start_time = time.time()
    request.request_time = lambda: "%.3f" % ((time.time() - request.
                                              request_start_time) * 1000)
