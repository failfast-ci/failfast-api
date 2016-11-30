import os


def getenv(value, envname, default=None):
    if not value:
        if default:
            value = os.getenv(envname, default)
        else:
            value = os.environ[envname]
    return value
