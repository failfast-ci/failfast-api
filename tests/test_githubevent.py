import pytest
from hub2labhook.exception import Unsupported
from hub2labhook.githubevent import GithubEvent


def test_ping_event(ping_data, ping_headers):
    ge = GithubEvent(ping_data, ping_headers)
    assert ge.event_type == "ping"
    with pytest.raises(Unsupported):
        assert ge.ref
    with pytest.raises(Unsupported):
        assert ge.refname
    with pytest.raises(Unsupported):
        assert ge.head_sha
    with pytest.raises(Unsupported):
        assert ge.repo =="ant31/jenkinstest"
    with pytest.raises(Unsupported):
        assert ge.user

def test_push_event(push_data, push_headers):
    ge = GithubEvent(push_data, push_headers)
    assert ge.event_type == "push"
    assert ge.head_sha == "3af890fa500d855c8a2536b9998e43efb25f1460"
    assert ge.istag() is False
    assert ge.ref == "refs/heads/ant31-patch-1"
    assert ge.refname == "ant31-patch-1"
    assert ge.repo =="ant31/jenkinstest"
    assert ge.user == "ant31"

def test_pr_event(pr_data, pr_headers):
    ge = GithubEvent(pr_data, pr_headers)
    assert ge.event_type == "pull_request"
    assert ge.head_sha == "aeee076b6504df51a60deab0d119be9a3bcabf9e"
    assert ge.istag() is False
    assert ge.ref == "master"
    assert ge.refname == "pr:ant31/jenkinstest:master"
    assert ge.repo =="ant31/jenkinstest"
    assert ge.user == "ant31"
