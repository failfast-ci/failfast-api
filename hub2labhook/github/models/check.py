from __future__ import absolute_import, unicode_literals
from datetime import datetime
import json
import logging

from hub2labhook.config import FFCONFIG
from hub2labhook.github.client import GITHUB_CHECK_MAP

logger = logging.getLogger(__name__)


class CheckStatus(object):
    def __init__(self, object):
        self.object = object

    @classmethod
    def ztime(cls, timestr=None):
        if timestr is None:
            return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            return datetime.strptime(timestr,
                                     "%Y-%m-%d %H:%M:%S %Z").isoformat() + "Z"

    @classmethod
    def task_actions(cls, extra_actions=None):
        actions = {
            "retry": {
                "label": "retry",
                "identifier": "retry",
                "description": "Retries the job"
            },
            "skip": {
                "label": "Skip test",
                "identifier": "skip",
                "description": "Marks the job as neutral"
            },
            "resync": {
                "label": "Resync status",
                "identifier": "resync",
                "description": "Resync the status from gitlab"
            }
        }

        if extra_actions:
            actions.update(extra_actions)
        return actions

    @property
    def object_kind(self):
        return self.object['object_kind']

    @property
    def repourl(self):
        if self.object_kind == "pipeline":
            return self.object['project']['web_ur']
        elif self.object_kind == "build":
            return self.object['repository']['homepage']

    def build_trace_url(self, build_id):
        self.build_url(build_id) + "/trace"

    @property
    def sha(self):
        self.object['sha']

    def build_url(self, build_id):
        return self.repourl + "/builds/%s" % build_id,

    def pipeline_url(self, pipeline_id):
        return self.repourl + "/pipelines/%s" % pipeline_id

    @property
    def details_url(self):
        if self.object_kind == "pipeline":
            return self.pipeline_url(self.object_id)
        elif self.object_kind == "build":
            return self.build_url(self.object_id)

    @property
    def object_id(self):
        if self.object_kind == "pipeline":
            return self.object['id']
        elif self.object_kind == "build":
            return self.object['build_id']

    @property
    def project_id(self):
        if self.object_kind == "pipeline":
            return self.object['project']['id']
        elif self.object_kind == "build":
            return self.object['project_id']

    @property
    def external_id(self):
        return {
            'object_kind': self.object_kind,
            'object_id': self.object_id,
            'project_id': self.project_id
        }

    def check_name(self):
        if self.object_kind == "build":
            return "%s/job/%s" % (FFCONFIG.github['context'],
                                  self.object['build_name'])
        else:
            return "%s/%s" % (FFCONFIG.github['context'], "pipeline")

    def check_output(self):
        if self.object_kind == "build":
            output = {
                "title": self.check_title(),
                "summary": self.check_summary(),
                "text": self.check_text(),
            }
        else:
            output = {
                "title": self.check_pipeline_title(),
                "summary": self.check_pipeline_summary(),
                "text": self.check_pipeline_text(),
            }
        return output

    @property
    def started_at(self):
        if self.object_kind == "build":
            return self.object['build_started_at']
        else:
            return self.object['created_at']

    @property
    def finished_at(self):
        if self.object_kind == "build":
            return self.object['build_finished_at']
        else:
            return self.object['finished_at']

    @property
    def status(self):
        if self.object_kind == "build":
            # If allow_failure, set check-status to 'neutral'
            if self.object['build_status'] == "failed" and self.object['build_allow_failure'] is True:
                status = 'allow_failure'
            status = self.object['build_status']
        else:
            status = self.object['status']
        return status

    def _set_status(self, started_at, finished_at, gitlab_status):
        extra = {'conclusion': None, 'started_at': None, 'completed_at': None}
        if not started_at:
            check_status = "queued"
        elif not finished_at:
            check_status = "in_progress"
            extra['started_at'] = self.ztime(started_at)
        else:
            check_status = "completed"
            extra['conclusion'] = GITHUB_CHECK_MAP[gitlab_status]
            extra['started_at'] = self.ztime(started_at)
            extra['completed_at'] = self.ztime(finished_at)

        extra['status'] = check_status

        return {k: v for k, v in extra.items() if v is not None}

    def render_check(self):
        check = self._set_status(self.started_at, self.finished_at,
                                 self.status)
        check.update({
            "name": self.check_name(),
            "head_sha": self.sha,
            "external_id": json.dumps(self.external_id),
            "details_url": self.details_url,
            "output": self.check_output(),  # noqa
            "actions": self.task_actions().values()
        })
        logger.info(check)
        return check

    def check_title(self):
        return "%s/%s" % (self.object['build_stage'],
                          self.object['build_name'])

    def check_summary(self):
        return "%s/%s" % (self.object['build_name'], self.status)

    def check_text(self):
        return ("# %s/%s" %
                (self.object['build_stage'], self.object['build_name']) +
                "\n\n ## Trace available: %s" % self.details_url)

    def check_pipeline_title(self):
        return "pipeline/%s" % (self.object_id)

    def check_pipeline_summary(self):
        return "pipeline %s: %s" % (self.object_id, self.status)

    def check_pipeline_text(self):
        return "pipeline %s: %s" % (self.object_id, self.status)
