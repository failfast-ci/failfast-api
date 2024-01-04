#!/usr/bin/env python3
from ffci.config import GConfig
from ffci.github.client import GithubClient
import logging

logger = logging.getLogger(__name__)

# Singleton to get the GithubClient instance for the app instance
# pylint: disable=super-init-not-called
# G[lobal]GithubClient is a singleton
class GGithubClient(GithubClient):
    __instance__: GithubClient | None = None
    installation_id: int = -1
    integration_id: int = -1
    integration_pem_b64: str = ""

    @classmethod
    def _init(cls, *, installation_id: int = -1, integration_id: int = -1, integration_pem_b64: str = ""):
        if installation_id == -1:
            installation_id = GConfig().github.installation_id
        if integration_id == -1:
            integration_id = GConfig().github.integration_id
        if integration_pem_b64 == "":
            integration_pem_b64 = GConfig().github.integration_pem

        cls.installation_id = installation_id
        cls.integration_id = integration_id
        cls.integration_pem_b64 = integration_pem_b64

    def __init__(self, *, installation_id: int = -1, integration_id: int = -1, integration_pem_b64: str = ""):
        self._init(installation_id=installation_id,
                   integration_id=integration_id,
                   integration_pem_b64=integration_pem_b64)
        super().__init__(installation_id=self.installation_id,
                         integration_id=self.integration_id,
                         integration_pem_b64=self.integration_pem_b64)

    def __new__(cls, installation_id: int = -1,
                integration_id: int = -1,
                integration_pem_b64: str = ""):
        if cls.__instance__ is None:
            cls._init(installation_id=installation_id,
                      integration_id=integration_id,
                      integration_pem_b64=integration_pem_b64)
            cls.__instance__ = GithubClient(installation_id=cls.installation_id,
                                            integration_id=cls.integration_id,
                                            integration_pem_b64=cls.integration_pem_b64)
        return cls.__instance__

    @classmethod
    async def reinit(cls) -> None:
        if cls.__instance__ != None:
            await cls.__instance__.close()
        cls.__instance__ = None

    @classmethod
    async def close(cls) -> None:
        await cls.reinit()

class GGitlabClient:
    pass

ALL_CLIENTS = {"github": GGithubClient, "gitlab": "GGitlabClient"}
