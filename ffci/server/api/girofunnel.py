#!/usr/bin/env python3
# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods
import logging
import uuid

from aiohttp.client_exceptions import ClientConnectorError, ClientResponseError
from fastapi import APIRouter

from ffci.config import GConfig
from ffci.models import AsyncResponse, GiroFunnelV1, Job
from ffci.server.exception import Unexpected
from ffci.temporal.workflows import CaseWorkflowInput, EngineCaseWorkflow

from . import tclient

# from ffci.temporal.workflows import GiroCaseWorkflow, GiroCaseWorkflowInput

router = APIRouter(
    prefix="/api/v1/girofunnel",
    tags=["ffci", "girofunnel", "connectors"],
)
logger = logging.getLogger(__name__)


@router.post("/girofunnel-async", response_model=AsyncResponse)
async def girofunnel_async(funnel: GiroFunnelV1, delay: int = 60) -> AsyncResponse:
    try:
        logger.info({"funnel": funnel.model_dump()})
        jid = f"girocase-{uuid.uuid4()}-{funnel.contactDetails.email}"
        # Run workflow
        client = await tclient()
        _ = await client.start_workflow(
            EngineCaseWorkflow.run,
            CaseWorkflowInput(
                mapper_name="girofunnel-v1-0-0",
                product_name="girokosten-transatlantis",
                funnel=funnel,
                wait_for_seconds=delay,
                engine_conf=GConfig().engine,
            ),
            id=jid,
            task_queue="girofunnel-queue",
        )
        ar = AsyncResponse()
        ar.payload.jobs.append(
            Job(uuid=jid, name="ffci.temporal.workflows:EngineCaseWorkflow")
        )
        ar.gen_signature()
        return ar
    except (ClientConnectorError, ClientResponseError) as err:
        raise Unexpected("unexpected server error") from err


# @router.put("/girofunnel-async", response_model=AsyncResponse)
# async def girofunnel_async_update(
#     funnel: dict[str, Any], job_name: str = "update-case"
# ) -> AsyncResponse:
#     try:
#         if not funnel.callback:
#             raise UnauthorizedAccess("Callback is missing")
#         ar = funnel.callback
#         if not ar.check_signature():
#             raise UnauthorizedAccess("Callback signature mismatch")
#         workflow_id = ar.payload.jobs[0].uuid
#         client = await tclient()
#         # Retrieve running workflow handler
#         handler = client.get_workflow_handle_for(
#             workflow_id=workflow_id, workflow=GiroCaseWorkflow.run
#         )
#         funnel.inform_my_bank = True
#         # Send signal to update the case on the running worflow
#         _ = (await handler.signal(GiroCaseWorkflow.update_case, funnel),)
#         return ar
#     except (ClientConnectorError, ClientResponseError) as err:
#         raise Unexpected("unexpected server error") from err
