"""
Runtime options derived from environment name
"""

import os
from iziconf import Iziconf

LOCAL_DIR = os.path.dirname(__file__)
DEFAULT_ENV = os.getenv("HUB2LAB_ENV", "development")

default_conf = {
    "envvar_name": "HUB2LAB_SETTINGS_FILE",
    "settings_file": LOCAL_DIR + "/../conf/" + DEFAULT_ENV + ".yaml",
    "callback": None
}

options = Iziconf(default_conf)
