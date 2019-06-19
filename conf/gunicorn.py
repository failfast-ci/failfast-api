from hub2labhook.config import logfile_path
from prometheus_client import multiprocess

logconfig = logfile_path(debug=False)
bind = 'unix:/tmp/gunicorn_registry.sock'
workers = 2
worker_class = 'gthread'
preload_app = True


def child_exit(server, worker):
    multiprocess.mark_process_dead(worker.pid)
