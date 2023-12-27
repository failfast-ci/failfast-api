import os
import platform
import subprocess
from typing import Any

import ffci


def get_git_sha():
    if os.path.exists("GIT_HEAD"):
        with open("GIT_HEAD", "r", encoding="utf-8") as openf:
            return openf.read()
    else:
        try:
            return (
                subprocess.check_output(["git", "rev-parse", "HEAD"])
                .strip()[0:8]
                .decode()
            )
        except (OSError, subprocess.CalledProcessError):
            pass
    return "unknown"


class Version:
    def __init__(self):
        self.version: dict[str, Any] = {
            "version": ffci.__version__,
            "python": {
                "version": platform.python_version(),
                "implementation": platform.python_implementation(),
            },
            "system": platform.system(),
            "sha": get_git_sha(),
        }

    def __str__(self) -> str:
        return self.text()

    @property
    def app_version(self) -> str:
        return self.version["version"]

    def to_dict(self) -> dict[str, Any]:
        return self.version

    def text(self) -> str:
        return ", ".join(
            [
                f"Running ffci {self.version['version']}",
                f"with {self.version['python']['implementation']} {self.version['python']['version']}",
                f"on {self.version['system']}",
            ]
        )


VERSION = Version()
