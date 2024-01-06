#!/usr/bin/env python3
# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods
import datetime
import logging
from enum import StrEnum
from typing import Any, Literal, Optional, TypeAlias, Union

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

logger = logging.getLogger(__name__)

class ModelWithExtra(BaseModel):
    model_config = ConfigDict(extra="allow")

class CheckSuiteActionsEnum(StrEnum):
    REQUESTED = "requested"
    REREQUESTED = "rerequested"
    COMPLETED = "completed"

class GithubEventsEnum(StrEnum):
    CHECK_SUITE = "check_suite"
    CHECK_RUN = "check_run"
    PULL_REQUEST = "pull_request"
    PUSH = "push"
    PING = "ping"
    ISSUE_COMMENT = "issue_comment"

class CheckRunActionsEnum(StrEnum):
    REQUESTED = "requested"
    REQUESTED_ACTION = "requested_action"
    COMPLETED = "completed"
    CREATED = "created"

class PullRequestActionsEnum(StrEnum):
    OPENED = "opened"
    SYNCHRONIZE = "synchronize"
    REOPENED = "reopened"
    CLOSED = "closed"
    EDITED = "edited"
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
    LABELED = "labeled"
    UNLABELED = "unlabeled"
    REVIEW_REQUESTED = "review_requested"
    REVIEW_REQUEST_REMOVED = "review_request_removed"
    READY_FOR_REVIEW = "ready_for_review"
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    AUTO_MERGE_ENABLED = "auto_merge_enabled"
    AUTO_MERGE_DISABLED = "auto_merge_disabled"
    AUTO_MERGE_FAILED = "auto_merge_failed"
    AUTO_MERGE_SKIPPED = "auto_merge_skipped"
    CONVERTED_TO_DRAFT = "converted_to_draft"
    HEAD_REF_DELETED = "head_ref_deleted"
    HEAD_REF_RESTORED = "head_ref_restored"
    MERGED = "merged"
    REVIEW_DISMISSED = "review_dismissed"
    USER_BLOCKED = "user_blocked"

class GithubCheckRunConclusionEnum(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    NEUTRAL = "neutral"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    ACTION_REQUIRED = "action_required"
    STALE = "stale"
    SKIPPED = "skipped"


class GithubHeaders(ModelWithExtra):
    x_hub_signature_256: str = Field(default="", alias="X-Hub-Signature-256")
    x_hub_signature: str = Field(default="", alias="X-Hub-Signature")
    x_github_event: str = Field(default="", alias="X-GitHub-Event")
    x_github_delivery: str = Field(default="",alias="X-GitHub-Delivery")
    x_github_hook_id: str = Field(default="", alias="X-GitHub-Hook-ID")
    x_github_hook_installation_target_id: str = Field(default="",
        alias="X-GitHub-Hook-Installation-Target-ID"
    )
    x_github_hook_installation_target_type: str = Field(default="",
        alias="X-GitHub-Hook-Installation-Target-Type"
    )


class GithubLabel(ModelWithExtra):
    id: int = Field(default=0)
    node_id: str = Field(default="")
    url: str = Field(default="")
    name: str = Field(default="")
    color: str = Field(default="")
    default: bool = Field(default=False)
    description: str | None = Field(default="")


class GithubCheckRunOutput(ModelWithExtra):
    title: str = Field(default="")
    summary: str = Field(default="")
    text: str = Field(default="")
    annotations_count: int = Field(default=0)
    annotations_url: str = Field(default="")


class GithubCheckRunPRRepo(ModelWithExtra):
    id: int = Field(default=0)
    url: str = Field(default="")
    name: str = Field(default="")


class GithubCheckRunPRCommit(ModelWithExtra):
    ref: str = Field(default="")
    sha: str = Field(default="")
    repo: GithubCheckRunPRRepo = Field(default_factory=GithubCheckRunPRRepo)


class GithubCheckRunPR(ModelWithExtra):
    url: str = Field(default="")
    id: int = Field(default=0)
    number: int = Field(default=0)
    head: GithubCheckRunPRCommit = Field(default_factory=GithubCheckRunPRCommit)
    base: GithubCheckRunPRCommit = Field(default_factory=GithubCheckRunPRCommit)


class GithubCheckSuite(ModelWithExtra):
    id: int = Field(default=0)
    node_id: str = Field(default="")
    head_branch: str = Field(default="")
    head_sha: str = Field(default="")
    status: Literal[
        "queued",
        "in_progress",
        "completed",
    ] = Field(default="queued")
    conclusion: Literal[
        "success",
        "failure",
        "neutral",
        "cancelled",
        "timed_out",
        "action_required",
        "stale",
    ] | None = Field(default="neutral")
    url: str = Field(default="")
    before: str = Field(default="")
    after: str = Field(default="")
    pull_requests: list[GithubCheckRunPR] = Field(default_factory=list)
    app: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)


