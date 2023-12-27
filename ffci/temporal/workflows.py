#!/usr/bin/env python3
import asyncio
from datetime import timedelta
from typing import Any

from pydantic import BaseModel, Field
from temporalio import workflow
from temporalio.common import RetryPolicy

from ffci.models import EngineResponse, FunnelsType, HeyflowFunnel
from ffci.temporal.activities import (
    ActionTriggerInput,
    CreateCaseInput,
    DownloadUploadFileInput,
    EngineConfigInput,
    UpdateCaseInput,
    action_trigger,
    create_case,
    download_upload_file,
    update_case,
)


class CaseWorkflowInput(BaseModel):
    funnel: FunnelsType = Field(...)
    mapper_name: str = Field(...)
    product_name: str = Field(...)
    engine_conf: EngineConfigInput = Field(...)
    wait_for_seconds: int = Field(default=0)


@workflow.defn
class FunnelEchoWorkflow:
    def __init__(self) -> None:
        self.funnel: None | FunnelsType = None

    @workflow.run
    async def run(self, funnel: FunnelsType) -> FunnelsType:
        workflow.logger.info(f"EchoFunnel: {funnel.model_dump_json()}")
        self.funnel = funnel
        return funnel

    @workflow.query
    def echo(self) -> FunnelsType | None:
        return self.funnel


