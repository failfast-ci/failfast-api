from __future__ import absolute_import
from celery import Task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


class JobBase(Task):
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        pass

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        pass

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        pass

    def on_success(self, retval, task_id, args, kwargs):
        pass

    def task_queue(self):
        return self._app.amqp.routes[0].route_for_task(self.name)['queue']

    def task_routing_key(self):
        return self._app.amqp.routes[0].route_for_task(
            self.name)['routing_key']
