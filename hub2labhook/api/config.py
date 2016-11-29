import os


class Config(object):
    """ Default configuration """
    DEBUG = False
    GITLAB_TOKEN = os.getenv('GITLAB_TOKEN', "changeme")


class ProductionConfig(Config):
    """ Production configuration """


class DevelopmentConfig(Config):
    """ Development configuration """
    DEBUG = True
