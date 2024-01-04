#!/usr/bin/env python3
from datetime import datetime
import aiohttp

import pytest
from ffci.github.models import GithubEventPullRequest, GithubEventPush, github_event_factory, GithubBaseEvent, GithubHeaders, GithubEventPing, CreateGithubCheckRun, GithubCheckRun, UpdateGithubCheckRun, GithubEventCheckRun, GithubEventChecksuite
from ffci.clients import GGithubClient

def test_factory_ping(ping_data, ping_headers):
    ghe = GithubBaseEvent.model_validate(ping_data)
    ghe._headers = GithubHeaders.model_validate(ping_headers)
    ghe_ping = github_event_factory(ghe)
    assert isinstance(ghe_ping, GithubEventPing)

def test_factory_push(push_data, push_headers):
    ghe = GithubBaseEvent.model_validate(push_data)
    ghe._headers = GithubHeaders.model_validate(push_headers)
    ghe_model = github_event_factory(ghe)
    assert isinstance(ghe_model, GithubEventPush)

def test_factory_pr(pr_data, pr_headers):
    ghe = GithubBaseEvent.model_validate(pr_data)
    ghe._headers = GithubHeaders.model_validate(pr_headers)
    ghe_model = github_event_factory(ghe)
    assert isinstance(ghe_model, GithubEventPullRequest)

def test_factory_check_run(checkrun_data, checkrun_headers):
    ghe = GithubBaseEvent.model_validate(checkrun_data)
    ghe._headers = GithubHeaders.model_validate(checkrun_headers)
    ghe_model = github_event_factory(ghe)
    assert isinstance(ghe_model, GithubEventCheckRun)

def test_factory_check_suite(checksuite_data, checksuite_headers):
    ghe = GithubBaseEvent.model_validate(checksuite_data)
    ghe._headers = GithubHeaders.model_validate(checksuite_headers)
    ghe_model = github_event_factory(ghe)
    assert isinstance(ghe_model, GithubEventChecksuite)

def test_factory_unknown(checksuite_data, checksuite_headers):
    ghe = GithubBaseEvent.model_validate(checksuite_data)
    ghe._headers = GithubHeaders.model_validate(checksuite_headers)
    ghe._headers.x_github_event = "unknown"
    with pytest.raises(NotImplementedError):
        github_event_factory(ghe)


@pytest.mark.asyncio
async def test_get_token(mock_gh_token):
    _ = mock_gh_token
    client = GGithubClient()
    token = await client.get_token()
    assert token == "valid-access-token"

@pytest.mark.asyncio
async def test_headers(mock_gh_token):
    _ = mock_gh_token
    client = GGithubClient()
    headers = await client.headers()
    assert headers['Authorization'] == "token valid-access-token"

@pytest.mark.asyncio
async def test_create_check_run(aioresponses, mock_gh_token):
    _ = mock_gh_token
    github_repo = "ant31/ffci"
    path = f"https://api.github.com/repos/{github_repo}/check-runs"
    aioresponses.post(path, status=200, body=GithubCheckRun(name="test", head_sha="1234", status="in_progress", started_at=datetime.fromisoformat("2021-01-01T00:00:00Z"), id=3).model_dump_json())
    client = GGithubClient()
    body = CreateGithubCheckRun(name="test",
                                head_sha="1234",
                                status="in_progress",
                                started_at=datetime.fromisoformat("2021-01-01T00:00:00Z"),
                                )

    resp = await client.create_check(github_repo=github_repo, check_body=body)
    assert resp.name == "test"
    assert resp.id == 3

@pytest.mark.asyncio
async def test_update_check_run(aioresponses, mock_gh_token):
    _ = mock_gh_token
    github_repo = "ant31/ffci"
    path = f"https://api.github.com/repos/{github_repo}/check-runs/3"
    aioresponses.patch(path, status=200, body=GithubCheckRun(name="test", head_sha="1234", status="in_progress", started_at=datetime.fromisoformat("2021-01-01T00:00:00Z"), id=3).model_dump_json())
    client = GGithubClient()
    body = UpdateGithubCheckRun(name="test",
                                status="completed",
                                started_at=datetime.fromisoformat("2021-01-01T00:00:00Z"),
                                )

    resp = await client.update_check_run(github_repo=github_repo, check_body=body, check_id=3)
    assert resp.name == "test"
    assert resp.id == 3

