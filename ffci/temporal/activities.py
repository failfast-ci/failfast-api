# pylint: disable=import-outside-toplevel
import logging
from typing import Final

from pydantic import BaseModel, Field
from temporalio import activity

from ffci.config import GConfig, S3ConfigSchema
from ffci.mapper import GMapper
from ffci.models import (
    EngineMapper,
    EngineResponse,
    EngineTrigger,
    FunnelsType,
    S3Dest,
)

logger = logging.getLogger(__name__)


class EngineConfigInput(BaseModel):
    token: str = Field(default="changeme")
    endpoint: str = Field(default="https://engine.stg.conny.dev")


class DownloadUploadFileInput(BaseModel):
    source: str = Field(...)
    s3conf: S3ConfigSchema | None = Field(default=None)
    dest: str = Field(default="")
    bucket: str = Field(default="")
    prefix: str = Field(default="")


class ActionTriggerInput(BaseModel):
    name: str = Field(...)
    trigger_id: str = Field(...)
    engine_response: EngineResponse = Field(...)
    engine_conf: EngineConfigInput = Field(...)


class UpdateCaseInput(BaseModel):
    funnel: FunnelsType = Field(...)
    request_id: int = Field(...)
    engine_conf: EngineConfigInput = Field(...)
    mapper_name: str = Field(...)
    product_name: str = Field(...)


class CreateCaseInput(BaseModel):
    funnel: FunnelsType = Field(...)
    engine_conf: EngineConfigInput = Field(...)
    mapper_name: str = Field(...)
    product_name: str = Field(...)


@activity.defn
async def action_trigger(data: ActionTriggerInput) -> EngineResponse:
    from ffci.client.engine import EngineClient

    activity.logger.info(
        f"Running activity; ActionTrigger; request_id: {data.engine_response.request_id}"
    )
    engine_response = data.engine_response
    reqid: Final[int | None] = engine_response.request_id
    client = EngineClient(
        endpoint=data.engine_conf.endpoint, token=data.engine_conf.token
    )
    if reqid:
        engine_response.triggers.append(
            await client.action_trigger(
                EngineTrigger(
                    request_id=reqid,
                    trigger_id=data.trigger_id,
                    name=data.name,
                    attempt=activity.info().attempt,
                    client="ffci",
                )
            )
        )

    await client.session.close()
    return engine_response


async def submit_to_engine(
    mapper: EngineMapper,
    funnel: FunnelsType,
    engine_conf: EngineConfigInput,
    reqid: int | None = None,
) -> EngineResponse:
    from ffci.client.engine import EngineClient

    client = EngineClient(endpoint=engine_conf.endpoint, token=engine_conf.token)
    enginereq = GMapper().to_engine_request(
        engine_mapper=mapper, data=funnel.model_dump()
    )
    if not reqid:
        request = await client.create_request(enginereq)
    else:
        request = await client.update_request(reqid, enginereq)
    resp = EngineResponse(**request)
    await client.session.close()
    return resp


@activity.defn
async def create_case(data: CreateCaseInput) -> EngineResponse:
    activity.logger.info(
        f"Running activity; CreateCase[{data.product_name}][{data.mapper_name}]"
    )
    mapper = GMapper().get(name=data.mapper_name, product=data.product_name)
    return await submit_to_engine(mapper, data.funnel, data.engine_conf)


@activity.defn
async def update_case(data: UpdateCaseInput) -> EngineResponse:
    activity.logger.info(
        f"Running activity; UpdateCase[{data.product_name}][{data.mapper_name}]; request_id: {data.request_id}"
    )
    mapper = GMapper().get(name=data.mapper_name, product=data.product_name)
    return await submit_to_engine(
        mapper, data.funnel, data.engine_conf, data.request_id
    )


@activity.defn
async def download_upload_file(data: DownloadUploadFileInput) -> S3Dest:
    from ffci.fetchdocument import download
    from ffci.s3 import S3Client

    activity.logger.info(
        f"Running activity; DownloadUploadfile[{data.source}][{data.dest}]"
    )
    filepath = await download(data.source)
    if data.s3conf is None:
        data.s3conf = GConfig().s3
    s3client = S3Client(data.s3conf, data.bucket, data.prefix)
    return s3client.upload_file(filepath, data.dest)
