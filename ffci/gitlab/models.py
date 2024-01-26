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

class CreateGitlabProjectVariable(GitlabModel):
    key: str = Field(..., description="The key of a variable; must have no more than 255 characters; only A-Z, a-z, 0-9, and _ are allowed")
    value: str = Field(..., description="The value of a variable")
    description: str | None = Field(None, description="The description of the variable. Default: null. Introduced in GitLab 16.2.")
    environment_scope: str | None = Field(None, description="The environment_scope of the variable. Default: *")
    masked: bool | None = Field(None, description="Whether the variable is masked. Default: false")
    protected: bool | None = Field(None, description="Whether the variable is protected. Default: false")
    raw: bool | None = Field(None, description="Whether the variable is treated as a raw string. Default: false. When true, variables in the value are not expanded.")
    variable_type: str | None = Field(None, description="The type of a variable. Available types are: env_var (default) and file")

class UpdateGitlabProjectVariable(CreateGitlabProjectVariable):
    """
    filter	hash	No	Available filters: [environment_scope]. See the filter parameter details."
    """
    filter: dict[str, str] | None = Field(None, description="Available filters: [environment_scope]")

class GitlabProjectVariable(ModelWithExtra):
    """
    Gitlab Project Variables model
    https://docs.gitlab.com/ee/api/project_level_variables.html#get-a-single-variable
    """
    variable_type: str | None = Field(None, description="The type of the variable")
    key: str | None = Field(None, description="The key of the variable")
    value: str | None = Field(None, description="The value of the variable")
    protected: bool | None = Field(None, description="Whether the variable is protected")
    masked: bool | None = Field(None, description="Whether the variable is masked")
    raw: bool | None = Field(None, description="Whether the variable is raw")
    environment_scope: str | None = Field(None, description="The environment scope of the variable")
    description: str | None = Field(None, description="The description of the variable")



class GitlabProject(ModelWithExtra):
    """Gitlab Project model"""
    id: int | None = Field(None, description="The ID of the project")
    description: str | None = Field(None, description="The description of the project")
    default_branch: str | None = Field(None, description="The default branch of the project")
    ssh_url_to_repo: str | None = Field(None, description="The SSH URL to the repository")
    http_url_to_repo: str | None = Field(None, description="The HTTP URL to the repository")
    web_url: str | None = Field(None, description="The HTTP URL to the project")
    readme_url: str | None = Field(None, description="The HTTP URL to the readme file")
    topics: list[str] = Field(default_factory=list, description="The list of tags of the project")
    owner: dict[str, Any] = Field(default_factory=dict, description="The owner of the project")
    name: str | None = Field(None, description="The name of the project")
    name_with_namespace: str | None = Field(None, description="The name with namespace of the project")
    path: str | None = Field(None, description="The path of the project")
    path_with_namespace: str | None = Field(None, description="The path with namespace of the project")
    created_at: datetime.datetime | None = Field(None, description="The date the project was created")
    last_activity_at: datetime.datetime | None = Field(None, description="The date of the last activity in the project")
    forks_count: int | None = Field(None, description="The number of forks of the project")
    avatar_url: str | None = Field(None, description="The URL to the avatar of the project")
    star_count: int | None = Field(None, description="The number of stars of the project")
    forks: int | None = Field(None, description="The number of forks of the project")
    open_issues: int | None = Field(None, description="The number of open issues of the project")
    public_jobs: bool | None = Field(None, description="Whether the project has public jobs")
    shared_runners_enabled: bool | None = Field(None, description="Whether shared runners are enabled")
    only_allow_merge_if_pipeline_succeeds: bool | None = Field(None, description="Whether only merge requests with a passing pipeline can be merged into the project")
    only_allow_merge_if_all_discussions_are_resolved: bool | None = Field(None, description="Whether merge requests can only be merged when all the discussions are resolved")
    merge_method: str | None = Field(None, description="The merge method of the project")
    jobs_enabled: bool | None = Field(None, description="Whether jobs are enabled")
    runners_token: str | None = Field(None, description="The token of the project runners")



class CreateGitlabWebhook(GitlabModel):
    """Gitlab webhook configuration"""
    # Requries a project ID or URL-encoded path

    # id is inherited from GitlabModel
    url: str = Field(..., description="The hook URL")

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
