from hub2labhook.exception import Unsupported


class GithubEvent(object):
    def __init__(self, event, headers):
        self.event = event
        self.headers = headers
        self._refname = None

    @property
    def ref(self):
        if self.event_type == "push":
            ref = self.event['ref']
        elif self.event_type == "pull_request":
            ref = self.event['pull_request']['head']['ref']
        else:
            self._raise_unsupported()
        return ref

    def _parse_ref(self, ref):
        for header in ["refs/tags/", "refs/heads/"]:
            if str.startswith(str(ref), header):
                return ref.split(header)[1]
        return ref

    @property
    def refname(self):
        if not self._refname:
            self._refname = self._parse_ref(self.ref)
        if self.event_type == "push":
            return self._refname
        elif self.event_type == "pull_request":
            return "pr:%s:%s" % (self.event['pull_request']['head']['repo']['full_name'],
                                 self._refname)

    @property
    def event_type(self):
        return self.headers.get("X-GITHUB-EVENT", "push")

    @property
    def head_sha(self):
        if self.event_type == "push":
            sha = self.event['head_commit']['id']
        elif self.event_type == "pull_request":
            sha = self.event['pull_request']['head']['sha']
        else:
            self._raise_unsupported()
        return sha

    def _raise_unsupported(self):
        raise Unsupported("unsupported event: %s" % self.event_type,
                          {"event": self.event_type})

    @property
    def repo(self):
        if self.event_type not in ["push", "pull_request"]:
            self._raise_unsupported()

        return self.event['repository']['full_name']

    @property
    def user(self):
        if self.event_type == "push":
            user = self.event['pusher']['name']
        elif self.event_type == "pull_request":
            user = self.event['pull_request']['user']['login']
        else:
            self._raise_unsupported()
        return user

    def istag(self):
        return "tags" in self.ref
