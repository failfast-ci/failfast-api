import os
import json
import pytest

from hub2labhook.api.app import create_app


LOCAL_DIR = os.path.dirname(__file__)


@pytest.fixture
def app():
    app = create_app()
    return app


def get_request(name):
    f = open(LOCAL_DIR + "/data/%s.json" % name)
    r = f.read()
    f.close()
    return json.loads(r)


@pytest.fixture()
def push_headers():
    return {"User-Agent": " GitHub-Hookshot/d9ba1f0",
            "X-GITHUB-DELIVERY": "5ca32b80-b638-11e6-8213-373827616e33",
            "X-GITHUB-EVENT": "push"}

@pytest.fixture()
def pr_headers():
    return {"User-Agent": " GitHub-Hookshot/d9ba1f0",
            "X-GITHUB-DELIVERY": "5ca32b80-c638-11e6-8213-373827616e33",
            "X-GITHUB-EVENT": "pull_request"}


@pytest.fixture()
def ping_headers():
    return {"User-Agent": "GitHub-Hookshot/d9ba1f0",
            "X-GITHUB-DELIVERY": "1766f700-b56f-11e6-929b-85ab127f9469",
            "X-GITHUB-EVENT": "ping"}


@pytest.fixture(scope="session")
def ping_data():
    return get_request('ping')


@pytest.fixture(scope="session")
def pr_data():
    return get_request('pull_request')


@pytest.fixture(scope="session")
def push_data():
    return get_request('push')
