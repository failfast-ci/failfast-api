import sys
import os
from hub2labhook.api.app import create_app
from hub2labhook.config import FFCONFIG


metrics_dir = FFCONFIG.failfast['metrics_dir']

os.environ['prometheus_multiproc_dir'] = metrics_dir
if not os.path.exists(metrics_dir):
    os.mkdir(metrics_dir)

ffapp = create_app()
app = ffapp.app
