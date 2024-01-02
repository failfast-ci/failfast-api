import asyncio
import base64
import datetime
import logging
from typing import Any, Literal
from urllib.parse import ParseResult, urlparse

import aiohttp
import jwt
import requests
from aiohttp_prometheus_exporter.trace import PrometheusTraceConfig

from ffci.config import GConfig
from ffci.server.exception import ResourceNotFound
from ffci.version import VERSION

logger = logging.getLogger(__name__)

GITHUB_STATUS_MAP = {
    "failed": "failure",
    "success": "success",
    "skipped": "success",
    "unknown": "error",
    "manual": "success",
    "canceled": "error",
    "pending": "pending",
    "created": "pending",
    "running": "pending",
    "warning": "success",
}

# success, failure, neutral, cancelled, timed_out, or action_required. When the conclusion is action_required
GITHUB_CHECK_MAP = {
    "allow_failure": "neutral",
    "failed": "failure",
    "success": "success",
    "skipped": "success",
    "unknown": "failure",
    "manual": "action_required",
    "canceled": "cancelled",
    "pending": "queued",
    "created": None,  # manual -> ignore
    "running": "in_progress",
    "warning": "neutral",
}


def icon_url(icon):
    return "https://s3.conny.dev/public/icons-failfast/%s.png" % icon


GITHUB_CHECK_ICONS = {
    "allow_failure": icon_url("warning"),
    "failed": icon_url("failed2"),
    "success": icon_url("happy-agnes-icon_43743"),
    "skipped": icon_url("skip"),
    "unknown": icon_url("failed2"),
    "manual": icon_url("play"),
    "canceled": icon_url("cancel"),
    "pending": icon_url("waiting"),
    "created": icon_url("waiting"),
    "running": icon_url("running"),
    "warning": icon_url("warning"),
}


def jwt_token(integration_id: int, integration_pem: bytes) -> str:
    payload = {
        "iat": datetime.datetime.utcnow(),
        "exp": (datetime.datetime.utcnow() + datetime.timedelta(seconds=60)),
        "iss": integration_id,
    }
    return jwt.encode(payload, integration_pem, algorithm="RS256")


class BaseClient:
    session: aiohttp.ClientSession
    verify_tls: bool

    def __init__(
        self, endpoint: str, client_name: str = "client", requests_verify: bool = True
    ) -> None:
        self.endpoint: ParseResult = self._configure_endpoint(endpoint)
        self._headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": f"ffci-cli/{client_name}-{VERSION.app_version}",
        }
        self.verify_tls = requests_verify
        self.session = aiohttp.ClientSession(
            trace_configs=[PrometheusTraceConfig(client_name=client_name)]
        )

    def __del__(self):
        asyncio.shield(self.session.close())

    @property
    def ssl_mode(self) -> bool | None:
        return None if self.verify_tls else False

    # pylint: disable=too-many-arguments
    async def log_request(
        self,
        path: str,
        params: dict[str, Any],
        body: dict[str, Any],
        method: str,
        headers: dict[str, str],
        resp: aiohttp.ClientResponse,
    ) -> None:
        raw = await resp.text()
        logger.debug(
            {
                "query": {
                    "params": params,
                    "body": body,
                    "path": path,
                    "method": method,
                    "headers": headers,
                },
                "response": {"status": resp.status, "raw": raw},
            }
        )

    def _url(self, path) -> str:
        """Construct the url from a relative path"""
        return self.endpoint.geturl() + path

    def _configure_endpoint(self, endpoint: str) -> ParseResult:
        return urlparse(endpoint)

    def headers(
        self,
        content_type: Literal["json", "form"] = "json",
        extra: dict[str, str] | None = None,
    ) -> dict[str, str]:
        headers: dict[str, str] = {}
        headers.update(self._headers)

        if content_type == "json":
            headers["Content-Type"] = "application/json"
        elif content_type == "form":
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        if extra:
            headers.update(extra)

        return headers


