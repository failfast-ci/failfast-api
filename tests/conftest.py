import jwt
import base64
import json
import os

import pytest
from ffci.config import GConfig
LOCAL_DIR = os.path.dirname(__file__)


@pytest.fixture(autouse=True)
def mock_jwttoken(monkeypatch):
    def jwttoken(*args, **kwargs):
        return "mocked-token"
    monkeypatch.setattr(jwt, "encode", jwttoken)

@pytest.fixture(autouse=True)
def reset_config():
    GConfig.reinit()
    GConfig()

@pytest.fixture()
def mock_gh_token(aioresponses):
    GConfig.reinit()
    installation_id = GConfig().github.installation_id
    token = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    aioresponses.post(token, status=200, payload={"token": "valid-access-token"})

@pytest.fixture
def app():
    from ffci.api.app import create_app

    app = create_app().app
    return app


def get_request(name):
    f = open(LOCAL_DIR + "/data/%s.json" % name)
    r = f.read()
    f.close()
    return json.loads(r)


@pytest.fixture(scope="session")
def testenv(monkeypatch):
    monkeypatch.setenv("GITHUB_INTEGRATION_PEM", base64.b64encode("fakepem"))


@pytest.fixture()
def push_headers():
    return {
        "User-Agent": " GitHub-Hookshot/d9ba1f0",
        "X-GitHub-Delivery": "5ca32b80-b638-11e6-8213-373827616e33",
        "X-GitHub-Event": "push",
    }


@pytest.fixture()
def pr_headers():
    return {
        "User-Agent": " GitHub-Hookshot/d9ba1f0",
        "X-GitHub-Delivery": "5ca32b80-c638-11e6-8213-373827616e33",
        "X-GitHub-Event": "pull_request",
   }


@pytest.fixture()
def ping_headers():
    return {
        "User-Agent": "GitHub-Hookshot/d9ba1f0",
        "X-GitHub-Delivery": "1766f700-b56f-11e6-929b-85ab127f9469",
        "X-GitHub-Event": "ping",
    }

@pytest.fixture()
def checkrun_headers():
    return {
        "User-Agent": "GitHub-Hookshot/d9ba1f0",
        "X-GitHub-Delivery": "1766f700-b56f-11e6-929b-85ab127f9469",
        "X-GitHub-Event": "check_run",
    }
@pytest.fixture()
def checksuite_headers():
    return {
        "User-Agent": "GitHub-Hookshot/d9ba1f0",
        "X-GitHub-Delivery": "1766f700-b56f-11e6-929b-85ab127f9469",
        "X-GitHub-Event": "check_suite",
    }


@pytest.fixture(scope="session")
def ping_data():
    return get_request("ping")

@pytest.fixture(scope="session")
def checkrun_data():
    return get_request("checkrun")


@pytest.fixture(scope="session")
def checksuite_data():
    return get_request("checksuite")

@pytest.fixture(scope="session")
def pipeline_hook_data():
    return get_request("gitlab/pipeline-hook")


@pytest.fixture(scope="session")
def pipeline_hook2_data():
    return get_request("gitlab/pipeline-hook2")


@pytest.fixture(scope="session")
def build_hook_data():
    return get_request("gitlab/build-hook")


@pytest.fixture(scope="session")
def pr_data():
    return get_request("pull_request")


@pytest.fixture(scope="session")
def push_data():
    return get_request("push")
