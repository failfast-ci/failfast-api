import os
from ffci.config import GConfig


def test_config_test_env():
    assert GConfig().app.env == "test"

def test_config_github():
    assert GConfig().github.secret_token == "secret"
    assert GConfig().github.context == "ffci"
    assert GConfig().github.integration_id == 266

def test_config_gitlab():
    assert GConfig().gitlab.namespace == "ffci"

def test_config_fields():
    assert GConfig().sentry.dsn == None
    assert GConfig().temporalio.host == "localhost:7233"
    assert GConfig().server.port == 8080
    assert GConfig().logging.level == "info"
    assert GConfig().conf.app.env == "test"
    assert GConfig().ffci.authorized_users == []

def test_config_reinit():
    conf = GConfig().dump()
    GConfig.reinit()
    assert GConfig().dump() == conf
    # Changes are ignored without reinit
    GConfig("tests/data/config-2.yaml")
    assert GConfig().dump() == conf
    # Changes are applied after reinit
    GConfig.reinit()
    GConfig("tests/data/config-2.yaml")
    assert GConfig().dump() != conf


def test_config_path_load():
    GConfig.reinit()
    GConfig("tests/data/config-2.yaml")
    assert GConfig().app.env == "test-2"

def test_config_path_load_from_env(monkeypatch):
    GConfig.reinit()
    monkeypatch.setattr(os, 'environ', {'FFCI_CONFIG': 'tests/data/config-2.yaml'})
    assert GConfig().app.env == "test-2"

def test_config_path_failed_path_fallback():
    GConfig.reinit()
    GConfig("tests/data/config-dontexist.yaml")
    assert GConfig().app.env == "dev"
