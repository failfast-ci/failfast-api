from ffci.client.github.models import GithubEvents

class GithubEventFactory(object):
    def __init__(self, event: GithubEvents, event_name: str | None = "push"):
        self.event = event
        self.event_name
        self._refname = None
