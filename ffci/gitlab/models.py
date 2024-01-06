#!/usr/bin/env python3
#!/usr/bin/env python3
# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods
import datetime
import logging
from enum import StrEnum
from typing import Any, Literal, Optional, TypeAlias, Union

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from ffci.github.models import ModelWithExtra

logger = logging.getLogger(__name__)

def url_encode_id(v: int | str) -> int | str:
    if isinstance(v, int):
        return v
    if '/' in v:
        v = v.replace('/', '%2F')
    return v

class ModelWithExtra(BaseModel):
    model_config = ConfigDict(extra="allow")

class GitlabModel(ModelWithExtra):
    id: int | str = Field(..., description="The ID or URL-encoded path of the project")

    @field_validator("id")
    @classmethod
    def encode_id(cls, v: int | str) -> int | str:
        return url_encode_id(v)

class GitlabCILintRequest(BaseModel):
    ref: str | None = Field(None, description="When dry_run is true, sets the branch or tag context to use to validate the CI/CD YAML configuration. Defaults to the project’s default branch when not set.")
    include_jobs: bool | None= Field(default=False), description="Include jobs in the response")
    dry_run: bool | None = Field(default=False, description="Run pipeline creation simulation, or only do static check. Default: false")

class GitlabCILintContent(GitlabCILintRequest):
    content: str = Field(..., description="The content of the .gitlab-ci.yml file")

class GitlabCILintSha(GitlabCILintRequest):
    sha: str = Field(default="HEAD", description="")

class GitlabCILint(ModelWithExtra):
    valid: bool = Field(..., description="Whether the configuration is valid")
    merged_yaml: str = Field(default="", description="The merged YAML content")
    errors: list[str] = Field(default_factory=list, description="The list of errors")
    warnings: list[str] = Field(default_factory=list, description="The list of warnings")

class CreateGitlabWebhook(GitlabModel):
    """Gitlab webhook configuration"""
    # Requries a project ID or URL-encoded path

    # id is inherited from GitlabModel
    url: str = Fie  ld(..., description="The hook URL")

    # Optional parameters
    confidential_issues_events: Optional[bool] = Field(default=None, description="Trigger hook on confidential issues events")
    confidential_note_events: Optional[bool] = Field(default=None, description="Trigger hook on confidential note events")
    deployment_events: Optional[bool] = Field(default=None, description="Trigger hook on deployment events")
    enable_ssl_verification: Optional[bool] = Field(default=None, description="Do SSL verification when triggering the hook")
    issues_events: Optional[bool] = Field(default=None, description="Trigger hook on issues events")
    job_events: Optional[bool] = Field(default=None, description="Trigger hook on job events")
    merge_requests_events: Optional[bool] = Field(default=None, description="Trigger hook on merge requests events")
    note_events: Optional[bool] = Field(default=None, description="Trigger hook on note events")
    pipeline_events: Optional[bool] = Field(default=None, description="Trigger hook on pipeline events")
    push_events: Optional[bool] = Field(default=None, description="Trigger hook on push events")
    push_events_branch_filter: Optional[str] = Field(default=None, description="Trigger hook on push events for matching branches only")
    release_events: Optional[bool] = Field(default=None, description="Trigger hook on release events")
    tag_push_events: Optional[bool] = Field(default=None, description="Trigger hook on tag push events")
    token: Optional[str] = Field(default=None, description="Secret token to validate received payloads; the token isn’t returned in the response")
    wiki_page_events: Optional[bool] = Field(default=None, description="Trigger hook on wiki events")

class UpdateGitlabWebhook(CreateGitlabWebhook):
    """Gitlab webhook configuration"""
    hook_id: int | str = Field(..., description="The ID or URL-encoded path of the project")

    @field_validator("hook_id")
    @classmethod
    def encode_hook_id(cls, v: int | str) -> int | str:
        return url_encode_id(v)

class GitlabWebhook(ModelWithExtra):
    # id is inherited from GitlabModel
    url: str = Field(..., description="The hook URL")
    project_id: Optional[int] = Field(default=None, description="The ID of the project")
    # Optional parameters
    confidential_issues_events: Optional[bool] = Field(default=None, description="Trigger hook on confidential issues events")
    confidential_note_events: Optional[bool] = Field(default=None, description="Trigger hook on confidential note events")
    deployment_events: Optional[bool] = Field(default=None, description="Trigger hook on deployment events")
    enable_ssl_verification: Optional[bool] = Field(default=None, description="Do SSL verification when triggering the hook")
    issues_events: Optional[bool] = Field(default=None, description="Trigger hook on issues events")
    job_events: Optional[bool] = Field(default=None, description="Trigger hook on job events")
    merge_requests_events: Optional[bool] = Field(default=None, description="Trigger hook on merge requests events")
    note_events: Optional[bool] = Field(default=None, description="Trigger hook on note events")
    pipeline_events: Optional[bool] = Field(default=None, description="Trigger hook on pipeline events")
    push_events: Optional[bool] = Field(default=None, description="Trigger hook on push events")
    push_events_branch_filter: Optional[str] = Field(default=None, description="Trigger hook on push events for matching branches only")
    release_events: Optional[bool] = Field(default=None, description="Trigger hook on release events")
    tag_push_events: Optional[bool] = Field(default=None, description="Trigger hook on tag push events")
    token: Optional[str] = Field(default=None, description="Secret token to validate received payloads; the token isn’t returned in the response")
    wiki_page_events: Optional[bool] = Field(default=None, description="Trigger hook on wiki events")
    url_variables: Optional[list[str]] = Field(default=None, description="URL variables")
    created_at: Optional[datetime.datetime] = Field(default=None, description="Date the webhook was created")
    alert_status: Optional[str] = Field(default=None, description="Status of the webhook")
    disabled_until: Optional[datetime.datetime] = Field(default=None, description="Date the webhook was disabled until")
    repository_update_events: Optional[bool] = Field(default=None, description="Trigger hook on repository update events")
