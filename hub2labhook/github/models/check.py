from __future__ import absolute_import, unicode_literals
from datetime import datetime
import json
import logging

from hub2labhook.config import FFCONFIG
from hub2labhook.github.client import GITHUB_CHECK_MAP
from hub2labhook.exception import Unexpected

logger = logging.getLogger(__name__)


class CheckStatus(object):
    def __init__(self, obj):
        self.object = obj
        if self.object_kind not in ['pipeline', 'build']:
            raise Unexpected("Object kind unknown %s" % self.object_kind)

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
            return self.object['project']['web_url']
        elif self.object_kind == "build":
            return self.object['repository']['homepage']

    def build_trace_url(self, build_id):
        return self.build_url(build_id) + "/trace"

    @property
    def sha(self):
        if self.object_kind == "pipeline":
            return self.object['object_attributes']['sha']
        else:
            return self.object['sha']

    def build_url(self, build_id):
        return self.repourl + "/builds/%s" % build_id

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
            return self.object['object_attributes']['id']
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

    @classmethod
    def list_task_actions(cls):
        return list(cls.task_actions().values())

    def check_name(self):
        if self.object_kind == "build":
            return "%s/-/%s" % (FFCONFIG.github['context'],
                                self.object['build_name'])
        else:
            return "%s/%s" % (FFCONFIG.github['context'], "Pipeline")

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
            started = self.object['build_started_at']
        elif self.object_kind == "pipeline":
            started = self.object['object_attributes']['created_at']

        if started is None:
            return None
        return self.ztime(started)

    @property
    def finished_at(self):
        if self.object_kind == "build":
            finished = self.object['build_finished_at']
        else:
            finished = self.object['object_attributes']['finished_at']

        if finished is None:
            return None
        return self.ztime(finished)

    @property
    def completed_at(self):
        return self.finished_at

    @property
    def status(self):
        if not self.started_at:
            check_status = "queued"
        elif not self.finished_at:
            check_status = "in_progress"
        else:
            check_status = "completed"
        return check_status

    @property
    def conclusion(self):
        if self.status != "completed":
            return None
        else:
            return GITHUB_CHECK_MAP[self.gitlab_status]

    @property
    def gitlab_status(self):
        if self.object_kind == "build":
            # If allow_failure, set check-status to 'neutral'
            if self.object['build_status'] == "failed" and self.object['build_allow_failure'] is True:
                return 'allow_failure'
            return self.object['build_status']
        else:
            return self.object['object_attributes']['status']

    def render_check(self):
        check = {
            "name": self.check_name(),
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "conclusion": self.conclusion,
            "head_sha": self.sha,
            "external_id": json.dumps(self.external_id),
            "details_url": self.details_url,
            "output": self.check_output(),
            "actions": self.list_task_actions()
        }
        check = {k: v for k, v in check.items() if v is not None}
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

