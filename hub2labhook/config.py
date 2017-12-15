"""
Acquire runtime configuration from environment variables (etc).
"""

import os


def logfile_path(jsonfmt=False, debug=False):
    """
    Returns the a logfileconf path following this rules:
      - conf/logging_debug_json.conf # jsonfmt=true,  debug=true
      - conf/logging_json.conf       # jsonfmt=true,  debug=false
      - conf/logging_debug.conf      # jsonfmt=false, debug=true
      - conf/logging.conf            # jsonfmt=false, debug=false
    Can be parametrized via envvars: JSONLOG=true, DEBUGLOG=true
  """
    _json = ""
    _debug = ""

    if jsonfmt or os.getenv('JSONLOG', 'false').lower() == 'true':
        _json = "_json"

    if debug or os.getenv('DEBUGLOG', 'false').lower() == 'true':
        _debug = "_debug"

    return os.path.join(FFCI_CONF_DIR, "logging%s%s.conf" % (_debug, _json))


def getenv(name, default=None, convert=str):
    """
    Fetch variables from environment and convert to given type.

    Python's `os.getenv` returns string and requires string default.
    This allows for varying types to be interpolated from the environment.
    """

    # because os.getenv requires string default.
    internal_default = "(none)"
    val = os.getenv(name, internal_default)

    if val == internal_default:
        return default

    if callable(convert):
        return convert(val)

    return val


def envbool(value: str):
    return value and (value.lower() in ('1', 'true'))


GITLAB_TIMEOUT = 30

APP_ENVIRON = getenv("APP_ENV", "development")

# Events from GitLab hooks will be authenticated with this token.
GITLAB_SECRET_TOKEN_DEFAULT = "e19c1283c925b3206685ff522acfe3e6"
GITLAB_SECRET_TOKEN = getenv("GITLAB_TOKEN", GITLAB_SECRET_TOKEN_DEFAULT)

GITLAB_API = getenv("GITLAB_API", "https://gitlab.com")
GITLAB_REPO = getenv("GITLAB_REPO", None)
GITLAB_BRANCH = getenv("GITLAB_BRANCH", None)
GITLAB_TRIGGER = getenv("GITLAB_TRIGGER", None)
GITLAB_USER = getenv("GITLAB_USER", None)
GITLAB_ENABLE_JOBS = True  # without this, CI is moot.

GITLAB_ENABLE_SHARED_RUNNERS = getenv("GITLAB_SHARED_RUNNERS", default=False,
                                      convert=envbool)

GITLAB_ENABLE_CONTAINER_REGISTRY = getenv("GITLAB_CONTAINER_REGISTRY",
                                          default=False, convert=envbool)

GITLAB_ENABLE_WIKI = getenv("GITLAB_WIKI", default=False, convert=envbool)
GITLAB_ENABLE_SNIPPETS = getenv("GITLAB_SNIPPETS", default=False,
                                convert=envbool)

GITLAB_ENABLE_MERGE_REQUESTS = getenv("GITLAB_MERGE_REQUESTS", default=False,
                                      convert=envbool)
GITLAB_ENABLE_ISSUES = getenv("GITLAB_ISSUES", default=False, convert=envbool)

GITLAB_REPO_PRIVACY = getenv("GITLAB_REPO_PRIVACY", default="internal")

if GITLAB_REPO_PRIVACY not in ("private", "internal", "public"):
    GITLAB_REPO_PRIVACY = "private"

GITHUB_CONTEXT = getenv("GITHUB_CONTEXT", "gitlab-ci")
GITHUB_INTEGRATION_ID = getenv("GITHUB_INTEGRATION_ID", "743")
GITHUB_INSTALLATION_ID = getenv("GITHUB_INSTALLATION_ID", "3709")
GITHUB_SECRET_TOKEN = getenv("GITHUB_SECRET_TOKEN", None)

FAILFASTCI_NAMESPACE = getenv("FAILFASTCI_NAMESPACE", "failfast-ci")
FAILFASTCI_API = getenv("FAILFAST_CI_API", "https://jobs.failfast-ci.io")

# The GitLab runner tag to require on CI jobs introduced by failfast
FAILFASTCI_REQUIRE_RUNNER_TAG = getenv("FAILFASTCI_RUNNER_TAG", "failfast-ci")

if FAILFASTCI_REQUIRE_RUNNER_TAG.lower() in ('none', ):
    FAILFASTCI_REQUIRE_RUNNER_TAG = None

BUILD_PULL_REQUEST = getenv("BUILD_PULL_REQUEST", "true")
BUILD_PUSH = getenv("BUILD_PUSH", "false")

FFCI_SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
FFCI_ROOT_DIR = os.path.abspath(os.path.join(FFCI_SOURCE_DIR, "../"))
FFCI_CONF_DIR = os.getenv("FFCI_CONF_DIR", os.path.join(
    FFCI_ROOT_DIR, "conf/"))
