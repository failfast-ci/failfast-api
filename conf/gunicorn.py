import sys
import os
from hub2labhook.config import logfile_path



logconfig = logfile_path(debug=False)
bind = 'unix:/tmp/gunicorn_registry.sock'
workers = 2
worker_class = 'gthread'
preload_app = True