class GithubCheckRun(ModelWithExtra):
    """ Model for Github getting check run """
    id: int = Field(default=0)
    node_id: str = Field(default="")
    head_sha: str = Field(default="")
    external_id: str = Field(default="")
    url: str = Field(default="")
    html_url: str = Field(default="")
    details_url: str = Field(default="")
    status: Literal[
        "queued",
        "in_progress",
        "completed",
    ] = Field(default="queued")
    conclusion: Literal[
        "success",
        "failure",
        "neutral",
        "cancelled",
        "timed_out",
        "action_required",
        "stale",
    ] | None = Field(default="neutral")
    started_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    completed_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    output: GithubCheckRunOutput = Field(default_factory=GithubCheckRunOutput)
    name: str = Field(default="")
    check_suite: GithubCheckSuite = Field(default_factory=GithubCheckSuite)
    app: dict[str, Any] = Field(default_factory=dict)
    pull_requests: list[GithubCheckRunPR] = Field(default_factory=list)


# Model for Github webhook
class GithubUser(ModelWithExtra):
    login: str = Field(default="")
    id: int = Field(default=0)
    node_id: str = Field(default="")
    avatar_url: str = Field(default="")
    gravatar_id: str = Field(default="")
    url: str = Field(default="")
    html_url: str = Field(default="")
    followers_url: str = Field(default="")
    following_url: str = Field(default="")
    gists_url: str = Field(default="")
    starred_url: str = Field(default="")
    subscriptions_url: str = Field(default="")
    organizations_url: str = Field(default="")
    repos_url: str = Field(default="")
    events_url: str = Field(default="")
    received_events_url: str = Field(default="")
    type: Literal["User", "Organization", "Bot"] = Field(default="User")
    site_admin: bool = Field(default=False)


class GithubOrganization(ModelWithExtra):
    login: str = Field(default="")
    id: int = Field(default=0)
    node_id: str = Field(default="")
    url: str = Field(default="")
    repos_url: str = Field(default="")
    events_url: str = Field(default="")
    hooks_url: str = Field(default="")
    issues_url: str = Field(default="")
    members_url: str = Field(default="")
    public_members_url: str = Field(default="")
    avatar_url: str = Field(default="")
    description: str | None = Field(default="")



