#!/usr/bin/env python3
# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods
import datetime
import logging
from enum import StrEnum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class ModelWithExtra(BaseModel):
    model_config = ConfigDict(extra="allow")


class GithubHeaders(ModelWithExtra):
    x_hub_signature_256: str = Field(alias="X-Hub-Signature-256")
    x_hub_signature: str = Field(alias="X-Hub-Signature")
    x_github_event: str = Field(alias="X-GitHub-Event")
    x_github_delivery: str = Field(alias="X-GitHub-Delivery")
    x_github_hook_id: str = Field(alias="X-GitHub-Hook-ID")
    x_github_hook_installation_target_id: str = Field(
        alias="X-GitHub-Hook-Installation-Target-ID"
    )
    x_github_hook_installation_target_type: str = Field(
        alias="X-GitHub-Hook-Installation-Target-Type"
    )


class GithubCheckRunOutput(ModelWithExtra):
    title: str = Field("")
    summary: str = Field("")
    text: str = Field("")
    annotations_count: int = Field(0)
    annotations_url: str = Field("")


class GithubCheckRunPRRepo(ModelWithExtra):
    id: int = Field(0)
    url: str = Field("")
    name: str = Field("")


class GithubCheckRunPRCommit(ModelWithExtra):
    ref: str = Field("")
    sha: str = Field("")
    repo: GithubCheckRunPRRepo = Field(default_factory=GithubCheckRunPRRepo)


class GithubCheckRunPR(ModelWithExtra):
    url: str = Field("")
    id: int = Field(0)
    number: int = Field(0)
    head: GithubCheckRunPRCommit = Field(default_factory=GithubCheckRunPRCommit)
    base: GithubCheckRunPRCommit = Field(default_factory=GithubCheckRunPRCommit)


class GithubCheckSuite(ModelWithExtra):
    id: int = Field(0)
    node_id: str = Field("")
    head_branch: str = Field("")
    head_sha: str = Field("")
    status: Literal[
        "queued",
        "in_progress",
        "completed",
    ] = Field("queued")
    conclusion: Literal[
        "success",
        "failure",
        "neutral",
        "cancelled",
        "timed_out",
        "action_required",
        "stale",
    ] | None = Field("neutral")
    url: str = Field("")
    before: str = Field("")
    after: str = Field("")
    pull_requests: list[GithubCheckRunPR] = Field(default_factory=list)
    app: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)


class GithubCheckRun(ModelWithExtra):
    id: int = Field(0)
    node_id: str = Field("")
    head_sha: str = Field("")
    external_id: str = Field("")
    url: str = Field("")
    html_url: str = Field("")
    details_url: str = Field("")
    status: Literal[
        "queued",
        "in_progress",
        "completed",
    ] = Field("queued")
    conclusion: Literal[
        "success",
        "failure",
        "neutral",
        "cancelled",
        "timed_out",
        "action_required",
        "stale",
    ] | None = Field("neutral")
    started_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    completed_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    output: GithubCheckRunOutput = Field(default_factory=GithubCheckRunOutput)
    name: str = Field("")
    check_suite: GithubCheckSuite = Field(default_factory=GithubCheckSuite)
    app: dict[str, Any] = Field(default_factory=dict)
    pull_requests: list[GithubCheckRunPR] = Field(default_factory=list)


# Model for Github webhook
class GithubUser(ModelWithExtra):
    login: str = Field("")
    id: int = Field(0)
    node_id: str = Field("")
    avatar_url: str = Field("")
    gravatar_id: str = Field("")
    url: str = Field("")
    html_url: str = Field("")
    followers_url: str = Field("")
    following_url: str = Field("")
    gists_url: str = Field("")
    starred_url: str = Field("")
    subscriptions_url: str = Field("")
    organizations_url: str = Field("")
    repos_url: str = Field("")
    events_url: str = Field("")
    received_events_url: str = Field("")
    type: Literal["User", "Organization", "Bot"] = Field("User")
    site_admin: bool = Field(False)


class GithubOrganization(ModelWithExtra):
    login: str = Field("")
    id: int = Field(0)
    node_id: str = Field("")
    url: str = Field("")
    repos_url: str = Field("")
    events_url: str = Field("")
    hooks_url: str = Field("")
    issues_url: str = Field("")
    members_url: str = Field("")
    public_members_url: str = Field("")
    avatar_url: str = Field("")
    description: str = Field("")


