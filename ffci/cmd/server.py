import logging

import click
import uvicorn

from ffci.config import LOG_LEVELS, Config, GConfig
from ffci.init import init
from ffci.server.server import serve

LEVEL_CHOICES = click.Choice(list(LOG_LEVELS.keys()))
logger = logging.getLogger("ffci.info")


def run_server(config: Config):
    logger.info("Starting server")
    click.echo(f"{config.server.model_dump()}")
    init("fastapi")
    uvicorn.run(
        serve,
        host=config.server.host,
        port=config.server.port,
        log_level=config.logging.level,
        # log_config=config.logging.log_config,
        use_colors=config.logging.use_colors,
        reload=config.server.reload,
        factory=True,
    )


# pylint: disable=no-value-for-parameter
# pylint: disable=too-many-arguments
@click.command(context_settings={"auto_envvar_prefix": "FASTAPI"})
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default=None,
    help="Configuration file in YAML format.",
    show_default=True,
)
@click.option(
    "--host",
    type=str,
    default=None,
    help="Address of the server",
    show_default=True,
)
@click.option(
    "--temporal-host",
    type=str,
    default=None,
    help="Address of the server",
    show_default=True,
)
@click.option(
    "--log-config",
    type=click.Path(exists=True),
    default=None,
    help="Logging configuration file. Supported formats: .ini, .json, .yaml.",
    show_default=True,
)
@click.option(
    "--log-level",
    type=LEVEL_CHOICES,
    default="info",
    help="Log level.",
    show_default=True,
)
@click.option(
    "--use-colors/--no-use-colors",
    is_flag=True,
    default=True,
    help="Enable/Disable colorized logging.",
)
@click.option(
    "--port",
    default=None,
    type=int,
    help="Port to listen on",
)
def server(
    config: str,
    host: str,
    port: int,
    temporal_host: str,
    use_colors: bool,
    log_level: str,
    log_config: str,
) -> None:
    _config = GConfig(config)
    if host:
        _config.server.host = host
    if temporal_host:
        _config.temporalio.host = temporal_host
    if port:
        _config.server.port = port
    if log_level:
        _config.logging.level = log_level
    if log_config:
        _config.logging.log_config = log_config
    if use_colors is not None:
        _config.logging.use_colors = use_colors
    if host:
        _config.conf.server.host = host

    run_server(_config)
