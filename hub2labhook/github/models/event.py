import json
import logging
from hub2labhook.exception import Unsupported

logger = logging.getLogger(__name__)

def target_refname(pr_id, refname):
    return "pr-%s-%s" % (pr_id, refname)

class GithubEvent(object):
    def __init__(self, event, headers):
        self.event = event
        self.headers = {str.upper(k): v for k, v in headers.items()}
        self._refname = None

    @property
    def external_id(self):
        if self.event_type in ["check_run"]:
            logger.info(self.event['check_run']['external_id'])
            return json.loads(self.event['check_run']['external_id'])
        else:
            self._raise_unsupported()

    @property
    def labels(self):
        if self.event_type == "pull_request":
            labels = [x["name"] for x in self.event['pull_request']['labels']]
        else:
            self._raise_unsupported()
        return labels

    @property
    def ref(self):
        if self.event_type == "push":
            ref = self.event['ref']
        elif self.event_type == "pull_request":
            ref = self.event['pull_request']['head']['ref']
        elif self.event_type == "check_run":
            ref = self.event["check_run"]["pull_requests"][0]["ref"]
        elif self.event_type == "check_suite":
            ref = self.event["check_suite"]["pull_requests"][0]["ref"]
        else:
            self._raise_unsupported()
        return ref

    def _parse_ref(self, ref):
        for header in ["refs/tags/", "refs/heads/"]:
            if str.startswith(str(ref), header):
                return ref.split(header)[1]
        return ref

    @property
    def pr_id(self):
        if self.event_type != "pull_request":
            return ""
        return self.event['number']

    @property
    def commit_message(self):
        if self.event_type == "push":
            ref = self.event['head_commit']['message']
        elif self.event_type == "pull_request":
            ref = self.event['pull_request']['title']
        else:
            self._raise_unsupported()
        return ref

    @property
    def commit_url(self):
        if self.event_type == "push":
            ref = self.event['head_commit']['url']
        elif self.event_type == "pull_request":
            ref = self.event['pull_request']['html_url']
        else:
            self._raise_unsupported()
        return ref

    @property
    def clone_url(self):
        return self.event['repository']['clone_url']

    @property
    def installation_id(self):
        return self.event['installation']['id']

    @property
    def refname(self):
        if self.event_type not in [
                "push", "pull_request", "check_suite", "check_run"
        ]:
            self._raise_unsupported()

        if not self._refname:
            self._refname = self._parse_ref(self.ref)

        return self._refname

    @property
    def target_refname(self):
        if self.event_type == "push":
            return self.ref
        elif self.event_type == "pull_request":
            return target_refname(self.pr_id, self.ref)
        else:
            self._raise_unsupported()

    @property
    def event_type(self):
        print(self.headers)
        return self.headers.get("X-GITHUB-EVENT", "push")

    @property
    def comment(self):
        if self.event_type == "issue_comment":
            return self.event['issue']['comment']['body']
        else:
            self._raise_unsupported()
        return None

    @property
    def author_association(self):
        return self.event['issue']['comment']['author_association']

    @property
    def action(self):
        return self.event['action']

    @property
    def label(self):
        if self.event_type != "pull_request" and self.action != "labeled":
            self._raise_unsupported()
        return self.event['pull_request']['label']['name']

    @property
    def pull_request_url(self):
        return self.event['issue']['pull_request']['url']

    @property
    def head_sha(self):
        if self.event_type == "push":
            sha = self.event['head_commit']['id']
        elif self.event_type == "pull_request":
            sha = self.event['pull_request']['head']['sha']
        elif self.event_type == "check_run":
            sha = self.event["check_run"]["head_sha"]
        elif self.event_type == "check_suite":
            sha = self.event["check_suite"]["head_sha"]
        else:
            self._raise_unsupported()
        return sha

    def _raise_unsupported(self):
        raise Unsupported("unsupported event: %s" % self.event_type, {
            "event": self.event_type
        })

    @property
    def repo(self):
        if self.event_type not in [
                "push", "pull_request", "check_run", "check_suite"
        ]:
            self._raise_unsupported()

        return self.event['repository']['full_name']

    @property
    def pr_repo(self):
        if self.event_type not in ["pull_request"]:
            self._raise_unsupported()
        return self.event['pull_request']['head']['repo']['full_name']

    @property
    def user(self):
        if self.event_type == "push":
            user = self.event['pusher']['name']
        elif self.event_type == "pull_request":
            user = self.event['pull_request']['user']['login']
        elif self.event_type == "issue_comment":
            user = self.event['issue']['comment']['user']['login']
        else:
            self._raise_unsupported()
        return user

    def istag(self):
        return "tags" in self.ref

    @property
    def source_repo(self):
        if self.pr_id == "":
            source_repo = self.repo
        else:
            source_repo = self.pr_repo
        return source_repo