class GithubLabel(ModelWithExtra):
    id: int = Field(0)
    node_id: str = Field("")
    url: str = Field("")
    name: str = Field("")
    color: str = Field("")
    default: bool = Field(False)
    description: str = Field("")


class GithubRepo(ModelWithExtra):
    id: int = Field(0)
    node_id: str = Field("")
    name: str = Field("")
    full_name: str = Field("")
    private: bool = Field(False)
    owner: GithubUser = Field(default_factory=GithubUser)
    html_url: str = Field("")
    description: str = Field("")
    fork: bool = Field(False)
    url: str = Field("")
    forks_url: str = Field("")
    keys_url: str = Field("")
    collaborators_url: str = Field("")
    teams_url: str = Field("")
    hooks_url: str = Field("")
    issue_events_url: str = Field("")
    events_url: str = Field("")
    assignees_url: str = Field("")
    branches_url: str = Field("")
    tags_url: str = Field("")
    blobs_url: str = Field("")
    git_tags_url: str = Field("")
    git_refs_url: str = Field("")
    trees_url: str = Field("")
    statuses_url: str = Field("")
    languages_url: str = Field("")
    stargazers_url: str = Field("")
    contributors_url: str = Field("")
    subscribers_url: str = Field("")
    subscription_url: str = Field("")
    commits_url: str = Field("")
    git_commits_url: str = Field("")
    comments_url: str = Field("")
    issue_comment_url: str = Field("")
    contents_url: str = Field("")
    compare_url: str = Field("")
    merges_url: str = Field("")
    archive_url: str = Field("")
    downloads_url: str = Field("")
    issues_url: str = Field("")
    pulls_url: str = Field("")
    milestones_url: str = Field("")
    notifications_url: str = Field("")
    labels_url: str = Field("")
    releases_url: str = Field("")
    deployments_url: str = Field("")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    pushed_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    git_url: str = Field("")
    ssh_url: str = Field("")
    clone_url: str = Field("")
    svn_url: str = Field("")
    homepage: str = Field("")
    size: int = Field(0)
    stargazers_count: int = Field(0)
    watchers_count: int = Field(0)
    language: str = Field("")
    has_issues: bool = Field(False)
    has_projects: bool = Field(False)
    has_downloads: bool = Field(False)
    has_wiki: bool = Field(False)
    has_pages: bool = Field(False)
    has_discussions: bool = Field(False)
    forks_count: int = Field(0)
    mirror_url: Optional[str] = Field(None)
    archived: bool = Field(False)
    disabled: bool = Field(False)
    open_issues_count: int = Field(0)
    license: Optional[dict[str, Any]] = Field(None)
    default_branch: str = Field("main")
    topics: list[str] = Field(default_factory=list)
    visibility: Literal["public", "private", "visibility", "internal"] = Field("public")
    forks: int = Field(0)
    open_issues: int = Field(0)
    watchers: int = Field(0)


class GithubPRCommit(ModelWithExtra):
    label: str = Field("")
    ref: str = Field("")
    sha: str = Field("")
    user: GithubUser = Field(default_factory=GithubUser)
    repo: GithubRepo = Field(default_factory=GithubRepo)


class GithubInstallation(ModelWithExtra):
    id: int = Field(0)
    node_id: str = Field("")


