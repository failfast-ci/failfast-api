from temporalio.client import Client
from temporalloop.converters.pydantic import pydantic_data_converter

from ffci.config import GConfig, TemporalConfigSchema

TEMPORAL_CLIENT: Client | None = None


async def tclient(conf: TemporalConfigSchema | None = None) -> Client:
    return await GTClient(conf).client()


class TClient:
    def __init__(self, conf: TemporalConfigSchema | None = None):
        if conf is None:
            conf = GConfig().temporalio

        self.conf: TemporalConfigSchema = conf
        self._client = None

    def set_client(self, client: Client) -> None:
        self._client = client

    async def client(self) -> Client:
        if self._client is None:
            self._client = await Client.connect(
                self.conf.host,
                namespace=self.conf.namespace,
                lazy=True,
                data_converter=pydantic_data_converter,
            )
        return self._client


class GTClient(TClient):
    def __new__(cls, conf: TemporalConfigSchema | None = None):
        if not hasattr(cls, "instance") or cls.instance is None:
            cls.instance = TClient(conf)
        return cls.instance

    def reinit(self) -> None:
        self.instance = None