@pytest.mark.asyncio
async def test_get_ci_file(aioresponses, mock_gh_token):
    _ = mock_gh_token
    github_repo = "ant31/ffci"
    ref = "1234"
    path = f"https://api.github.com/repos/{github_repo}/contents/.gitlab-ci.yml?ref={ref}"
    aioresponses.get(path, status=200, payload={"content": "dGVzdA==", "encoding": "base64"})
    client = GGithubClient()
    resp = await client.get_ci_file(source_repo=github_repo, ref=ref)
    assert resp == {"content": b"test", "file": ".gitlab-ci.yml"}

@pytest.mark.asyncio
async def test_get_ci_file_not_found(aioresponses, mock_gh_token):
    _ = mock_gh_token
    github_repo = "ant31/ffci"
    ref = "1234"

    path = f"https://api.github.com/repos/{github_repo}/contents/.gitlab-ci.yml?ref={ref}"
    path2 = f"https://api.github.com/repos/{github_repo}/contents/.failfast-ci.jsonnet?ref={ref}"
    aioresponses.get(path, status=404, payload={})
    aioresponses.get(path2, status=500, payload={})
    client = GGithubClient()
    with pytest.raises(aiohttp.ClientResponseError) as excinfo:
        await client.get_ci_file(source_repo=github_repo, ref=ref)
        assert excinfo.value.status == 500
    aioresponses.get(path, status=404, payload={})
    aioresponses.get(path2, status=404, payload={})
    with pytest.raises(aiohttp.ClientResponseError) as excinfo:
        await client.get_ci_file(source_repo=github_repo, ref=ref)
        assert excinfo.value.status == 404

def test_jwt_token(mock_jwttoken):
    client = GGithubClient()
    token = client.jwt_token()
    assert token == "mocked-token"

async def test_close_session():
    client = GGithubClient()
    assert client.session.closed is False
    await client.close()
    assert client.session.closed
    await GGithubClient.reinit()

async def test_close_session_reinit():
    await GGithubClient.reinit()
    client = GGithubClient()
    assert client.session.closed is False
    await client.close()
    assert client.session.closed is True
    await GGithubClient.reinit()
    client = GGithubClient()
    assert client.session.closed is False
    await GGithubClient.close()
    assert client.session.closed is True
    assert GGithubClient().session.closed is False

@pytest.mark.xfail
@pytest.mark.asyncio
async def test_post_status(aioresponses, mock_gh_token):
    _ = mock_gh_token
    github_repo = "ant31/ffci"
    ref = "1234"
    path = f"https://api.github.com/repos/{github_repo}/commits/{ref}/statuses"
    aioresponses.post(path, status=200, payload={"test": "test"})
    client = GGithubClient()
    resp = await client.post_status(github_repo=github_repo, sha=ref, body={"test": "test"})
    assert resp["test"] == "test"
    pytest.fail("Not implemented with pydantic")

# def test_ping_event(ping_data, ping_headers):
#     ghe = GithubEvent(ping_data, ping_headers)
#     assert ghe.event_type == "ping"
#     with pytest.raises(Unsupported):
#         assert ghe.ref
#     with pytest.raises(Unsupported):
#         assert ghe.refname
#     with pytest.raises(Unsupported):
#         assert ghe.head_sha
#     with pytest.raises(Unsupported):
#         assert ghe.repo == "ant31/jenkinstest"
#     with pytest.raises(Unsupported):
#         assert ghe.user


# def test_push_event(push_data, push_headers):
#     ghe = GithubEvent(push_data, push_headers)
#     assert ghe.event_type == "push"
#     assert ghe.head_sha == "3af890fa500d855c8a2536b9998e43efb25f1460"
#     assert ghe.istag() is False
#     assert ghe.ref == "refs/heads/ant31-patch-1"
#     assert ghe.refname == "ant31-patch-1"
#     assert ghe.repo == "ant31/jenkinstest"
#     assert ghe.user == "ant31"


# def test_pr_event(pr_data, pr_headers):
#     ghe = GithubEvent(pr_data, pr_headers)
#     assert ghe.event_type == "pull_request"
#     assert ghe.head_sha == "495d0b659a0a78855183135c5d427ce79ac43552"
#     assert ghe.istag() is False
#     assert ghe.ref == "fix_weave_start"
#     assert ghe.refname == "fix_weave_start"
#     assert ghe.repo == "kubernetes-incubator/kargo"
#     assert ghe.user == "mattymo"
