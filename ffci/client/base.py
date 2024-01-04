from typing import Any, Literal
from urllib.parse import ParseResult, urlparse
import logging
import aiohttp
from aiohttp_prometheus_exporter.trace import PrometheusTraceConfig

from ffci.version import VERSION
logger = logging.getLogger(__name__)

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
