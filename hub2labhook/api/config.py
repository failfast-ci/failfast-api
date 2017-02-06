import os


class Config(object):
    """ Default configuration """
    DEBUG = True
    GITLAB_TOKEN = os.getenv('GITLAB_TOKEN', "changeme")
    GITLAB_API = os.getenv('GITLAB_API', "https://gitlab.com")


class ProductionConfig(Config):
    """ Production configuration """


class DevelopmentConfig(Config):
    """ Development configuration """
    DEBUG = True
