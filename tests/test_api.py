# #!/usr/bin/env python3
# import copy
# import json
# import os
# import urllib.parse
# from typing import Any, Optional, Type

# import pytest
# import requests
# from aioresponses import aioresponses
# from fastapi.testclient import TestClient
# from temporalio.testing import WorkflowEnvironment
# from temporalio.worker import UnsandboxedWorkflowRunner, Worker
# from temporalloop.converters.pydantic import pydantic_data_converter

# import funnelboat.config
# import funnelboat.server.api.girofunnel as api
# import funnelboat.server.api.request_info as api_info
# import funnelboat.version
# from funnelboat.models import AsyncResponse, GiroFunnelV1
# from funnelboat.server.api import GTClient
# from funnelboat.server.exception import APIException
# from funnelboat.server.server import serve
# from funnelboat.temporal.activities import create_case
# from funnelboat.temporal.workflows import EngineCaseWorkflow

# DEFAULT_PREFIX = "http://localhost:5000"


# class TestServer:
#     @property
#     def token(self) -> str:
#         return "changeme"

#     def headers(self) -> dict[str, str]:
#         d = {
#             "Content-Type": "application/json",
#             "admin-token": "dummy_key",
#         }
#         if self.token:
#             d["token"] = self.token
#         return d

#     class Client(object):
#         def __init__(
#             self, client: requests.Session, headers: Optional[dict[str, str]] = None
#         ) -> None:
#             self.client = client
#             self.headers = headers

#         def _request(
#             self, method: str, path: str, params: dict[str, str], body: dict[str, Any]
#         ) -> requests.Response:
#             if params:
#                 path = path + "?" + urllib.parse.urlencode(params)

#             return getattr(self.client, method)(
#                 path,
#                 data=json.dumps(body, sort_keys=True, default=str),
#                 headers=self.headers,
#             )

#         def get(
#             self, path: str, params: dict[str, str] = {}, body: dict[str, Any] = {}
#         ) -> requests.Response:
#             path = path + "?" + urllib.parse.urlencode(params)
#             return self.client.get(path, headers=self.headers)

#         def delete(
#             self, path: str, params: dict[str, str] = {}, body: dict[str, Any] = {}
#         ) -> requests.Response:
#             path = path + "?" + urllib.parse.urlencode(params)
#             return self.client.delete(path, json=body)

#         def post(
#             self, path: str, params: dict[str, str] = {}, body: dict[str, Any] = {}
#         ) -> requests.Response:
#             return self._request("post", path, params, body)

#     def json(self, res: requests.Response) -> Any:
#         return res.json()

#     def _url_for(self, path: str) -> str:
#         return DEFAULT_PREFIX + self.api_prefix + path

#     @property
#     def api_prefix(self) -> str:
#         return os.getenv("GIROFUNNEL_API_PREFIX", "")

#     @pytest.fixture(autouse=True)
#     def client(self) -> requests.Session:
#         client = TestClient(serve())
#         return client

#     def test_root(self, client: requests.Session) -> None:
#         url = self._url_for("")
#         res = self.Client(client, self.headers()).get(url)
#         assert res.status_code == 200
#         assert self.json(res) == {"version": funnelboat.version.VERSION.app_version}

#     def test_version(self, client: requests.Session) -> None:
#         url = self._url_for("")
#         res = self.Client(client, self.headers()).get(url)
#         assert res.status_code == 200
#         assert self.json(res) == {"version": funnelboat.version.VERSION.app_version}

#     def test_error(self, client: requests.Session) -> None:
#         url = self._url_for("/error")
#         res = self.Client(client, self.headers()).get(url)
#         assert res.status_code == 403

#     def test_404(self, client: requests.Session) -> None:
#         url = self._url_for("/unknown")
#         res = self.Client(client, self.headers()).get(url)
#         assert res.status_code == 404

#     def test_500(self, client: requests.Session) -> None:
#         url = self._url_for("/error_uncatched")

#         res = self.Client(client, self.headers()).get(url)
#         assert res.status_code == 500

