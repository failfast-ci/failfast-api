import click
import yaml

from ffci.config import LOGGING_CONFIG, ConfigSchema, LoggingConfigSchema


@click.command()
def default_config() -> None:
    config = ConfigSchema(logging=LoggingConfigSchema(log_config=LOGGING_CONFIG))
    print(yaml.dump(config.dict(), default_flow_style=False))
