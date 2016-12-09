from __future__ import absolute_import, unicode_literals

from hub2labhook.githubevent import GithubEvent
from hub2labhook.pipeline import Pipeline

from .runner import app
from .job_base import JobBase


@app.task(bind=True, base=JobBase, retry=3)
def pipeline(self, event, headers):
    gevent = GithubEvent(event, headers)
    pipeline = Pipeline(gevent)
    return pipeline.trigger_pipeline()