#     # @pytest.mark.asyncio
#     # async def test_funnelboat_200(
#     #         self, client: requests.Session, funnel
#     # ) -> None:
#     #     with aioresponses() as m:
#     #         async with await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter) as env:
#     #             GTClient().set_client(env.client)
#     #             async with Worker(env.client,
#     #                               task_queue="girofunnel-queue", workflows=[EngineCaseWorkflow], activities=[create_case],
#     #                               workflow_runner=UnsandboxedWorkflowRunner()):
#     #                 url = self._url_for("/api/v1/girofunnel/girofunnel-async")
#     #                 m.post(
#     #                     "https://engine.local/api/admin/data_source",
#     #                     body="{}",
#     #                     status=200,
#     #                     repeat=True,
#     #                 )
#     #                 rep = await api.girofunnel_async(funnel)
#     #                 m.post(url, body=rep.json())
#     #                 res = self.Client(client, self.headers()).post(url, body=funnel.dict())
#     #                 assert (
#     #                 list(res.json().keys())
#     #                 == list(AsyncResponse().dict().keys())
#     #                 )
#     #             m.assert_called_once_with('https://engine.local/api/admin/data_source')
#     #             assert res.status_code == 200

#     # @pytest.mark.asyncio
#     # async def test_funnelboat_500(self, funnel) -> None:
#     #     print(funnel)
#     #     async with await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter) as env:
#     #         GTClient().set_client(env.client)
#     #         async with Worker(env.client, task_queue="girofunnel-queue", workflows=[EngineCaseWorkflow], activities=[create_case]
#     #                           , workflow_runner=UnsandboxedWorkflowRunner()):

#     #             with aioresponses() as m:
#     #                 m.post(
#     #                     "https://engine.local/api/admin/data_source",
#     #                     status=400,
#     #                     repeat=True,
#     #                 )

#     #             with pytest.raises(APIException) as e:
#     #                 res = await api.girofunnel_async(funnel)
#     #                 res2 = await api_info.girofunnel_status(res)
#     #                 print(res)
#     #                 print(res2)
#     #             assert e.value.status_code == 200

#     def test_funnelboat_422_bad_iban(
#         self, client: requests.Session, funnel_payload: dict[str, Any]
#     ) -> None:
#         """Wrong Iban"""
#         url = self._url_for("/api/v1/girofunnel/girofunnel-async")
#         payload = copy.deepcopy(funnel_payload)
#         payload["iban"] = "DC13432040404"
#         res = self.Client(client, self.headers()).post(url, body=payload)
#         assert res.status_code == 422

#     def test_funnelboat_422_address(
#         self, client: requests.Session, funnel_payload: dict[str, Any]
#     ) -> None:
#         url = self._url_for("/api/v1/girofunnel")

#     #     def no_city(payload: dict[str, Any]) -> dict[str, Any]:
#     #         del payload["contactDetails"]["address"]["city"]
#     #         return payload

#     #     def bad_city(payload: dict[str, Any]) -> dict[str, Any]:
#     #         payload["contactDetails"]["address"]["city"] = " "
#     #         return payload

#     #     def no_house(payload: dict[str, Any]) -> dict[str, Any]:
#     #         del payload["contactDetails"]["address"]["house"]
#     #         return payload

#     #     def bad_house(payload: dict[str, Any]) -> dict[str, Any]:
#     #         payload["contactDetails"]["address"]["house"] = " "
#     #         return payload

#     #     def no_postal_code(payload: dict[str, Any]) -> dict[str, Any]:
#     #         del payload["contactDetails"]["address"]["postalCode"]
#     #         return payload

#     #     def bad_postal_code(payload: dict[str, Any]) -> dict[str, Any]:
#     #         payload["contactDetails"]["address"]["postalCode"] = " "
#     #         return payload

#     #     def no_street(payload: dict[str, Any]) -> dict[str, Any]:
#     #         del payload["contactDetails"]["address"]["street"]
#     #         return payload

#     #     def bad_street(payload: dict[str, Any]) -> dict[str, Any]:
#     #         payload["contactDetails"]["address"]["street"] = " "
#     #         return payload

