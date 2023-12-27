#!/usr/bin/env python3
from typing import Any, Union, Optional

AnyJSON: TypeAlias = Union[dict[str, Any], list[Any]]

class Job(BaseModel):
    uuid: str = Field(...)
    name: str = Field(...)
    status: str | None = Field(default=None)
    result: dict | EngineCaseInfo = Field(default={})


class JobList(BaseModel):
    jobs: list[Job] = Field([])


class AsyncResponse(BaseModel):
    payload: JobList = Field(default=JobList(jobs=[]))
    signature: str | None = Field(default=None)

    def gen_signature(self):
        self.signature = hmac.new(
            self.secret_key, self.payload.model_dump_json().encode(), hashlib.sha256
        ).hexdigest()
        return self.signature

    def check_signature(self):
        expect = hmac.new(
            self.secret_key, self.payload.model_dump_json().encode(), hashlib.sha256
        ).hexdigest()
        if expect != self.signature:
            return False
        return True

    @property
    def secret_key(self):
        return b"PrivateSecret...."


class GithubEventResponse(BaseModel):
    request_id: int = Field(default=-1)
    user_id: Optional[int] = Field(default=None)
    status: Optional[int] = Field(default=None)
    result: dict | None = Field(default=None)
    tokenized_emails: dict | None = Field(default=None)
    reference_number: str | None = Field(default=None)
    triggers: list[EngineTrigger] = Field(default=[])