class GithubPullRequest(ModelWithExtra):
    url: str = Field("")
    id: int = Field(0)
    node_id: str = Field("")
    html_url: str = Field("")
    diff_url: str = Field("")
    patch_url: str = Field("")
    issue_url: str = Field("")
    number: int = Field(0)
    state: Literal["open", "closed", "all"] = Field("open")
    locked: bool = Field(False)
    title: str = Field("")
    user: GithubUser = Field(default_factory=GithubUser)
    body: str = Field("")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    closed_at: Optional[datetime.datetime] = Field(None)
    merged_at: Optional[datetime.datetime] = Field(None)
    merge_commit_sha: Optional[str] = Field(None)
    assignee: Optional[GithubUser] = Field(None)
    assignees: list[GithubUser] = Field(default_factory=list)
    requested_reviewers: list[GithubUser] = Field(default_factory=list)
    requested_teams: list[dict[str, Any]] = Field(default_factory=list)
    labels: list[GithubLabel] = Field(default_factory=list)
    milestone: Optional[dict[str, Any]] = Field(None)
    draft: bool = Field(False)
    commits_url: str = Field("")
    review_comments_url: str = Field("")
    review_comment_url: str = Field("")
    comments_url: str = Field("")
    statuses_url: str = Field("")
    head: GithubPRCommit = Field(default_factory=GithubPRCommit)
    base: GithubPRCommit = Field(default_factory=GithubPRCommit)
    _links: dict[str, Any] = Field(default_factory=dict)
    author_association: Literal[
        "COLLABORATOR",
        "CONTRIBUTOR",
        "FIRST_TIMER",
        "FIRST_TIME_CONTRIBUTOR",
        "MEMBER",
        "NONE",
        "OWNER",
    ] = Field("NONE")
    merged: bool = Field(False)
    mergeable: Optional[bool] = Field(None)
    rebaseable: Optional[bool] = Field(None)
    mergeable_state: Literal["behind", "blocked", "clean", "dirty", "unknown"] = Field(
        "unknown"
    )
    merged_by: Optional[GithubUser] = Field(None)
    comments: int = Field(0)
    review_comments: int = Field(0)
    maintainer_can_modify: bool = Field(False)
    commits: int = Field(0)
    additions: int = Field(0)
    deletions: int = Field(0)
    changed_files: int = Field(0)


class GithubPusher(ModelWithExtra):
    name: str = Field("")
    email: str = Field("")
    username: str = Field("")


class GithubCommit(ModelWithExtra):
    id: str = Field("")
    tree_id: str = Field("")
    distinct: bool = Field(False)
    message: str = Field("")
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    url: str = Field("")
    author: GithubPusher = Field(default_factory=GithubPusher)
    committer: GithubPusher = Field(default_factory=GithubPusher)
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    modified: list[str] = Field(default_factory=list)


class GithubRequestedAction(ModelWithExtra):
    identifier: str = Field("")


class CheckSuiteActions(StrEnum):
    REQUESTED = "requested"
    REREQUESTED = "rerequested"
    COMPLETED = "completed"


class GithubEvents(StrEnum):
    CHECK_SUITE = "check_suite"
    CHECK_RUN = "check_run"
    PULL_REQUEST = "pull_request"
    PUSH = "push"


class CheckRunActions(StrEnum):
    REQUESTED = "requested"
    REQUESTED_ACTION = "requested_action"
    COMPLETED = "completed"
    CREATED = "created"


class PullRequestActions(StrEnum):
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


class GithubEvent(ModelWithExtra):
    repository: GithubRepo = Field(default_factory=GithubRepo)
    organization: GithubOrganization = Field(default_factory=GithubOrganization)
    sender: GithubUser = Field(default_factory=GithubUser)
    installation: GithubInstallation = Field(default_factory=GithubInstallation)


class GithubEventPullRequest(GithubEvent):
    action: PullRequestActions = Field(PullRequestActions.OPENED)
    number: int = Field(0)
    pull_request: GithubPullRequest = Field(default_factory=GithubPullRequest)


class GithubEventCheckRun(GithubEvent):
    action: CheckRunActions = Field(CheckRunActions.REQUESTED_ACTION)
    check_run: GithubCheckRun = Field(default_factory=GithubCheckRun)
    requested_action: GithubRequestedAction = Field(
        default_factory=GithubRequestedAction
    )


class GithubEventChecksuite(GithubEvent):
    action: CheckSuiteActions = Field(CheckSuiteActions.REQUESTED)
    check_suite: GithubCheckSuite = Field(default_factory=GithubCheckSuite)


class GithubEventPush(GithubEvent):
    ref: str = Field("")
    before: str = Field("")
    after: str = Field("")
    repository: GithubRepo = Field(default_factory=GithubRepo)
    pusher: GithubPusher = Field(default_factory=GithubPusher)
    created: bool = Field(False)
    deleted: bool = Field(False)
    forced: bool = Field(False)
    base_ref: Optional[str] = Field(None)
    compare: str = Field("")
    commits: list[GithubCommit] = Field(default_factory=list)
    head_commit: GithubCommit = Field(default_factory=GithubCommit)
