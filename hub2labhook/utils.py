import os
import time
from threading import Thread


def getenv(value, envname, default=None):
    if not value:
        if default:
            value = os.getenv(envname, default)
        else:
            value = os.environ[envname]
    return value


class DelayedRequest(Thread):
    def __init__(self, delay, func):
        Thread.__init__(self)
        self.delay = delay
        self.func = func

    def run(self):
        time.sleep(self.delay)
        self.func()


def clone_url_with_auth(base_url, auth):
    return base_url.replace("https://", "https://%s@" % auth)
