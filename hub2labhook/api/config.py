from hub2labhook.config import FFCONFIG


class Config(object):
    """ Default configuration """
    DEBUG = FFCONFIG.failfast['debug']
    GITLAB_TOKEN = FFCONFIG.gitlab['secret_token']
    GITLAB_API = FFCONFIG.gitlab['gitlab_url']


class ProductionConfig(Config):
    """ Production configuration """


class DevelopmentConfig(Config):
    """ Development configuration """
    DEBUG = True
