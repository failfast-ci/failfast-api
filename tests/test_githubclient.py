import base64
from unittest.mock import Mock

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from hub2labhook.github import client


@pytest.fixture(scope="module")
def integration_key():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem, key.public_key()


@pytest.mark.parametrize("integration_id", [12345, "12345"])
def test_jwt_token_issuer_is_string(integration_key, integration_id):
    pem, public_key = integration_key

    token = client.jwt_token(integration_id, pem)
    payload = jwt.decode(
        token, public_key, algorithms=["RS256"], issuer="12345"
    )

    assert isinstance(token, str)
    assert payload["iss"] == "12345"
    assert isinstance(payload["iat"], int)
    assert isinstance(payload["exp"], int)
    assert 60 <= payload["exp"] - payload["iat"] <= 61


def test_github_client_fetches_and_caches_installation_token(
    monkeypatch, integration_key
):
    pem, public_key = integration_key
    monkeypatch.setenv(
        "GITHUB_INTEGRATION_PEM", base64.b64encode(pem).decode("ascii")
    )
    monkeypatch.setattr(client, "INTEGRATION_ID", 12345)
    response = Mock()
    response.json.return_value = {"token": "test-installation-token"}

    def post(url, headers):
        assert url == "https://api.github.com/app/installations/67890/access_tokens"
        scheme, token = headers["Authorization"].split(" ", 1)
        assert scheme == "Bearer"
        payload = jwt.decode(
            token, public_key, algorithms=["RS256"], issuer="12345"
        )
        assert payload["iss"] == "12345"
        return response

    post_mock = Mock(side_effect=post)
    monkeypatch.setattr(client.requests, "post", post_mock)
    github_client = client.GithubClient(installation_id=67890)

    assert github_client.headers()["Authorization"] == "token test-installation-token"
    assert github_client.headers()["Authorization"] == "token test-installation-token"
    assert post_mock.call_count == 1
    response.raise_for_status.assert_called_once_with()