class GithubRepo(ModelWithExtra):
    id: int = Field(default=0)
    node_id: str = Field(default="")
    name: str = Field(default="")
    full_name: str = Field(default="")
    private: bool = Field(default=False)
    owner: GithubUser = Field(default_factory=GithubUser)
    html_url: str = Field(default="")
    description: str | None = Field(default="")
    fork: bool = Field(default=False)
    url: str = Field(default="")
    forks_url: str = Field(default="")
    keys_url: str = Field(default="")
    collaborators_url: str = Field(default="")
    teams_url: str = Field(default="")
    hooks_url: str = Field(default="")
    issue_events_url: str = Field(default="")
    events_url: str = Field(default="")
    assignees_url: str = Field(default="")
    branches_url: str = Field(default="")
    tags_url: str = Field(default="")
    blobs_url: str = Field(default="")
    git_tags_url: str = Field(default="")
    git_refs_url: str = Field(default="")
    trees_url: str = Field(default="")
    statuses_url: str = Field(default="")
    languages_url: str = Field(default="")
    stargazers_url: str = Field(default="")
    contributors_url: str = Field(default="")
    subscribers_url: str = Field(default="")
    subscription_url: str = Field(default="")
    commits_url: str = Field(default="")
    git_commits_url: str = Field(default="")
    comments_url: str = Field(default="")
    issue_comment_url: str = Field(default="")
    contents_url: str = Field(default="")
    compare_url: str = Field(default="")
    merges_url: str = Field(default="")
    archive_url: str = Field(default="")
    downloads_url: str = Field(default="")
    issues_url: str = Field(default="")
    pulls_url: str = Field(default="")
    milestones_url: str = Field(default="")
    notifications_url: str = Field(default="")
    labels_url: str = Field(default="")
    releases_url: str = Field(default="")
    deployments_url: str = Field(default="")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    pushed_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    git_url: str = Field(default="")
    ssh_url: str = Field(default="")
    clone_url: str = Field(default="")
    svn_url: str = Field(default="")
    homepage: str | None = Field(default="")
    size: int = Field(default=0)
    stargazers_count: int = Field(default=0)
    watchers_count: int = Field(default=0)
    language: str = Field(default="")
    has_issues: bool = Field(default=False)
    has_projects: bool = Field(default=False)
    has_downloads: bool = Field(default=False)
    has_wiki: bool = Field(default=False)
    has_pages: bool = Field(default=False)
    has_discussions: bool = Field(default=False)
    forks_count: int = Field(default=0)
    mirror_url: Optional[str] = Field(default=None)
    archived: bool = Field(default=False)
    disabled: bool = Field(default=False)
    open_issues_count: int = Field(default=0)
    license: Optional[dict[str, Any]] = Field(default=None)
    default_branch: str = Field(default="main")
    topics: list[str] = Field(default_factory=list)
    visibility: Literal["public", "private", "visibility", "internal"] = Field(default="public")
    forks: int = Field(default=0)
    open_issues: int = Field(default=0)
    watchers: int = Field(default=0)


class GithubPRCommit(ModelWithExtra):
    label: str = Field(default="")
    ref: str = Field(default="")
    sha: str = Field(default="")
    user: GithubUser = Field(default_factory=GithubUser)
    repo: GithubRepo = Field(default_factory=GithubRepo)


class GithubInstallation(ModelWithExtra):
    id: int = Field(default=0)
    node_id: str = Field(default="")