class GithubClient(BaseClient):
    def __init__(self, installation_id: int) -> None:
        super().__init__("https://api.github.com")
        self.installation_id = installation_id
        self._token: str = ""
        integration_pem_b64 = GConfig().github.integration_pem
        self.integration_pem: bytes = base64.b64decode(integration_pem_b64)
        self._integration_id: int = GConfig().github.integration_id

    def headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.machine-man-preview+json",
            "Authorization": f"token {self.get_token()}",
        }
        if extra is not None:
            headers.update(extra)
        return super().headers("json", extra=headers)

    async def get_token(self):
        if not self._token:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/vnd.github.machine-man-preview+json",
                "User-Agent": "ffci: %s" % VERSION.app_version,
                "Authorization": "Bearer %s"
                % jwt_token(self._integration_id, self.integration_pem),
            }
            path = self._url(f"/app/installations/{self.installation_id}/access_tokens")
            resp = await self.session.post(
                path,
                headers=headers,
                ssl=None if self.verify_tls else False,
            )
            await self.log_request(
                path=path,
                params={},
                body={},
                method="POST",
                headers=headers,
                resp=resp,
            )

            resp.raise_for_status()
            self._token = (await resp.json())["token"]
        return self._token

    async def post_status(
        self, body: dict[str, Any], github_repo: str, sha: str
    ) -> dict[str, Any]:
        path = self._url(f"/repos/{github_repo}/commits/{sha}/statuses")
        headers = self.headers()
        resp = await self.session.post(
            path,
            json=body,
            headers=headers,
            ssl=self.ssl_mode,
            timeout=15,
        )
        await self.log_request(
            path=path,
            params={},
            body={},
            method="POST",
            headers=headers,
            resp=resp,
        )

        resp.raise_for_status()
        return await resp.json()

    async def fetch_file(self, repo: str, file_path: str, ref: str = "master") -> bytes:
        path = self._url(f"/repos/{repo}/contents/{file_path}")
        params: dict[str, str] = {"ref": ref}
        headers = self.headers()
        resp = await self.session.get(
            path, ssl=self.ssl_mode, params=params, headers=headers, timeout=30
        )
        await self.log_request(
            path=path,
            params=params,
            body={},
            method="GET",
            headers=headers,
            resp=resp,
        )
        resp.raise_for_status()
        content = await resp.json()
        filecontent = content["content"]
        if content["encoding"] == "base64":
            filecontent = base64.b64decode(filecontent)
        return filecontent

    async def get_ci_file(self, source_repo: str, ref: str) -> dict[str, Any] | None:
        content = None
        for filepath in [".gitlab-ci.yml", ".failfast-ci.jsonnet"]:
            try:
                content = await self.fetch_file(source_repo, filepath, ref=ref)
                return {"content": content, "file": filepath}
            except requests.exceptions.HTTPError as e:
                if e.response and e.response.status_code != 404:
                    raise e
        if content is None:
            raise ResourceNotFound("no .gitlab-ci.yml or .failfail-ci.jsonnet")
        return None

    async def get_checks(self, github_repo: str, sha: str) -> dict[str, Any]:
        path = self._url(f"/repos/{github_repo}/commits/{sha}/check-runs")
        headers = self.headers(
            extra={"Accept": "application/vnd.github.antiope-preview+json"}
        )
        resp = await self.session.get(
            path, params={}, headers=headers, ssl=self.ssl_mode, timeout=30
        )
        await self.log_request(
            path=path,
            params={},
            body={},
            method="GET",
            headers=headers,
            resp=resp,
        )

        resp.raise_for_status()
        return await resp.json()

    async def create_check(
        self, github_repo: str, check_body: dict[str, Any]
    ) -> dict[str, Any]:
        path = self._url(f"/repos/{github_repo}/check-runs")
        headers = self.headers(
            extra={"Accept": "application/vnd.github.antiope-preview+json"}
        )
        resp = await self.session.post(
            path, json=check_body, headers=headers, ssl=self.ssl_mode, timeout=30
        )

        await self.log_request(
            path=path,
            params={},
            body=check_body,
            method="POST",
            headers=headers,
            resp=resp,
        )
        resp.raise_for_status()
        return await resp.json()

    async def update_check_run(
        self, github_repo: str, check_body: dict[str, Any], check_id: str
    ) -> dict[str, Any]:
        path = self._url(f"/repos/{github_repo}/check-runs/{check_id}")
        headers = self.headers(
            extra={"Accept": "application/vnd.github.antiope-preview+json"}
        )
        resp = await self.session.patch(
            path, json=check_body, headers=headers, ssl=self.ssl_mode, timeout=30
        )

        await self.log_request(
            path=path,
            params={},
            body=check_body,
            method="PATCH",
            headers=headers,
            resp=resp,
        )
        resp.raise_for_status()

        return await resp.json()
