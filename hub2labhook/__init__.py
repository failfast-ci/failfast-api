# -*- coding: utf-8 -*-
import os
import subprocess

__author__ = 'Antoine Legrand'
__email__ = '2t.antoine@gmail.com'
__version__ = '0.4.1'


def _get_git_sha():
    if os.path.exists("GIT_HEAD"):
        with open("GIT_HEAD", "r") as f:
            return f.read()
    else:
        try:
            return subprocess.check_output(["git", "rev-parse",
                                            "HEAD"]).strip()[0:8].decode()
        except (OSError, subprocess.CalledProcessError):
            pass
    return "unknown"


__gitsha__ = _get_git_sha()