class GithubPullRequest(ModelWithExtra):
    url: str = Field(default="")
    id: int = Field(default=0)
    node_id: str = Field(default="")
    html_url: str = Field(default="")
    diff_url: str = Field(default="")
    patch_url: str = Field(default="")
    issue_url: str = Field(default="")
    number: int = Field(default=0)
    state: Literal["open", "closed", "all"] = Field(default="open")
    locked: bool = Field(default=False)
    title: str = Field(default="")
    user: GithubUser = Field(default_factory=GithubUser)
    body: str = Field(default="")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    closed_at: Optional[datetime.datetime] = Field(default=None)
    merged_at: Optional[datetime.datetime] = Field(default=None)
    merge_commit_sha: Optional[str] = Field(default=None)
    assignee: Optional[GithubUser] = Field(default=None)
    assignees: list[GithubUser] = Field(default_factory=list)
    requested_reviewers: list[GithubUser] = Field(default_factory=list)
    requested_teams: list[dict[str, Any]] = Field(default_factory=list)
    labels: list[GithubLabel] = Field(default_factory=list)
    milestone: Optional[dict[str, Any]] = Field(default=None)
    draft: bool = Field(default=False)
    commits_url: str = Field(default="")
    review_comments_url: str = Field(default="")
    review_comment_url: str = Field(default="")
    comments_url: str = Field(default="")
    statuses_url: str = Field(default="")
    head: GithubPRCommit = Field(default_factory=GithubPRCommit)
    base: GithubPRCommit = Field(default_factory=GithubPRCommit)
    links: dict[str, Any] = Field(default_factory=dict, alias="_links")
    author_association: Literal[
        "COLLABORATOR",
        "CONTRIBUTOR",
        "FIRST_TIMER",
        "FIRST_TIME_CONTRIBUTOR",
        "MEMBER",
        "NONE",
        "OWNER",
    ] = Field(default="NONE")
    merged: bool = Field(default=False)
    mergeable: Optional[bool] = Field(default=None)
    rebaseable: Optional[bool] = Field(default=None)
    mergeable_state: Literal["behind", "blocked", "clean", "dirty", "unknown"] = Field(default=
        "unknown"
    )
    merged_by: Optional[GithubUser] = Field(default=None)
    comments: int = Field(default=0)
    review_comments: int = Field(default=0)
    maintainer_can_modify: bool = Field(default=False)
    commits: int = Field(default=0)
    additions: int = Field(default=0)
    deletions: int = Field(default=0)
    changed_files: int = Field(default=0)


class GithubPusher(ModelWithExtra):
    name: str = Field(default="")
    email: str = Field(default="")
    username: str = Field(default="")


class GithubCommit(ModelWithExtra):
    id: str = Field(default="")
    tree_id: str = Field(default="")
    distinct: bool = Field(default=False)
    message: str = Field(default="")
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    url: str = Field(default="")
    author: GithubPusher = Field(default_factory=GithubPusher)
    committer: GithubPusher = Field(default_factory=GithubPusher)
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    modified: list[str] = Field(default_factory=list)


class GithubRequestedAction(ModelWithExtra):
    identifier: str = Field(default="")



class GithubBaseEvent(ModelWithExtra):
    repository: GithubRepo = Field(default_factory=GithubRepo)
    organization: GithubOrganization = Field(default_factory=GithubOrganization)
    sender: GithubUser = Field(default_factory=GithubUser)
    _headers: GithubHeaders = PrivateAttr(default_factory=GithubHeaders)

class GithubEvent(GithubBaseEvent):
    installation: GithubInstallation = Field(default_factory=GithubInstallation)

class GithubEventPing(GithubBaseEvent):
    zen: str = Field(default="")
    hook_id: int = Field(default=0)
    hook: dict[str, Any] = Field(default_factory=dict)

class GithubEventPullRequestLabel(GithubEvent):
    action: PullRequestActionsEnum = Field(default=PullRequestActionsEnum.LABELED)
    number: int = Field(default=0)
    pull_request: GithubPullRequest = Field(default_factory=GithubPullRequest)
    label: GithubLabel = Field(default_factory=GithubLabel)


class GithubEventPullRequest(GithubEvent):
    action: PullRequestActionsEnum = Field(default=PullRequestActionsEnum.OPENED)
    number: int = Field(default=0)
    pull_request: GithubPullRequest = Field(default_factory=GithubPullRequest)


class GithubEventCheckRun(GithubEvent):
    action: CheckRunActionsEnum = Field(default=CheckRunActionsEnum.REQUESTED_ACTION)
    check_run: GithubCheckRun = Field(default_factory=GithubCheckRun)
    requested_action: GithubRequestedAction = Field(
        default_factory=GithubRequestedAction
    )


class GithubEventChecksuite(GithubEvent):
    action: CheckSuiteActionsEnum = Field(default=CheckSuiteActionsEnum.REQUESTED)
    check_suite: GithubCheckSuite = Field(default_factory=GithubCheckSuite)


