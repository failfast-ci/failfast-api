from hub2labhook.config import (GITLAB_SECRET_TOKEN, GITLAB_API)


class Config(object):
    """ Default configuration """
    DEBUG = True
    GITLAB_TOKEN = GITLAB_SECRET_TOKEN
    GITLAB_API = GITLAB_API


class ProductionConfig(Config):
    """ Production configuration """


class DevelopmentConfig(Config):
    """ Development configuration """
    DEBUG = True
