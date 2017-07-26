import pytest
from hub2labhook.exception import Unsupported
from hub2labhook.githubevent import GithubEvent


def test_ping_event(ping_data, ping_headers):
    ghe = GithubEvent(ping_data, ping_headers)
    assert ghe.event_type == "ping"
    with pytest.raises(Unsupported):
        assert ghe.ref
    with pytest.raises(Unsupported):
        assert ghe.refname
    with pytest.raises(Unsupported):
        assert ghe.head_sha
    with pytest.raises(Unsupported):
        assert ghe.repo == "ant31/jenkinstest"
    with pytest.raises(Unsupported):
        assert ghe.user


def test_push_event(push_data, push_headers):
    ghe = GithubEvent(push_data, push_headers)
    assert ghe.event_type == "push"
    assert ghe.head_sha == "3af890fa500d855c8a2536b9998e43efb25f1460"
    assert ghe.istag() is False
    assert ghe.ref == "refs/heads/ant31-patch-1"
    assert ghe.refname == "ant31-patch-1"
    assert ghe.repo == "ant31/jenkinstest"
    assert ghe.user == "ant31"


def test_pr_event(pr_data, pr_headers):
    ghe = GithubEvent(pr_data, pr_headers)
    assert ghe.event_type == "pull_request"
    assert ghe.head_sha == "495d0b659a0a78855183135c5d427ce79ac43552"
    assert ghe.istag() is False
    assert ghe.ref == "fix_weave_start"
    assert ghe.refname == "fix_weave_start"
    assert ghe.repo == "kubernetes-incubator/kargo"
    assert ghe.user == "mattymo"
