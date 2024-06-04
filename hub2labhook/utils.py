import time
from threading import Thread


class DelayedRequest(Thread):
    def __init__(self, delay, func):
        Thread.__init__(self)
        self.delay = delay
        self.func = func

    def run(self):
        time.sleep(self.delay)
        self.func()


def pretty_time_delta(seconds):
    if seconds is None:
        return "-"
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days > 0:
        return '%dd %dh% dm %ds' % (days, hours, minutes, seconds)
    elif hours > 0:
        return '%dh %dm %ds' % (hours, minutes, seconds)
    elif minutes > 0:
        return '%dm %ds' % (minutes, seconds)
    else:
        return '%ds' % (seconds, )


def clone_url_with_auth(base_url, auth):
    return base_url.replace("https://", "https://%s@" % auth)


def strtobool(s):
    if s in ["yes", "on", "true", "True", "TRUE"]:
        return True
    else:
        return False