#     #     def no_email(payload: dict[str, Any]) -> dict[str, Any]:
#     #         del payload["contactDetails"]["email"]
#     #         return payload

#     #     def bad_email(payload: dict[str, Any]) -> dict[str, Any]:
#     #         payload["contactDetails"]["email"] = " "
#     #         return payload

#     #     def bad_email_format(payload: dict[str, Any]) -> dict[str, Any]:
#     #         payload["contactDetails"]["email"] = "a@b"
#     #         return payload

#     #     def no_first_name(payload: dict[str, Any]) -> dict[str, Any]:
#     #         del payload["contactDetails"]["firstName"]
#     #         return payload

#     #     def bad_first_name(payload: dict[str, Any]) -> dict[str, Any]:
#     #         payload["contactDetails"]["firstName"] = " "
#     #         return payload

#     #     def no_last_name(payload: dict[str, Any]) -> dict[str, Any]:
#     #         del payload["contactDetails"]["lastName"]
#     #         return payload

#     #     def bad_last_name(payload: dict[str, Any]) -> dict[str, Any]:
#     #         payload["contactDetails"]["lastName"] = " "
#     #         return payload

#     #     def no_bank_name(payload: dict[str, Any]) -> dict[str, Any]:
#     #         del payload["bankName"]
#     #         return payload

#     #     def bad_bank_name(payload: dict[str, Any]) -> dict[str, Any]:
#     #         payload["bankName"] = " "
#     #         return payload

#     #     test_cases: list[Callable[[dict[str, Any]], dict[str, Any]]] = [
#     #         no_city,
#     #         bad_city,
#     #         no_house,
#     #         bad_house,
#     #         no_postal_code,
#     #         bad_postal_code,
#     #         no_street,
#     #         bad_street,
#     #         no_email,
#     #         bad_email,
#     #         bad_email_format,
#     #         no_first_name,
#     #         bad_first_name,
#     #         no_last_name,
#     #         bad_last_name,
#     #         no_bank_name,
#     #         bad_bank_name,
#     #     ]
#     #     for tc in test_cases:
#     #         res = self.Client(client, self.headers()).post(
#     #             url, body=tc(copy.deepcopy(funnel_payload))
#     #         )
#     #         assert (
#     #             res.status_code == 422
#     #         ), f"{tc.__name__}: expected 422, got {res.status_code}"


# BaseTestServer = TestServer


# @pytest.mark.usefixtures("live_server")
# class LiveTestServer(BaseTestServer):
#     class Client(object):
#         def __init__(
#             self,
#             client: requests.Session = requests.session(),
#             headers: dict[str, str] = {},
#         ) -> None:
#             self.client = client
#             self.headers = headers

#         def _request(
#             self, method: str, path: str, params: dict[str, str], body: dict[str, Any]
#         ) -> requests.Response:
#             return getattr(self.client, method)(
#                 path,
#                 params=params,
#                 data=json.dumps(body, sort_keys=True, default=str),
#                 headers=self.headers,
#             )

#         def get(
#             self, path: str, params: dict[str, str] = {}, body: dict[str, Any] = {}
#         ) -> requests.Response:
#             return self._request("get", path, params, body)

#         def delete(
#             self, path: str, params: dict[str, str] = {}, body: dict[str, Any] = {}
#         ) -> requests.Response:
#             return self._request("delete", path, params, body)

#         def post(
#             self, path: str, params: dict[str, str] = {}, body: dict[str, Any] = {}
#         ) -> requests.Response:
#             return self._request("post", path, params, body)

#     def _url_for(self, path: str) -> str:
#         # FIXME: not sure what this line is trying to do; there is nothing called `request` in this file.
#         return request.url_root + self.api_prefix + path

#     def json(self, res: requests.Response) -> Any:
#         return res.json()


# def get_server_class() -> Type[BaseTestServer]:
#     if os.getenv("GIROFUNNEL_TEST_LIVESERVER", "false") == "true":
#         return LiveTestServer
#     else:
#         return BaseTestServer


# ServerTest = get_server_class()
