from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette_exporter import handle_metrics
from starlette_exporter.middleware import PrometheusMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from ffci.config import Config, GConfig
from ffci.init import init

from .api import info
from .middlewares.errors import catch_exceptions_middleware
from .middlewares.process_time import add_process_time_header
from .middlewares.token import TokenAuthMiddleware


class Server:
    def __init__(self, conf: Config):
        self.config: Config = conf
        self.app: FastAPI = FastAPI()
        self.load_middlewares()
        self.load_routers()

    def load_middlewares(self):
        self.app.middleware("http")(catch_exceptions_middleware)
        self.app.middleware("http")(add_process_time_header)
        self.app.add_middleware(PrometheusMiddleware, app_name="ffci")
        self.app.add_middleware(ProxyHeadersMiddleware)
        if "cors" in self.config.server.middlewares:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origin_regex=self.config.server.cors.allow_origin_regex,
                allow_origins=self.config.server.cors.allow_origins,
                allow_credentials=self.config.server.cors.allow_credentials,
                allow_methods=self.config.server.cors.allow_methods,
                allow_headers=self.config.server.cors.allow_headers,
            )
        if "tokenAuth" in self.config.server.middlewares:
            self.app.add_middleware(TokenAuthMiddleware, token=self.config.server.token)

    def load_routers(self):
        self.app.add_route("/metrics", handle_metrics)
        self.app.include_router(info.router)
        self.app.include_router(girofunnel.router)
        self.app.include_router(heyflow_hooks.router)


def serve() -> FastAPI:
    init("fastapi")
    server = Server(GConfig())
    return server.app
