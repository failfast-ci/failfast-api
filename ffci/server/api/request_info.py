# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods
import logging
from typing import Any, Tuple

import temporalio.client
from fastapi import APIRouter
from temporalloop.importer import import_from_string

from ffci.models import AsyncResponse, EngineCaseInfo, Job
from ffci.server.exception import ResourceNotFound

from . import tclient

router = APIRouter(prefix="/api/v1/request", tags=["ffci", "request"])

logger = logging.getLogger(__name__)


async def get_handler_from_ar(
    ar: AsyncResponse,
) -> Tuple[temporalio.client.WorkflowHandle[Any, Any], Any]:
    return await get_handler(ar.payload.jobs[0].uuid, ar.payload.jobs[0].uuid)


async def get_handler(
    workflow_id: str,
    workflow_name: str,
) -> Tuple[temporalio.client.WorkflowHandle[Any, Any], Any]:
    workflow = import_from_string(workflow_name)
    # Retrieve running workflow handler
    client = await tclient()
    return (
        client.get_workflow_handle_for(workflow_id=workflow_id, workflow=workflow.run),
        workflow,
    )


@router.post("/request/status", response_model=AsyncResponse)
async def status(ar: AsyncResponse) -> AsyncResponse:
    workflow_id = ar.payload.jobs[0].uuid
    handler, workflow = await get_handler_from_ar(ar)
    describe = await handler.describe()
    j = ar.payload.jobs[0]
    if not describe.status:
        raise ResourceNotFound("Workflow not found", {"workflow_id": workflow_id})
    j.status = describe.status.name
    if describe.status == temporalio.client.WorkflowExecutionStatus.COMPLETED:
        j.result = await handler.result()
    else:
        j.result = await handler.query(workflow.request_info)
    ar.gen_signature()
    return ar


@router.post("/request/id", response_model=Job)
async def reqid(ar: AsyncResponse) -> Job:
    workflow_id = ar.payload.jobs[0].uuid
    handler, workflow = await get_handler_from_ar(ar)
    describe = await handler.describe()
    j = ar.payload.jobs[0]
    if not describe.status:
        raise ResourceNotFound("Workflow not found", {"workflow_id": workflow_id})

    j.status = describe.status.name
    engine_info = await handler.query(workflow.request_info)
    j.result = EngineCaseInfo(
        user_id=engine_info.get("user_id", -1),
        request_id=engine_info.get("request_id", -1),
        reference_number=engine_info.get("reference_number", ""),
        tokenized_emails=engine_info.get("tokenized_emails", {}),
        status=engine_info.get("status"),
    )
    return j