class GithubEventPush(GithubEvent):
    ref: str = Field(default="")
    before: str = Field(default="")
    after: str = Field(default="")
    repository: GithubRepo = Field(default_factory=GithubRepo)
    pusher: GithubPusher = Field(default_factory=GithubPusher)
    created: bool = Field(default=False)
    deleted: bool = Field(default=False)
    forced: bool = Field(default=False)
    base_ref: Optional[str] = Field(default=None)
    compare: str = Field(default="")
    commits: list[GithubCommit] = Field(default_factory=list)
    head_commit: GithubCommit = Field(default_factory=GithubCommit)



class CreateGithubImage(BaseModel):
    alt: str = Field(default="")
    image_url: str = Field("")
    caption: str = Field("")

class CreateGithubAnnotation(BaseModel):
    path: str = Field(default="")
    start_line: int = Field(default=0)
    end_line: int = Field(default=0)
    annotation_level: Literal[
        "notice",
        "warning",
        "failure",
    ] = Field(default="notice")
    message: str = Field(default="")
    title: str = Field(default="")
    raw_details: str = Field(default="")


class CreateGithubCheckRunOutput(BaseModel):
    title: str = Field(default="")
    summary: str = Field(default="")
    text: str = Field(default="")
    annotations: list[CreateGithubAnnotation] = Field(default_factory=list)
    images: list[CreateGithubImage] = Field(default_factory=list)

class CreateGithubAction(BaseModel):
    label: str = Field(default="")
    description: str | None = Field(default="")
    identifier: str = Field(default="")


class SetGithubCheckRun(BaseModel):
    """ Base class for creating and updating Github check runs """
    name: str = Field() # required
    details_url: str = Field(default="")
    external_id: str = Field(default="")
    status: Literal[
        "queued",
        "in_progress",
        "completed",
    ] = Field(default="queued")
    started_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    completed_at: datetime.datetime | None = Field(default=None)
    conclusion: GithubCheckRunConclusionEnum | None = Field(default=None)
    output: GithubCheckRunOutput | None = Field(default=None)
    actions: list[dict[str, Any]] = Field(default_factory=list)

class CreateGithubCheckRun(SetGithubCheckRun):
    head_sha: str = Field(default="") # required

class UpdateGithubCheckRun(SetGithubCheckRun):
    pass

class GithubCommitStatusStateEnum(StrEnum):
    ERROR = "error"
    FAILURE = "failure"
    PENDING = "pending"
    SUCCESS = "success"


class CreateGithubCommitStatus(ModelWithExtra):
    state: GithubCommitStatusStateEnum = Field(default=GithubCommitStatusStateEnum.PENDING)
    target_url: str = Field(default="")
    description: str = Field(default="")
    context: str = Field(default="ffci")

class GithubCommitStatus(ModelWithExtra):
    state: GithubCommitStatusStateEnum = Field(default=GithubCommitStatusStateEnum.PENDING)
    target_url: str = Field(default="")
    description: str = Field(default="")
    context: str = Field(default="ffci")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    id: int = Field(default=0)
    url: str = Field(default="")
    avatar_url: str = Field(default="")
    creator: GithubUser = Field(default_factory=GithubUser)


GithubEvents: TypeAlias = Union[
    GithubEventPing,
    GithubEventPullRequest,
    GithubEventCheckRun,
    GithubEventChecksuite,
    GithubEventPush,
]

def github_event_factory(event: GithubBaseEvent) -> GithubEvents:
    print(event._headers)
    event_name: str = event._headers.x_github_event
    event_dict = event.model_dump()
    if event_name == "ping":
        return GithubEventPing.model_validate(event_dict)
    elif event_name == "pull_request":
        return GithubEventPullRequest.model_validate(event_dict)
    elif event_name == "check_run":
        return GithubEventCheckRun.model_validate(event_dict)
    elif event_name == "check_suite":
        return GithubEventChecksuite.model_validate(event_dict)
    elif event_name == "push":
        return GithubEventPush.model_validate(event_dict)
    else:
        raise NotImplementedError(f"Event {event_name} not implemented")
