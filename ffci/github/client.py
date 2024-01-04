import base64
import datetime
import logging
from typing import Any

import jwt
import aiohttp

from ffci.client_base import BaseClient
from ffci.github.models import UpdateGithubCheckRun, GithubCheckRun, CreateGithubCheckRun


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
        "iat": datetime.datetime.now(datetime.UTC),
        "exp": (datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=60)),
        "iss": integration_id,
    }
    return jwt.encode(payload, integration_pem, algorithm="RS256")


class GithubClient(BaseClient):
    def __init__(self, *, installation_id: int, integration_id: int, integration_pem_b64: str) -> None:
        super().__init__(endpoint="https://api.github.com", client_name="gh")
        self.installation_id = installation_id
        self._token: str = ""
        self.integration_pem: bytes = base64.b64decode(integration_pem_b64)
        self.integration_id: int = integration_id

    def jwt_token(self):
        return jwt_token(self.integration_id, self.integration_pem)

    async def headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.machine-man-preview+json",
            "Authorization": f"token {await self.get_token()}",
        }
        if extra is not None:
            headers.update(extra)
        return super().headers("json", extra=headers)

    async def get_token(self):
        if not self._token:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/vnd.github+json",
                "User-Agent": "ffci: %s" % VERSION.app_version,
                "Authorization": "Bearer %s"
                % jwt_token(self.integration_id, self.integration_pem),
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
        headers = await self.headers()
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
        headers = await self.headers()
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
        last_exception: aiohttp.ClientResponseError | None = None
        for filepath in [".gitlab-ci.yml", ".failfast-ci.jsonnet"]:
            try:
                content = await self.fetch_file(source_repo, filepath, ref=ref)
                return {"content": content, "file": filepath}
            except aiohttp.ClientResponseError as exc:
                last_exception = exc
                if exc.status != 404:
                    raise exc
        if last_exception:
            raise(last_exception)

    async def create_check(
        self, github_repo: str, check_body: CreateGithubCheckRun
    ) -> GithubCheckRun:
        path = self._url(f"/repos/{github_repo}/check-runs")
        headers = await self.headers(
            extra={"Accept": "application/vnd.github.antiope-preview+json"}
        )
        resp = await self.session.post(
            path, json=check_body, headers=headers, ssl=self.ssl_mode, timeout=30
        )

        await self.log_request(
            path=path,
            params={},
            body=check_body.model_dump(exclude_defaults=True),
            method="POST",
            headers=headers,
            resp=resp,
        )
        resp.raise_for_status()
        return GithubCheckRun.model_validate(await resp.json())

    async def update_check_run(
        self, github_repo: str, check_body: UpdateGithubCheckRun, check_id: int
    ) -> GithubCheckRun:
        path = self._url(f"/repos/{github_repo}/check-runs/{check_id}")
        headers = await self.headers(
            extra={"Accept": "application/vnd.github.antiope-preview+json"}
        )
        resp = await self.session.patch(
            path, json=check_body.model_dump(exclude_defaults=True), headers=headers, ssl=self.ssl_mode, timeout=30
        )

        await self.log_request(
            path=path,
            params={},
            body=check_body.model_dump(exclude_defaults=True),
            method="PATCH",
            headers=headers,
            resp=resp,
        )
        resp.raise_for_status()

        return  GithubCheckRun.model_validate(await resp.json())

    async def close(self):
        if self.session.closed is False:
            await self.session.close()
