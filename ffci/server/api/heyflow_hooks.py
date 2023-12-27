#!/usr/bin/env python3
# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods
import logging
import uuid
from typing import Any

from aiohttp.client_exceptions import ClientConnectorError, ClientResponseError
from fastapi import APIRouter, Request
from temporalio.client import WorkflowHandle
from temporalio.service import RPCError, RPCStatusCode

from ffci.config import GConfig
from ffci.models import AsyncResponse, HeyflowFunnel, Job
from ffci.server.api.request_info import get_handler
from ffci.server.exception import InvalidParams, Unexpected
from ffci.temporal.activities import EngineConfigInput
from ffci.temporal.workflows import (
    CaseWorkflowInput,
    EngineCaseWorkflow,
    FunnelEchoWorkflow,
)

from . import tclient

router = APIRouter(
    prefix="/api/v1/heyflow",
    tags=["ffci", "heyflow", "connectors"],
)
logger = logging.getLogger(__name__)

WAIT_FOR = 60 * 60 * 4


@router.post("/echo", response_model=HeyflowFunnel)
async def echo(
    funnel: HeyflowFunnel, mapper: str | None, productName: str | None, request: Request
) -> HeyflowFunnel:
    try:
        logger.info(await request.body())
        logger.info(await request.json())
        if mapper:
            funnel.mapper = mapper
        if productName:
            funnel.productName = productName

        logger.info({"funnel": funnel.model_dump()})
        jid = f"echo-hf-{funnel.productName}-{uuid.uuid4()}-{funnel.id}"
        # Run workflow
        client = await tclient()
        _ = await client.start_workflow(
            FunnelEchoWorkflow.run,
            funnel,
            id=jid,
            task_queue="ffci-echo-queue",
        )
        return funnel
    except (ClientConnectorError, ClientResponseError) as err:
        raise Unexpected("unexpected server error") from err


async def create_new_workflow(
    jid: str, funnel: HeyflowFunnel, wait_for_seconds: int = WAIT_FOR
) -> WorkflowHandle[Any, Any]:
    client = await tclient()
    handler = await client.start_workflow(
        EngineCaseWorkflow.run,
        CaseWorkflowInput(
            mapper_name=funnel.mapper,
            product_name=funnel.productName,
            funnel=funnel,
            wait_for_seconds=wait_for_seconds,
            engine_conf=EngineConfigInput.model_validate(GConfig().engine.model_dump()),
        ),
        search_attributes={
            "userEmail": [funnel.get_email()],
            "productName": [funnel.productName],
        },
        id=jid,
        task_queue="ffci-queue",
    )
    return handler


@router.post("/webhook", response_model=AsyncResponse)
async def heyflow_async(
    funnel: HeyflowFunnel, mapper: str | None = None, productName: str | None = None
) -> AsyncResponse:
    try:
        if mapper:
            funnel.mapper = mapper
        if productName:
            funnel.productName = productName

        logger.info({"funnel": funnel.model_dump()})
        # can't create an Engine Case without an email
        if not funnel.get_email():
            raise InvalidParams("missing an email to create the request")

        # Generate a unique id for the workflow
        jid = f"{funnel.productName}-hf-{funnel.get_uuid()}"
        handler, _ = await get_handler(
            jid, "ffci.temporal.workflows:EngineCaseWorkflow"
        )
        try:
            # Try to update the workflow
            _ = await handler.describe()
            exit_steps = None
            if "hf:completed" in funnel.fields:
                exit_steps = int(funnel.fields["hf:completed"])
            _ = await handler.signal(
                EngineCaseWorkflow.update_case, args=[funnel, exit_steps]
            )
        except RPCError as exc:
            # If it fails because the workflow is not found or already completed,
            # create a new one
            if exc.status != RPCStatusCode.NOT_FOUND:
                logger.error("unexpected error: %s", exc)
                # Do not raise create a new workflow
                # raise exc
            waitfor = WAIT_FOR  #
            handler = await create_new_workflow(jid, funnel, waitfor)

        ar = AsyncResponse()
        ar.payload.jobs.append(
            Job(uuid=jid, name="ffci.temporal.workflows:EngineCaseWorkflow")
        )
        ar.gen_signature()
        return ar
    except (ClientConnectorError, ClientResponseError) as err:
        raise Unexpected("unexpected server error") from err
