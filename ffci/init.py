#!/usr/bin/env python3

import pathlib

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from ffci.config import GConfig


def init_sentry(integration_app: str = ""):
    if GConfig().sentry.dsn:
        integrations = []
        if integration_app == "fastapi":
            integrations = [
                StarletteIntegration(),
                FastApiIntegration(),
            ]
        sentry_sdk.init(  # pylint: disable=abstract-class-instantiated # noqa: E0110
            dsn=GConfig().sentry.dsn,
            integrations=integrations,
            traces_sample_rate=GConfig().sentry.traces_sample_rate,
            environment=GConfig().sentry.environment,
        )


def _create_tmp_dir() -> None:
    pathlib.Path(GConfig().app.prometheus_dir).mkdir(parents=True, exist_ok=True)


def init(app: str = ""):
    _create_tmp_dir()
    init_sentry(app)