@workflow.defn
class EngineCaseWorkflow:
    def __init__(self) -> None:
        self._updated_funnels: list[FunnelsType] = []
        self._current_step: int = 0
        self._exit_steps: None | int = None
        self._documents: set[str] = set()
        self._executed_trigger: dict[str, str] = {}
        self._engine_response: EngineResponse = EngineResponse()
        self._exit: bool = False

    async def download_documents(self, documents: list[str]) -> list[str]:
        documents_res = []
        workflow.logger.info(f"EngineCase: Start fetching documents: {documents}")

        for document in documents:
            if document in self._documents:
                continue
            self._documents.add(document)
            documents_res.append(
                workflow.execute_activity(
                    download_upload_file,
                    DownloadUploadFileInput(source=document),
                    start_to_close_timeout=timedelta(seconds=60),
                    schedule_to_close_timeout=timedelta(minutes=360),
                )
            )
        workflow.logger.info("EngineCase: Stop fetchign documents{documents_res}")
        return [x.url for x in list(await asyncio.gather(*documents_res))]

    async def trigger_actions(
        self, triggers, trigger_cond, engine_conf, fields: dict[str, str]
    ) -> EngineResponse:
        workflow.logger.info(
            f"Case: trigger engine actions {triggers} {trigger_cond} {fields}"
        )
        # Triggers are ordered
        for action, trigger_v in triggers:
            _, name, pos = action.split(":")
            atcond = "atcond:" + name + ":" + pos
            workflow.logger.info(f"atcond: {atcond}")
            if atcond in trigger_cond:
                field_name, field_v = trigger_cond[atcond]
                # Stop on the first trigger that doesn't match the cond
                if field_name not in fields or fields[field_name] != field_v:
                    return self._engine_response
            self._engine_response = await workflow.execute_activity(
                action_trigger,
                ActionTriggerInput(
                    name=action,
                    trigger_id=trigger_v,
                    engine_response=self._engine_response,
                    engine_conf=engine_conf,
                ),
                schedule_to_close_timeout=timedelta(minutes=360),
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=10),
                    maximum_interval=timedelta(seconds=1800),
                ),
            )
            self._executed_trigger[action] = trigger_v
            workflow.upsert_search_attributes(
                {"actionTriggers": list(self._executed_trigger.keys())}
            )
        return self._engine_response

    @workflow.run
    async def run(self, data: CaseWorkflowInput) -> EngineResponse:
        funnel = data.funnel
        wait_for_seconds: int = data.wait_for_seconds
        workflow.logger.info("Running workflow: EngineCase")

        # 1. Create the case the engine
        workflow.logger.info("EngineCase: Create case on engine")
        funnel.set_documents(await self.download_documents(funnel.get_documents()))
        self._engine_response = await workflow.execute_activity(
            create_case,
            CreateCaseInput(
                mapper_name=data.mapper_name,
                product_name=data.product_name,
                funnel=funnel,
                engine_conf=data.engine_conf,
            ),
            schedule_to_close_timeout=timedelta(minutes=360),  # Fail after 6 hours
            start_to_close_timeout=timedelta(seconds=60),
        )
        self._updated_funnels.insert(0, funnel)
        self._current_step = 1

        # reset documents fields to no upload them again
        workflow.logger.info(
            f"EngineCase: response: {self._engine_response.model_dump()}"
        )
        await asyncio.sleep(60)
        await self.trigger_actions(
            funnel.get_action_triggers(),
            funnel.get_action_trigger_conditions(),
            data.engine_conf,
            funnel.get_fields(),
        )
        # Case is created, waiting for next steps
        # 2. Wait for receiving and udpate (user signature)
        while self._exit is False:
            try:
                workflow.logger.info(
                    f"Case: Wait for update(max: {wait_for_seconds} seconds)"
                )
                # wait for N seconds or until more funnels are received.
                # current_step starts at 1 (case created), then it's incremented after each update
                await workflow.wait_condition(
                    lambda: len(self._updated_funnels) > self._current_step
                    and self._engine_response.request_id > 0,
                    timeout=timedelta(seconds=wait_for_seconds),
                )
                start = self._current_step
                for update_funnel in self._updated_funnels[start:]:
                    self._current_step += 1
                    await self.engine_update(data, update_funnel)

                # @TODO: Find new exit conditions
                # if self._exit_steps is not None:
                #     if self._current_step >= self._exit_steps:
                #         self._exit = True

            except asyncio.TimeoutError:
                # It continues as planned, even if no signal is received
                self._exit = True
        # Teardown any remaining updates
        if len(self._updated_funnels) > self._current_step:
            await self.engine_update(data, self._updated_funnels[-1])
        workflow.logger.info(f"Case: exit workflow {self._engine_response.request_id}")
        return self._engine_response

    async def engine_update(
        self, data: CaseWorkflowInput, updated_funnel: FunnelsType
    ) -> None:
        # 3. Update is received via signal, submit the data to engine
        workflow.logger.info("Case: update case on engine")
        if updated_funnel is not None and self._engine_response.request_id > 0:
            if updated_funnel is not None:
                workflow.logger.info(
                    f"Case: update documents {updated_funnel.get_documents()}"
                )
            if updated_funnel is not None:
                updated_funnel.set_documents(
                    await self.download_documents(updated_funnel.get_documents())
                )

            _ = await workflow.execute_activity(
                update_case,
                UpdateCaseInput(
                    mapper_name=data.mapper_name,
                    product_name=data.product_name,
                    funnel=updated_funnel,
                    request_id=self._engine_response.request_id,
                    engine_conf=data.engine_conf,
                ),
                schedule_to_close_timeout=timedelta(minutes=360),
                start_to_close_timeout=timedelta(seconds=60),
            )
            workflow.logger.info(f"Case updated {self._engine_response.request_id}")
            # 4. Trigger actions on engine
            if updated_funnel is not None:
                updated_funnel.update_action_triggers(self._executed_trigger)
            if updated_funnel is not None:
                self._engine_response = await self.trigger_actions(
                    updated_funnel.get_action_triggers(),
                    updated_funnel.get_action_trigger_conditions(),
                    data.engine_conf,
                    updated_funnel.get_fields(),
                )

    @workflow.signal
    async def update_case(
        self, funnel: dict[str, Any], exit_steps: int | None = None
    ) -> None:
        if exit_steps is not None:
            self._exit_steps = exit_steps
        self._updated_funnels.append(HeyflowFunnel(**funnel))
        workflow.logger.info(
            "Case: signal_received to update (#%s)", len(self._updated_funnels)
        )

    @workflow.query
    def request_id(self) -> int:
        return self._engine_response.request_id

    @workflow.query
    def request_info(self) -> EngineResponse | None:
        return self._engine_response

    @workflow.query
    def updated_cases(self) -> list[FunnelsType]:
        return self._updated_funnels

    @workflow.query
    def current_step(self) -> int:
        return self._current_step
