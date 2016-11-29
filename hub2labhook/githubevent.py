from hub2labhook.exception import Unsupported


class GithubEvent(object):
    def __init__(self, event, headers):
        self.event = event
        self.headers = headers

    @property
    def ref(self):
        if self.event_type == "push":
            ref = self.event['ref']
        elif self.event_type == "pull_request":
            ref = self.event['pull_request']['head']['ref']
        else:
            raise Unsupported("unsupported event: %s" % self.event_type,
                              {"event": self.event_type})
        return ref

    def ref_name(self):
        return self.ref.split("/")[-1]

    @property
    def event_type(self):
        return self.headers.get("HTTP_X_GITHUB_EVENT", "push")

    @property
    def uuid(self):
        return self.headers.get("HTTP_X_REQUEST_ID", None)

    @property
    def head_sha(self):
        if self.event_type == "push":
            sha = self.event['head_commit']['id']
        elif self.event_type == "pull_request":
            sha = self.event['pull_request']['head']['sha']
        else:
            raise Unsupported("unsupported event: %s" % self.event_type,
                              {"event": self.event_type})
        return sha

    @property
    def repo(self):
        return self.event['repository']['full_name']

    @property
    def user(self):
        if self.event_type == "push":
            user = self.event['pusher']['name']
        elif self.event_type == "pull_request":
            user = self.event['pull_request']['user']['login']
        else:
            raise Unsupported("unsupported event: %s" % self.event_type,
                              {"event": self.event_type})
        return user

    def istag(self):
        return "tags" in self.ref

    def to_dict(self):
        details = {
            "repo": self.repo,
            "sha": self.head_sha,
            "ref": self.ref,
            "istag": self.istag(),
            "refname": self.ref_name(),
            "user": self.user
        }
        return details
