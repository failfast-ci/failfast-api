# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods
import asyncio
import json
import logging
from typing import Any, Literal, Union, cast
from urllib.parse import ParseResult, urlparse

import aiohttp
from aiohttp_prometheus_exporter.trace import PrometheusTraceConfig

from ffci.config import GConfig
from ffci.models import EngineRequest, EngineTrigger
from ffci.version import VERSION

logger = logging.getLogger(__name__)


class EngineClient:
    session: aiohttp.ClientSession
    verify_tls: bool

    def __init__(
        self,
        endpoint: str = "",
        token: Union[str, None] = None,
        requests_verify: bool = True,
    ):
        self.endpoint: ParseResult = self._configure_endpoint(endpoint)
        self.host: str = self.endpoint.geturl()
        self.token = token
        self._headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": f"ffci-cli/{VERSION.app_version}",
        }
        self.verify_tls = requests_verify
        self.session = aiohttp.ClientSession(
            trace_configs=[PrometheusTraceConfig(client_name="engine-client")]
        )

    def _url(self, path: str) -> str:
        return self.endpoint.geturl() + path

    def _configure_endpoint(self, endpoint: str) -> ParseResult:
        return urlparse(endpoint)

    def headers(self, content_type: Literal["json", "form"] = "json") -> dict[str, str]:
        headers: dict[str, str] = {}
        headers.update(self._headers)

        if content_type == "json":
            headers["Content-Type"] = "application/json"
        elif content_type == "form":
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        if self.token:
            headers["token"] = self.token

        return headers

    async def health(self) -> Any:
        path: str = "/_health"
        resp = await self.session.get(
            self._url(path),
            headers=self.headers(),
            ssl=None if self.verify_tls else False,
        )
        resp.raise_for_status()
        return await resp.json()

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
        logger.info(
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

    # pylint: enable=too-many-arguments
    async def action_triggers(
        self, request_id: int, triggers: list[dict[str, str]]
    ) -> list[EngineTrigger]:
        return list(
            await asyncio.gather(
                *[
                    self.action_trigger(
                        EngineTrigger(
                            request_id=request_id,
                            name=trigger["name"],
                            trigger_id=trigger["trigger_id"],
                        )
                    )
                    for trigger in triggers
                ]
            )
        )

    async def action_trigger(self, engine_trigger: EngineTrigger) -> EngineTrigger:
        path = f"/api/admin/action_triggers/{engine_trigger.trigger_id}"
        params = engine_trigger.model_dump(include={"request_id", "client", "attempt"})
        resp = await self.session.put(
            self._url(path),
            params=params,
            headers=self.headers("form"),
            ssl=None if self.verify_tls else False,
        )
        await self.log_request(
            path=path,
            params=params,
            body=cast(dict[str, Any], {}),
            method="PUT",
            headers=self.headers("form"),
            resp=resp,
        )

        if GConfig().app.env == "staging":
            engine_trigger.status = {"status": resp.status}
            return engine_trigger

        resp.raise_for_status()
        engine_trigger.status = await resp.json()
        return engine_trigger

    async def create_request(self, enginereq: EngineRequest) -> Any:
        payload = enginereq.dict()
        payload["fields"] = json.dumps(payload["fields"], sort_keys=True, default=str)
        payload["request_id"] = None
        path = "/api/admin/data_source"
        resp = await self.session.post(
            self._url(path),
            headers=self.headers("form"),
            ssl=None if self.verify_tls else False,
            data=payload,
        )
        await self.log_request(
            path=path,
            params={},
            body=payload,
            method="POST",
            headers=self.headers("form"),
            resp=resp,
        )
        # Suspicious...
        if GConfig().app.env == "staging":
            return {"status": resp.status}
        resp.raise_for_status()
        return await resp.json()

    async def update_request(self, request_id: int, enginereq: EngineRequest) -> Any:
        payload = enginereq.dict()
        payload["fields"] = json.dumps(payload["fields"], sort_keys=True, default=str)
        payload["request_id"] = request_id
        path = "/api/admin/data_source"
        resp = await self.session.put(
            self._url(path),
            headers=self.headers("form"),
            ssl=None if self.verify_tls else False,
            data=payload,
            params={},
        )
        await self.log_request(
            path=path,
            params={},
            body=payload,
            method="PUT",
            headers=self.headers("form"),
            resp=resp,
        )
        # Still suspicious...
        if GConfig().app.env == "staging":
            return {"status": resp.status}
        resp.raise_for_status()
        return await resp.json()
